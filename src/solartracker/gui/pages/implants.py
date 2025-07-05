import streamlit as st
import pandas as pd
import json
from pathlib import Path
from .support import add_implant
import pydeck as pdk


def load_all_implants(folder: Path = Path("data/")) -> pd.DataFrame:
    rows = []

    for subfolder in sorted(folder.iterdir()):
        if not subfolder.is_dir():
            continue

        site_path = subfolder / "site.json"
        implant_path = subfolder / "implant.json"

        if not site_path.exists() or not implant_path.exists():
            continue  # ignora cartelle incomplete

        try:
            with site_path.open() as f:
                site = json.load(f)
            with implant_path.open() as f:
                implant = json.load(f)

            row = {
                "site_name": site["name"],
                "city": site["city"],
                "address": site["address"],
                "implant_name": implant["name"],
                "module": implant["module"]["name"],
                "inverter": implant["inverter"]["name"],
                "mount_type": implant["mount"]["type"],
                "coordinates": {
                    "lat": site["coordinates"]["lat"],
                    "lon": site["coordinates"]["lon"],
                },
            }
            rows.append(row)

        except Exception as e:
            print(f"Errore nella cartella {subfolder.name}: {e}")
            continue

    return pd.DataFrame(rows)


def render():
    st.title("💡 IMPLANTS")

    # Change page to add implant
    if "adding_implant" not in st.session_state:
        st.session_state.adding_implant = False

    if st.session_state.adding_implant:
        add_implant.render()

    else:

        df = load_all_implants()
        st.dataframe(
            df[["site_name", "implant_name", "module", "inverter", "mount_type"]]
        )

        # config_path = Path("data/implants_config.json")

        # # Verifica esistenza file
        # if not config_path.exists():
        #     st.error("❌ File implants_config.json non trovato.")
        #     return

        # try:
        #     with config_path.open("r") as f:
        #         implants_config = json.load(f)
        # except json.JSONDecodeError as e:
        #     st.error(f"❌ Errore nel file JSON: {e}")
        #     return

        # Normalizza e seleziona colonne chiave
        # df = pd.json_normalize(implants_config.values(), sep=".")[
        #     [
        #         "site.name",
        #         "site.owner",
        #         "site.address",
        #         "implant.name",
        #         "implant.module.name",
        #         "implant.inverter.name",
        #         "implant.mount_type",
        #     ]
        # ]

        # Mostra tabella
        # st.dataframe(df, use_container_width=True)

        # Pulsanti
        # col1, col2 = st.columns(2)
        # if col1.button("➕ Add Implant"):
        #     st.session_state.adding_implant = True
        # if col2.button("❌ Delete Implant"):
        #     st.warning("Funzione rimozione non ancora implementata.")

        show_implants_map(df)


def show_implants_map(df: pd.DataFrame):
    rows = []

    for imp in df.to_dict(orient="records"):
        try:
            address = imp["address"]
            city = imp["city"]
            site_name = imp["site_name"]
            lat = imp["coordinates"]["lat"]
            lon = imp["coordinates"]["lon"]
            rows.append(
                {
                    "site_name": site_name,
                    "address": address,
                    "city": city,
                    "lat": lat,
                    "lon": lon,
                }
            )
        except KeyError:
            continue

    if not rows:
        st.info("ℹ️ No valid implant found")
        return

    df = pd.DataFrame(rows)

    st.subheader("📌 Map")

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[lon, lat]",
        get_color="[255, 0, 0, 160]",
        get_radius=100,  # raggio base (in metri)
        radius_scale=1,  # scala dinamica rispetto allo zoom
        radius_min_pixels=5,  # dimensione minima sullo schermo (pixel)
        radius_max_pixels=25,  # dimensione massima sullo schermo (pixel)
        pickable=True,
    )

    tooltip = {
        "html": "<b>{site_name}</b><br/>Ad: {address}<br/>City: {city}",
        "style": {"backgroundColor": "white", "color": "black"},
    }

    view_state = pdk.ViewState(
        latitude=df["lat"].mean(), longitude=df["lon"].mean(), zoom=6, pitch=0
    )

    deck = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip)

    st.pydeck_chart(deck)
