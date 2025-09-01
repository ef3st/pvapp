# Graphic User Interface (GUI)
Given that both `pandapower` and `pvlib` are high-level Python packages, the configuration of all the required parameters of a photovoltaic *Plant* and the subsequent integration of their simulation results may represent a non-trivial task. To address this complexity, a dedicated Graphic User Interface (GUI) has been developed with the specific objective of providing an intuitive and accessible interaction layer, even for users without prior experience in Python programming.  

The design of the PVApp GUI has been conceived to faithfully reflect both the physical structure of the plant components and the logical organization of the underlying computational processes.  
>
---

# Pages
*PVApp* is divided in three main pages and two utily pages:
### 1. ***Home***
Here the README.md is showed. Hence, the user can find basic commands and a summary of what PVApp does and eventually some relevant future updates. 
> #### ► **Manager and Analyser Pages** 
### 2. ***Plants***
Having 
Here you can find main details about the plants grouped in a table. Moreover a map shows you the actual positions of plants. Here you can also add plants, setting basic properties of PV module, inverters and mounting system.
![Plants-Pages](/docs/GUI/img/Plants.png)
### 3. ***Plants comparison***  
This page provides an overview and detailed comparative analysis of simulation parameters for the PV plants selected by the user.  In the top section of the page.  
![Plants-Comparison-Page](/docs/GUI/img/plant_comparison_TOP.png)
Comparisons can be performed on a seasonal, annual on averaged or summend parameter values, but also on on hourly basis, over a time range that spans either the entire simulation or a user-defined interval. Be aware that currently, comparisons are performed only on the first PV array setted in each *Plant*. Check [below](#plant-manager) for more details about simulation, saving and
### 4. ***Plant Manager***
Selecting the desired *Plant* in the top, from this page it is possible setting the electrical grid of the *Plant*, changing *Plant* setup, both for module and site, and analyses the simulation results both for PV arrays and the entire grid. For more information about how set the grid, check the relative documentation (`/docs/Quick Start Guide.md`). Instead, to know how manage and analyse look at *Plant manager* [paragraph](#plant-manager)
![Plant-Manager-Page](/docs/GUI/img/Plant_Manage_TOP.png)  
> #### ► **Utility Pages**  
### 5. ***Guide***
If the user need more detailed information about:
- how to use *PVApp*;  
- simulation mechanisms;  
- operation of specialized technical libraries for this purpose;  
- and parameter entry  
he can check this page searching the dedicated paragraph in the sidebar menu
> A tip: When you select this page, the menu in the left sidebar changes, displaying folders and documents related to specific topics. Sometimes, on the first try, selecting a folder below the first one may appear to be blank or inclomplete. In this case:
> - Open the first folder
> - Select a displayed document
> - Finally, try again with the desired starting folder.  
![Guide-Page](/docs/GUI/img/guide.png)
### 6. ***Logs***
In this page is possible to check for errors, informative and warning messages. If some kind of log message is created in the current session, icon and color page change following this codes:
![Logs-Icon&Color-Code](/docs/GUI/img/messages.png)
In a table, user can see all log messages with all details about them: time, logger name, file that generated the message, clickable and copyable description and, finally, the severity.  
As already explained, code is divided in 4 sections (analysis,backend, gui and tools) and folders in `src/pvapp` follow this logic. So from a tab selector on the right, user can filter log messages de-selecting the un-interesting files logs. Moreover, also a starting time from which starting to check logs can be settend in the "Time Filter" container on the top of the page 
> NOTE: Logs comes from `/logs/pvapp.log` and it contains all the logs history: keep on the toggle in the page top "*Use start of last run*"
![Log-Page](/docs/GUI/img/log_page.png)
>
---


### Sidebar
The PVApp pages can be selected via the sidebar menu showed below:  
![Sidebar](/docs/GUI/img/sidebar.png)
In the bottom of the sidebar some buttons are aviable:
- ⚙️: it's the PVApp setup button where user can select language and decide to (de)activate auto-saving or auto-simulating systems. If they are on, these action are operated at each change realized on the plant in *Plant Manager* page.  
- 🔥 Simulate All: when pressed, every *Plant* will be simulated with the current states. Be aware that each simulation can takes at least 2 minutes.  
- 📃 Download Guide: pressing this, a pdf with the PVApp guide will be downloaded in /Downloads folder in user PC.
- ✍️ Write to developer: a form can be compiled when this button is pressed. There the user can conctact directly the developer to suggest any improvement or report any bugs or errors.
![Bottom-Sidebar](/docs/GUI/img/sidebar_bottom.png)

---

# *Plant* Manager