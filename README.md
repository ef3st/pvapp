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
---




---
---
# 👨‍💻Programming
> Commands, consideration and phylosophy for developers




## 🚀 To start

```bash
# run streamlit
make streamlit

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

# PV system modelling software package 
https://www.researchgate.net/publication/313249264_PHOTOVOLTAIC_SYSTEM_MODELLING_USING_PVLIB-PYTHON

PVLib has been choosen since it is a well-kwon commercially aviable package. This toolbox is a standard repository for high quality PV system modelling and analysis algorithms, continuosly and collaboratively developed and validated. Its code is open-source and this has been manipulated to create, test and simulate di mounting system for which this project was born.

PVLib is a product of the collaborative group of PV professionals, PV Performance Modelling Collaborative (PVPMC), facilitated by Sandia Laboratories.
### Modelling steps (NOT FINISHED)
![Logo](https://www.researchgate.net/profile/Arnold-Rix/publication/313249264/figure/fig1/AS:457596613206016@1486110942064/PVLib-workflow-chart.png)
1. *Wether and design*: collection of weather data of the desidered site and details of the orientation and set up of the array.
2. *DC module IV characteristics*: modelling of PV module behaviour according to its V characteristics depending on the prevailing conditions and module model.
3. *DC array IV*: projecting the likely behaviour of PV modules are combined into an array; paying particular attention to DC wiring losses and  mismatch effects.
4. *DC to AC conversion* - estimating DC-AC conversion efficiency using a variety of model algorithms. DC-AC conversion allows the solar power to be tied to the grid.
5. *AC system output* - determining and accounting for all the energy losses on the AC side before the utility meter. 
These steps are incorporated by the PVLib toolbox using modular programming and the source code is grouped into ten modules namely: tools, tmy, location, solar position, atmosphere, modelchain, tracking, irradiance, clear sky and pv system (http://pvlibpython.readthedocs.io/en/latest/modules.html)

...


> ‼️ Future update:
> - Notifiche con streamlit-custom-notification-box (https://github.com/Socvest/streamlit-custom-notification-box): 
>```python
>  styles = {'material-icons':{'color': 'red'},
>                      'text-icon-link-close-container': {'box-shadow': '#3896de 0px 4px'},
>                      'notification-text': {'':''},
>                      'close-button':{'':''},
>                      'link':{'':''}}
>
>            custom_notification_box(icon='info', textDisplay=f"Simulation for {implant["name"]} in site {site["name"]} done", externalLink='more info', url='#', styles=styles, key="foo")
>           