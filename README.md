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

# Simulations
>‼️ **FUTURE UPDATE**: 
> - Verrà implementata anche la possibilità di gestire stringhe di pannelli e settare anche l'altezza da terra
> - Attraverso le cordiante dei vertici del terreno e della posizione e dimensione dei pannelli, si potrà memorizzare e visualizzare sulla mappa l'estensione dell'impianto e rendere automatica il settaggio di alcuni parametri
> - In ottica di sviluppo di questa app come monitoraggio, sarà possibile visualizzare anche lo stato dei pannelli sulla mappa in base ai dati in input (sia in simulazione, che magari nella realtà)
> NOTE: Nei grafici della simulazione "stagionali" dove si mostrano somme e medie, vengono considerati anche gli 0 della "notte", quindi la media è oggettivamente più bassa di quella effettiva

# Modules - Inverters parameters:
#### 1. **CEC (California Energy Commission) database**
##### ⚠️ ***MODULE***
 | Parameter    | Description                                      | Unit    | Example Value* |
 | ------------ | ------------------------------------------------ | ------- | -------------- |
 | `Technology` | Cell type (e.g., mono, multi, thin film)         | -       | Multi-c-Si     |
 | `Bifacial`   | Indicates bifacial design (1 = yes, 0 = no)      | Boolean | 0              |
 | `STC`        | Rated power at STC (1000 W/m², 25°C, AM1.5)      | W       | 224.99         |
 | `PTC`        | Rated power under PVUSA Test Conditions          | W       | 193.5          |
 | `A_c`        | Module area                                      | m²      | 1.624          |
 | `Length`     | Length of the module                             | m       | 1.632          |
 | `Width`      | Width of the module                              | m       | 0.995          |
 | `N_s`        | Number of cells in series                        | -       | 60             |
 | `I_sc_ref`   | Short-circuit current at STC                     | A       | 8.04           |
 | `V_oc_ref`   | Open-circuit voltage at STC                      | V       | 36.24          |
 | `I_mp_ref`   | Current at maximum power point at STC            | A       | 7.44           |
 | `V_mp_ref`   | Voltage at maximum power point at STC            | V       | 30.24          |
 | `alpha_sc`   | Temperature coefficient of *I_sc*                | A/°C    | 0.004406       |
 | `beta_oc`    | Temperature coefficient of *V_oc*                | V/°C    | -0.131334      |
 | `T_NOCT`     | Nominal Operating Cell Temperature               | °C      | 50.2           |
 | `a_ref`      | Modified ideality factor                         | -       | 1.671782       |
 | `I_L_ref`    | Light-generated current at reference conditions  | A       | 8.047206       |
 | `I_o_ref`    | Diode saturation current at reference conditions | A       | 0.0            |
 | `R_s`        | Series resistance                                | Ohm     | 0.14737        |
 | `R_sh_ref`   | Shunt resistance at reference                    | Ohm     | 164.419479     |
 | `Adjust`     | Empirical correction factor (CEC model)          | %       | 20.698376      |
 | `gamma_r`    | Power temperature coefficient                    | %/°C    | -0.5196        |
 | `BIPV`       | Building Integrated PV indicator                 | Yes/No  | N              |
 | `Version`    | Database version                                 | -       | SAM 2018.11.11 |
 | `Date`       | Entry date                                       | -       | 1/3/2019       |

*A10Green_Technology_A10J_M60_225 is used as example
> #### NOTE:
> - I parametri a_ref, I_L_ref, I_o_ref, R_s, R_sh_ref, Adjust sono usati nel single-diode model, il più dettagliato in pvlib.
> - Il parametro gamma_r è spesso usato nel PVWatts model, come semplificazione.
> - Le efficienze e perdite degli inverter si calcolano con i coefficienti C0, C1, C2, C3, e Pso secondo la formula CEC efficiency model.  

##### 🔌 ***INVERTER***: 
### ‼️ Not valid for simulations
| Parameter | Description                                         | Unit  | Example Value* |
| --------- | --------------------------------------------------- | ----- | -------------- |
| `Vac`     | Rated AC output voltage                             | V     | 208.0 V        |
| `Paco`    | Maximum AC output power                             | W     | 250.0 W        |
| `Pdco`    | Nominal DC input power                              | W     | 259.6 W        |
| `Vdco`    | Nominal DC voltage                                  | V     | 40.0 V         |
| `Pso`     | Power consumed at night (standby losses)            | W     | 0.364 W        |
| `C0`      | Coefficient 0 (efficiency polynomial)               | 1/W   | -1.153e-05     |
| `C1`      | Coefficient 1 (efficiency polynomial)               | 1/V   | 0.00023052     |
| `C2`      | Coefficient 2 (efficiency polynomial)               | 1/W²  | -1.104e-06     |
| `C3`      | Coefficient 3 (efficiency polynomial)               | 1/W·V | 1.523e-05      |
| `Pnt`     | Night-time tare loss (power consumed with no input) | W     | 0.25 W         |
| `Eta_max` | Maximum efficiency (not always listed)              | %     | 95.5 %         |.

*ABB__MICRO_0_25_I_OUTD_US_208__208V_ is used as example

#### 2. **SandiaMod (Sandia Module) Database**
| Parameter              | Description                                                | Unit | Example* |
| ---------------------- | ---------------------------------------------------------- | ---- | -------- |
| `Vintage`              | Year of characterization                                   | -    | 2006     |
| `Area`                 | Aperture area of the module                                | m²   | 1.312    |
| `Material`             | Technology (e.g., mc-Si = multi-crystalline silicon)       | -    | mc-Si    |
| `Cells_in_Series`      | Number of cells connected in series                        | -    | 72       |
| `Isco`                 | Short-circuit current at reference conditions              | A    | 5.564    |
| `Voco`                 | Open-circuit voltage at reference                          | V    | 42.832   |
| `Impo`                 | Current at MPP                                             | A    | 5.028    |
| `Vmpo`                 | Voltage at MPP                                             | V    | 32.41    |
| `Aisc, Aimp`           | Temperature coefficients of Isc and Imp                    | A/°C | ≈0.0005  |
| `Bvoco, Bvmpo`         | Temp. coefficients of Voc and Vmp                          | V/°C | ≈-0.17   |
| `C0, C1, C2, C3`       | Empirical fit coefficients for irradiance dependence       | -    |          |
| `A0–A4, B0–B5`         | Coefficients for angle of incidence response               | -    |          |
| `DTC`                  | Delta T cell-temp to air-temp offset (for SAPM temp model) | °C   | 3.0      |
| `FD`                   | Diffuse fraction derate factor                             | -    | 1.0      |
| `IXO, IXXO`            | Empirical fitting params                                   | A    |          |
| `C4, C5, C6, C7`       | Misc. coefficients for MPP estimation                      | -    |          |

*Advent_Solar_AS160___2006_ is used as example

> #### NOTE
> Il Sandia Module Model è un modello empirico e ad alta fedeltà, basato su curve IV misurate realmente in laboratorio in varie condizioni di irradianza e temperatura.
> I parametri che vedi sono curve fitting coefficients che permettono a pvlib di calcolare:
> - Corrente e tensione ai punti operativi (MPP, Voc, Isc, ecc.)
> - Variazioni dovute a temperatura e irradianza
> - Efficienza, fattori angolari, derating, ecc.

#### 3. **Custum parameters**
- Moudule: {
    pdc0: nominal power of the module (DC) in Watts at STC (Standard Test Conditions: 1000 W/m², 25°C, AM1.5) 
         -> It is the maximum power that the module can generate under ideal conditions. e.g. a 400 Wp module → pdc0 = 400
    γ_pdc: temperature coefficient of power, in 1/°C 
         -> It tells you how much the module loses in power for each degree above 25°C (STC). It is assumed negative, because efficiency decreases as the temperature increases 
            (‼️ SO DON'T FORGET TO PUT MINUS WHEN USE IT IN THIS APP)
            e.g. γ_pdc = -0.004   → -0.4% per °C
}
- Inverter: {
    pdc0: nominal DC input power of the inverter, in Watts.
         -> It is the reference value on which the efficiency of the inverter and the clipping are evaluated. 
}

‼️ **FUTURE UPDATE** Verrà implementato a breve ANCHE il parametro *eta_inv_nom* nell'inverter, cioè la Nominal inverter efficiency (normalmente circa 96%). Al momento l'efficienza potrebbe essere assunta come 1.0 (MOLTO IRREALISTICO, ma la simulazione per ora si concentra su analisi pre-inverter)
> NOTE: Per simulazioni più realistiche (con CEC inverter model) bisognerà considerare
> | Parametro | Descrizione                                | Esempio    |
> | --------- | ------------------------------------------ | ---------- |
> | `pdc0`    | Nominal DC input power \[W]                | 5200       |
> | `paco`    | Max AC output power \[W]                   | 5000       |
> | `ps0`     | Night/standby losses \[W]                  | 1.0        |
> | `c0 - c3` | Coefficienti del modello di efficienza CEC | vedi sotto |
> ```python
> inverter_parameters = {
>     'pdc0': 5200,
>     'paco': 5000,
>     'ps0': 1.0,
>     'c0': 0.0001,
>     'c1': 0.001,
>     'c2': 0.00001,
>     'c3': 0.000005
> }
> ```
---
# Mount System
#### 1. Fixed

|   **Parameter**    | **GUI selection name** | **Desription**                                                                                 |
| ------------------ | ---------------------- | ---------------------------------------------------------------------------------------------- |
| `surface_tilt`     | Tilt                   | (in degrees) Angle of inclination wrt the vertical (0 -> panel parallel to the soil)           |
| `surface_azimuth`  | Azimuth                | (in degrees) Angle of rotation wrt the North (0 -> when tilt > 0, panel surface points north)  | 
#### 2. SingleAxisTrackerMount 
|   **Parameter**    | **GUI selection name**     | **Desription**                                                                                                |
| ------------------ | -------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `azis_tilt`        | Tilt                       | (in degrees) Angle of inclination wrt the vertical (0 -> panel parallel to the soil)                          |
| `azis_azimuth`     | Azimuth                    | (in degrees) Angle of rotation wrt the North (0 -> when tilt > 0, panel surface points north)                 | 
| `max_angle`        | Max Angle inclination      | (in degrees) Maximum angle that the panel can cover (45 -> if tilt = 0, panel can cover ±45°)                 | 
| `cross_axis_tilt`  | Surface Angle              | (in degrees) Angle of soil inclination to consider in tracking system (0 -> soil is horizonatal               | 
| `gcr`              | Ground Surface Ratio       | (pure number) Ratio between area covered by panel and total area aviable (must be 0 < gcr ≤ 1)                | 
| `backtrack`        | Avoid shadings (backtrack) | (bool) If selected (True), the sistem moves panel avoiding that panes cover others (computed on base of *cr*) |
#### 3. ValidatedMount
At this moment same as in [SingleAxisTrackerMount](#2-singleaxistrackermount)
#### 4. DevelopementMounts
At this moment same as in [SingleAxisTrackerMount](#2-singleaxistrackermount)

---
# ➡️ OUTPUT SIMULATION DATA

| **Variable**           | **Description**                                            | **Unit** | **Source Function**      | **Example values** |
| ---------------------- | ---------------------------------------------------------- | -------- | ------------------------ | ------------------ |
| `poa_global`           | Plane-of-array global irradiance (direct + diffuse)        | W/m²     | `get_total_irradiance`   | 950.0              |
| `poa_direct`           | Direct irradiance on the plane of array                    | W/m²     | `get_total_irradiance`   | 750.0              |
| `poa_diffuse`          | Diffuse irradiance on the plane of array                   | W/m²     | `get_total_irradiance`   | 200.0              |
| `aoi`                  | Angle of incidence between sun and module surface          | degrees  | `get_total_irradiance`   | 10.3               |
| `effective_irradiance` | Irradiance adjusted for AOI and spectral losses            | W/m²     | `sapm`                   | 920.0              |
| `v_mp`                 | Voltage at maximum power point                             | V        | `sapm, single_diode`     | 30.5               |
| `i_mp`                 | Current at maximum power point                             | A        | `sapm, single_diode`     | 7.8                |
| `p_mp`                 | Power at maximum power point                               | W        | `sapm, single_diode`     | 237.9              |
| `i_sc`                 | Short-circuit current                                      | A        | `sapm, single_diode`     | 8.1                |
| `v_oc`                 | Open-circuit voltage                                       | V        | `sapm, single_diode`     | 39.8               |
| `diode_voltage`        | Voltage across the internal diode                          | V        | `single_diode`           | 0.6                |
| `shunt_current`        | Current lost due to shunt resistance                       | A        | `single_diode`           | 0.01               |
| `temp_cell`            | PV cell temperature                                        | °C       | temperature model        | 45.0               |
| `temp_module`          | Module backside temperature                                | °C       | temperature model        | 43.0               |
| `dc_power`             | DC output power from module/system                         | W        | `ModelChain, PVSystem`   | 240.0              |
| `ac_power`             | AC output power after inverter                             | W        | `ModelChain, PVSystem`   | 230.4              |
| `losses`               | Total system loss factor (optional, if modeled)            | %        | `ModelChain, PVSystem`   | 0.14               |
| `zenith`               | Solar zenith angle                                         | degrees  | `solarposition`          | 35.0               |
| `azimuth`              | Solar azimuth angle                                        | degrees  | `solarposition`          | 150.0              |
| `airmass`              | Relative air mass (optical path length through atmosphere) | -        | `solarposition`          | 1.8                |
| `clearsky_ghi`         | Global horizontal irradiance (clearsky model)              | W/m²     | `clearsky`               | 1020.0             |
| `clearsky_dni`         | Direct normal irradiance (clearsky model)                  | W/m²     | `clearsky`               | 880.0              |
| `clearsky_dhi`         | Diffuse horizontal irradiance (clearsky model)             | W/m²     | `clearsky`               | 140.0              |

> NOTE
> Some variables may not appear depending on the model used (e.g., sapm, single_diode, or pvwatts).
> Use ModelChain or PVSystem objects to get standardized outputs across models.

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