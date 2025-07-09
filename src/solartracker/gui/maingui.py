import streamlit as st
from .pages import home, implant_performance
from streamlit_option_menu import option_menu
import sys
from simulator.simulator import Simulate
from pathlib import Path
import json
from typing import List
from .pages.implants import ImplantsPage
from .pages.implants_comparison import ImplantsComparisonPage
from .pages.support.implant_distribution import implant_distribution

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


def T(key: str):
    return translate(f"main.{key}")


def streamlit():
    pages = {
        "implants": ImplantsPage(),
        "implants_comparison": ImplantsComparisonPage(),
    }
    if "T" not in st.session_state:
        st.session_state.T = load_translation("it")
        st.session_state.current_lang = "it"

    st.set_page_config(page_title="Implant Simulator", layout="wide")

    # 🔤 Gestione lingua
    with st.sidebar:
        st.markdown("## 🌅 PV Implants Analyser")
        st.markdown("---")
        a, b = st.columns(2)
        with a.popover(f"🌍 {T('buttons.language')}"):

            index = aviable_language().index(st.session_state.current_lang)

            lang = st.selectbox(
                "",
                aviable_language(),
                key="language",
                index=index,
            )
        with b.popover("🧰 Tools"):
            if st.button(f"🔥 {T('buttons.simulate')}"):
                simulate_all()

    # Caricamento traduzioni solo se cambiate
    if st.session_state.get("current_lang") != lang:
        st.session_state.T = load_translation(lang)
        st.session_state.current_lang = lang

    # 📋 Menu principale
    with st.sidebar:
        st.markdown(" ")
        selected = option_menu(
            None,
            options=T("menu") + ["Real-time monitor  (beta)"],
            icons=["house", "tools", "bar-chart", "graph-up"],
            menu_icon="cast",
            default_index=0,
        )

    # 🔁 Routing alle pagine
    if selected == T("menu")[0]:  # "Home"
        home.render()
    elif selected == T("menu")[1]:  # "Implants"
        pages["implants"].render()
    elif selected == T("menu")[2]:  # "Implants comparison"
        pages["implants_comparison"].render()
    elif selected == T("menu")[3]:  # "Implant performance"
        implant_performance.render()
    elif "Real-time monitor (beta)":
        implant_distribution()
