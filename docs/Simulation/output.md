
# OUTPUT SIMULATION DATA DESCRIPTION

---
## From `pvlib` simulation
| **Variable**           | **Description**                                            | **Source Function**      | **Example values** | **Unit** |
| ---------------------- | ---------------------------------------------------------- | ------------------------ | ------------------ | -------- |
| `poa_global`           | Plane-of-array global irradiance (direct + diffuse)        | `get_total_irradiance`   | 950.0              | W/m²     |
| `poa_direct`           | Direct irradiance on the plane of array                    | `get_total_irradiance`   | 750.0              | W/m²     |
| `poa_diffuse`          | Diffuse irradiance on the plane of array                   | `get_total_irradiance`   | 200.0              | W/m²     |
| `aoi`                  | Angle of incidence between sun and module surface          | `get_total_irradiance`   | 10.3               | degrees  |
| `effective_irradiance` | Irradiance adjusted for AOI and spectral losses            | `sapm`                   | 920.0              | W/m²     |
| `v_mp`                 | Voltage at maximum power point                             | `sapm, single_diode`     | 30.5               | V        |
| `i_mp`                 | Current at maximum power point                             | `sapm, single_diode`     | 7.8                | A        |
| `p_mp`                 | Power at maximum power point                               | `sapm, single_diode`     | 237.9              | W        |
| `i_sc`                 | Short-circuit current                                      | `sapm, single_diode`     | 8.1                | A        |
| `v_oc`                 | Open-circuit voltage                                       | `sapm, single_diode`     | 39.8               | V        |
| `diode_voltage`        | Voltage across the internal diode                          | `single_diode`           | 0.6                | V        |
| `shunt_current`        | Current lost due to shunt resistance                       | `single_diode`           | 0.01               | A        |
| `temp_cell`            | PV cell temperature                                        | `temperature model`      | 45.0               | °C       |
| `temp_module`          | Module backside temperature                                | `temperature model`      | 43.0               | °C       |
| `dc_power`             | DC output power from module/system                         | `ModelChain, PVSystem`   | 240.0              | W        |
| `ac_power`             | AC output power after inverter                             | `ModelChain, PVSystem`   | 230.4              | W        |
| `losses`               | Total system loss factor (optional, if modeled)            | `ModelChain, PVSystem`   | 0.14               | %        |
| `zenith`               | Solar zenith angle                                         | `solarposition`          | 35.0               | degrees  |
| `azimuth`              | Solar azimuth angle                                        | `solarposition`          | 150.0              | degrees  |
| `airmass`              | Relative air mass (optical path length through atmosphere) | `solarposition`          | 1.8                | -        |
| `clearsky_ghi`         | Global horizontal irradiance (clearsky model)              | `clearsky`               | 1020.0             | W/m²     |
| `clearsky_dni`         | Direct normal irradiance (clearsky model)                  | `clearsky`               | 880.0              | W/m²     |
| `clearsky_dhi`         | Diffuse horizontal irradiance (clearsky model)             | `clearsky`               | 140.0              | W/m²     |
---
---
## From `pandapower` simulation
### 🟦 `res_bus`
| **Variable**   | **Description**              | **Source Function** | **Example values** | **Unit** |
| -------------- | ---------------------------- | ------------------- | ------------------ | -------- |
| `vm_pu`        | Voltage magnitude (per-unit) | `pp.runpp`          | 0.98               | p.u.     |
| `va_degree`    | Voltage angle                | `pp.runpp`          | -1.2               | °        |
| `p_mw`         | Net active power at bus      | `pp.runpp`          | 12.3               | MW       |
| `q_mvar`       | Net reactive power at bus    | `pp.runpp`          | 4.5                | Mvar     |

---

### 🟦 `res_line`
| **Variable**      | **Description**             | **Source Function** | **Example values** | **Unit** |
| ----------------- | --------------------------- | ------------------- | ------------------ | -------- |
| `p_from_mw`       | Active power at "from" bus  | `pp.runpp`          | 1.5                | MW       |
| `q_from_mvar`     | Reactive power at "from" bus| `pp.runpp`          | 0.2                | Mvar     |
| `p_to_mw`         | Active power at "to" bus    | `pp.runpp`          | 1.5                | MW       |
| `q_to_mvar`       | Reactive power at "to" bus  | `pp.runpp`          | 0.2                | Mvar     |
| `pl_mw`           | Active power losses in line | `pp.runpp`          | 0.05               | MW       |
| `ql_mvar`         | Reactive power losses       | `pp.runpp`          | 0.01               | Mvar     |
| `i_from_ka`       | Current at "from" bus       | `pp.runpp`          | 0.18               | kA       |
| `i_to_ka`         | Current at "to" bus         | `pp.runpp`          | 0.18               | kA       |
| `loading_percent` | Thermal loading of the line | `pp.runpp`          | 72.5               | %        |

---

### 🟦 `res_trafo`
| **Variable**      | **Description**             | **Source Function** | **Example values** | **Unit** |
| ----------------- | --------------------------- | ------------------- | ------------------ | -------- |
| `p_hv_mw`         | Active power at HV side     | `pp.runpp`          | 5.0                | MW       |
| `q_hv_mvar`       | Reactive power at HV side   | `pp.runpp`          | 1.2                | Mvar     |
| `p_lv_mw`         | Active power at LV side     | `pp.runpp`          | 5.0                | MW       |
| `q_lv_mvar`       | Reactive power at LV side   | `pp.runpp`          | 1.2                | Mvar     |
| `pl_mw`           | Active power losses         | `pp.runpp`          | 0.1                | MW       |
| `ql_mvar`         | Reactive power losses       | `pp.runpp`          | 0.02               | Mvar     |
| `i_hv_ka`         | Current at HV side          | `pp.runpp`          | 0.15               | kA       |
| `i_lv_ka`         | Current at LV side          | `pp.runpp`          | 0.16               | kA       |
| `loading_percent` | Transformer loading factor  | `pp.runpp`          | 85.0               | %        |

---

### 🟦 `res_sgen`
| **Variable** | **Description**            | **Source Function** | **Example values** | **Unit** |
| ------------ | -------------------------- | ------------------- | ------------------ | -------- |
| `p_mw`       | Active power injected      | `pp.runpp`          | 0.95               | MW       |
| `q_mvar`     | Reactive power injected    | `pp.runpp`          | 0.05               | Mvar     |
| `vm_pu`      | Terminal voltage magnitude | `pp.runpp`          | 0.99               | p.u.     |

---

### 🟦 `res_load`
| **Variable** | **Description**            | **Source Function** | **Example values** | **Unit** |
| ------------ | -------------------------- | ------------------- | ------------------ | -------- |
| `p_mw`       | Active power consumed      | `pp.runpp`          | 0.50               | MW       |
| `q_mvar`     | Reactive power consumed    | `pp.runpp`          | 0.12               | Mvar     |
| `vm_pu`      | Terminal voltage magnitude | `pp.runpp`          | 0.98               | p.u.     |

---

### 🟦 `res_gen`
| **Variable** | **Description**            | **Source Function** | **Example values** | **Unit** |
| ------------ | -------------------------- | ------------------- | ------------------ | -------- |
| `p_mw`       | Active power generated     | `pp.runpp`          | 10.0               | MW       |
| `q_mvar`     | Reactive power generated   | `pp.runpp`          | 2.0                | Mvar     |
| `vm_pu`      | Terminal voltage magnitude | `pp.runpp`          | 1.01               | p.u.     |

---

### 🟦 `res_ext_grid`
| **Variable** | **Description**           | **Source Function** | **Example values** | **Unit** |
| ------------ | ------------------------- | ------------------- | ------------------ | -------- |
| `p_mw`       | Active power exchanged    | `pp.runpp`          | -3.0               | MW       |
| `q_mvar`     | Reactive power exchanged  | `pp.runpp`          | -0.8               | Mvar     |
| `vm_pu`      | Voltage setpoint (p.u.)   | `pp.runpp`          | 1.00               | p.u.     |

---
---
> NOTE:  
>- Some variables may not appear depending on the model used (e.g., sapm, single_diode, or pvwatts).  