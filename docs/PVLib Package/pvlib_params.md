# Elements of a PV Array
In order to simulate a *PV* sistem, four are the elements to know:
- ***Module***

> This is the core of simulation. Many parameters define the performance and characteristics of a PV module. To semplify the user's task, it is possible to select a pre-defined module present in the California Energy Commission (CEC) [database](https://www.energy.ca.gov/media/2367) and [SAM](https://zenodo.org/records/14173605) also avilable in a dedicated SAM GitHub [repository](https://github.com/NREL/SAM/tree/develop/deploy/libraries). The parameters from [CEC](#module) and [SAM](#2-sandia-mod-sandia-module-database) modules are described in detail below. 
> Since only a few parameters are essentials for simulations, and databases are not always updated with the latest models, so it is possible to define also a "custom" module by specifying only the ***nominal DC input power***(`pdc0`, in Watt) and the ***power temperature coefficient*** (`gamma_r`, in %/°C, the percentage of power lost in production for each degree above 25°C). [Future-updates](#future-updates)

- ***Inverter***
> Solar modules generate **Direct Current** (**DC**), but homes, appliances and the grid require **Alternating Current** (**AC**). So inverters are necessary in PV systems. These devices, adjust the voltage and frequency of the AC output in order to match the grid standards (e.g. 230V, 50Hz in Europe). 
> In addition, inverters continuosly tracks the **maximum power point** (**MPPT**) of the PV module to maximize energy extraction under varying irradiance and temperature condition. Considering the high variability and potential electrical faults that can occur to a PV system, inverters also provide sessential safeguards against overvoltage, short circuits and ground faults. They include *anti-islanding protection*, which automatically disconnects the PV system during grid outage. [Future-updates](#future-updates)
- ***Mounting***
> The mounting system defines the mechanical installation of PV modules, determining their tilt, orientation, and, where avible, the tracking of the sun. In the most common use case, modules are installed at a fixed tilt and orientation, optimized for the site latitude to maximize annual energy production. More advanced systems adopt single-axis or dual-axis trackers, which continuously adjust the module angle to follow the sun’s position, thus increasing energy yield but at higher cost and complexity.
In `pvlib`, mounting configurations are modeled through the pvlib.pvsystem.Mount classes, which provide tools to simulate both ***fixed-tilt*** and ***tracking systems***. The library implements typical functions such as `FixedMount`, `SingleAxisTrackerMount`, allowing the user to evaluate the impact of mounting choice on irradiance collection and overall PV performance.  [Future-updates](#future-updates)
- ***Arrays***
> Individual PV modules are almost never connected to a single inverter. By connecting multiple modules, it is possible to optimize the overall system voltage, current and power. `pvlib` accounts for this providing methods to simulate arrays defined by the number of modules connected in series (forming a *string*) and the number of strings connected in parallel. the advantages are many:
> + *Series*: connecting modules in series increases the total voltage - summing the module's voltages - mantaining the same current and so allowing the system to reach the inverter's operating voltage window (typically several hundred volts).
> + *Parallel*: connecting strings in parallel increases the total current while keeping the voltage constant, thereby raising the overall system power.
 The  More then one module connected to a string allow to reach the operating input voltage of the inverter (usually hundreds of V) summing the single voltages; while connecting modules in parralle allows to increase the the currents in single branchses increasing then the total power leaving the voltage constant. 
>> Note: even though this structure is managed by `pvlib`, in this App, the input of *module-per-string* number and the *number-of-string* are set withn the grid section. The inverter output then acts as an input to the grid calculus

---
# Paramterers


## Modules And Inverters parameters:
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
> - `a_ref`, `I_L_ref`, `I_o_ref`, `R_s`, `R_sh_ref`, `Adjust` parmas are used in the single-diod model, the most detailed in `pvlib`.
> - `gamma_r` is usually used in the PVWatts model, as simplification.
> - The efficiencies and losses of the inverters are calculated with the coefficients C0, C1, C2, C3, and Pso according to the CEC efficiency model formula:
> ```python
> A = Pdco * (1 + C1 * (v_dc - Vdco))
> B = Pso * (1 + C2 * (v_dc - Vdco))
> C = C0 * (1 + C3 * (v_dc - Vdco))
> 
> power_ac = (Paco / (A - B) - C * (A - B)) * (p_dc - B) + C * (p_dc - B)**2
> ```
>> - Paco (or PAC0): Maximum AC power rating of the inverter at reference operating conditions.
>> - Pdco (or PDC0): DC power input required to reach the AC rating Paco at the reference DC voltage Vdco.
>> - Vdco (or VDC0): Reference DC input voltage at which Pdco yields Paco.
>> - Pso (or Ps0): DC power consumed by the inverter for startup or self-consumption; significantly affects efficiency at low loading.
>> - C0: Curvature (parabolic coefficient) of the AC–DC power relationship at the reference operating point.
>> - C1: Empirical coefficient describing how Pdco varies linearly with DC voltage (in units of 1/V).
>> - C2: Empirical coefficient describing how Pso varies linearly with DC voltage (1/V).
>> - C3: Empirical coefficient describing how C0 varies linearly with DC voltage (1/V).
>> - Pnt (night tare): AC power consumed by the inverter at night to maintain internal circuits (optional usage).


##### 🔌 ***INVERTER***: 
### ‼️ Not valid for simulations: 
Even if aviable in the selection, currently, inverters aviable for simulations must be setted manually as "custom" inverters

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


#### 3. **Custum parameters**
- Moudule: 
    - pdc0: nominal power of the module (DC) in Watts at STC (Standard Test Conditions: 1000 W/m², 25°C, AM1.5) 
        - It is the maximum power that the module can generate under ideal conditions. 
        - e.g. a 400 Wp module → pdc0 = 400
    - γ_pdc: temperature coefficient of power, in 1/°C 
        - It tells how much the module loses in power for each degree above 25°C (at STC). It is assumed negative, because efficiency decreases as the temperature increases     
        (❗***SO DON'T FORGET TO PUT MINUS WHEN USE IT IN THIS APP***)
        - e.g. γ_pdc = -0.004  →  -0.4% per °C

- Inverter:  [Future-updates](#future-updates)
    - pdc0: nominal DC input power of the inverter, in Watts.
    -> It is the reference value on which the efficiency of the inverter and the clipping are evaluated. 



> *NOTE*: For more realistic simulations (with CEC inverter model) it will be necessary to consider
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
> ***The Sandia Module Model***
>
> It is an empirical, high-fidelity model based on IV curves measured in the laboratory under various irradiance and temperature conditions.
> The parameters provided are curve-fitting coefficients that allow pvlib to calculate:
> - Current and voltage at operating points (MPP, Voc, Isc, etc.)
> - Variations due to temperature and irradiance
> - Efficiency, angular factors, derating, etc.
---
## Mount System
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
#### 4. DevelopementMount
At this moment same as in [SingleAxisTrackerMount](#2-singleaxistrackermount)

---

## Future updates
1. It will be possible to set more parameters to define custom modules and inverters
2. The `eta_inv_nom` parameter, i.e. the ***nominal inverter efficiency*** (typically around 96%), will also be implemented soon in the inverter settings and simulation. Currently, the efficiency could be assumed to be 1.0 (❗VERY UNREALISTIC, but the simulations are currently focusing on other kind of analysis).
3. In simulation, it will be possible to consider the shutdown of a PV array suggested by the inverter analysis as happend in the real cases
4. Since `pvlib` does not currently implement a *dual-axis* tracking system, this functionality will be developed and tested. During the development phase, a prototype will be made available as `DevelopmentMount` in the gui selection. Once the implementation is successfully and fully validated, it will be promoted to the `ValidatedMount`.