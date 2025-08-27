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




# Simulation Setup
>‼️ **FUTURE UPDATE**: 
> - Verrà implementata anche la possibilità di gestire stringhe di pannelli e settare anche l'altezza da terra
> - Attraverso le cordiante dei vertici del terreno e della posizione e dimensione dei pannelli, si potrà memorizzare e visualizzare sulla mappa l'estensione dell'impianto e rendere automatica il settaggio di alcuni parametri
> - In ottica di sviluppo di questa app come monitoraggio, sarà possibile visualizzare anche lo stato dei pannelli sulla mappa in base ai dati in input (sia in simulazione, che magari nella realtà)
> NOTE: Nei grafici della simulazione "stagionali" dove si mostrano somme e medie, vengono considerati anche gli 0 della "notte", quindi la media è oggettivamente più bassa di quella effettiva