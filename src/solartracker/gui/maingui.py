import streamlit as st
from .pages import home, implant_performance, implants, implants_comparison
from streamlit_option_menu import option_menu
import sys
from simulator.simulator import Simulate
from pathlib import Path
import json
from typing import List
from .pages.implants import ImplantsPage
from .pages.implants_comparison import ImplantsComparisonPage

sys.dont_write_bytecode = True


def simulate_all(folder: Path = Path("data/")):
    for subfolder in sorted(folder.iterdir()):
        if subfolder.is_dir():
            Simulate(subfolder)

def load_translation(lang):
    with open(f"src/solartracker/gui/i18n/{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)
    
def aviable_language(folder: Path = Path("src/solartracker/gui/i18n/")) -> List:
    langs = []
    for file in sorted(folder.iterdir()):
        if file.is_file():
            langs.append(file.stem)
    return langs

def translate(key: str) -> str | list:
    keys = key.split(".")
    result = st.session_state.get("T", {})
    for k in keys:
        if isinstance(result, dict) and k in result:
            result = result[k]
        else:
            return key  # fallback se manca qualcosa
    return result

def T(key:str):
    return translate(f"main.{key}")

def streamlit():
    pages ={
        "implants": ImplantsPage(),
        "implants_comparison": ImplantsComparisonPage()
    }
    if "T" not in st.session_state:
        st.session_state.T = load_translation("it")
        st.session_state.current_lang = "it"

    st.set_page_config(page_title="Implant Simulator", layout="wide")

    # 🔤 Gestione lingua
    with st.sidebar:
        st.markdown("## 🌅 PV Implants Analyser")
        st.markdown("---")
        index = aviable_language().index(st.session_state.current_lang)
        lang = st.selectbox(f"🌍 {T('buttons.language')}", aviable_language(), key="language",index=index)

    # Caricamento traduzioni solo se cambiate
    if st.session_state.get("current_lang") != lang:
        st.session_state.T = load_translation(lang)
        st.session_state.current_lang = lang

    # 📋 Menu principale
    with st.sidebar:
        selected = option_menu(
            None,
            options=T("menu"),
            icons=["house", "tools", "bar-chart", "graph-up"],
            menu_icon="cast",
            default_index=1,
        )

        st.markdown("---")
        if st.button(f"🔥 {T('buttons.simulate')}"):
            simulate_all()

    # 🔁 Routing alle pagine
    if selected == T("menu")[0]:  # "Home"
        home.render()
    elif selected == T("menu")[1]:  # "Implants"
        pages["implants"].render()
    elif selected == T("menu")[2]:  # "Implants comparison"
        pages["implants_comparison"].render()
    elif selected == T("menu")[3]:  # "Implant performance"
        implant_performance.render()




