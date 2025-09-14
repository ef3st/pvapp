.PHONY: help install shell run dev run-cli build compose-build up down logs restart fmt lint test check docs clean tidy

# ===========================
#            Config
# ===========================
# Override these at call time, e.g.:
#   make run PORT=8601 ENTRY=src/pvapp/ui/app.py
PY           ?= poetry run
ENTRY        ?= src/pvapp/main.py                  
PORT         ?= 8501
ENV          ?= development
TZ           ?= Europe/Rome

# Docker/Compose executables (override if needed)
DOCKER       ?= docker
COMPOSE      ?= docker compose

# ===========================
#         Basic setup
# ===========================
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Common targets:"
	@echo "  install         Install project dependencies with Poetry"
	@echo "  shell           Activate Poetry shell"
	@echo "  run             Run Streamlit app (ENTRY=$(ENTRY), PORT=$(PORT))"
	@echo "  dev             Alias of run (explicit local dev)"
	@echo "  run-cli         Run pvapp CLI entrypoint (poetry script)"
	@echo "  fmt             Format code (black)"
	@echo "  lint            Lint code (ruff)"
	@echo "  test            Run tests (pytest)"
	@echo "  check           Lint + Test"
	@echo "  docs            Build docs with pdoc"
	@echo "  build           Build Docker image pvapp:latest"
	@echo "  compose-build   Build services via Docker Compose (no cache)"
	@echo "  up              Start services via Docker Compose (detached)"
	@echo "  down            Stop services via Docker Compose"
	@echo "  logs            Tail Compose logs"
	@echo "  restart         Restart Compose services"
	@echo "  clean           Remove caches and temporary files"
	@echo "  tidy            fmt + lint + test"
	@echo ""

install:
	poetry install

shell:
	poetry shell

# ===========================
#           Run
# ===========================
run:
	$(PY) streamlit run $(ENTRY)  --logger.level=debug gui --server.port=$(PORT) --server.address=0.0.0.0
	

dev: run

# Run the Poetry console script defined in pyproject:
# [tool.poetry.scripts] pvapp = "pvapp.main:main"
run-cli:
	$(PY) pvapp

# ===========================
#         Docker / Compose
# ===========================
build:
	$(DOCKER) build -t pvapp:latest .

compose-build:
	$(COMPOSE) build --no-cache

up:
	ENV=$(ENV) TZ=$(TZ) PORT=$(PORT) $(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

restart:
	$(COMPOSE) down && ENV=$(ENV) TZ=$(TZ) PORT=$(PORT) $(COMPOSE) up --build -d

# ===========================
#        Quality & Docs
# ===========================
fmt:
	$(PY) black .

lint:
	$(PY) ruff check .

test:
	$(PY) pytest

check: lint test

docs:
	$(PY) pdoc -o docs src/pvapp

# ===========================
#           Clean
# ===========================
clean:
	find . -name "__pycache__" -type d -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache

tidy: fmt lint test
