# 📓Quick Start Guide

- !["How to build a Plant"](#️-how-to-build-a-plant)
- !["How to build the Grid"](#-how-to-build-the-grid)

---
> ***RULES to read this steps***  
> - Buttons are identified with `*button name*`  
> - Input sections are identified with `_input name_`  
> - Variables or parameters are written in the form `variable_name`  
> - Names of files in this guide are identify with italics like *`File Name`*, while folders with bold and italics as ***`Folder name`***

## 🏗️ How To build a Plant

### 1. Go to *Plants* page  
From here, the user can have an overview of all plants created.
![Plants-Page](/docs/img/Plant_page.png) 


### 2. Press  `*Add Plant*` 
On the top right, below the title, click `*Add Plant*`. A side panel will open to configure the PV system (see image).  
![Add-Section](/docs/img/Add_Plant.png)

You will go through **six steps**:

1. [**Site**](#3-set-the-site) — enter the site name and address (city and district). If the site already exists, simply select it for automatic filling.
2. [**Location**](#4-set-the-location) — verify/update the **coordinates** (lat/lon), **altitude**, and **time zone**; a map helps you check the data.
3. [**Module**](#5-set-the-module) — select a **module** (CEC/Sandia database or **Custom**) and define its parameters (e.g., `pdc0`, `γ_pdc`).
4. [**Inverter**](#6-set-the-inverter) — choose an **inverter** (CEC database or **Custom**) and set the minimal parameters (e.g., `pdc0`).
5. [**Mount**](#7-set-the-mount) — select the **mount type** (Fixed or Single-Axis) and configure its geometrical parameters (tilt, azimuth, etc.).
6. [**Save**](#8-save) — final recap: assign a **name** to the plant and save (optionally start the simulation).

### 3. Set the *Site*
To add a new site, select *Other* in `_Site Name_`. Then write a Name of the site in `_New Name_` (e.g. "Rossi Srl") and the address in the form "Via Matteotti, 5" in `_Address_` with the city below in `_City_` and the province in `_District_`. 
> If the Site already exists, just select it in `_Site Name_`. Fields will be automatically completed  
>
Then click `*Next*` in the bottom of the form.
![New-Site-Form](/docs/img/New_Site.png)  

### 4. Set the *Location*
Coordinates and the altitude of the site are important for modules performances simulations. The form below appears for setting them. If  possible, coordinates are pre-compiled from the address youthe user eneterd before.
> ❗ Be Careful: the package used to obtain coordiantes automatically (`geopy` package) is not perfect and can handle only 1 request per second. Hence, check always coordinates in the map!  
>
Then click `*Next*` in the bottom of the form.
![Location-Form](/docs/img/Location_selection.png)

### 5. Set the *Moudule*
Simulation of modules performances aren't complex, so just ***nominal DC input power*** (`pdc0`, in Watt) and ***power temperature coefficient*** (`γ_pdc`, negative number in %/°C), namely the percentage power loss for each degree over 25°C. Setting the module can be done in two ways selecting the desired one in `_Origin_` box:
- Custom: selecting *Custom* or *pvwatts* (currently no differences exists among them)  
> Here the user is able to enter the desidered properties of the module. For now it's enough to know `pdc0` and `γ_pdc` and set the name in `_Custom Module Name_` box
![Custom-Module-Form](/docs/img/Custom_module.png)
- Modules from databases: selecting *CECMod* or *SandiaMod*
> Module parameters are taken from the respective databases (for details about these, look at the *`Elements of a PV Array`* file in ***`PVLib Package`*** ) and automatically taken in background
![DataBase-Module-Form](/docs/img/Database_module.png)  

---
### 6. Set the *Inverter*
Currently, simulation for inverters require only `pdc0` parameter (in Watt) and, similarly to module form, also here the user can set a *Custom* inverter or take it from CECInverter DataBase, but the latter is NOT aviable for simulation at the moment. Future update is predicted to include it. 
![Inverter-Form](/docs/img/Inverter_selection.png)  

---
### 7. Set the *Mount*
The mount types aviable are 2 selectable in `_Select Mount Type_` box.  On the bottom of the form the user can see a simple representation of panel tilt and azimuth angles.  
> Note: in the `_Select Mount Type_` box, the user can find two other types - *ValidatedMount* and *DevelopementMount* - to check and validate new mounting systems in the simulations. Currently, they have the same effect of *FixedMount*

- **Fixed Mount**
> The simplest one, with module fixed on a roof or in a unchangeable position. This need just 2 parameters both in degrees:  
> - Tilt: the angle between the plane of the solar panel and the horizontal ground.  
>> A tilt of 0° means the panel is lying flat, while 90° means it is standing vertically.  
>> Optimizing the tilt allows the panel to capture the maximum amount of sunlight depending on the latitude and season.
> - Azimuth: the compass direction that the front side of the solar panel faces. It is measured clockwise from true north (0°).  
>> For example, 90° corresponds to east, 180° to south, and 270° to west (in the Northern Hemisphere, panels are usually oriented towards the south to maximize solar gain).
![Fixed-Axis-Form](/docs/img/FixedMount.png)
- **Single Axis mount Mount**
> A tracking system where the modules rotate around a single axis (usually horizontal, north-south oriented). This allows the panels to follow the sun’s apparent motion, improving energy yield compared to fixed mounts.  
> The configuration requires the following parameters (all in degrees unless otherwise specified):  
> - Tilt: `_tilt_` defines the inclination of the tracker’s axis with respect to the ground.  
>> A value of 0° means the axis is perfectly horizontal, while higher values tilt the rotation axis.  
> - Azimuth: `_azimuth_` defines the compass direction that the tracker’s rotation axis points to. It is measured clockwise from true north (0°).  
>> Example: 180° means the axis runs north–south.  
> - Max Angle Inclination: `max_angle_inclination` sets the maximum rotation angle the tracker can reach from the horizontal position.  
>> For instance, 45° allows the panel to rotate 45° east in the morning and 45° west in the evening.  
> - Surface Angle: `surface_angle` defines the slope of the terrain where the tracker is installed.  
>> A flat ground corresponds to 0°.  
> - Ground Coverage Ratio: `gcr` (ratio, not degrees) defines the distance between rows of trackers relative to their size.  
>> A low GCR reduces shading but requires more land.  
> - Avoid Shadings (Backtrack): `_avoid_shadings_` option enables **backtracking**, meaning the trackers will slightly adjust their tilt during sunrise and sunset to prevent one row from shading the next.  

![Single-Axis-Form](/docs/img/SingleAxisMount.png)  


---
### 8. Save
The user can check the setup created and choose a name for the plant in the final saving form.
![Saving-Form](/docs/img/save_form.png)

---

## ⚡ How To build the Grid

The **Grid** is the electrical network that connects the PV plant to the external system.  
It is built on top of a *pandapower* network and must include at least:
- **Buses** → nodes where elements connect.  
- **Links** (e.g. lines) → connections between buses.  
- **At least one voltage source** (a `gen` with *Slack = ON* or an `ext_grid`) → required for power flow initialization.  
- **Optional generators** (`sgen`, typically PV arrays) → inject the plant’s power into the grid.  

❗ *Without at least these components (bus, link, slack, sgen), the grid is not simulable.*

---



### 1. Go to *Grid* page  
Open the plant first, then select the **Grid** page. Here you can create and manage the electrical network with *pandapower* via the in-app UI.  
<!-- ![Grid-Page](/docs/img/Grid_page.png) -->
>
---

### 2. Tabs overview  
The page is split into tabs (top of the page):
- **Links** → buses, lines (and transformers soon).  
- **Generators** → `sgen` (PV or other static generators) and `gen` (voltage-controlled / slack).  
- **Passive** → (coming soon).  
- **Sensors** → (coming soon).

---

### 3. Add Buses
Open the **Links** tab and expand `*New item*`.

1. Choose **Bus** in the chip selector.  
2. Fill the form `_Name_`, `_Bus level_` (b/n/m), `_In service_`.  
3. Set the **voltage level** (LV/MV/HV/EHV). The numeric `vn_kv` is auto-filled accordingly.  
4. (Optional) Enable min/max voltage limits with `_Set limits_`.  
5. If you need multiple identical buses, set `_Quantity_`.  
6. Click `*Add*`.

---

### 4. Add Lines (connect buses)
Still in **Links → New item**, choose **Line**.

1. Select the **start bus** and **end bus**.  
2. Set `_Std type_`, `_Length (km)_`, `_Name_`.  
3. The UI performs an **availability check**:  
   - ✅ `0` Link available  
   - ❌ `1` Same bus  
   - ❌ `2` Different voltages  
   - ❌ `3` Already present  
4. Click `*Add*` to create the line.

---

### 5. Inspect & Edit (Managers)
- **Bus Manager (tree)** → shows buses with their connected elements. Click a bus to open the edit dialog.  
- **Connections View** → compact list of links with voltage-color coding. Click a link name to open its dialog.  

---

### 6. Add Generators (Active elements)
Switch to the **Generators** tab.

#### A. Add PV or other SGen
1. Choose **SGen**.  
2. Fill `_Name_`, `_p_mw_`, `_scaling_`, `_q_mvar_` (if not PV).  
3. Select **SGen type**:  
   - *PV*: shows `_module_per_string_` and `_strings_per_inverter_`.  
   - *Others*: generic PQ injection.  
4. Select the `_Bus_` where it connects.  
5. Click `*Add*`.

#### B. Add Gen (Slack or Voltage-controlled)
1. Choose **Gen**.  
2. Toggle `_Slack_` to define if this is the **reference source**.  
   - *Slack = ON*: set `_vm_pu_`.  
   - *Slack = OFF*: set `_p_mw_`, `_q_mvar_`/limits, `_vm_pu_`.  
3. Pick the `_Bus_`.  
4. Click `*Add*`.

*(Storage: coming soon.)*

---

### 7. Save your work
Click `*Save*`. This writes:
- *`grid.json`* → full pandapower net (buses, lines, gens, sgens…).  
- *`arrays.json`* → PV array metadata linked to created `sgen`.

---

### 8. Quick Checklist (minimal working grid)
1. Create **two buses**: e.g. `PCC_0p4kV` (slack side) and `INV_0p4kV`.  
2. Add a **line** between them.  
3. Add a **slack gen** at `PCC_0p4kV`.  
4. Add an **SGen PV** at `INV_0p4kV`.  
5. `*Save*`.

This is enough for a valid power flow simulation.

---

### 9. Troubleshooting
- ❌ *Line not available*: same bus, different voltages, or already linked.  
- ⚡ *No convergence*: ensure at least one slack/ext_grid and that all buses are connected.  
- 🟡 *PV arrays*: sizing data (`_module_per_string_`, `_strings_per_inverter_`) are stored in *arrays.json*.  

