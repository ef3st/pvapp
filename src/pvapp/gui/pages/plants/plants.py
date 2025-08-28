import streamlit as st
import streamlit_antd_components as sac
import json
from pathlib import Path

import pandas as pd
import pydeck as pdk

from .add_plant import add_plant
from gui.pages import Page


class PlantsPage(Page):
    def __init__(self):
        super().__init__("plants")

    def _load_plants(self, folder: Path = Path("data/")) -> pd.DataFrame:
        """Load plant and site data from JSON files."""
        rows = []

        titles = self.T("df_title")  # list of column labels
        for subfolder in sorted(folder.iterdir()):
            if not subfolder.is_dir():
                continue

            site_path = subfolder / "site.json"
            plant_path = subfolder / "plant.json"
            simulation_path = subfolder / "simulation.csv"
            grid_path = subfolder / "grid.json"
            array_path = subfolder / "array.json"
            if not site_path.exists() or not plant_path.exists():
                continue
            simulated = False
            grid = False
            array = False
            if simulation_path.exists():
                simulated = True
            if grid_path.exists():
                grid = True
            if array_path.exists():
                array = True
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
                st.warning(f"{self.T("messages.folder_error")} {subfolder.name}: {e}")
                continue

        if not rows:
            rows.append({})
        return pd.DataFrame(rows)

    def render(self):
        if "adding_plant" not in st.session_state:
            st.session_state.adding_plant = False

        if st.session_state.adding_plant:  # PAGE WITH ADD SECTION
            main, lateral = st.columns([7, 5])

            with lateral:
                with st.container(border=True):
                    add_plant.render()
            with main:
                # st.title("🏛️ " + self.T("title"))
                sac.alert(
                    self.T("title"),
                    variant="quote",
                    color="white",
                    size=35,
                    icon=sac.BsIcon("buildings", color="cyan"),
                )

                st.markdown("---")
                df = self._load_plants()

                # Show table with selected columns
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
        else:  # PAGE WITHOUT ADD SECTION
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
                    "Command not perfomed yet",
                    description=f"To delete a plant, delete its folder in /data after check the name of site and Plant in site.json and plant.json files →‼️ DO NOT delete the /data folder ",
                    closable=True,
                    color="warning",
                    variant="light",
                    icon=sac.BsIcon("info-circle"),
                )
            if df.empty:
                messages = self.T("messages.no_plant_found")
                sac.result(messages[0], description=messages[1], status="empty")
                return
            # Show table with selected columns
            titles = self.T("df_title")
            columns_to_show = [titles[i] for i in [0, 3, 4, 5, 6, 10]] + [
                "Grid",
                "Array",
            ]
            st.dataframe(df[columns_to_show], use_container_width=True)

            self._render_map(df)

    def _render_map(self, df: pd.DataFrame):
        """Visualize plant locations on a map."""
        import streamlit_antd_components as sac

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
