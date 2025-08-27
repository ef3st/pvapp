
# PVApp 
#### ***The Photovoltaic Plant Simulator and Analyser***  

![Python](https://img.shields.io/badge/python-3.10-blue.svg) ![Pandapower](https://img.shields.io/badge/pandapower-%3E=2.14-blue?logo=python&logoColor=white) ![pvlib](https://img.shields.io/badge/pvlib-%3E=0.13-green?logo=python&logoColor=white)
<!-- 
 [![Docs](https://img.shields.io/badge/docs-latest-blue)](https://pvlib-python.readthedocs.io/) [![Docs](https://img.shields.io/badge/docs-streamlit.dev-blue)](https://docs.streamlit.io/)   -->

<!-- [![Last Commit](https://img.shields.io/github/last-commit/ef3st/solartracker)](https://github.com/ef3st/solartracker/commits/main)   -->
>
An accademic photovoltaic systems and grids simulator based on `pvlib` and `pandapower` packages. Created in python in the backend and a *user friendly* **GUI** (written thanks to `streamlit` package) is aviable to create and manage projects simulator. 


# Table of Contents
- [Introduction](#introduction)
- [Architecture](#architecture)
  - [Plant Data](#plant-data)
  - [More Information](#more-information)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Run & Deployment](#run--deployment)
- [Testing](#testing)
- [Documentation](#documentation)
- [Author](#author)


---

# Introduction  

PVapp was originally created to design and optimize a solar tracker, a mechanical (or electromechanical) system that orients photovoltaic (PV) panels to maintain the best possible incidence angle with sunlight. Over time, the project evolved into a broader platform for simulating and testing solutions within PV systems, including their integration into more complex electrical networks.  

The main goal of PVapp is to provide users with a powerful, flexible, and transparent tool to **simulate** how design choices, modifications, or innovative technologies can affect the performance of both the PV system and the electrical grid it connects to.  

With the graphical interface (GUI), users can easily set up a project (the *Plant*) by defining:  
- the geographical information of the installation (*Site*),  
- the technical features of PV modules (*Module*),  
- and the inverter characteristics (*Inverter*).  
>
Since PVapp runs in a local web environment, it is compatible with all operating systems.  
In the documentation, users can also learn how a *Plant* is stored. Although it is technically possible to create configuration files manually, this is not recommended: the GUI was designed both as a simplification for non-Python users and as a safeguard against configuration errors that may lead to unreliable results.  

PVapp continues to improve, and users are welcome to suggest enhancements through the dedicated feedback form available in the left sidebar.  

>
---  

# Architecture
The code of the project is located in `/src/pvapp` divided in 4 parts:
- `/backend`: this contains all classes, functions and possible configurations files for create and manage a project (named *Plant*).  
  Simulation is managed by Simulator class in `/simulation/simulator.py` that has the role to integrate computations from `pvlib`(mean) and `pandapower` package (by means of `PVSystemManager` and `PlantPowerGrid` classes, saved in `/pvlib_plant_model` and `/pandapower_network` respectively) in a single `pandas.DataFrame` managed by a dedicated manager class defined in the `/pvapp/analysis/database.py`.  
- `/analysis`: the folder contains classes and functions to write, read and manage the results from simulations saved in `.csv` files and loaded into `pandas.DataFrame` object into the class saved in `/database.py`
- `/gui`: here the app is built with `streamlit` package.  
  Each page behaves differently from the other but with some specific function needs. So a class `Page` has been created, mainly to handle translation and common page features setup. Each Page is a class saved in the dediucated folder inside `/pages`. the structure and constraints of pages derive directly from backend requirements.  
- `/tools`: the app need some utility functions and helper classes decoupled from the simulation and frontend logic. They are saved here.  
  An example is the central logger important to check the correct behavior of the app.  
>
### *Plant* Data
All simulation input and output data are stored in the folder `/data`: each  *Plant* is saved in a folder named with a progressive number.  Data for a plant simulation are saved in four .json format files:
- plant.json: module and inverteres parameters, mount type and plant name are saved here-;  
- site.json: this contain the site name, with its coordinates, time zone, address and altitude;  
- arrays.json: if the system has more than one module, the PV arrays are saved here;  
- grid.json: `pandapower` gives the possibility to save grid params in a json file. This is the result of `pandapower.to_json()` function.  
Simulation results with both `pvlib` and `pandapower` data are exported and stored in `/data/.../simulation.csv`.
> ⚠️ Note: currently no backup system is implemented, so handle the /data directory with care.
>
#### More information  
For more details, check the documentation in `/docs` folder or in the PVApp from *Guide* page.
Developer is working to create a better pre-configuration setup with TOML.

```bash
.
├── .github/                 # CI (GitHub Actions)
├── data/                    # plant projects files, both setup and simulation results
│   ├──0/
│   │  ├── plant.json     # Module and inverter properties
│   │  ├── site.json      # plant site infos
│   │  ├── arrays.json    # arrays of PV module in the plant (if created)
│   │  ├── grid.json      # connection grid (if created)
│   │  └── simulation.csv # simulation result in a .csv file
│   ├──1/
│   └── ...
├── docs/                    # documentation
├── notebooks/               # experiments and specific analysis
├── src/
│   └── pvapp/
│       ├── analysis/          # results analysis, metrics and post processingì
│       ├── backend/           # simulator, `pvlib` and `pandapower` managers, mounting systems
│       │   ├── mount/
│       │   │   ├── development/    # model in developing
│       │   │   └── validated/      # validated mount system
│       │   ├── pandapower_network/ # models and utils to simulate grid with pandapower
│       │   ├── pvlib_plant_model/  # models and utils to simulate  modules with pvlib
│       │   └── simulation/         # PV/grid simulation orchestration
│       ├── gui/                 # Streamlit app
│       │   ├── i18n/            # languages json files
│       │   ├── pages/           # pages in the app
│       │   │   ├── home/          
│       │   │   ├── plants/            # CRUD all plants
│       │   │   ├── plants_comparison/ # Plants performance simulated comparison
│       │   │   ├── plant_manager/ # UI plant, module, grid management
│       │   │   │   ├── grid/      # mainly related to pandapower features
│       │   │   │   ├── module/    # mainly related to pvlib features
│       │   │   │   └── site/      
│       │   │   ├── guide/         # guide, documentation and suggestions
│       │   │   └── logs/          # viewer/log console
│       │   └── utils/             # utilità condivise
│       │       ├── graphics/      # graphics utilities 
│       │       │   ├── feedback_form.py
│       │       │   └── md_render.py   # render markdown/HTML for streamlit
│       │       ├── plots/             # plot generator
│       │       └── translation/       # translator funtion
│       ├── tools/
│       │   ├── documentation/   # pdf guide generator
│       │   └── logger.py        # central logger/CLI
│       └── main.py            # entrypoint tool
├── tests/                   # unit/integration tests (pytest, coverage)
├── streamlit/               # config Streamlit (theme, secrets, ecc.)
├── pyproject.toml           # Poetry + tool configs (ruff/pytest/coverage)
└── README.md
```


---

# Installation


--- 
# Usage
    
---
# Configuration

---
# Run & Deployment

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
# Testing

---
# Documentation

---
# Author
Lorenzo Pepa



