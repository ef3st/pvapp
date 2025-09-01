# `class Simulator`
Simulations are performed under the control of this class (`/src/pvapp/backend/simulation/simulator.py`). Do exectute a simulation is enought to applay the following code knowing the path of *Plant* data in the folder:
```python
from backend.simulation import simulator
import pandas as pd
sim = simulator.Simulator("/data/0")
df_time = pd.date_range(
            start="2024-03-01",
            end="2025-02-28",
            freq="1h",
            tz=tz,
            name="annual_01_03_24",
        )
sim.run(df_time)
```
A default times `pandas.DataFrame` can be used: it cover a year from 01/03/2025 to 28/02/2025 (from spring to winter end) with one hour intervals.  
>
---
## Simulation Process
#### Loading  
The methods `load_site()`,`load_pvsetup()`, takes data from `site.json`, `plant.json` files in the folder passed in inizialization. They are mandatory and without them simulation fail.
> They must have the following format:
> - **plant.json**: it must have 4 keys:  
>  ``````
>     1. "module"
```jso
 "module": {        
     "origin": "SandiaMod",
     "name": "Advent_Solar_AS160___2006_",
     "model": {},
     "dc_model": "cec",
     "dc_module": "sapm"
 }
``` 
>       2. "inverter"
```json
"inverter": {
     "origin": "Custom",
     "name": "Inv_450",
     "model": {
         "pdc0": 450.0
     },
     "ac_model": "pvwatts"
 }
```    
>       3. "mount":
>>         -  Single Axis Mount:
```json
"mount": {
        "type": "SingleAxisTrackerMount",
        "params": {
            "axis_tilt": 0,
            "axis_azimuth": 270,
            "max_angle": 45.0,
            "cross_axis_tilt": 0.0,
            "gcr": 0.35,
            "backtrack": true
        }
    }
```
>>           - Fixed Mount:
```json
"mount": {
        "type": "FixedMount",
        "params": {
            "surface_tilt": 30,
            "surface_azimuth": 270
        }
    }
```
>       4. "name": a single string with the name of the plant

>> ---
> - **site.json**
```json
{
    "name": "Aereoporto Ravenna",
    "address": "Via Dismano, 160",
    "city": "Ravenna (RA)",
    "coordinates": {
        "lat": 44.3603615,
        "lon": 12.2144328
    },
    "altitude": 0,
    "tz": "Europe/Rome"
}
```
`load_pvsetup()` saves data in attributes `module`, `inverter` and `mount` as well-defined `dict`.  
>
If grid is defined, in the folder will be also its structure saved in `grid.json` thanks to `load_grid()` method. Unlike previous load methods, this file is created and readed by dedicated `pandapower`  functions, so the file is just passed to the contructor of `PlantPowerGrid` (`/src/pvapp/backend/pandapower_network/pvnetwork.py`), an this objacted passed to `Simulator`  attribute named `grid`.  
>
Usually in this case also arrays are defined and saved in `arrays.json` file. It is read and passed to `arrays` attribute via `load_arrays()` method. 
> The arrays.json format is the following, where the key is the `sgen` (static generator) ID in the `pandapower` grid.
```json
{
    "0": {
        "module_per_string": 2,
        "strings_per_inverter": 4
    },
    "1": {
        "module_per_string": 2,
        "strings_per_inverter": 4
    }
}
```
>
---
>
### Simulation
Once the time series on which to simulate has been defined (`_init_times()`), the method `build_simulation()` is called, and simulation starts with the following steps.
#### 1. Build model chain 
This `ModelChain`object from `pvlib ` is the PV sytem simulations orchestrator. The function `BuildModelChain()` (in `src/pvapp/backend/pvlib_plant_model/modelchain.py`) create this object for each arrays saved in `arrays.json`. If there is no array, default parameters for `module_per_string`  and `strings` (both equal to 1) are used.
> #### `pvlib` `ModelChain()` object 
> #### Overview
> The **`ModelChain` class** in pvlib is a high-level object designed to simplify the
> simulation of a photovoltaic (PV) system.  
> It links together the different models available in pvlib (irradiance,
> module temperature, electrical performance) and executes them in sequence,
> providing the expected output of the PV system.
> 
> ---
> 
> ## Key Features
> - **Orchestration**: Automatically connects subsystems (`PVSystem`, `Location`,
>   temperature models, loss models, etc.) into a consistent calculation pipeline.
> - **Model selection**: Allows configuration of which irradiance transposition,
>   loss, module temperature, or inverter models to use.
> - **Inputs**: Requires a weather time series (typically a `pandas.DataFrame`
>   with at least GHI, DNI, DHI, ambient temperature, and wind speed).
> - **Outputs**: Produces a `ModelChainResult` object with multiple levels of results:
>   - Plane-of-array irradiance
>   - Module temperature
>   - DC power
>   - AC power
>   - Inverter efficiency
>   - Intermediate efficiencies and losses
> ---
> #### Configuration 
> 
> | Parameter        | Options (examples)                                                        | Description                                                               | Pros                                                                                     | Cons                                                 |
> |------------------|---------------------------------------------------------------------------|---------------------------------------------------------------------------|------------------------------------------------------------------------------------------|------------------------------------------------------|
> | **AOI Model**    | `"physical"`, `"ashrae"`, `"sapm"`, `"no_loss"`                           | Angle-of-incidence loss model                                             | *Physical* is more accurate, *Ashrae* is simple, *SAPM* aligns with Sandia DB            | More accurate models require more parameters/data    |
> | **Spectral Model** | `"sapm"`, `"first_solar"`, `"no_loss"`                                  | Accounts for spectral mismatch between solar spectrum and module response | Improves accuracy for varying air masses and climates                                    | Increases complexity; requires extra parameters      |
> | **Temperature Model** | `"sapm"`, `"pvsyst"`, `"fuentes"`                                    | Estimates cell/module temperature                                         | *SAPM* matches Sandia DB, *PVsyst* widely used in industry                               | Requires wind speed and ambient temp data            |
> | **DC Model**     | `"pvwatts"`, `"sapm"`, `"desoto"`                                         | Converts irradiance & temperature to DC output                            | *PVWatts* is simple; *SAPM* highly detailed; *DeSoto* used in many PV models             | Detailed models require more input data              |
> | **AC Model**     | `"sandia"`, `"pvwatts"`, `"adr"`                                          | Converts DC to AC power via inverter model                                | *Sandia* is detailed; *PVWatts* is simple; *ADR* fits to manufacturer’s curves           | Sandia/ADR require inverter database or extra params |
> | **Losses Model** | `pvwatts_losses`, custom functions                                        | Accounts for soiling, shading, wiring, degradation, etc.                  | Flexible; `pvwatts_losses` is quick default                                              | Custom losses must be defined manually               |
> | **Tracking**     | `FixedMount`, `SingleAxisTrackerMount`, custom `Mount` subclasses         | Mount configuration, tilt, azimuth, tracking axis                         | Built-in compatibility with pvlib mounting structures                                    | Complex trackers may require custom models           |
> | **Weather Input**| DataFrame with `ghi`, `dni`, `dhi`, `temp_air`, `wind_speed` (at minimum) | Required meteorological inputs                                            | Flexible — accepts real measurements or synthetic data                                   | Accuracy depends heavily on input data quality       |
> | **Results**      | `ModelChainResult` object (AC/DC power, temperatures, irradiance, etc.)   | Stores results of the full pipeline                                       | Easy access to all intermediate and final results                                        | Can be large in memory for long time-series          |
> 

#### 2. Run `pvlib` simulation
Once the `ModelChain` object for an array is defined, `Nature` object (in `/src/pvapp/backend/simulation/nature.py`) is created. This contains, data and models for the whether, mandatory to build the simulation of a PV module performance. With `Nature(site,timeseries).weather_simulation()`, a `pandas.DataFrame`.
> ### `Nature.weather_simulation()`
> This method returns a `**pandas.DataFrame` indexed by time (`self.times`) with five key columns:
> 
> 1. **ghi** – *Global Horizontal Irradiance*  
>    - Total solar irradiance incident on a horizontal surface.  
>    - Computed using a simplified semi-empirical model:  
>    - Values are clipped between 0 and 1000 W/m².
> 
> 2. **dni** – *Direct Normal Irradiance*  
>    - Direct irradiance perpendicular to the sun’s rays.  
>    - Derived from GHI and corrected for atmospheric effects using relative air mass and a simplified transmittance factor:  
>    - Clipped between 0 and 1000 W/m².
> 
> 3. **dhi** – *Diffuse Horizontal Irradiance*  
>    - Diffuse component of solar radiation reaching a horizontal surface.  
>    - Calculated as:  
>    - Clipped to values ≥ 0.
> 
> 4. **temp_air** – *Air Temperature*  
>    - Simulated seasonal variation following a sinusoidal trend:  
>      - Mean = 20 °C  
>      - Amplitude = ±10 °C  
>      - Maximum in summer, minimum in winter.  
> 
> 5. **wind_speed** – *Wind Speed*  
>    - Randomly generated with a uniform distribution between 1 and 2 m/s (`1 + rand()`),  
>      with optional seeding for reproducibility.
> 
> ---
> Basically, this DataFrame provides a **synthetic weather dataset** that includes both radiative (GHI, DNI, DHI) and environmental (temperature, wind) variables. It is specifically designed as input for **PV simulation models**, representing a simplified but physically consistent climatic profile over the chosen time range.

After weather dataframe definition, the simulation can be runned with the `run_model()` method of `ModelChain` object
>
#### 3. Add result in `SimulationResults` object
`Simulator` has the attribute `simresults`. It is an object `SimulationResults` implemented (in `/src/pvapp/analysis/database.py`) to handle, manipulate and save in .csv format the data obtained by simulation. It is based on `pandas.Dataframe` on which `ModuleChainResults` for each array are saved with `SimulationResults.add_modelchainresult()` method.
>
#### 4. Merge grid simulation
After simulated arrays performance, if aviable, the simulation of electical network can be runned via the dedicated `PlantPowerGrid` method showed below in its core:
```python
def runnet(
        self,
        timeseries: Union[pd.DataFrame, None] = None,
        selectors: Optional[List[str]] = None,
        return_df: bool = False,
    ) -> Union[List[str], Tuple[List[str], Optional[pd.DataFrame]]]:
        """
        Run a steady-state (pp.runpp) or time-series (pp.run_timeseries) power flow and
        optionally return results as a pandas DataFrame.

        Execution modes
        --------------
        1) Steady-state:
           If `timeseries` is None, a single power flow is executed (pp.runpp).
        2) Time-series:
           If `timeseries` is a DataFrame with tupled columns of the form
           ("sgen", "p_mw" | "q_mvar", <element_index>), ConstControls are created
           on-the-fly and a time-series simulation is executed (pp.run_timeseries).

        When `return_df=True`
        ---------------------
        • Steady-state: returns a single-row DataFrame with tupled columns
          (res_table, column, element_index).
        • Time-series: results are captured via an OutputWriter configured from
          `selectors`, and consolidated into one wide DataFrame with tupled columns
          (res_table, column, element_index) indexed by the original `timeseries.index`.

        Parameters
        ----------
        timeseries : pandas.DataFrame or None, default None
            Input profiles for time-series simulation. Expected to be the output of a
            function like `build_pp_dfdata_from_pvlib`, i.e. a wide DataFrame with
            tupled columns ("sgen", "p_mw" | "q_mvar", idx). If None, run a single
            steady-state power flow instead.
        selectors : list[str] or None, default None
            Result variables to collect, each in the form "res_table.column".
            Examples: ["res_bus.vm_pu", "res_line.loading_percent", "res_sgen.p_mw"].
            If None, a reasonable default set is used.
        return_df : bool, default False
            If True, also return a DataFrame of results as described above.

        Returns
        -------
        errors : list[str]
            A list of error messages emitted during checks or execution. Empty if no errors.
        results_df : pandas.DataFrame or None
            Only returned if `return_df=True`. In time-series mode, indexed by
            `timeseries.index`; in steady-state mode, a single row indexed by [0].

        Notes
        -----
        • `pandapower.timeseries.run_timeseries` does not return DataFrames directly.
          Results are logged during the simulation via `OutputWriter`. This method
          uses a dedicated utility to configure the OutputWriter from `selectors` and
          consolidate logs into a single wide DataFrame.
        • The method assumes that `self.net` is a valid pandapower network and
          `self.check_prerequisites()` verifies the minimal conditions to run a power flow.
        """
        t0 = time.perf_counter()
        # ---------- helpers ----------
        def _default_selectors() -> List[str]:
            """Return a reasonable default set of result variables."""
            return [
                "res_bus.vm_pu",
                "res_bus.va_degree",
                "res_line.loading_percent",
                "res_line.pl_mw",
                "res_trafo.loading_percent",
                "res_sgen.p_mw",
                "res_sgen.q_mvar",
                "res_load.p_mw",
                "res_load.q_mvar",
                "res_ext_grid.p_mw",
                "res_ext_grid.q_mvar",
            ]

        def _collect_with_outputwriter(
            selects: List[str], index: pd.Index
        ) -> pd.DataFrame:
            """
            Configure an OutputWriter from the provided selectors, run the time-series
            using label-based time_steps (the given `index`), and consolidate all logs
            into a single wide DataFrame.

            This function is robust to non-data keys in `ow.output` (e.g., "Parameters").
            Only variables explicitly requested via `selectors` are processed.

            Parameters
            ----------
            selects : list[str]
                Variables to log, each "res_table.column".
            index : pandas.Index
                Exact time_steps to simulate; must match DFData index labels (e.g., DateTimeIndex).

            Returns
            -------
            pandas.DataFrame
                Wide DataFrame with tupled columns (res_table, column, element_index)
                and `index` as the row index.
            """
            ...
           

        # ---------- pre-checks ----------
        errors: List[str] = self.check_prerequisites()
        if errors:
            self.logger.error("[runnet] Prerequisite errors: %s", errors)
            return (errors, None) if return_df else errors

        selectors = selectors or _default_selectors()

        results_df: Optional[pd.DataFrame] = None

        # Build DFData and bind ConstControls for sgens (p and q, if present)
        data_source = DFData(timeseries)
        p_cols = [
            c
            for c in timeseries.columns
            if isinstance(c, tuple)
            and len(c) == 3
            and c[0] == "sgen"
            and c[1] == "p_mw"
        ]
        q_cols = [
            c
            for c in timeseries.columns
            if isinstance(c, tuple)
            and len(c) == 3
            and c[0] == "sgen"
            and c[1] == "q_mvar"
        ]
        if not p_cols:
            msg = (
                "No ('sgen','p_mw', idx) columns found in timeseries DataFrame."
            )
            self.logger.error("[runnet] %s", msg)
            raise ValueError(msg)
        # Align element indices with the network's existing sgens
        sgen_idxs_p = [c[2] for c in p_cols if c[2] in self.net.sgen.index]
        if sgen_idxs_p:
            ConstControl(
                self.net,
                element="sgen",
                element_index=sgen_idxs_p,
                variable="p_mw",
                data_source=data_source,
                profile_name=p_cols,
            )
        if q_cols:
            sgen_idxs_q = [c[2] for c in q_cols if c[2] in self.net.sgen.index]
            if sgen_idxs_q:
                ConstControl(
                    self.net,
                    element="sgen",
                    element_index=sgen_idxs_q,
                    variable="q_mvar",
                    data_source=data_source,
                    profile_name=q_cols,
                )
        
        if return_df:
            # Capture results via OutputWriter using label-based time steps
            results_df = _collect_with_outputwriter(selectors, timeseries.index)
        else:
            run_timeseries(self.net, time_steps=list(timeseries.index))
        return (errors, results_df) if return_df else errors
```
Time data on which simulate and passed to `timeseries`are taken thanks to the `SimulationResults.get_df_for_pandapower()`, which uses the ModelChainResult added previously to return a wide-format `pandas-DataFrame` indexed by time with tupled columns:  
- ("sgen", "p_mw", <sgen_idx>)  
- ("sgen", "q_mvar", <sgen_idx>)  
>
With `return_df=True`, it will return a `pandas.DataFrame` with the results of network performance for each time in the `timeseries`, after checking the runnabily of the computations with `check_prerequisites()` method.  
Finally, if aviable, grid simulations are added to `simresults` attribute with `SimulationResults.add_gridresult()` method.  

#### 5. Save
Thanks to the `SimulationResults.save()` method, data are saved in the *Plant* subfolder in `/data` with the name `simualtion.csv`

---

An admission. Simulation is currently very slow since at least 2/3 minutes are necessary to get results. This is due to the process for loading grid simulation results on a `pandas.Dataframe`. This will be resolved in the future, but in the meanwhile, developer suggests to not touch the GUI while waiting