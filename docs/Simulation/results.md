
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
| `temp_cell`            | PV cell temperature                                        | °C       | `temperature model`      | 45.0               |
| `temp_module`          | Module backside temperature                                | °C       | `temperature model`      | 43.0               |
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