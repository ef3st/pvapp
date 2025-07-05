import streamlit as st
import json
from pathlib import Path

config_path = Path("data/implants_config.json")

def init_session():
    if "implant_step" not in st.session_state:
        st.session_state.implant_step = 0
        st.session_state.new_implant = {}

def save_implant():
    if config_path.exists():
        with open(config_path) as f:
            data = json.load(f)
    else:
        data = {}

    st.session_state.adding_implant = False
    new_id = str(len(data))
    data[new_id] = st.session_state.new_implant

    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)

    st.success("✅ Nuovo impianto salvato.")
    st.session_state.implant_step = 0
    st.session_state.new_implant = {}

def render():
    st.title("➕ Add New Implant")
    init_session()

    step = st.session_state.implant_step
    new_implant = st.session_state.new_implant

    if step == 0:
        name = st.text_input("📝 Implant Name")
        if st.button("Avanti"):
            if name:
                new_implant["implant"] = {"name": name}
                st.session_state.implant_step = 1
            else:
                st.warning("Inserisci un nome valido")

    elif step == 1:
        address = st.text_input("📍 Indirizzo impianto")
        if st.button("Avanti"):
            if address:
                new_implant.setdefault("site", {})["address"] = address
                st.session_state.implant_step = 2
            else:
                st.warning("Inserisci un indirizzo valido")

    elif step == 2:
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("🌐 Latitudine", format="%.6f")
        with col2:
            lon = st.number_input("🌐 Longitudine", format="%.6f")

        if st.button("Avanti"):
            new_implant["site"]["coordinates"] = {"lat": lat, "lon": lon}
            st.session_state.implant_step = 3

    elif step == 3:
        mount_type = st.selectbox("⚙️ Tipo tracker", [
            "FixedMount",
            "SingleAxisTrackerMount",
            "DualAxisTrackerMount"
        ])
        inverter_power = st.number_input("🔌 Potenza inverter (kW)", min_value=0)

        if st.button("Avanti"):
            new_implant["implant"]["mount_type"] = mount_type
            new_implant["implant"]["inverter"] = {"pdc0": inverter_power}
            st.session_state.implant_step = 4

    elif step == 4:
        st.markdown("### 🧾 Riepilogo")
        st.json(new_implant)

        col1, col2 = st.columns(2)
        if col1.button("✅ Salva impianto"):
            save_implant()
        if col2.button("🔄 Annulla"):
            st.session_state.implant_step = 0
            st.session_state.new_implant = {}
