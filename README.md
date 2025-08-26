```mermaid
flowchart TD
    A[Streamlit UI<br/>src/pvapp/gui] --> B[Plant Manager & Pages<br/>plant_manager/, pages/, guide/, home/]
    B --> C[PV Simulation (pvlib)<br/>pvlib_plant_model/, simulation/]
    C --> D[Grid Modeling (pandapower)<br/>pandapower_network/, grid/]
    D --> E[Analysis & Validation<br/>analysis/, mount/validated/]
    B --> F[Mount models<br/>mount/development/, mount/validated/]
    E --> G[Plots & Graphics<br/>plots/, utils/graphics/]
    E --> H[Translation & Imaging<br/>translation/, imaging/]
    A --> L[Logs<br/>logs/]
    subgraph Runtime data
      I[data/, logs/]
    end
    A -. config .-> J[backend/ & utils/<br/>md_render.py, feedback_form.py]
    K[tools/<br/>docbuilder.py, logger.py] --> J
    J --> C
    J --> D

```
<!-- [![CI](https://img.shields.io/github/actions/workflow/status/ef3st/pvapp/ci.yml?branch=main&label=CI)](https://github.com/ef3st/pvapp/actions)
[![Coverage](https://img.shields.io/codecov/c/github/ef3st/pvapp?label=coverage)](https://codecov.io/gh/ef3st/pvapp)
[![Last Commit](https://img.shields.io/github/last-commit/ef3st/pvapp)](https://github.com/ef3st/pvapp/commits/main) -->


<!-- > Solar Tracking software for a PV plant. Written in python, the iplant is model with pvlib -->

# 🖼️ Basic Guide to the GUI

*PVApp* is divided in four main pages and two utily pages:
1. ***Home***: (You are here!). Basic commands and a summury of what PVApp does and eventually some important future updaes.
> **Manager and Analyser Pages**
2. ***Plants***: Here you can find main details about the plants grouped in a table. Moreover a map shows you the actual positions of plants. Here you can also add plants, setting basic properties of PV module, inverters and mounting system.
3. ***Plants comparison***: This page provides an overview and detailed comparative analysis of simulation parameters for the PV plants selected by the user. Comparisons can be performed on a seasonal, annual on averaged or summend parameter values, but also on on hourly basis, over a time range that spans either the entire simulation or a user-defined interval.
4. ***Plant Manager***: From this page, it is possible setting the electrical grid of the plant, changing plant setup, both for module and site, and analyses the simulation results both for PV arrays and entire grid. 
  
> **Utility Pages**  
5. ***Guide***: More detailed information on how to use *PVApp*, simulation mechanisms, operation of specialized technical libraries for this purpose and parameter entry can be found in this sectio
>> A tip: When you select this page, the menu in the left sidebar changes, displaying folders and documents related to specific topics. Sometimes, on the first try, selecting a folder below the first one may appear to be blank or inclomplete. In this case:
>> - Open the first folder
>> - Select a displayed document
>> - Finally, try again with the desired starting folder.  
6. ***Logs***: in this page is possible to check for errors, informative and warning messages. Look at the icon of this page to see the status of the App and the presence of messages
In the sidebare (on the left) you can select these pages. With the "⚙️" button but you can also change language and setting the auto-save and auto-simulation options, with which operate these operation at each change in the plant setup. The "🔥 Simulate All", insteand, allow to simulate everything in one shot.

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

 ## 💡 Plant simulation

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
>            custom_notification_box(icon='info', textDisplay=f"Simulation for {plant["name"]} in site {site["name"]} done", externalLink='more info', url='#', styles=styles, key="foo")
>           
