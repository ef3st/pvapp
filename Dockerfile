FROM python:3.12-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VERSION=1.8.3 \
    PATH="/root/.local/bin:${PATH}"

# APT robusto + dipendenze di sistema
RUN set -eux; \
    if [ -f /etc/apt/sources.list ]; then \
      sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list; \
    elif [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
    fi; \
    printf 'Acquire::Retries "5";\nAcquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n' > /etc/apt/apt.conf.d/99retries; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates curl git build-essential \
        libcairo2 libpango-1.0-0 libgdk-pixbuf-2.0-0 fonts-liberation shared-mime-info \
        wkhtmltopdf pandoc \
    ; rm -rf /var/lib/apt/lists/*

# Installa Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION \
 && poetry --version

WORKDIR /app

# Copia i metadati prima per sfruttare la cache
COPY pyproject.toml poetry.lock* /app/

# Installa le dipendenze (senza build del tuo pacchetto)
RUN set -eux; \
    poetry check || true; \
    poetry install --only main --no-interaction --no-ansi --no-root -vvv

# Ora copia il resto del codice
COPY . /app

EXPOSE 8501
CMD ["poetry", "run", "streamlit", "run", "src/pvapp/main.py", "--logger.level=debug", "gui"]
