import streamlit as st
from pathlib import Path
import json
import pandas as pd
from pvlib.pvsystem import retrieve_sam
from simulation.simulator import Simulator
from analysis.plantanalyser import PlantAnalyser
import pydeck as pdk
from ....utils.plots import plots
from ....utils.translation.traslator import translate
from ...page import Page


class ModuleManager(Page):
    def __init__(self, subfolder) -> None:
        super().__init__("module_manager")
        self.plant_file: Path = subfolder / "plant.json"
        self.plant: dict = json.load(self.plant_file.open())
        self.change = False

    # ========= RENDERS =======
    def render_setup(self) -> bool:
        plant = self.plant.copy()
        plant["name"] = st.text_input(
            self.T("buttons.plant.name"), plant["name"], on_change=self.changed
        )

        # Module configuration
        with st.expander(f"***{self.T("buttons.plant.module.title")}***", icon="⚡"):
            col1, col2 = st.columns(2)
            module_origins = ["CECMod", "SandiaMod", "pvwatts", "Custom"]
            origin_index = module_origins.index(plant["module"]["origin"])
            plant["module"]["origin"] = col1.selectbox(
                self.T("buttons.plant.module.origin"),
                module_origins,
                index=origin_index,
                on_change=self.changed,
            )

            if plant["module"]["origin"] in ["CECMod", "SandiaMod"]:
                modules = retrieve_sam(plant["module"]["origin"])
                module_names = list(modules.columns)
                module_index = 0
                if plant["module"]["name"] in module_names:
                    module_index = module_names.index(plant["module"]["name"])
                plant["module"]["name"] = col2.selectbox(
                    self.T("buttons.plant.module.model"),
                    module_names,
                    index=module_index,
                    on_change=self.changed,
                )

                if st.checkbox(self.T("buttons.plant.module.details")):
                    st.code(modules[plant["module"]["name"]], language="json")

            else:
                plant["module"]["name"] = col2.text_input(
                    self.T("buttons.plant.module.name"),
                    plant["module"]["name"],
                    on_change=self.changed,
                )
                sub1, sub2 = st.columns(2)
                plant["module"]["model"]["pdc0"] = sub1.number_input(
                    "pdc0 (W)",
                    value=float(plant["module"]["model"]["pdc0"]),
                    min_value=0.0,
                    on_change=self.changed,
                )
                plant["module"]["model"]["gamma_pdc"] = sub2.number_input(
                    "γ_pdc (%/C)",
                    value=float(plant["module"]["model"]["gamma_pdc"]),
                    min_value=0.0,
                    on_change=self.changed,
                )

            plant["module"]["dc_module"] = {"CECMod": "cec", "SandiaMod": "sapm"}.get(
                plant["module"]["origin"], "pvwatts"
            )

        # Inverter configuration
        with st.expander(f"***{self.T("buttons.plant.inverter.title")}***", icon="🔌"):
            col1, col2 = st.columns(2)
            inverter_origins = ["cecinverter", "pvwatts", "Custom"]
            inv_index = inverter_origins.index(plant["inverter"]["origin"])
            plant["inverter"]["origin"] = col1.selectbox(
                self.T("buttons.plant.inverter.origin"),
                inverter_origins,
                index=inv_index,
                on_change=self.changed,
            )

            if plant["inverter"]["origin"] == "cecinverter":
                inverters = retrieve_sam("cecinverter")
                inv_names = list(inverters.columns)
                inv_name_index = 0
                if plant["inverter"]["name"] in inv_names:
                    inv_name_index = inv_names.index(plant["inverter"]["name"])
                plant["inverter"]["name"] = col2.selectbox(
                    self.T("buttons.plant.inverter.model"),
                    inv_names,
                    index=inv_name_index,
                    on_change=self.changed,
                )

                if st.checkbox(self.T("buttons.plant.inverter.details")):
                    st.code(inverters[plant["inverter"]["name"]], language="json")
            else:
                plant["inverter"]["name"] = col2.text_input(
                    self.T("buttons.plant.inverter.name"),
                    plant["inverter"]["name"],
                    on_change=self.changed,
                )
                plant["inverter"]["model"]["pdc0"] = st.number_input(
                    "pdc0 (W)",
                    value=float(plant["inverter"]["model"]["pdc0"]),
                    min_value=0.0,
                    on_change=self.changed,
                )

            plant["inverter"]["ac_model"] = (
                "cec" if plant["inverter"]["origin"] == "cecinverter" else "pvwatts"
            )
        self.mount_setting(plant["mount"])
        if not (self.plant == plant):
            self.plant = plant

        return self.return_changed()

    def render_analysis(self):
        path: Path = self.plant_file.parent / "simulation.csv"
        if path.exists():
            analyser = PlantAnalyser(self.plant_file.parent)
            plots.seasonal_plot(analyser.periodic_report(), "plant_performance")
            plots.time_plot(analyser.numeric_dataframe(), page="plant_performance")
        else:
            st.warning("⚠️ Simulation not perfermed")

    # ========= SUMUPS =======
    def get_scheme(self): ...
    def get_description(self): ...

    # ========= UTILITIES METHODS =======
    def save(self):
        with open(self.plant_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        keep_mount_params = {}
        if self.plant["mount"]["type"] == "FixedMount":
            keep_mount_params = {"surface_tilt", "surface_azimuth"}
        else:
            keep_mount_params = {
                "axis_tilt",
                "axis_azimuth",
                "max_angle",
                "backtrack",
                "gcr",
                "cross_axis_tilt",
            }
        self.plant["mount"]["params"] = {
            k: v
            for k, v in self.plant["mount"]["params"].items()
            if k in keep_mount_params
        }
        upload = self.plant.copy()
        json.dump(upload, self.plant_file.open("w"), indent=4)

    # --------> SETUP <------
    def changed(self):
        self.change = True

    def return_changed(self) -> bool:
        if self.change:
            self.change = False
            return True
        return False

    def mount_setting(self, plant_mount):
        mount_opts = [
            "SingleAxisTrackerMount",
            "FixedMount",
            "ValidatedMount",
            "DevelopementMount",
        ]
        mount_index = mount_opts.index(plant_mount["type"])

        with st.expander(f"***{self.T("buttons.plant.mount.title")}***", icon="⚠️"):
            col1, col2 = st.columns([2, 1])
            with col1:
                plant_mount["type"] = st.selectbox(
                    self.T("buttons.plant.mount.type"),
                    mount_opts,
                    index=mount_index,
                    on_change=self.changed,
                )
                if plant_mount["type"] == "FixedMount":
                    l, r = st.columns(2)
                    value = 30
                    if "surface_tilt" in plant_mount["params"]:
                        value = plant_mount["params"]["surface_tilt"]
                    tilt = l.number_input("Tilt", value=value, on_change=self.changed)
                    plant_mount["params"]["surface_tilt"] = tilt
                    value = 270
                    if "surface_azimuth" in plant_mount["params"]:
                        value = plant_mount["params"]["surface_azimuth"]
                    azimuth = r.number_input(
                        "Azimuth", value=value, on_change=self.changed
                    )
                    plant_mount["params"]["surface_azimuth"] = azimuth
                else:
                    # plant_mount["type"] == "SingleAxisTrackerMount":
                    l, c, r, rr = st.columns(4)
                    value = 0
                    if "axis_tilt" in plant_mount["params"]:
                        value = plant_mount["params"]["axis_tilt"]
                    tilt = l.number_input("Tilt", value=value, on_change=self.changed)
                    plant_mount["params"]["axis_tilt"] = tilt
                    value = 270
                    if "axis_azimuth" in plant_mount["params"]:
                        value = plant_mount["params"]["axis_azimuth"]
                    azimuth = c.number_input(
                        "Azimuth", value=value, on_change=self.changed
                    )
                    plant_mount["params"]["axis_azimuth"] = azimuth
                    value = 45
                    if "max_angle" in plant_mount["params"]:
                        value = plant_mount["params"]["max_angle"]
                    max_angle = r.number_input(
                        "Max Angle inclination",
                        value=float(value),
                        min_value=0.0,
                        max_value=90.0,
                        on_change=self.changed,
                    )
                    plant_mount["params"]["max_angle"] = max_angle
                    value = 0
                    if "cross_axis_tilt" in plant_mount["params"]:
                        value = plant_mount["params"]["cross_axis_tilt"]
                    cross_axis_tilt = rr.number_input(
                        "Surface angle",
                        value=float(value),
                        min_value=0.0,
                        max_value=90.0,
                        on_change=self.changed,
                    )
                    plant_mount["params"]["cross_axis_tilt"] = cross_axis_tilt
                    q, _, _, _, _ = st.columns([5, 2, 5, 2, 1])

                    value = 0.35
                    if "gcr" in plant_mount["params"]:
                        value = plant_mount["params"]["gcr"]
                    gcr = q.number_input(
                        "Ground Coverage Ratio",
                        value=value,
                        min_value=0.0,
                        max_value=1.0,
                        on_change=self.changed,
                    )
                    plant_mount["params"]["gcr"] = gcr
                    value = True
                    if "backtrack" in plant_mount["params"]:
                        value = plant_mount["params"]["backtrack"]
                    backtrack = st.toggle("Avoid shadings (backtrack)", value=value)
                    plant_mount["params"]["backtrack"] = backtrack

            with col2:
                plots.pv3d(tilt, azimuth)


# --------> ANALYSIS <------
