from pathlib import Path
from typing import Optional, Literal, Union, TypedDict, Dict

import json
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from pvlib.modelchain import ModelChain
from pvlib.pvsystem import retrieve_sam

from tools.logger import get_logger, log_performance
from pvapp.backend.pandapower_network.pvnetwork import PlantPowerGrid
from pvapp.backend.pvlib_plant_model import PVSystemManager, Site, BuildModelChain
from pvapp.analysis.database import SimulationResults
from .nature import Nature


class PV_Simulation(TypedDict, total=False):
    """
    Container for a single PV array simulation.

    Attributes:
        pvsystem (PVSystemManager): Configured PV system manager for the array.
        modelchain (Optional[ModelChain]): pvlib ModelChain built for the array.
    """

    pvsystem: PVSystemManager
    modelchain: Optional[ModelChain]


# * =============================
# *          SIMULATOR
# * =============================
class Simulator:
    """
    Orchestrates an end-to-end PV plant simulation.

    Description
    -----------
    This class loads site/plant/grid/array configuration from a folder, builds pvlib
    models for each array, generates synthetic weather, runs the simulations, optionally
    runs a pandapower time-series on the configured grid, aggregates the results and
    persists them to disk.

    Attributes:
        logger: Application logger instance (`get_logger("pvapp")`).
        subfolder (Path): Root folder containing JSON configuration files.
        site (Optional[Site]): Site object from `site.json`; `None` until `load_site()`.
        module (Optional[dict]): PV module descriptor (SAM or custom), set by `load_pvsetup()`.
        inverter (Optional[dict]): Inverter descriptor (SAM or pvwatts/custom), set by `load_pvsetup()`.
        mount (Optional[dict]): Mount configuration with keys `type` and `params`.
        grid (Optional[PlantPowerGrid]): Grid model built from `grid.json`, if present.
        pv_setup_data (Optional[dict]): Raw payload from `plant.json` (with Plant name, inverter, moudle, mount params).
        arrays (Dict[int, Dict[str, int]] | dict): Per-array wiring configuration.
        sims (Dict[int, Simulation] | Simulation): Handles per array (`pvsystem`, `modelchain`).
        simresults (SimulationResults): Collector for pvlib outputs (and grid results).
        times (Optional[pd.DatetimeIndex]): Time index used for simulations.

    Methods:
        run: Execute the full pipeline (load → build → simulate → save).
        load_site: Parse `site.json` and build a `Site`.
        load_pvsetup: Parse `plant.json` and resolve module/inverter/mount params.
        load_grid: if `grid.json` is present build `PlantPowerGrid` and set it in self.grid.
        load_arrays: Load `arrays.json` in self.arrays or use a default placeholder.
        configure_pvsystem: Create and configure a `PVSystemManager`.
        load_component: Resolve a component from SAM DB, pvwatts, or custom payload.
        build_simulation: Build and run pvlib for each array; optionally run grid.
        simulate: Run a `ModelChain` with synthetic weather from `Nature` class.
        merge_grid: Map AC powers to sgens and run a pandapower time series.
        save_results: Persist `SimulationResults` to disk.
        plant_name (property): Pretty name requiring loaded site and plant data.

    ---
    Example:
        >>> from pathlib import Path
        >>> sim = Simulator(subfolder=Path("data/0"))
        >>> ok = sim.run()

    ---
    Notes:
    - SAM database access is performed via `pvlib.pvsystem.retrieve_sam`.
    - If `arrays.json` is missing, a minimal 1x1 configuration is used.
    - `CecInverters` are explicitly not supported in this simulator.

    ---
    TODO:
    - Create other constructor opts
    """

    # * =========================================================
    # *                      LIFECYCLE
    # * =========================================================
    def __init__(self, subfolder: Path):
        """
        Initialize the simulator with a configuration folder.

        Args:
            subfolder (Path): Root folder containing configuration JSON files
                (`site.json`, `plant.json`, optional `arrays.json`, optional `grid.json`).
        """
        self.logger = get_logger("pvapp")
        self.subfolder: Path = subfolder

        # Core configuration containers (populated by loaders in `run()`)
        self.site: Optional[Site] = None
        self.module = None
        self.inverter = None
        self.mount: Optional[dict] = None
        self.grid: Optional[PlantPowerGrid] = None
        self.pv_setup_data: Optional[dict] = None

        # NOTE Arrays configuration: {array_idx -> {"modules_per_string": int, "strings_per_inverter": int, ...}}
        # ? Default non-crashing placeholder to avoid KeyError
        self.arrays: Dict[int, Dict[str, int]] | dict = {"": {"": None}}

        # Simulation holders
        self.sims: Union[Dict[int, PV_Simulation], PV_Simulation] = {}
        self.simresults: SimulationResults = SimulationResults()

        # Time index gets set in `run()`
        self.times: Optional[pd.DatetimeIndex] = None

    # * =========================================================
    # *                      PUBLIC API
    # * =========================================================
    @log_performance("Run_simulation")
    def run(
        self,
        times: Optional[pd.DatetimeIndex] = None,
    ) -> bool:
        """
        Run the full simulation pipeline.

        Args:
            times (Optional[pd.DatetimeIndex]): Custom time index to use. If `None`,
                a default (hourly, one-year window) is generated based on site tz.

        Returns:
            bool: `True` if the pipeline completed without fatal errors, `False` otherwise.

        ---
        Notes:
        - Exceptions are caught and logged; the method reports success via the return value.
        """
        # 1) Load configuration files
        try:
            self.load_site()
            self.load_pvsetup()
            self.load_grid()
            self.load_arrays()
        except Exception as e:
            self.logger.error(f"[Simulator] Loading error: {type(e).__name__}: {e}")
            return False
        self.logger.info(
            f"[Simulator] Configuration loaded successfully for {self._safe_plant_name()}"
        )

        try:
            # 2) Define time range
            self._init_times(times)

            # 3) Build and run all simulations
            built = self.build_simulation()
            if not built:
                self.logger.error(
                    "[Simulator] Aborting: build_simulation() did not complete."
                )
                return False

            # 4) Save results
            self.save_results()

        except (FileNotFoundError, KeyError, ValueError) as e:
            self.logger.error(
                f"[Simulator] Simulation failed for {self._safe_plant_name()}: {e}"
            )
            return False
        except Exception as e:
            self.logger.error(
                f"[Simulator] [UNEXPECTED ERROR] Failed for {self._safe_plant_name()} -> {type(e).__name__}: {e}"
            )
            return False
        return True

    # * =========================================================
    # *                        LOADERS
    # * =========================================================
    def load_site(self) -> None:
        """
        Load `site.json` and construct a `Site`.

        Raises:
            FileNotFoundError: If `site.json` is missing.
            KeyError: If required keys are missing in `site.json`.
            ValueError: If `site.json` is not valid JSON.
        """
        site_path = self.subfolder / "site.json"
        self.logger.debug(f"[Simulator] Loading site from: {site_path}")

        if not site_path.exists():
            raise FileNotFoundError(f"Missing site.json in {self.subfolder}")

        try:
            with site_path.open() as f:
                data_site = json.load(f)

            self.site = Site(
                name=data_site["name"],
                coordinates=(
                    data_site["coordinates"]["lat"],
                    data_site["coordinates"]["lon"],
                ),
                altitude=data_site["altitude"],
                tz=data_site["tz"],
            )
            self.logger.debug(f"[Simulator] Site loaded: {self.site.name}")
        except KeyError as e:
            raise KeyError(f"Missing site key: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in site.json: {e}")

    def load_pvsetup(self) -> None:
        """
        Load `plant.json` and extract PV components and mount info.

        Raises:
            FileNotFoundError: If `plant.json` is missing.
            ValueError: If `plant.json` is invalid JSON.
            KeyError: If required plant or mount keys are missing.
        """
        plant_path = self.subfolder / "plant.json"
        self.logger.debug(f"[Simulator] Loading plant setup from: {plant_path}")

        if not plant_path.exists():
            raise FileNotFoundError(f"Missing plant.json in {self.subfolder}")

        try:
            with plant_path.open() as f:
                self.pv_setup_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in plant.json: {e}")

        # Configure components
        self.module = self.load_component("module")
        self.mount = {
            "type": self.pv_setup_data["mount"]["type"],
            "params": self.pv_setup_data["mount"]["params"],
        }
        self.inverter = self.load_component("inverter")

        self.logger.debug(
            f"[Simulator] Plant setup loaded for '{self.pv_setup_data.get('name','<unnamed>')}'"
        )

    def load_grid(self) -> None:
        """
        Load `grid.json` and build a `PlantPowerGrid` if presentm, if missing, no grid is used.

        Notes:
            - If the file is not present, the method logs and no-ops.
        """
        grid_path: Path = self.subfolder / "grid.json"
        self.logger.debug(f"[Simulator] Loading grid from: {grid_path}")

        if grid_path.exists():
            try:
                self.grid = PlantPowerGrid(grid_path)
                self.logger.debug("[Simulator] Grid configuration loaded")
            except Exception as e:
                raise Exception(f"Error in loading grid: {e}")
        else:
            self.logger.debug("[Simulator] No grid.json found; skipping grid")

    def load_arrays(self) -> None:
        """
        Load `arrays.json` (optional). If missing, a default 1x1 placeholder is used.

        Raises:
            ValueError: If `arrays.json` contains invalid JSON.
            Exception: On other unexpected errors while loading arrays.
        """
        arrays_path: Path = self.subfolder / "arrays.json"
        self.logger.debug(f"[Simulator] Loading arrays from: {arrays_path}")

        if arrays_path.exists():
            try:
                with arrays_path.open() as f:
                    self.arrays = json.load(f)
                self.logger.debug(
                    f"[Simulator] Arrays configuration loaded: {len(self.arrays)} arrays"
                )
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in arrays.json: {e}")
            except Exception as e:
                raise Exception(f"Error in loading arrays: {e}")
        else:
            self.arrays = {"0": {"modules_per_string": 1, "strings_per_inverter": 1}}
            self.logger.info(
                f"[Simulator] arrays.json not found: using default placeholder configuration for {self.plant_name}"
            )

    # * =========================================================
    # *                        BUILDERS
    # * =========================================================
    def configure_pvsystem(
        self, modules_per_string: int = 1, strings: int = 1
    ) -> PVSystemManager:
        """
        Create and configure a `PVSystemManager` for the current plant and mount settings.

        Args:
            modules_per_string (int): Number of modules per string for the array.
            strings (int): Number of parallel strings per inverter for the array.

        Returns:
            PVSystemManager: Configured PV system manager instance.

        Raises:
            ValueError: If PV setup or module is not properly loaded.
            KeyError: If required keys for `PVSystemManager` initialization are missing.
        """
        if self.pv_setup_data is None:
            raise ValueError("PV setup data is not loaded.")

        try:
            pvsystem: PVSystemManager = PVSystemManager(
                name=self.pv_setup_data["name"],
                location=self.site,  # Site object from pvlib_plant_model.Site
                # Optional: owner/description/id can be set here if needed
            )
        except KeyError as e:
            raise KeyError(f"Error in defining PVSystemManager: {e}")

        if self.module is None:
            raise ValueError("Module is not defined. Cannot set PV Array.")

        # Configure PV components for this system
        pvsystem.set_pv_components(
            module=self.module,
            inverter=self.inverter,
            mount_type=self.mount["type"],
            params=self.mount["params"],
            modules_per_string=modules_per_string,
            strings=strings,
        )
        return pvsystem

    def load_component(self, component: Literal["module", "inverter"]):
        """
        Resolve a component (module or inverter) from configuration.

        Description:
            Supports three sources:
            1) Custom payload (`origin == "Custom"`)
            2) pvwatts inverter model (for inverter with `origin == "pvwatts"`)
            3) SAM database lookup via `retrieve_sam(origin.lower())[name]`

        Args:
            component (Literal["module","inverter"]): Component type to resolve.

        Returns:
            Any: The component data/object to be passed into pvlib / PVSystemManager.

        Raises:
            ValueError: On missing payload, unsupported origins, or SAM retrieval errors.
            KeyError: If required keys like `origin` or `name` are missing.
        """
        if self.pv_setup_data is None:
            raise ValueError("PV setup data is not loaded.")

        comp_data: dict = self.pv_setup_data.get(component, {})
        origin = comp_data.get("origin")
        name = comp_data.get("name")

        if not origin:
            raise KeyError(f"Missing origin for {component}")

        # Not supported path
        if component == "inverter" and origin == "cecinverter":
            raise ValueError(
                "CecInverters are not supported in this simulator. Please use a different inverter."
            )

        # Custom object or pvwatts inverter passed through as-is
        if origin == "Custom" or (component == "inverter" and origin == "pvwatts"):
            model = comp_data.get("model")
            if model is None:
                raise ValueError(f"Missing 'model' payload for custom {component}")
            self.logger.debug(f"[Simulator] Loaded custom {component}")
            return model

        # Retrieve from SAM database
        try:
            sam_data = retrieve_sam(origin.lower())
            value = sam_data[name]
            self.logger.debug(
                f"[Simulator] Loaded {component} '{name}' from SAM '{origin}'"
            )
            return value
        except KeyError:
            raise ValueError(
                f"{component.capitalize()} '{name}' not found in {origin} database."
            )
        except Exception as e:
            raise ValueError(f"Error retrieving {component} from SAM ({origin}): {e}")

    def build_simulation(self) -> bool:
        """
        Build and execute the pvlib `ModelChain` for each configured array.

        Returns:
            bool: `True` if the build loop completes (even with per-array warnings).

        Raises:
            ValueError: If mandatory elements (module, site, mount) are missing.
        """
        # Validate prerequisites
        if self.module is None or self.site is None or self.mount is None:
            raise ValueError(
                "Module or site or mount are not defined. Cannot simulate."
            )

        # If grid exists but arrays are missing (placeholder), warn the user
        if self.grid is not None and self.arrays == {"": {"": None}}:
            self.logger.warning("Missing pv 'arrays' data, but grid is defined.")

        # Iterate over arrays (works also with the placeholder, which will raise in configure_pvsystem)
        for array_idx in self.arrays:
            pvsystem_for_array = None
            modelchain_for_array = None

            try:
                modules_per_string = self.arrays[array_idx].get("modules_per_string", 1)
                strings = self.arrays[array_idx].get("strings_per_inverter", 1)

                pvsystem_for_array = self.configure_pvsystem(
                    modules_per_string=modules_per_string,
                    strings=strings,
                )
                modelchain_for_array = BuildModelChain(
                    system=pvsystem_for_array.getplant(),
                    site=self.site.location,  # passes pvlib Location
                )
            except Exception as e:
                self.logger.warning(
                    f"[Simulator] Build failed for array {array_idx} in plant {self._safe_plant_name()}: {e}"
                )
                # ? Skip to next array but keep tracking placeholders
                continue

            # Store handles for this array
            self.sims[array_idx] = {
                "pvsystem": pvsystem_for_array,
                "modelchain": modelchain_for_array,
            }

            # Run the pvlib simulation
            try:
                self.simulate(modelchain_for_array)
            except Exception as e:
                self.logger.warning(
                    f"[Simulator] Run failed for array {array_idx} in plant {self._safe_plant_name()}: {e}"
                )
                # keep going with other arrays
                continue

            # Collect results
            try:
                self.simresults.add_modelchainresult(
                    pvSystemId=array_idx,
                    results=modelchain_for_array.results,
                    period=self.times.name if self.times is not None else None,
                )
                self.logger.debug(
                    f"[Simulator] Array {array_idx} of {self._safe_plant_name()} EXECUTED"
                )
            except Exception as e:
                self.logger.warning(
                    f"[Simulator] Result collection failed for array {array_idx}: {e}"
                )

        # After all arrays: optionally simulate the grid
        if self.grid is None:
            self.logger.debug("[Simulator] No grid configured; skipping pandapower run")
        else:
            try:
                self.merge_grid()
            except Exception as e:
                self.logger.error(
                    f"[Simulator] Grid simulation failed for {self._safe_plant_name()}: {e}"
                )
        self.logger.info(
            f"[Simulator] Simulation for Plant {self._safe_plant_name()} has been EXECUTED successfully"
        )
        return True

    # * =========================================================
    # *                       EXECUTORS
    # * =========================================================
    @log_performance("pvlib_simulation")
    def simulate(self, modelchain: ModelChain) -> None:
        """
        Run pvlib's `ModelChain` using synthetic weather generated by `Nature`.

        Args:
            modelchain (ModelChain): The pvlib model chain to execute.

        Raises:
            ValueError: If the model chain, site, or times are not set.
        """
        if modelchain is None:
            raise ValueError(
                "[Simulator] ModelChain is not defined. Cannot run simulation."
            )
        if self.site is None or self.times is None:
            raise ValueError(
                "[Simulator] Site or times not set. Cannot run simulation."
            )

        self.logger.debug(
            "[Simulator] Generating synthetic weather and running ModelChain"
        )
        nature = Nature(self.site.location, self.times)

        # -------------> Weather Synthesis <--------
        weather = nature.weather_simulation(temp_air=25, wind_speed=1)

        # -------------> pvlib Execution <--------
        modelchain.run_model(weather)

    @log_performance("pandapower_simulation")
    def merge_grid(self) -> None:
        """
        If a pandapower grid is configured, push array AC powers as sgen profiles and run a time-series power flow.

        Raises:
            Exception: Propagates unexpected failures during pandapower execution.
        """
        try:
            df_timeseries = self.simresults.get_df_for_pandapower(self.grid.net)
            self.logger.debug(
                f"[Simulator] Running pandapower time-series simulation for {self.plant_name}"
            )
            errors, results = self.grid.runnet(timeseries=df_timeseries, return_df=True)
            if errors:
                self.logger.error(f"[Simulator] Grid run encountered errors: {errors}")
            else:
                self.logger.debug(f"[Simulator] Grid run completed successfully.")
                self.simresults.add_gridresult(results)
        except Exception as e:
            self.logger.error(f"[Simulator] Grid run failed: {e}")
            # Results integration into `simresults` can be added here in future
            return

    def save_results(self) -> None:
        """
        Export `SimulationResults` inside `subfolder`.

        Notes:
            - If there are no results, the method logs a warning and returns early.
        """
        try:
            if self.simresults.is_empty:
                self.logger.warning("[Simulator] Nothing to save. No results found.")
                return
            self.simresults.save(self.subfolder)
            self.logger.info(
                f"[Simulator] Results for {self._safe_plant_name()} SAVED in /{self.subfolder}/simulation.csv successfully"
            )
        except Exception as e:
            self.logger.error(f"[Simulator] Failed to save results: {e}")

    # * =========================================================
    # *                HELPERS & PROPERTIES
    # * =========================================================
    def _init_times(self, times: Optional[pd.DatetimeIndex]) -> None:
        """
        Initialize `self.times` using the provided index or a default one-year hourly range.

        Args:
            times (Optional[pd.DatetimeIndex]): Custom time index to use. If `None`,
                a default index is created from 2024-03-01 to 2025-02-28 with 1h freq,
                using the site timezone when available, otherwise UTC.

        Raises:
            ValueError: If called before `load_site()` and the site timezone cannot be determined.
        """
        if times is not None:
            self.times = times
            self.logger.debug(
                f"[Simulator] Using provided times index: {times[0]} -> {times[-1]} ({len(times)} pts)"
            )
            return

        if self.site is None or self.site.site is None or self.site.site.tz is None:
            # Fall back to naive UTC if tz is unavailable (shouldn't happen if load_site succeeded)
            self.logger.warning(
                "[Simulator] Site timezone not available; defaulting to naive UTC time index"
            )
            tz = "UTC"
        else:
            tz = self.site.site.tz

        self.times = pd.date_range(
            start="2024-03-01",
            end="2025-02-28",
            freq="1h",
            tz=tz,
            name="annual_01_03_24",
        )
        self.logger.debug(
            f"[Simulator] Default times index created: {self.times[0]} -> {self.times[-1]} ({len(self.times)} pts)"
        )

    @property
    def plant_name(self) -> str:
        """
        Pretty plant name for logs.

        Returns:
            str: A string in the format `"[{site.name} : {plant_name}]"`.

        Raises:
            AssertionError: If site or plant data are not yet loaded.
        """
        assert self.site is not None, "Site must be defined to get plant name."
        assert (
            self.pv_setup_data is not None
        ), "Plant data must be defined to get plant name."
        return f"[{self.site.name} : {self.pv_setup_data['name']}]"

    def _safe_plant_name(self) -> str:
        """
        Safe display name for logs before site/plant are fully loaded.

        Returns:
            str: A string in the format `"[{site_or_<??>} : {plant_or_<??>}]"`.
        """
        site_name = getattr(self.site, "name", "<site?>")
        plant_name = (
            self.pv_setup_data.get("name", "<plant?>")
            if self.pv_setup_data
            else "<plant?>"
        )
        return f"[{site_name} : {plant_name}]"
