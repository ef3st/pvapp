# 📓Quick Start Guide

---

## 🏗️ How To build a Plant
> ***RULES to read this steps***  
> Since this guide is in english, but the PVApp has also the option to select italian, the commands name in the latter language will be inside "[...]"  
> - Buttons are identified with `*button name*`  
> - Input sections are identified with `_input name_`  
> - Variables or parameters are written in the form `variable_name`  
> - Names of files in this guide are identify with italics like *`File Name`*, while folders with bold and italics as ***`Folder name`***

### 1. Go to *Plants* [*Impianti*] page  
From here, the user can have an overview of all plants created.
![Plants-Page](/docs/img/Plant_page.png) 


### 2. Press  `*Add Plant*` 
On the top rigth, below the title, click `*Add Plant*`[`*Aggiungi Impianto*`]. Then a section on the rigth will be open to set the PV system (see image below). 
![Add-Section](/docs/img/Add_Plant.png)  
The user is going to complete six steps:  
1. ![Site](#3-set-the-site): setting names and address of the city. Currently, only Italy is aviable to set correctly the site informations (No updates are predicted for now!).
2. ![Location](#4-set-the-location):
3. ![Module](#5-set-the-moudule):
4. ![Inverter](#6-set-the-inverter):
5. ![Mount](#7-set-the-mount):
6. ![Save](#8-save):

### 3. Set the *Site*
To add a new site, select *Other* [*Altro*] in `_Site Name_`. Then write a Name of the site in `_New Name_` (e.g. "Rossi Srl") and the address in the form "Via Matteotti, 5" in `_Address_` with the city below in `_City_` and the province in `_District_`. 
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