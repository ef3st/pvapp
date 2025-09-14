# Base image
FROM python:3.12-bookworm

# Python/Poetry and network robustness
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/root/.local/bin:${PATH}" \
    # install timeouts/retries
    POETRY_REQUESTS_TIMEOUT=120 \
    POETRY_INSTALLER_MAX_WORKERS=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_NO_CACHE_DIR=1

# --- System deps (HTTPS-ready APT) ---
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg; \
    update-ca-certificates; \
    # make APT a bit more resilient
    printf 'Acquire::Retries "5";\nAcquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n' \
      > /etc/apt/apt.conf.d/99retries; \
    # switch mirrors to HTTPS after CA is present
    if [ -f /etc/apt/sources.list ]; then \
      sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list; \
    elif [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
    fi; \
    apt-get update; \
    # runtime/system libs you need (wkhtmltopdf/pandoc + gfx libs)
    apt-get install -y --no-install-recommends \
        git build-essential \
        libcairo2 libpango-1.0-0 libgdk-pixbuf-2.0-0 fonts-liberation shared-mime-info \
        wkhtmltopdf pandoc; \
    rm -rf /var/lib/apt/lists/*

# --- Poetry (pinned) ---
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION \
 && poetry --version \
 && poetry config installer.max-workers 1

WORKDIR /app

# Copy only dependency metadata first (better layer caching)
COPY pyproject.toml poetry.lock* ./

# --- Export deps from Poetry and install with pip (robust) ---
#   If you use optional groups, you can tweak: --with docs --without dev
RUN set -eux; \
    poetry check || true; \
    poetry export --only main --without-hashes -f requirements.txt -o requirements.txt; \
    python -m pip install --upgrade pip setuptools wheel; \
    python -m pip install --retries 10 --timeout 120 -r requirements.txt

# Now copy the rest of the project
COPY . .

# Streamlit port
EXPOSE 8501

# Since POETRY_VIRTUALENVS_CREATE=false, packages are in the system site-packages:
# you can run Streamlit directly (no need for "poetry run").
CMD ["streamlit", "run", "src/pvapp/main.py", "--logger.level=debug", "gui"]
