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
from streamlit_elements import elements, mui, html

sys.dont_write_bytecode = True

def simulate_all(folder: Path = Path("data/")):
    from streamlit_elements import elements, mui, html
    # bar = st.progress(0, text="Simulations execution")
    
    l = len(sorted(folder.iterdir()))
    for i, subfolder in enumerate(sorted(folder.iterdir())):
        if subfolder.is_dir():
            Simulate(subfolder)
            # bar.progress((i+1)/l, text=f"Simulations {i+1}/{l} executed")
    # bar.empty()


def load_translation(lang):
    with open(f"src/solartracker/gui/i18n/{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)


def aviable_languages(folder: Path = Path("src/solartracker/gui/i18n/")) -> List:
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
        # with a.popover(f"🌍 {T('buttons.language')}"):
        if not "current_lang" in st.session_state:
            st.session_state.current_lang = "it"
        lang = st.segmented_control(
            " ",
            options=aviable_languages(),
            label_visibility="collapsed",
            default=st.session_state.current_lang,
        )
        # if lang is None:
        #     st.rerun()
        if lang and lang != st.session_state.current_lang:
            st.session_state.T = load_translation(lang)
            st.session_state.current_lang = lang
            st.rerun()

        if not "beta_tools" in st.session_state:
            st.session_state.beta_tools = False
        st.markdown(" ")
        if "menu" not in st.session_state:
            st.session_state.menu = 1

        options = T("menu") + (
            ["Real-time monitor  (beta)"] if st.session_state.get("beta_tools") else []
        )

        selected = option_menu(
            None,
            options=options,
            icons=["house", "tools", "bar-chart", "graph-up"][: len(options)],
            menu_icon="cast",
            default_index=(
                st.session_state.menu if st.session_state.menu < len(options) else 0
            ),
            key="option_menu",
        )
        if (
            selected
            != options[
                st.session_state.menu if st.session_state.menu < len(options) else 0
            ]
        ):
            st.session_state.menu = (
                options.index(selected) if selected in options else 0
            )

        with st.popover("🧰 Tools"):
            a, b = st.columns(2)
            if a.button(f"{T('buttons.simulate')}", icon="🔥"):
                simulate_all()
            b.toggle("🧬 β tools", key="beta_tools", on_change=st.rerun)

    # 🔁 Routing alle pagine
    if selected == options[0]:  # "Home"
        home.render()
    elif selected == options[1]:  # "Implants"
        pages["implants"].render()
    elif selected == options[2]:  # "Implants comparison"
        pages["implants_comparison"].render()
    elif selected == options[3]:  # "Implant performance"
        implant_performance.render()
    elif selected == options[-1]:
        implant_distribution()
