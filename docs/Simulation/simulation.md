 # 💡 Plant simulation

---

# Photovoltaic Simulations with pvlib

## Theory: what a PV performance model does

A grid-connected PV simulation predicts AC power at the point of interconnection from weather and system specs. The pipeline, conceptually:

1) **Solar geometry**  
   - Compute the sun’s **apparent position**: zenith, elevation, azimuth.  
   - Depends on timestamp, latitude/longitude, and time zone.

2) **Irradiance at ground (GHI/DNI/DHI)**  
   - From **meteorological inputs** (e.g., measured GHI/DNI/DHI) or a **clear-sky model** (e.g., Ineichen) plus transmittance / turbidity estimates.  
   - Components:
     - **DNI** (beam normal): collimated beam from the solar disk.  
     - **DHI** (diffuse horizontal): scattered sky.  
     - **GHI** (global horizontal): \( \mathrm{GHI} = \mathrm{DNI}\cdot\cos(\theta_z) + \mathrm{DHI} \).

3) **Plane-of-array (POA) irradiance (tilted surface)**  
   - Project the sky onto the module plane.  
   - **Transposition models** map (DNI, DHI, GHI) to **POA_beam**, **POA_sky diffuse**, **POA_ground-reflected** using sky diffuse models (Hay–Davies, Perez, Isotropic, etc.) and **albedo** for ground reflection.  
   - Tracker kinematics (for single-axis or dual-axis) adjust the plane orientation in time; **backtracking** reduces row-to-row shading using **GCR**.

4) **Angle-of-incidence (AOI) & optical losses (IAM)**  
   - The effective irradiance on the glass is reduced as AOI grows.  
   - **IAM** models (ASHRAE, Martin–Ruiz, SAPM IAM) correct POA-beam for reflection losses.  
   - **Soiling**, **snow**, and **mismatch** losses are typically handled as multiplicative derates if not explicitly modeled.

5) **Spectral & air mass effects (optional)**  
   - Module response is wavelength-dependent; **spectral mismatch** corrections (e.g., SAPM spectral loss vs. airmass & precipitable water) refine the **effective irradiance**.

6) **Cell/module temperature**  
   - Cell temperature depends on POA irradiance, ambient temperature, wind speed, mounting config.  
   - Models: **NOCT/PNOCT**, **Faiman**, **SAPM temperature**.  
   - Temperature affects IV curve parameters and thus DC power.

7) **DC performance model**  
   - **Empirical models**: **SAPM** (Sandia Array Performance Model) uses fitted coefficients from lab IV curves across irradiance/temperature.  
   - **Physics-based single-diode models**: **De Soto/CEC**, **PVsyst**, etc. Compute IV curve via a 5-parameter diode equation; solve max power point (MPP).  
   - Output: \( P_{dc} \), \( V_{mp} \), \( I_{mp} \), etc. Optionally clip to **inverter DC limits**.

8) **Inverter & AC-side**  
   - Map DC operating point to AC using inverter efficiency curves: **CEC/Sandia/ADR** inverter models or **PVWatts** simplified conversion.  
   - Account for **clipping** (AC nameplate), **night tare losses**, optional **power factor/Q** strategies, and wiring/transformer losses if modeled.

9) **Aggregation & results**  
   - Sum over strings/arrays/inverters; produce timeseries \( P_{ac}(t) \), energy (Wh), and derived KPIs (performance ratio, specific yield, capacity factor, etc.).

---

> ## How the code mirrors the theory
> 
> ###  Core building blocks
> 
> ```python
> import pvlib
> from pvlib.location import Location
> 
> site = Location(latitude=44.50, longitude=11.35, tz="Europe/Rome", altitude=50)
> times = pd.date_range(start="2024-07-01 00:00", end="2024-07-07 23:00", freq="1h", tz=site.tz)
> solar_pos = site.get_solarposition(times)
> 
> # Clear-sky as fallback
> clearsky = site.get_clearsky(times, model="ineichen")  # DNI, GHI, DHI
> ```
> 
> ### Minimal end-to-end example
> 
> ```python
> import pandas as pd
> from pvlib.location import Location
> from pvlib.pvsystem import PVSystem, retrieve_sam
> from pvlib.modelchain import ModelChain
> 
> # Site & time
> site = Location(44.50, 11.35, 'Europe/Rome', altitude=50)
> times = pd.date_range('2024-06-01', '2024-06-07', freq='15min', tz=site.tz)
> solpos = site.get_solarposition(times)
> weather = site.get_clearsky(times, 'ineichen')  # replace with measured data
> weather['temp_air'] = 25.0
> weather['wind_speed'] = 1.0
> 
> # Components (CEC)
> cec_modules = retrieve_sam('CECMod')
> cec_inverters = retrieve_sam('cecinverter')
> module = cec_modules.iloc[0]
> inverter = cec_inverters.iloc[0]
> 
> system = PVSystem(
>     surface_tilt=28, surface_azimuth=180,
>     module_parameters=module,
>     inverter_parameters=inverter,
>     temperature_model_parameters={'a': -3.47, 'b': -0.0594, 'deltaT': 3},
>     modules_per_string=12, strings_per_inverter=3, albedo=0.2
> )
> 
> mc = ModelChain(
>     system, site,
>     transposition_model='haydavies',
>     aoi_model='sapm', spectral_model='no_loss',
>     temperature_model='sapm',
>     dc_model='cec', ac_model='sandia'
> )
> 
> mc.run_model(weather)
> ac_power = mc.results.ac  # W
> energy = ac_power.resample('1D').sum()/1000  # kWh per day
>```





# PV system modelling software package 

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


# Documentation
Gurupira, Tafadzwa & Rix, Arnold. (2016). PHOTOVOLTAIC SYSTEM MODELLING USING PVLIB-PYTHON. ![link](https://www.researchgate.net/publication/313249264_PHOTOVOLTAIC_SYSTEM_MODELLING_USING_PVLIB-PYTHON)



# Simulation Setup
>‼️ **FUTURE UPDATE**: 
> - Verrà implementata anche la possibilità di gestire stringhe di pannelli e settare anche l'altezza da terra
> - Attraverso le cordiante dei vertici del terreno e della posizione e dimensione dei pannelli, si potrà memorizzare e visualizzare sulla mappa l'estensione dell'impianto e rendere automatica il settaggio di alcuni parametri
> - In ottica di sviluppo di questa app come monitoraggio, sarà possibile visualizzare anche lo stato dei pannelli sulla mappa in base ai dati in input (sia in simulazione, che magari nella realtà)
> NOTE: Nei grafici della simulazione "stagionali" dove si mostrano somme e medie, vengono considerati anche gli 0 della "notte", quindi la media è oggettivamente più bassa di quella effettiva
