import streamlit as st
from pathlib import Path
import json
import pandas as pd
from pvlib.pvsystem import retrieve_sam
from backend.simulation.simulator import Simulator
from analysis.plantanalyser import PlantAnalyser
import pydeck as pdk
from ....utils.plots import plots
from ...page import Page


class SiteManager(Page):
    def __init__(self, subfolder) -> None:
        super().__init__("module_manager")
        self.site_file = subfolder / "site.json"
        self.site: dict = json.load(self.site_file.open())
        self.change = False

    # ========= RENDERS =======
    def render_setup(self) -> bool:
        site = self.site.copy()
        site["name"] = st.text_input(
            self.T("buttons.site.name"), site["name"], on_change=self.changed
        )
        with st.expander(f" 🏠 {self.T("subtitle.address")}"):
            site["address"] = st.text_input(
                self.T("buttons.site.address"), site["address"], on_change=self.changed
            )
            site["city"] = st.text_input(
                self.T("buttons.site.city"), site["city"], on_change=self.changed
            )

        with st.expander(f" 🗺️ {self.T("subtitle.coordinates")}"):
            col1, col2 = st.columns(2)
            site["coordinates"]["lat"] = col1.number_input(
                self.T("buttons.site.lat"),
                value=site["coordinates"]["lat"],
                format="%.4f",
                step=0.0001,
                on_change=self.changed,
            )
            site["coordinates"]["lon"] = col2.number_input(
                self.T("buttons.site.lon"),
                value=site["coordinates"]["lon"],
                format="%.4f",
                step=0.0001,
                on_change=self.changed,
            )
            df = pd.DataFrame(
                [{"lat": site["coordinates"]["lat"], "lon": site["coordinates"]["lon"]}]
            )
            view = pdk.ViewState(
                latitude=site["coordinates"]["lat"],
                longitude=site["coordinates"]["lon"],
                zoom=12,
            )

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=df,
                get_position="[lon, lat]",
                get_color="[255, 0, 0, 160]",
                get_radius=50,
                radius_scale=2,  # Aumenta/diminuisce con lo zoom
                radius_min_pixels=3,  # Dimensione minima visibile
                radius_max_pixels=10,  # Dimensione massima visibile
            )

            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=view,
                tooltip={"text": "📍 Posizione"},
            )

            st.pydeck_chart(deck, use_container_width=False, height=300)

        with st.expander(f" 🕐 {self.T("subtitle.altitude_tz")}"):
            site["altitude"] = st.number_input(
                f"{self.T("buttons.site.altitude")} (m)",
                value=site["altitude"],
                min_value=0,
                icon="🗻",
                on_change=self.changed,
            )
            site["tz"] = st.text_input(
                f"{self.T("buttons.site.timezone")}",
                site["tz"],
                icon="🕐",
                on_change=self.changed,
            )

        if not (self.site == site):
            self.site = site

        return self.return_changed()

    def render_analysis(self):
        raise NotImplementedError

    # ========= SUMUPS =======
    def get_scheme(self):
        raise NotImplementedError

    def get_description(self):
        raise NotImplementedError

    # ========= UTILITIES METHODS =======
    def save(self):
        json.dump(self.site, self.site_file.open("w"), indent=4)

    # --------> SETUP <------
    def changed(self):
        self.change = True

    def return_changed(self) -> bool:
        if self.change:
            self.change = False
            return True
        return False

    # --------> ANALYSIS <------
