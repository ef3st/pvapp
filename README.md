# Solartracker ☀️

<!-- [![CI](https://img.shields.io/github/actions/workflow/status/ef3st/solartracker/ci.yml?branch=main&label=CI)](https://github.com/ef3st/solartracker/actions)
[![Coverage](https://img.shields.io/codecov/c/github/ef3st/solartracker?label=coverage)](https://codecov.io/gh/ef3st/solartracker)
[![Last Commit](https://img.shields.io/github/last-commit/ef3st/solartracker)](https://github.com/ef3st/solartracker/commits/main) -->


> Solar Tracking software for a PV implant. Written in python, the iplant is model with pvlib


---
# 🖼️ Using GUI

The app is divided in 4 pages:
1. ***Home***: this page. Here you can find a guide to use the app, develop system, simulation and other aspects
2. ***Implants***: Here you can find main details about the implants grouped in a table. Moreover a map shows you the actual positions of implants. Here you can also add (remove is in developing) implants
3. ***Implants comparison***: Here you can select one or more implants and compare a parameter in 4 season or annually (both in mean and sum)
4. ***Implant performance***: here, after selecting ONE implant, you can change settings about tha implant, starting the simulation of the new settings and anylysing results of the simulation in some charateristic plots

In the sidebare (on the left) you can select these pages, but you can also change language and a button in the bottom will start all simulation in one shot

---
# 👨‍💻Programming
> Commands, consideration and phylosophy for developers




## 🚀 To start

```bash
# Intall with poetry
poetry install

# Linting with Ruff
poetry run ruff check src/

# Testing + coverage
poetry run pytest --cov=src --cov-report=term
```
---

 ## 💡 Implant simulation

1. Define Site Location
2. Create Time Series
3. Retrieve or Define Weather Data
4. Define the PV System:
    a. Module
    b. Inverter
    c. Mount (Fixed or Tracking)
    d. Temperature model
5. Instantiate ModelChain
6. Run Simulation
7. Analyze / Visualize Results