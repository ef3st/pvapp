from pathlib import Path
import json

import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit_antd_components as sac

from .add_plant import add_plant
from gui.pages import Page


# * =============================
# *          PLANTS PAGE
# * =============================
class PlantsPage(Page):
    """
    Streamlit page for listing, adding, and removing PV plants.

    Attributes:
        page_name (str): Page namespace for translations (inherited).
        logger: Logger instance (inherited).

    Methods:
        _load_plants: Load plant and site data from JSON files.
        _render_map: Visualize plants on a map using pydeck.
        render: Render the full page (with/without add section).
    """

    # * =========================================================
    # *                      LIFECYCLE
    # * =========================================================
    def __init__(self) -> None:
        """Initialize Plants page with translation namespace 'plants'."""
        super().__init__("plants")

    # * =========================================================
    # *                     DATA LOADING
    # * =========================================================
    def _load_plants(self, folder: Path = Path("data/")) -> pd.DataFrame:
        """
        Load plant and site data from JSON files.

        Args:
            folder (Path): Root folder containing plant subfolders.

        Returns:
            pd.DataFrame: Rows with site/plant/module/inverter/mount info + flags.
        """
        rows = []
        titles = self.T("df_title")  # list of column labels

        for subfolder in sorted(folder.iterdir()):
            if not subfolder.is_dir():
                continue

            site_path = subfolder / "site.json"
            plant_path = subfolder / "plant.json"
            simulation_path = subfolder / "simulation.csv"
            grid_path = subfolder / "grid.json"
            array_path = subfolder / "arrays.json"
            if not site_path.exists() or not plant_path.exists():
                continue

            simulated = simulation_path.exists()
            grid = grid_path.exists()
            array = array_path.exists()

            try:
                with site_path.open() as f:
                    site = json.load(f)
                with plant_path.open() as f:
                    plant = json.load(f)

                row = {
                    titles[0]: site["name"],
                    titles[1]: site["city"],
                    titles[2]: site["address"],
                    titles[3]: plant["name"],
                    titles[4]: plant["module"].get("name", ""),
                    titles[5]: plant["inverter"].get("name", ""),
                    titles[6]: plant["mount"].get("type", ""),
                    titles[7]: {
                        titles[8]: site["coordinates"].get("lat"),
                        titles[9]: site["coordinates"].get("lon"),
                    },
                    "Grid": "✅" if grid else "❌",
                    "Array": "✅" if array else "❌",
                    titles[10]: "✅" if simulated else "❌",
                }
                rows.append(row)

            except Exception as e:
                st.warning(f"{self.T('messages.folder_error')} {subfolder.name}: {e}")
                continue

        if not rows:
            rows.append({})
        return pd.DataFrame(rows)

    # * =========================================================
    # *                       RENDER PAGE
    # * =========================================================
    def render(self) -> None:
        """
        Render the Plants page, with conditional "add plant" section.

        Notes:
            - Uses session state flag `adding_plant`.
            - Supports two modes: list-only, or list + add form.
        """
        if "adding_plant" not in st.session_state:
            st.session_state.adding_plant = False

        if st.session_state.adding_plant:  # Page with "Add Plant" section
            main, lateral = st.columns([7, 5])

            with lateral:
                with st.container(border=True):
                    add_plant.render()
            with main:
                sac.alert(
                    self.T("title"),
                    variant="quote",
                    color="white",
                    size=35,
                    icon=sac.BsIcon("buildings", color="cyan"),
                )
                st.markdown("---")
                df = self._load_plants()

                if df.empty:
                    messages = self.T("messages.no_plant_found")
                    sac.result(messages[0], description=messages[1], status="empty")
                else:
                    titles = self.T("df_title")
                    columns_to_show = [titles[i] for i in [0, 3, 4, 5, 6, 10]] + [
                        "Grid",
                        "Array",
                    ]
                    st.dataframe(df[columns_to_show], use_container_width=True)
                    self._render_map(df)
            return

        # Page without "Add Plant" section
        sac.alert(
            self.T("title"),
            variant="quote",
            color="white",
            size=35,
            icon=sac.BsIcon("buildings", color="cyan"),
        )
        st.markdown("---")
        df = self._load_plants()

        items = [
            sac.ButtonsItem(
                self.T("buttons.add_plant"),
                icon=sac.BsIcon("building-add"),
                color="green",
            ),
            sac.ButtonsItem(
                self.T("buttons.remove_plant"),
                icon=sac.BsIcon("building-dash"),
                color="red",
            ),
        ]
        build_buttons = sac.buttons(
            items, variant="outline", align="start", return_index=True, index=None
        )
        if build_buttons == 0:
            st.session_state.adding_plant = True
            st.rerun()
        elif build_buttons == 1:
            sac.alert(
                "Command not performed yet",
                description=(
                    "To delete a plant, remove its folder in /data after verifying "
                    "the site and plant names in site.json and plant.json →‼️ DO NOT "
                    "delete the /data folder."
                ),
                closable=True,
                color="warning",
                variant="light",
                icon=sac.BsIcon("info-circle"),
            )

        if df.empty:
            messages = self.T("messages.no_plant_found")
            sac.result(messages[0], description=messages[1], status="empty")
            return

        titles = self.T("df_title")
        columns_to_show = [titles[i] for i in [0, 3, 4, 5, 6, 10]] + ["Grid", "Array"]
        st.dataframe(df[columns_to_show], use_container_width=True)
        self._render_map(df)

    # * =========================================================
    # *                        MAP RENDER
    # * =========================================================
    def _render_map(self, df: pd.DataFrame) -> None:
        """
        Visualize plant locations on a map using pydeck.

        Args:
            df (pd.DataFrame): DataFrame of plant metadata with coordinates.
        """
        titles = self.T("df_title")
        rows = []
        for row in df.to_dict(orient="records"):
            try:
                rows.append(
                    {
                        "site_name": row[titles[0]],
                        "address": row[titles[2]],
                        "city": row[titles[1]],
                        "lat": row[titles[7]][titles[8]],
                        "lon": row[titles[7]][titles[9]],
                    }
                )
            except KeyError:
                continue

        if not rows:
            st.info("ℹ️ No valid Plant for the map")
            return

        df_map = pd.DataFrame(rows)
        sac.divider(
            label=self.T("map.title"),
            icon=sac.BsIcon(name="crosshair", size=20),
            align="center",
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_map,
            get_position="[lon, lat]",
            get_color="[255, 0, 0, 160]",
            get_radius=100,
            radius_scale=1,
            radius_min_pixels=5,
            radius_max_pixels=25,
            pickable=True,
        )

        tooltip = {
            "html": "<b>{site_name}</b><br/>Ad: {address}<br/>City: {city}",
            "style": {"backgroundColor": "white", "color": "black"},
        }

        view_state = pdk.ViewState(
            latitude=df_map["lat"].mean(),
            longitude=df_map["lon"].mean(),
            zoom=6,
            pitch=0,
        )

        deck = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip)
        st.pydeck_chart(deck)
