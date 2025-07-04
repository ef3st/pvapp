# Solartracker ☀️

<!-- [![CI](https://img.shields.io/github/actions/workflow/status/ef3st/solartracker/ci.yml?branch=main&label=CI)](https://github.com/ef3st/solartracker/actions)
[![Coverage](https://img.shields.io/codecov/c/github/ef3st/solartracker?label=coverage)](https://codecov.io/gh/ef3st/solartracker)
[![Last Commit](https://img.shields.io/github/last-commit/ef3st/solartracker)](https://github.com/ef3st/solartracker/commits/main) -->


> Solar Tracking software for a PV implant. Written in python, the iplant is model with pvlib


---

## 🚀 To starty

```bash
# Intall with poetry
poetry install

# Linting with Ruff
poetry run ruff check src/

# Testing + coverage
poetry run pytest --cov=src --cov-report=term