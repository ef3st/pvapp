import streamlit as st
from pathlib import Path
import json
import pandas as pd
from pvlib.pvsystem import retrieve_sam
from simulation.simulator import Simulate
from analysis.implantanalyser import ImplantAnalyser
import pydeck as pdk
from ....utils.plots import plots
from ....utils.translation.traslator import translate
from ...page import Page


class ModuleManager(Page):
    def __init__(self, subfolder) -> None:
        super().__init__("module_manager")
        self.implant_file = subfolder / "implant.json"
        self.implant = json.load(self.implant_file.open())

    # ========= RENDERS =======
    def render_setup(self) -> bool:
        implant = self.implant
        implant["name"] = st.text_input(self.T("buttons.implant.name"), implant["name"])

        # Module configuration
        with st.expander(f"***{self.T("buttons.implant.module.title")}***", icon="⚡"):
            col1, col2 = st.columns(2)
            module_origins = ["CECMod", "SandiaMod", "pvwatts", "Custom"]
            origin_index = module_origins.index(implant["module"]["origin"])
            implant["module"]["origin"] = col1.selectbox(
                self.T("buttons.implant.module.origin"),
                module_origins,
                index=origin_index,
            )

            if implant["module"]["origin"] in ["CECMod", "SandiaMod"]:
                modules = retrieve_sam(implant["module"]["origin"])
                module_names = list(modules.columns)
                module_index = 0
                if implant["module"]["name"] in module_names:
                    module_index = module_names.index(implant["module"]["name"])
                implant["module"]["name"] = col2.selectbox(
                    self.T("buttons.implant.module.model"),
                    module_names,
                    index=module_index,
                )

                if st.checkbox(self.T("buttons.implant.module.details")):
                    st.code(modules[implant["module"]["name"]], language="json")

            else:
                implant["module"]["name"] = col2.text_input(
                    self.T("buttons.implant.module.name"), implant["module"]["name"]
                )
                sub1, sub2 = st.columns(2)
                implant["module"]["model"]["pdc0"] = sub1.number_input(
                    "pdc0 (W)",
                    value=float(implant["module"]["model"]["pdc0"]),
                    min_value=0.0,
                )
                implant["module"]["model"]["gamma_pdc"] = sub2.number_input(
                    "γ_pdc (%/C)",
                    value=float(implant["module"]["model"]["gamma_pdc"]),
                    min_value=0.0,
                )

            implant["module"]["dc_module"] = {"CECMod": "cec", "SandiaMod": "sapm"}.get(
                implant["module"]["origin"], "pvwatts"
            )

        # Inverter configuration
        with st.expander(
            f"***{self.T("buttons.implant.inverter.title")}***", icon="🔌"
        ):
            col1, col2 = st.columns(2)
            inverter_origins = ["cecinverter", "pvwatts", "Custom"]
            inv_index = inverter_origins.index(implant["inverter"]["origin"])
            implant["inverter"]["origin"] = col1.selectbox(
                self.T("buttons.implant.inverter.origin"),
                inverter_origins,
                index=inv_index,
            )

            if implant["inverter"]["origin"] == "cecinverter":
                inverters = retrieve_sam("cecinverter")
                inv_names = list(inverters.columns)
                inv_name_index = 0
                if implant["inverter"]["name"] in inv_names:
                    inv_name_index = inv_names.index(implant["inverter"]["name"])
                implant["inverter"]["name"] = col2.selectbox(
                    self.T("buttons.implant.inverter.model"),
                    inv_names,
                    index=inv_name_index,
                )

                if st.checkbox(self.T("buttons.implant.inverter.details")):
                    st.code(inverters[implant["inverter"]["name"]], language="json")
            else:
                implant["inverter"]["name"] = col2.text_input(
                    self.T("buttons.implant.inverter.name"), implant["inverter"]["name"]
                )
                implant["inverter"]["model"]["pdc0"] = st.number_input(
                    "pdc0 (W)",
                    value=float(implant["inverter"]["model"]["pdc0"]),
                    min_value=0.0,
                )

            implant["inverter"]["ac_model"] = (
                "cec" if implant["inverter"]["origin"] == "cecinverter" else "pvwatts"
            )
        self.mount_setting(implant["mount"])
        self.implant = implant
        return False

    def render_analysis(self): ...

    # ========= SUMUPS =======
    def get_scheme(self): ...
    def get_description(self): ...

    # ========= UTILITIES METHODS =======
    def save(self):
        keep_mount_params = {}
        if self.implant["mount"]["type"] == "FixedMount":
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
        self.implant["mount"]["params"] = {
            k: v
            for k, v in self.implant["mount"]["params"].items()
            if k in keep_mount_params
        }
        json.dump(self.implant, self.implant_file.open("w"), indent=4)

    # --------> SETUP <------
    def mount_setting(self, implant_mount):
        mount_opts = [
            "SingleAxisTrackerMount",
            "FixedMount",
            "ValidatedMount",
            "DevelopementMount",
        ]
        mount_index = mount_opts.index(implant_mount["type"])

        with st.expander(f"***{self.T("buttons.implant.mount.title")}***", icon="⚠️"):
            col1, col2 = st.columns([2, 1])
            with col1:
                implant_mount["type"] = st.selectbox(
                    self.T("buttons.implant.mount.type"), mount_opts, index=mount_index
                )
                if implant_mount["type"] == "FixedMount":
                    l, r = st.columns(2)
                    value = 30
                    if "surface_tilt" in implant_mount["params"]:
                        value = implant_mount["params"]["surface_tilt"]
                    tilt = l.number_input("Tilt", value=value)
                    implant_mount["params"]["surface_tilt"] = tilt
                    value = 270
                    if "surface_azimuth" in implant_mount["params"]:
                        value = implant_mount["params"]["surface_azimuth"]
                    azimuth = r.number_input("Azimuth", value=value)
                    implant_mount["params"]["surface_azimuth"] = azimuth
                else:
                    # implant_mount["type"] == "SingleAxisTrackerMount":
                    l, c, r, rr = st.columns(4)
                    value = 0
                    if "axis_tilt" in implant_mount["params"]:
                        value = implant_mount["params"]["axis_tilt"]
                    tilt = l.number_input("Tilt", value=value)
                    implant_mount["params"]["axis_tilt"] = tilt
                    value = 270
                    if "axis_azimuth" in implant_mount["params"]:
                        value = implant_mount["params"]["axis_azimuth"]
                    azimuth = c.number_input("Azimuth", value=value)
                    implant_mount["params"]["axis_azimuth"] = azimuth
                    value = 45
                    if "max_angle" in implant_mount["params"]:
                        value = implant_mount["params"]["max_angle"]
                    max_angle = r.number_input(
                        "Max Angle inclination",
                        value=float(value),
                        min_value=0.0,
                        max_value=90.0,
                    )
                    implant_mount["params"]["max_angle"] = max_angle
                    value = 0
                    if "cross_axis_tilt" in implant_mount["params"]:
                        value = implant_mount["params"]["cross_axis_tilt"]
                    cross_axis_tilt = rr.number_input(
                        "Surface angle",
                        value=float(value),
                        min_value=0.0,
                        max_value=90.0,
                    )
                    implant_mount["params"]["cross_axis_tilt"] = cross_axis_tilt
                    q, _, _, _, _ = st.columns([5, 2, 5, 2, 1])

                    value = 0.35
                    if "gcr" in implant_mount["params"]:
                        value = implant_mount["params"]["gcr"]
                    gcr = q.number_input(
                        "Ground Coverage Ratio",
                        value=value,
                        min_value=0.0,
                        max_value=1.0,
                    )
                    implant_mount["params"]["gcr"] = gcr
                    value = True
                    if "backtrack" in implant_mount["params"]:
                        value = implant_mount["params"]["backtrack"]
                    backtrack = st.toggle("Avoid shadings (backtrack)", value=value)
                    implant_mount["params"]["backtrack"] = backtrack

            with col2:
                plots.pv3d(tilt, azimuth)


# --------> ANALYSIS <------
