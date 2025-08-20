# ⚡ Pandapower Elements Parameters

This document summarizes the `TypedDict` parameter sets used in **pandapower**.  
Each section corresponds to one element (`net['xxx']`).  

---

## 📑 Table of Contents

- [SGenParams (net['sgen'])](#-sgenparams-netsgen)  
- [GenParams (net['gen'])](#-genparams-netgen)  
- [ExtGridParams (net['ext_grid'])](#-extgridparams-netext_grid)  
- [BusParams (net['bus'])](#-busparams-netbus)  
- [LineParams (net['line'])](#-lineparams-netline)  
- [SwitchParams (net['switch'])](#-switchparams-netswitch)  
- [TrafoParams (net['trafo'])](#-trafoparams-nettrafo)  
- [Trafo3WParams (net['trafo3w'])](#-trafo3wparams-nettrafo3w)  
- [LoadParams (net['load'])](#-loadparams-netload)  
- [StorageParams (net['storage'])](#-storageparams-netstorage)  

---

## 🔹 SGenParams (net['sgen'])

| Key          | Type  | Description                                         |
|--------------|-------|-----------------------------------------------------|
| bus          | int   | Bus index where the sgen is connected.              |
| p_mw         | float | Active power injection in MW (positive = generation)|
| q_mvar       | float?| Reactive power injection in MVAr.                   |
| name         | str?  | Human-readable element name.                        |
| scaling      | float | Multiplier applied to p_mw and q_mvar.              |
| in_service   | bool  | Whether the element is active.                      |
| type         | str?  | Connection type ("wye", "delta").                   |
| sn_mva       | float?| Rated apparent power in MVA.                        |
| max_p_mw     | float?| Upper bound for active power (OPF).                 |
| min_p_mw     | float?| Lower bound for active power (OPF).                 |
| max_q_mvar   | float?| Upper bound for reactive power (OPF).               |
| min_q_mvar   | float?| Lower bound for reactive power (OPF).               |
| controllable | bool? | If True, treated as flexible in OPF.                |

**Note:** See pandapower `sgen` for more details.

---

## 🔹 GenParams (net['gen'])

| Key          | Type  | Description                                   |
|--------------|-------|-----------------------------------------------|
| bus          | int   | Index of the connected bus.                   |
| p_mw         | float?| Active power setpoint in MW.                  |
| vm_pu        | float | Voltage magnitude setpoint in p.u.            |
| name         | str?  | Human-readable name.                          |
| q_mvar       | float?| Reactive power injection.                     |
| min_q_mvar   | float?| Minimum reactive power (OPF).                 |
| max_q_mvar   | float?| Maximum reactive power (OPF).                 |
| sn_mva       | float?| Rated apparent power in MVA.                  |
| slack        | bool? | If True, this generator acts as slack.        |
| scaling      | float?| Scaling factor for p_mw and q_mvar.           |
| in_service   | bool  | Whether the generator is active.              |
| controllable | bool? | If True, flexible for OPF.                    |

**Note:** See pandapower `gen` for more details.

---

## 🔹 ExtGridParams (net['ext_grid'])

| Key        | Type  | Description                 |
|------------|-------|-----------------------------|
| bus        | int   | Reference bus index.        |
| vm_pu      | float | Voltage magnitude in p.u.   |
| va_degree  | float | Voltage angle in degrees.   |
| name       | str?  | Human-readable name.        |
| in_service | bool  | Whether the slack is active.|

**Note:** See pandapower `ext_grid` for more details.

---

## 🔹 BusParams (net['bus'])

| Key        | Type                | Description                    |
|------------|---------------------|--------------------------------|
| vn_kv      | str \| float \| None| Nominal voltage level in kV.   |
| name       | str?                | Human-readable bus name.       |
| geodata    | tuple?              | Coordinates for plotting.      |
| type       | str?                | Bus type ("b", "n", "m").      |
| zone       | int \| str \| None  | Zone/area label.               |
| in_service | bool                | Whether the bus is active.     |
| min_vm_pu  | float?              | Minimum allowed voltage [p.u.].|
| max_vm_pu  | float?              | Maximum allowed voltage [p.u.].|

**Note:** See pandapower `bus` for more details.

---

## 🔹 LineParams (net['line'])

| Key        | Type  | Description                        |
|------------|-------|------------------------------------|
| from_bus   | int   | Sending-end bus index.              |
| to_bus     | int   | Receiving-end bus index.            |
| length_km  | float | Line length in km.                  |
| name       | str   | Human-readable line name.           |
| std_type   | str   | Standard type name (impedance data).|
| in_service | bool  | Whether the line is active.         |

**Note:** See pandapower `line` for more details.

---

## 🔹 SwitchParams (net['switch'])

| Key        | Type  | Description                             |
|------------|-------|-----------------------------------------|
| bus        | int   | Bus side of the switch.                 |
| element    | int   | Index of the connected element.         |
| et         | str   | Element type ("b", "l", "t", "t3").     |
| closed     | bool  | Switch status (True = closed).          |
| type       | str?  | Switch type ("CB", "LS", etc.).         |
| name       | str?  | Human-readable name.                    |
| in_service | bool? | Whether the switch is active.           |
| z_ohm      | float?| Resistance for bus-bus switches.        |

**Note:** See pandapower `switch` for more details.

---

## 🔹 TrafoParams (net['trafo'])

| Key                 | Type  | Description                 |
|---------------------|-------|-----------------------------|
| hv_bus              | int   | High-voltage bus index.     |
| lv_bus              | int   | Low-voltage bus index.      |
| std_type            | str?  | Transformer standard type.  |
| name                | str?  | Name.                       |
| tap_pos             | int?  | Tap position.               |
| in_service          | bool  | Whether transformer is on.  |
| parallel            | int?  | Number of parallel units.   |
| df                  | float?| Derating factor.            |
| max_loading_percent | float?| Loading limit.              |
| sn_mva              | float?| Rated apparent power.       |
| vn_hv_kv            | float?| HV voltage rating.          |
| vn_lv_kv            | float?| LV voltage rating.          |
| vkr_percent         | float?| Real short-circuit voltage. |
| vk_percent          | float?| Short-circuit voltage.      |
| pfe_kw              | float?| Iron losses.                |
| i0_percent          | float?| No-load current.            |
| shift_degree        | float?| Phase shift.                |
| tap_side            | str?  | Tap side ("hv", "lv").      |
| tap_neutral         | int?  | Neutral tap pos.            |
| tap_max             | int?  | Maximum tap.                |
| tap_min             | int?  | Minimum tap.                |
| tap_step_percent    | float?| Tap step [%].               |
| tap_step_degree     | float?| Tap step [deg].             |
| tap_phase_shifter   | bool? | Phase-shifting flag.        |

**Note:** See pandapower `trafo` for more details.

---

## 🔹 Trafo3WParams (net['trafo3w'])

| Key              | Type  | Description                     |
|------------------|-------|---------------------------------|
| hv_bus           | int   | High-voltage bus index.         |
| mv_bus           | int   | Medium-voltage bus index.       |
| lv_bus           | int   | Low-voltage bus index.          |
| std_type         | str?  | Transformer type.               |
| name             | str?  | Name.                           |
| tap_pos          | int?  | Tap position.                   |
| tap_at_star_point| bool? | Tap at star point flag.         |
| in_service       | bool  | Active status.                  |
| max_loading_percent | float?| Loading limit.               |

**Note:** See pandapower `trafo3w` for more details.

---

## 🔹 LoadParams (net['load'])

| Key               | Type  | Description                      |
|-------------------|-------|----------------------------------|
| bus               | int   | Bus index.                       |
| p_mw              | float | Active power demand in MW.       |
| q_mvar            | float | Reactive power demand in MVAr.   |
| name              | str?  | Name.                            |
| scaling           | float | Scaling factor for P/Q.          |
| in_service        | bool  | Active status.                   |
| const_z_p_percent | float?| Const-Z share of P.              |
| const_i_p_percent | float?| Const-I share of P.              |
| const_z_q_percent | float?| Const-Z share of Q.              |
| const_i_q_percent | float?| Const-I share of Q.              |
| sn_mva            | float?| Apparent power rating.           |
| type              | str?  | Connection type ("wye", "delta").|
| controllable      | bool? | Flexible in OPF.                 |

**Note:** See pandapower `load` for more details.

---

## 🔹 StorageParams (net['storage'])

| Key          | Type  | Description                        |
|--------------|-------|------------------------------------|
| bus          | int   | Bus index.                         |
| p_mw         | float | Active power. Positive = discharge.|
| max_e_mwh    | float | Maximum energy capacity.           |
| soc_percent  | float | State of charge [%].               |
| min_e_mwh    | float | Minimum allowed energy.            |
| q_mvar       | float | Reactive power in MVAr.            |
| sn_mva       | float | Apparent power rating.             |
| controllable | bool  | Flexible in OPF.                   |
| name         | str?  | Human-readable name.               |
| in_service   | bool  | Active status.                     |
| type         | str?  | Connection type label.             |
| scaling      | float?| Scaling factor.                    |

**Note:** See pandapower `storage` for more details.
