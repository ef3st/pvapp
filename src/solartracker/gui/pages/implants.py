import streamlit as st
import pandas as pd
import json
from pathlib import Path
from .support import add_implant
import pydeck as pdk

def render():
    st.title("💡 IMPLANTS")

    # Inizializza stato per cambio modalità
    if "adding_implant" not in st.session_state:
        st.session_state.adding_implant = False

    if st.session_state.adding_implant:
        add_implant.render()

    else:
        # Path del file
        config_path = Path("data/implants_config.json")

        # Verifica esistenza file
        if not config_path.exists():
            st.error("❌ File implants_config.json non trovato.")
            return

        try:
            with config_path.open("r") as f:
                implants_config = json.load(f)
        except json.JSONDecodeError as e:
            st.error(f"❌ Errore nel file JSON: {e}")
            return

        # Normalizza e seleziona colonne chiave
        df = pd.json_normalize(
            implants_config.values(), 
            sep="."
        )[
            ["site.name", "site.owner", "site.address", 
             "implant.name", "implant.module.name", 
             "implant.inverter.name", "implant.mount_type"]
        ]

        # Mostra tabella
        st.dataframe(df, use_container_width=True)
        

        # Pulsanti
        col1, col2 = st.columns(2)
        if col1.button("➕ Add Implant"):
            st.session_state.adding_implant = True
        if col2.button("❌ Delete Implant"):
            st.warning("Funzione rimozione non ancora implementata.")

        show_implants_map()

def show_implants_map(config_path="data/implants_config.json"):
    config_file = Path(config_path)

    if not config_file.exists():
        st.warning("❗ File implants_config.json non trovato.")
        return

    try:
        with config_file.open() as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        st.error(f"Errore nel parsing JSON: {e}")
        return

    # Costruisci DataFrame con lat, lon, name
    rows = []
    for imp in data.values():
        try:
            coords = imp["site"]["coordinates"]
            name = imp["implant"]["name"]
            rows.append({
                "lat": coords["lat"],
                "lon": coords["lon"],
                "name": name
            })
        except KeyError:
            continue  # salta se mancano dati

    if not rows:
        st.info("ℹ️ Nessun impianto valido con coordinate trovato.")
        return

    df = pd.DataFrame(rows)

    # Versione avanzata con tooltip
    st.subheader("📌 Mappa interattiva con dettagli")

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_color='[255, 0, 0, 160]',
        get_radius=100,               # raggio base (in metri)
        radius_scale=1,               # scala dinamica rispetto allo zoom
        radius_min_pixels=5,          # dimensione minima sullo schermo (pixel)
        radius_max_pixels=50,         # dimensione massima sullo schermo (pixel)
        pickable=True
    )

    tooltip = {
        "html": "<b>{name}</b><br/>Lat: {lat}<br/>Lon: {lon}",
        "style": {
            "backgroundColor": "white",
            "color": "black"
        }
    }

    view_state = pdk.ViewState(
        latitude=df["lat"].mean(),
        longitude=df["lon"].mean(),
        zoom=6,
        pitch=0
    )

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip
    )

    st.pydeck_chart(deck)