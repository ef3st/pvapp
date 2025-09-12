from __future__ import annotations

from typing import Dict, Any

import json
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

from ...page import Page


# * =============================
# *         SITE MANAGER
# * =============================
class SiteManager(Page):
    """
    Manage site metadata (name, address, coordinates, altitude, timezone).

    Attributes:
        site_file (Path): Path to the site's JSON file.
        site (dict[str, Any]): Dictionary with current site data.
        change (bool): Internal flag indicating whether the site was modified.

    Methods:
        render_setup: Render editable UI for site configuration.
        render_analysis: Placeholder for analysis tab.
        get_scheme: Placeholder for scheme summary.
        get_description: Placeholder for description summary.
        save: Persist site.json to disk.
        changed: Mark the site as changed.
        return_changed: Reset and return whether changes occurred.
    """

    # * =========================================================
    # *                      LIFECYCLE
    # * =========================================================
    def __init__(self, subfolder: Path) -> None:
        """
        Initialize SiteManager with a given subfolder.

        Args:
            subfolder (Path): Plant subfolder containing site.json.
        """
        super().__init__("module_manager")
        self.site_file: Path = subfolder / "site.json"
        self.site: Dict[str, Any] = json.load(self.site_file.open())
        self.change: bool = False

    # * =========================================================
    # *                    RENDER METHODS
    # * =========================================================
    def render_setup(self) -> bool:
        """
        Render the Streamlit setup UI for the site.

        Returns:
            bool: True if changes occurred, False otherwise.
        """
        site = self.site.copy()

        # ---- Basic name ----
        site["name"] = st.text_input(
            self.T("buttons.site.name"),
            site["name"],
            on_change=self.changed,
        )

        # ---- Address / City ----
        with st.expander(f" 🏠 {self.T('subtitle.address')}"):
            site["address"] = st.text_input(
                self.T("buttons.site.address"),
                site["address"],
                on_change=self.changed,
            )
            site["city"] = st.text_input(
                self.T("buttons.site.city"),
                site["city"],
                on_change=self.changed,
            )

        # ---- Coordinates ----
        with st.expander(f" 🗺️ {self.T('subtitle.coordinates')}"):
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

            # Map preview
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
                radius_scale=2,  # Increases/decreases with zoom
                radius_min_pixels=3,  # Minimum visible radius
                radius_max_pixels=10,  # Maximum visible radius
            )
            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=view,
                tooltip={"text": "📍 Position"},
            )
            st.pydeck_chart(deck, use_container_width=False, height=300)

        # ---- Altitude / Timezone ----
        with st.expander(f" 🕐 {self.T('subtitle.altitude_tz')}"):
            site["altitude"] = st.number_input(
                f"{self.T('buttons.site.altitude')} (m)",
                value=site["altitude"],
                min_value=0,
                icon="🗻",
                on_change=self.changed,
            )
            site["tz"] = st.text_input(
                f"{self.T('buttons.site.timezone')}",
                site["tz"],
                icon="🕐",
                on_change=self.changed,
            )

        if not (self.site == site):
            self.site = site

        return self.return_changed()

    def render_analysis(self) -> None:
        """Placeholder for analysis tab."""
        raise NotImplementedError

    # * =========================================================
    # *                    SUMMARIES (STUBS)
    # * =========================================================
    def get_scheme(self) -> None:
        """Placeholder for scheme summary."""
        raise NotImplementedError

    def get_description(self) -> None:
        """Placeholder for description summary."""
        raise NotImplementedError

    # * =========================================================
    # *                        UTILITIES
    # * =========================================================
    def save(self) -> None:
        """
        Persist current site dict to site.json on disk.
        """
        json.dump(self.site, self.site_file.open("w"), indent=4)

    def changed(self) -> None:
        """
        Mark the site as changed in the current session.
        """
        self.change = True

    def return_changed(self) -> bool:
        """
        Reset and return whether changes occurred.

        Returns:
            bool: True if changes occurred since last call.
        """
        if self.change:
            self.change = False
            return True
        return False
