from __future__ import annotations
from pathlib import Path
from typing import Any, Dict

import json
import pandas as pd
import streamlit as st
import pydeck as pdk
from pvlib.pvsystem import retrieve_sam

from backend.simulation.simulator import Simulator
from analysis.plantanalyser import PlantAnalyser
from ....utils.plots import plots
from ....utils.translation.traslator import translate
from ...page import Page


# * =============================
# *        MODULE MANAGER
# * =============================
class ModuleManager(Page):
    """
    Manage PV module, inverter, and mount settings for a plant.

    Attributes:
        plant_file (Path): Path to the plant.json file.
        plant (dict[str, Any]): Current plant configuration dictionary.
        change (bool): Flag indicating whether the configuration has changed.

    Methods:
        render_setup: Render editable UI for module/inverter/mount setup.
        render_analysis: Render plots from simulation results.
        render_data: Render raw simulation data.
        get_scheme: Placeholder for scheme summary.
        get_description: Placeholder for description summary.
        save: Persist plant.json with filtered mount parameters.
        changed: Mark the configuration as changed.
        return_changed: Reset and return change flag.
        mount_setting: Render UI for mount configuration.

    ---
    Notes:
    - This manager centralizes editing of the PV chain (DC → AC → Mount).
    - Some methods are placeholders and require proper implementation.

    TODO:
    - Implement `get_scheme()` to provide a visual summary of the PV setup.
    - Implement `get_description()` to return a textual overview of the configuration.
    - Improve 3D previews of mount geometry (currently minimal).
    - Validate inputs more robustly (e.g., numeric ranges, SAM model availability).
    - Support multiple arrays per plant (current design assumes a single array).
    """

    # * =========================================================
    # *                      LIFECYCLE
    # * =========================================================
    def __init__(self, subfolder: Path) -> None:
        """
        Initialize a ModuleManager for a given plant subfolder.

        Args:
            subfolder (Path): Directory containing plant.json.
        """
        super().__init__("module_manager")
        self.plant_file: Path = subfolder / "plant.json"
        self.plant: Dict[str, Any] = json.load(self.plant_file.open())
        self.change: bool = False

    # * =========================================================
    # *                        RENDERS
    # * =========================================================
    def render_setup(self) -> bool:
        """
        Render Streamlit UI for editing module, inverter, and mount.

        Returns:
            bool: True if changes occurred, False otherwise.
        """
        plant = self.plant.copy()

        # ---- Plant Name ----
        plant["name"] = st.text_input(
            self.T("buttons.plant.name"), plant["name"], on_change=self.changed
        )

        # ---- Module Configuration ----
        with st.expander(f"***{self.T('buttons.plant.module.title')}***", icon="⚡"):
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
                module_index = (
                    module_names.index(plant["module"]["name"])
                    if plant["module"]["name"] in module_names
                    else 0
                )
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

        # ---- Inverter Configuration ----
        with st.expander(f"***{self.T('buttons.plant.inverter.title')}***", icon="🔌"):
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
                inv_name_index = (
                    inv_names.index(plant["inverter"]["name"])
                    if plant["inverter"]["name"] in inv_names
                    else 0
                )
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

        # ---- Mount ----
        self.mount_setting(plant["mount"])

        if self.plant != plant:
            self.plant = plant

        return self.return_changed()

    def render_analysis(self) -> None:
        """Render seasonal and time plots from simulation results if available."""
        path: Path = self.plant_file.parent / "simulation.csv"
        if path.exists():
            analyser = PlantAnalyser(self.plant_file.parent)
            array = st.segmented_control(
                "Array selection",
                help="Select the array to analyse simulation results",
                options=analyser.array_ids,
                default=0,
            )
            plots.seasonal_plot(analyser.periodic_report(array), "plant_performance")
            plots.time_plot(analyser.numeric_dataframe(array), page="plant_performance")
        else:
            st.warning("⚠️ Simulation not performed")

    def render_data(self) -> None:
        """Render raw simulation data as a DataFrame if available."""
        path: Path = self.plant_file.parent / "simulation.csv"
        if path.exists():
            analyser = PlantAnalyser(self.plant_file.parent)
            array = st.segmented_control(
                "Array selection",
                help="Select the array to analyse simulation results",
                options=analyser.array_ids,
                default=0,
            )
            st.dataframe(analyser.arrays[array])
        else:
            st.warning("⚠️ Simulation not performed")

    # * =========================================================
    # *                         SUMMARIES
    # * =========================================================
    def get_scheme(self) -> None:
        """Placeholder for scheme summary."""
        raise NotImplementedError

    def get_description(self) -> None:
        """Placeholder for description summary."""
        raise NotImplementedError

    # * =========================================================
    # *                         UTILITIES
    # * =========================================================
    def save(self) -> None:
        """
        Persist current plant.json, filtering only relevant mount parameters.

        Notes:
        - Keeps only keys relevant to the chosen mount type.
        """
        with open(self.plant_file, "r", encoding="utf-8") as f:
            data = json.load(f)

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

    def changed(self) -> None:
        """Mark the module/inverter/mount as changed."""
        self.change = True

    def return_changed(self) -> bool:
        """
        Reset and return change flag.

        Returns:
            bool: True if changes occurred since last call.
        """
        if self.change:
            self.change = False
            return True
        return False

    def mount_setting(self, plant_mount: Dict[str, Any]) -> None:
        """
        Render Streamlit UI for mount configuration.

        Args:
            plant_mount (dict[str, Any]): Mount configuration dictionary.
        """
        mount_opts = [
            "SingleAxisTrackerMount",
            "FixedMount",
            "ValidatedMount",
            "DevelopementMount",
        ]
        mount_index = mount_opts.index(plant_mount["type"])

        with st.expander(f"***{self.T('buttons.plant.mount.title')}***", icon="⚠️"):
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
                    tilt = l.number_input(
                        "Tilt",
                        value=plant_mount["params"].get("surface_tilt", 30),
                        on_change=self.changed,
                    )
                    plant_mount["params"]["surface_tilt"] = tilt

                    azimuth = r.number_input(
                        "Azimuth",
                        value=plant_mount["params"].get("surface_azimuth", 270),
                        on_change=self.changed,
                    )
                    plant_mount["params"]["surface_azimuth"] = azimuth
                else:  # SingleAxisTrackerMount / other
                    l, c, r, rr = st.columns(4)
                    tilt = l.number_input(
                        "Tilt",
                        value=plant_mount["params"].get("axis_tilt", 0),
                        on_change=self.changed,
                    )
                    plant_mount["params"]["axis_tilt"] = tilt

                    azimuth = c.number_input(
                        "Azimuth",
                        value=plant_mount["params"].get("axis_azimuth", 270),
                        on_change=self.changed,
                    )
                    plant_mount["params"]["axis_azimuth"] = azimuth

                    max_angle = r.number_input(
                        "Max Angle inclination",
                        value=float(plant_mount["params"].get("max_angle", 45)),
                        min_value=0.0,
                        max_value=90.0,
                        on_change=self.changed,
                    )
                    plant_mount["params"]["max_angle"] = max_angle

                    cross_axis_tilt = rr.number_input(
                        "Surface angle",
                        value=float(plant_mount["params"].get("cross_axis_tilt", 0)),
                        min_value=0.0,
                        max_value=90.0,
                        on_change=self.changed,
                    )
                    plant_mount["params"]["cross_axis_tilt"] = cross_axis_tilt

                    q, _, _, _, _ = st.columns([5, 2, 5, 2, 1])
                    gcr = q.number_input(
                        "Ground Coverage Ratio",
                        value=plant_mount["params"].get("gcr", 0.35),
                        min_value=0.0,
                        max_value=1.0,
                        on_change=self.changed,
                    )
                    plant_mount["params"]["gcr"] = gcr

                    backtrack = st.toggle(
                        "Avoid shadings (backtrack)",
                        value=plant_mount["params"].get("backtrack", True),
                    )
                    plant_mount["params"]["backtrack"] = backtrack

            with col2:
                plots.pv3d(
                    plant_mount["params"].get("axis_tilt", 0),
                    plant_mount["params"].get("axis_azimuth", 270),
                )
