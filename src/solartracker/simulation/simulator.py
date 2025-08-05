import pandas as pd
from pvlib_implant_model.site import Site
from .nature import Nature
from pvlib_implant_model.implant import PVSystemManager
from pvlib_implant_model.modelchain import BuildModelChain
from pvlib.pvsystem import retrieve_sam
from analysis.database import Database
import json
from pathlib import Path
from utils.logger import get_logger

import json
from pathlib import Path
import pandas as pd


class Simulator:
    def __init__(self, subfolder: Path):
        self.logger = get_logger("solartracker")
        self.subfolder = subfolder
        self.site = None
        self.module = None
        self.modelchain = None
        self.database = Database()

    def run(self):
        try:
            try:
                self.load_site()
                self.load_implant()
            except Exception as e:
                self.logger.error(f"[Simulator] Loading error: {e}")
            else:
                self.logger.debug(
                    f"[Simulator] Simulator ready to simulate {self.plant_name}"
                )
            self.configure_implant()
            self.simulate()
            self.save_results()
        except (FileNotFoundError, KeyError, ValueError) as e:
            self.logger.error(
                f"[Simulator] Simulation failed for {self.plant_name}: {e}"
            )
        except Exception as e:
            self.logger.error(
                f"[Simulator] [UNEXPECTED ERROR] Simulator failed for {self.plant_name} -> {type(e).__name__}: {e}"
            )

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

    def load_implant(self):
        implant_path = self.subfolder / "implant.json"
        if not implant_path.exists():
            raise FileNotFoundError(f"Missing implant.json in {self.subfolder}")
        with implant_path.open() as f:
            self.data_implant = json.load(f)

        try:
            self.module = PVSystemManager(
                name=self.data_implant["name"],
                location=self.site,
                id=self.subfolder.name,
            )
        except KeyError as e:
            raise KeyError(f"Missing implant key: {e}")

    def configure_implant(self):
        module = self.load_component("module")
        inverter = self.load_component("inverter")

        mount_type = self.data_implant["mount"]["type"]
        mount_params = self.data_implant["mount"]["params"]

        self.module.setimplant(
            module=module, inverter=inverter, mount_type=mount_type, params=mount_params
        )

    def load_component(self, component: str):
        comp_data = self.data_implant[component]
        origin = comp_data.get("origin")
        if not origin:
            raise KeyError(f"Missing origin for {component}")

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

    def simulate(self):
        self.modelchain = BuildModelChain(
            system=self.module.system, site=self.site.site
        )

        times = pd.date_range(
            start="2024-03-01", end="2025-02-28", freq="1h", tz=self.site.site.tz
        )

        nature = Nature(self.site.site, times)
        weather = nature.weather_simulation(temp_air=25, wind_speed=1)
        self.modelchain.run_model(weather)
        self.logger.info(
            f"[Simulator] Simulation for Plant {self.plant_name} has been EXECUTED"
        )

    def save_results(self):
        self.database.add_modelchainresult(
            self.module.id,
            self.module.name,
            self.modelchain.results,
            "annual",
            mount=self.data_implant["mount"]["type"],
        )
        self.database.save(self.subfolder)
        self.logger.info(
            f"[Simulator] Simulation for Plant {self.plant_name} has been SAVED in /{self.subfolder}"
        )

    def reckon_grid(): ...

    @property
    def plant_name(self):
        return f"[{self.site["name"]} : {self.data_implant["name"]}]"
