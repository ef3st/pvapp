from pathlib import Path
from typing import Optional, Literal, Union, TypedDict, Dict

import json
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from pvlib.modelchain import ModelChain
from pvlib.pvsystem import retrieve_sam

from tools.logger import get_logger, log_performance
from backend.pvlib_plant_model import PVSystemManager, Site, BuildModelChain
from backend.pandapower_network.pvnetwork import PlantPowerGrid
from analysis.database import SimulationResults
from .nature import Nature


class Simulation(TypedDict, total=False):
    """Container for one PV array simulation objects."""

    pvsystem: PVSystemManager
    modelchain: Optional[ModelChain]


# * =============================
# *       SIMULATOR CLASS
# * =============================
class Simulator:
    """
    Orchestrates a full PV plant simulation:
    - Load site, plant, grid, and array configuration from JSON files in `subfolder`
    - Build PV systems and pvlib ModelChains for each array
    - Generate synthetic weather and run pvlib simulations
    - Optionally run a pandapower time-series on the configured grid
    - Aggregate and persist results

    Public API
    ----------
    - run(times: Optional[pd.DatetimeIndex] = None) -> None
      Entry point. Executes the full pipeline (load → build → simulate → save → grid).

    Internal methods
    ----------------
    - load_site() -> None
    - load_pvsetup() -> None
    - load_grid() -> None
    - load_arrays() -> None
    - configure_pvsystem(modules_per_string: int = 1, strings: int = 1) -> PVSystemManager
    - load_component(component: Literal["module", "inverter"])
    - build_simulation() -> None
    - simulate(modelchain: ModelChain) -> None
    - merge_grid() -> None
    - save_results() -> None
    - _init_times(times: Optional[pd.DatetimeIndex]) -> None
    - _safe_plant_name() -> str

    Parameters
    ----------
    subfolder (Path):
      Root folder containing the plant configuration JSON files:
      - site.json     : site metadata (name, coordinates, altitude, tz)
      - plant.json    : PV setup (module, inverter, mount)
      - arrays.json   : per-array wiring (modules_per_string, strings_per_inverter)
      - grid.json     : optional pandapower network description

    Attributes
    ----------
    logger:
      Application logger instance (via `get_logger("pvapp")`).

    subfolder (Path):
      Root folder with configuration JSON files.

    site (Optional[Site]):
      Site object loaded from site.json (None until `load_site()`).

    module:
      PV module descriptor (from SAM DB or custom payload), loaded by `load_pvsetup()`.

    inverter:
      Inverter descriptor (from SAM DB or custom/pvwatts), loaded by `load_pvsetup()`.

    mount (Optional[dict]):
      Mount configuration dict with keys:
      - type: str
      - params: dict

    grid (Optional[PlantPowerGrid]):
      Grid model wrapper loaded from grid.json (if present).

    pv_setup_data (Optional[dict]):
      Raw plant.json payload (module/inverter/mount/metadata).

    arrays (dict):
      Per-array configuration loaded from arrays.json.
      Schema: {array_idx: {"modules_per_string": int, "strings_per_inverter": int, ...}}.
      Defaults to {"": {"": None}} as a non-crashing placeholder.

    sims (dict[int, Simulation] | Simulation):
      Handles for each array:
      - pvsystem: PVSystemManager
      - modelchain: ModelChain

    simresults (SimulationResults):
      Results collector/manager for pvlib outputs (and future grid results).

    times (Optional[pd.DatetimeIndex]):
      Time index for the simulation. Set in `run()` via `_init_times()` if not provided.

    Properties
    ----------
    plant_name -> str:
      Pretty log-friendly name in format "[{site.name} : {plant_name}]".
      Requires `site` and `pv_setup_data` to be loaded.

    Methods (detailed)
    ------------------
    run(times: Optional[pd.DatetimeIndex] = None) -> None:
      Orchestrates the full pipeline: loading configs, building simulation objects,
      running pvlib on synthetic weather, saving results, and running the grid if configured.

    load_site() -> None:
      Parse site.json → build `Site`. Raises on missing keys or invalid JSON.

    load_pvsetup() -> None:
      Parse plant.json → resolve module, inverter, mount. Supports SAM databases,
      custom payloads, and pvwatts inverter. Raises on unsupported origins or missing entries.

    load_grid() -> None:
      If grid.json exists, build `PlantPowerGrid`. Otherwise, no-op.

    load_arrays() -> None:
      Load arrays.json into `self.arrays`. If missing, logs a warning and keeps placeholder.

    configure_pvsystem(modules_per_string: int = 1, strings: int = 1) -> PVSystemManager:
      Create and configure `PVSystemManager` with module/inverter/mount/wiring.

    load_component(component: Literal["module", "inverter"]):
      Retrieve component from SAM (by origin/name) or accept custom/pvwatts payloads.

    build_simulation() -> None:
      For each array:
      - create pvsystem + modelchain
      - `simulate()` with synthetic weather
      - push results into `simresults`
      Finally, call `merge_grid()`.

    simulate(modelchain: ModelChain) -> None:
      Build synthetic weather via `Nature` and run the pvlib ModelChain.

    merge_grid() -> None:
      If grid present, map AC power time series to sgens, create controllers,
      and run a pandapower time-series.

    save_results() -> None:
      Persist `simresults` under `subfolder` (e.g., simulation.csv).

    Raises
    ------
    FileNotFoundError:
      If required JSON files are missing where mandatory (e.g., site.json, plant.json).
    KeyError:
      On missing JSON keys (e.g., plant/mount/module definitions).
    ValueError:
      On invalid component origins, unsupported inverters, or misconfiguration.
    Exception:
      Propagated from grid loading/execution or SAM retrieval errors.

    Usage example
    -------------
    >>> from pathlib import Path
    >>> sim = Simulator(subfolder=Path("data/0"))
    >>> sim.run()  # or sim.run(times=my_datetime_index)
    """

    # ========== LIFECYCLE ==========
    def __init__(self, subfolder: Path):
        self.logger = get_logger("pvapp")
        self.subfolder: Path = subfolder

        # Core configuration containers (populated by loaders)
        self.site: Optional[Site] = None
        self.module = None
        self.inverter = None
        self.mount: Optional[dict] = None
        self.grid: Optional[PlantPowerGrid] = None
        self.pv_setup_data: Optional[dict] = None

        # Arrays configuration: {array_idx -> {"modules_per_string": int, "strings_per_inverter": int, ...}}
        # Default non-crashing placeholder to avoid KeyError
        self.arrays: Dict[int, Dict[str, int]] | dict = {"": {"": None}}

        # Simulation holders
        self.sims: Union[Dict[int, Simulation], Simulation] = {}
        self.simresults: SimulationResults = SimulationResults()

        # Time index gets set in `run`
        self.times: Optional[pd.DatetimeIndex] = None

    # ========== PUBLIC API ==========
    @log_performance("Run_simulation")
    def run(
        self,
        times: Optional[pd.DatetimeIndex] = None,
    ) -> bool:
        """
        Entry point: loads configuration, builds and executes simulations, saves results,
        and (if available) runs grid — all under configurable time limits.

        Args:
            times: Optional custom DatetimeIndex for the simulation.
        """
        # Merge/validate timeouts

        run_start = time.perf_counter()

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

        # Early timeout check
        try:
            # 2) Define time range
            self._init_times(times)

            # 3) Build and run all simulations (guarded by build timeout internally)
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

    # ========== LOADERS ==========
    def load_site(self):
        """Load site.json and construct a `Site`."""
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

    def load_pvsetup(self):
        """Load plant.json and extract PV components and mount info."""
        plant_path = self.subfolder / "plant.json"
        self.logger.debug(f"[Simulator] Loading plant setup from: {plant_path}")

        if not plant_path.exists():
            raise FileNotFoundError(f"Missing plant.json in {self.subfolder}")

        try:
            with plant_path.open() as f:
                self.pv_setup_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in plant.json: {e}")

        # Load components
        self.module = self.load_component("module")
        self.mount = {
            "type": self.pv_setup_data["mount"]["type"],
            "params": self.pv_setup_data["mount"]["params"],
        }
        self.inverter = self.load_component("inverter")

        self.logger.debug(
            f"[Simulator] Plant setup loaded for '{self.pv_setup_data.get('name','<unnamed>')}'"
        )

    def load_grid(self):
        """Load grid.json and build a PlantPowerGrid if present."""
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

    def load_arrays(self):
        """
        Load arrays.json (optional). Keeps default placeholder `self.arrays` if missing.
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

    # ========== BUILDERS ==========
    def configure_pvsystem(
        self, modules_per_string: int = 1, strings: int = 1
    ) -> PVSystemManager:
        """
        Build a PVSystemManager for the current plant and mount settings.
        """
        if self.pv_setup_data is None:
            raise ValueError("PV setup data is not loaded.")

        try:
            pvsystem: PVSystemManager = PVSystemManager(
                name=self.pv_setup_data["name"],
                location=self.site,  # Site is an object (pvlib_plant_model.Site)
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
        Load a component (module or inverter) from plant.json either as:
          - Custom object passed directly (origin == 'Custom'), or
          - pvwatts inverter model (for inverter + origin == 'pvwatts'), or
          - A SAM database lookup via `retrieve_sam(origin.lower())[name]`
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
        Build and execute the pvlib ModelChain for each configured array.
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
                # Skip to next array but keep tracking placeholders
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

    # ========== EXECUTORS ==========
    @log_performance("pvlib_simulation")
    def simulate(self, modelchain: ModelChain):
        """
        Run pvlib's ModelChain using synthetic weather generated by `Nature`.
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
        weather = nature.weather_simulation(temp_air=25, wind_speed=1)
        modelchain.run_model(weather)

    @log_performance("pandapower_simulation")
    def merge_grid(self):
        """
        If a pandapower grid is configured, push array AC powers as sgen profiles and run a time-series power flow.
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

    def save_results(self):
        """
        Persist SimulationResults to disk inside `subfolder`.
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

    # ========== Helpers & Properties ==========
    def _init_times(self, times: Optional[pd.DatetimeIndex]) -> None:
        """
        Initialize `self.times` with a default 1-hour resolution year window if not provided.
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
        Pretty plant name for logs. Requires site and plant data to be loaded.
        """
        assert self.site is not None, "Site must be defined to get plant name."
        assert (
            self.pv_setup_data is not None
        ), "Plant data must be defined to get plant name."
        return f"[{self.site.name} : {self.pv_setup_data['name']}]"

    def _safe_plant_name(self) -> str:
        """
        Safe version for logging before the site/plant are fully loaded.
        """
        site_name = getattr(self.site, "name", "<site?>")
        plant_name = (
            self.pv_setup_data.get("name", "<plant?>")
            if self.pv_setup_data
            else "<plant?>"
        )
        return f"[{site_name} : {plant_name}]"
