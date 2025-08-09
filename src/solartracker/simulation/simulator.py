import pandas as pd
from pvlib_implant_model.site import Site
from .nature import Nature
from pvlib_implant_model.implant import PVSystemManager
from pandapower_network.pvnetwork import PlantPowerGrid
from pvlib_implant_model.modelchain import BuildModelChain
from pvlib.modelchain import ModelChain
from pvlib.pvsystem import retrieve_sam
from analysis.database import SimulationResults
import json
from pathlib import Path
from utils.logger import get_logger
import json
from pathlib import Path
import pandas as pd
from typing import Optional, List, Literal, Union, TypedDict


class Simulation(TypedDict, total=False):
    pvsystem: PVSystemManager
    modelchain: Optional[ModelChain]


class Simulator:
    def __init__(self, subfolder: Path):
        self.logger = get_logger("solartracker")
        self.subfolder: Path = subfolder
        self.site: Site = None
        self.module = None
        self.grid: PlantPowerGrid = None
        self.arrays = {"": {"": None}}  # Default empty dict to avoid KeyError
        self.mount: dict = None
        self.pv_setup_data: dict = None
        self.sims: Union[dict[int, Simulation], Simulation, None] = None
        self.simresults: SimulationResults = SimulationResults()

    def run(self, times: Optional[pd.DatetimeIndex] = None):
        try:
            try:
                self.load_site()
                self.load_pvsetup()
                self.load_grid()
                self.load_arrays()
            except Exception as e:
                self.logger.error(f"[Simulator] Loading error: {e}")
            else:
                self.logger.debug(
                    f"[Simulator] Simulator ready to simulate {self.plant_name}"
                )
            # self.configure_pvsystem()
            if times is None:
                self.times: pd.DatetimeIndex = pd.date_range(
                    start="2024-03-01",
                    end="2025-02-28",
                    freq="1h",
                    tz=self.site.site.tz,
                    name="annual_01_03_24",
                )
            else:
                self.times = times
            self.build_simulation()
            self.save_results()
        except (FileNotFoundError, KeyError, ValueError) as e:
            self.logger.error(
                f"[Simulator] Simulation failed for {self.plant_name}: {e}"
            )
            return
        except Exception as e:
            self.logger.error(
                f"[Simulator] [UNEXPECTED ERROR] Simulator failed for {self.plant_name} -> {type(e).__name__}: {e}"
            )
            return

    def load_site(self):
        site_path = self.subfolder / "site.json"
        if not site_path.exists():
            raise FileNotFoundError(f"Missing site.json in {self.subfolder}")
        with site_path.open() as f:
            data_site = json.load(f)

        try:
            self.site = Site(
                name=data_site["name"],
                coordinates=(
                    data_site["coordinates"]["lat"],
                    data_site["coordinates"]["lon"],
                ),
                altitude=data_site["altitude"],
                tz=data_site["tz"],
            )
        except KeyError as e:
            raise KeyError(f"Missing site key: {e}")

    def load_pvsetup(self):
        plant_path = self.subfolder / "implant.json"
        if not plant_path.exists():
            raise FileNotFoundError(f"Missing implant.json in {self.subfolder}")
        with plant_path.open() as f:
            self.pv_setup_data = json.load(f)

        self.module = self.load_component("module")
        self.mount = {
            "type": self.pv_setup_data["mount"]["type"],
            "params": self.pv_setup_data["mount"]["params"],
        }
        self.inverter = self.load_component("inverter")

    def load_grid(self):
        grid_path: Path = self.subfolder / "grid.json"
        if grid_path.exists():
            try:
                self.grid = PlantPowerGrid(grid_path)
            except Exception as e:
                raise Exception(f" Error in loading grid: {e}")

    def load_arrays(self):
        arrays_path: Path = self.subfolder / "arrays.json"

        if arrays_path.exists():
            try:
                self.arrays: dict[int, dict[str, int]] = json.load(arrays_path.open())
            except Exception as e:
                raise Exception(f" Error in loading arrays: {e}")

    def configure_pvsystem(
        self, modules_per_string: int = 1, strings: int = 1
    ) -> PVSystemManager:
        try:
            pvsystem: PVSystemManager = PVSystemManager(
                name=self.pv_setup_data["name"],
                location=self.site,
                # You can set owner, descriprion, or id if needed
                # id=self.subfolder.name,
            )
        except KeyError as e:
            raise KeyError(f"Error in defining PVSystemManager: {e}")

        if not self.module is None:
            pvsystem.set_pv_components(
                module=self.module,
                inverter=self.inverter,
                mount_type=self.mount["type"],
                params=self.mount["params"],
                modules_per_string=modules_per_string,
                strings=strings,
            )
        else:
            raise ValueError("Module is not defined. Cannot set PV Array.")

    def load_component(self, component: Literal["module", "inverter"]):
        #! CHECK WHAT HAPPENS HERE
        comp_data: dict = self.pv_setup_data[component]
        origin = comp_data.get("origin")
        if not origin:
            raise KeyError(f"Missing origin for {component}")
        if component == "inverter" and origin == "cecinverter":
            raise ValueError(
                "CecInverters are not supported in this simulator. Please use a different inverter."
            )

        if origin == "Custom" or (component == "inverter" and origin == "pvwatts"):
            return comp_data.get("model")
        else:
            try:
                sam_data = retrieve_sam(origin.lower())
                return sam_data[comp_data["name"]]
            except KeyError:
                raise ValueError(
                    f"{component.capitalize()} '{comp_data['name']}' not found in {origin} database."
                )

    def build_simulation(self):
        if self.module is None or self.site is None or self.mount is None:
            raise ValueError(
                "Module or site or Mount are not defined. Cannot simulate."
            )
        else:

            if self.grid is not None:
                if self.arrays == {"": {"": None}}:
                    self.logger.warning(
                        "Missing pv 'arrays' data, but grid is defined."
                    )

            # Simulate each array in the plant
            for array_idx in self.arrays:
                try:
                    module_per_string = self.arrays[array_idx].get(
                        "modules_per_string", 1
                    )
                    strings = self.arrays[array_idx].get("strings_per_inverter", 1)
                    pvsydsystem = self.configure_pvsystem(module_per_string, strings)
                    modelchain = BuildModelChain(
                        system=pvsydsystem.getimplant(), site=self.site.location
                    )
                except Exception as e:
                    self.logger.warning(
                        f"[Simulator] Simulation for sgen {array_idx} in plant {self.plant_name} not performed due to following errors(s): {e}"
                    )
                    pass
                self.sims[array_idx] = {
                    "pvsystem": pvsydsystem,
                    "modelchain": modelchain,
                }
                try:
                    self.simulate(modelchain)
                except Exception as e:
                    self.logger.warning(
                        f"[Simulator] Simulation for pvArray {array_idx} in plant {self.plant_name} not performed due to following errors(s) during simulation: {e}"
                    )
                    pass
                self.simresults.add_modelchainresult(
                    pvSystemId=array_idx,
                    results=modelchain.results,
                    period=self.times.name,
                )
                self.logger.debug(
                    f"[Simulator] Simulation for pvArray {array_idx} of Plant {self.plant_name} has been EXECUTED"
                )

            self.reckon_grid()

            self.logger.info(
                f"[Simulator] Simulation for Plant {self.plant_name} has been EXECUTED"
            )

    def simulate(self, modelchain: ModelChain):
        if modelchain is None:
            raise ValueError(
                "[Simulator] Modelchain is not defined. Cannot run simulation."
            )
        nature = Nature(self.site.location, self.times)
        weather = nature.weather_simulation(temp_air=25, wind_speed=1)
        modelchain.run_model(weather)

    def save_results(self):
        if self.simresults.is_empty:
            self.logger.warning("[Simulator] Nothing to save. No results found.")
            return
        else:
            self.simresults.save(self.subfolder)
            self.logger.info(
                f"[Simulator] Simulation results for Plant {self.plant_name} has been SAVED in /{self.subfolder}/simulation.csv"
            )

    def reckon_grid(self):
        if not self.grid is None:
            ac_power_values = self.simresults.get_acPowers_perTime_perArray() / 1e6
            self.grid.create_controllers(element="sgen", data_source=ac_power_values)
            self.grid.runnet(timeseries=True)
        # TO ADD RESUTLS TO simulation results

    @property
    def plant_name(self):
        assert self.site is not None, "Site must be defined to get plant name."
        assert self.pv_setup_data is not None, "Implant data must be defined to get"
        return f"[{self.site.name} : {self.pv_setup_data["name"]}]"
