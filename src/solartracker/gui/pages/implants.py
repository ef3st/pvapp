import streamlit as st
import pandas as pd
import json
from pathlib import Path
import pydeck as pdk

from .support import add_implant
from .page import Page


def translate(key: str) -> str | list:
    keys = key.split(".")
    result = st.session_state.get("T", {})
    for k in keys:
        if isinstance(result, dict) and k in result:
            result = result[k]
        else:
            return key  # fallback se manca qualcosa
    return result


def T(key: str) -> str | list:
    return translate(f"implants.{key}")


class ImplantsPage(Page):
    def _load_implants(self, folder: Path = Path("data/")) -> pd.DataFrame:
        """Load implant and site data from JSON files."""
        rows = []

        titles = T("df_title")  # list of column labels
        for subfolder in sorted(folder.iterdir()):
            if not subfolder.is_dir():
                continue

            site_path = subfolder / "site.json"
            implant_path = subfolder / "implant.json"
            simulation_path = subfolder / "simulation.csv"
            if not site_path.exists() or not implant_path.exists():
                continue
            simulated = False
            if simulation_path.exists():
                simulated = True
            try:
                with site_path.open() as f:
                    site = json.load(f)
                with implant_path.open() as f:
                    implant = json.load(f)

                row = {
                    titles[0]: site["name"],
                    titles[1]: site["city"],
                    titles[2]: site["address"],
                    titles[3]: implant["name"],
                    titles[4]: implant["module"].get("name", ""),
                    titles[5]: implant["inverter"].get("name", ""),
                    titles[6]: implant["mount"].get("type", ""),
                    titles[7]: {
                        titles[8]: site["coordinates"].get("lat"),
                        titles[9]: site["coordinates"].get("lon"),
                    },
                    titles[10]: "✅" if simulated else "❌",
                }
                rows.append(row)

            except Exception as e:
                st.warning(f"Errore nella cartella {subfolder.name}: {e}")
                continue

        if not rows:
            st.info("⚠️ No implant founded")
            rows.append(
                {
                    titles[0]: "",
                    titles[1]: "",
                    titles[2]: "",
                    titles[3]: "",
                    titles[4]: "",
                    titles[5]: "",
                    titles[6]: "",
                    titles[7]: {
                        titles[8]: 0,
                        titles[9]: 0,
                    },
                }
            )
        return pd.DataFrame(rows)

    def render(self):
        st.title("💡 " + T("title"))

        if "adding_implant" not in st.session_state:
            st.session_state.adding_implant = False

        if st.session_state.adding_implant:
            main, lateral = st.columns([7, 2])
                     
            with lateral:
                add_implant.render()
            with main:
                df = self._load_implants()

                # Show table with selected columns
                titles = T("df_title")
                columns_to_show = [titles[i] for i in [0, 3, 4, 5, 6, 10]]
                st.dataframe(df[columns_to_show], use_container_width=True)

                self._render_map(df)
                if df.empty:
                    st.info("ℹ️ Nessun impianto disponibile.")
                    return
            return
        else:
            df = self._load_implants()

            col1, col2, space = st.columns([2, 2, 15])
            if col1.button("➕ " + T("buttons.add_implant")):
                st.session_state.adding_implant = True
                st.rerun()
            if col2.button("➖ " + T("buttons.remove_implant")):
                st.warning(
                    "Non abbiate fretta, ci stiamo lavorando: per cancellare un impianto, cancellate la cartella relativa in data/ (⚠️NON CANCELLATE /data⚠️ - solo la cartella dell'impianto da eliminare)"
                )

            if df.empty:
                st.info("ℹ️ Nessun impianto disponibile.")
                return
            # Show table with selected columns
            titles = T("df_title")
            columns_to_show = [titles[i] for i in [0, 3, 4, 5, 6, 10]]
            st.dataframe(df[columns_to_show], use_container_width=True)

            self._render_map(df)

        # if st.session_state.adding_implant:
        #     add_implant.render()
        #     return
        # else:

    def _render_map(self, df: pd.DataFrame):
        """Visualize implant locations on a map."""
        titles = T("df_title")
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
            st.info("ℹ️ Nessun impianto valido per la mappa.")
            return

        df_map = pd.DataFrame(rows)
        st.subheader("📌 " + T("map.title"))

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
