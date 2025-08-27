import streamlit as st
from pathlib import Path
import streamlit_antd_components as sac
from gui.utils.graphics.md_render import MarkdownStreamlitPage


import os


DOCS_PATH = Path("docs/")
GUI_PATH = Path("docs/gui/")
SIM_PATH = Path("docs/simulation")
PVLIB_PATH = Path("docs/pvlib")
PPOWER_PATH = Path("docs/pandapower")


MENU_MAP = {0: ("README.md", "house-door-fill"), 1: (None, "mortarboard-fill")}  # main
labels = ["Main"]


def render():
    # _,title,_ = st.columns([3,1,3])
    # with title:
    # sac.result(
    #     # "PVApp",
    #     # description="***PV Plant Simulator and Analyser***",
    #     icon=sac.BsIcon("sun", color="green", size=50),
    # )
    # sac.divider("HOME", align="center", icon=sac.BsIcon("house-door"))
    sac.divider(
        "",
        align="center",
        color="green",
        icon=sac.BsIcon(
            "sun",
            color="green",
            size=80,
        ),
        variant="dashed",
    )

    # sac.alert("Home: *PV Plant Analyser*",variant="quote-light", color="red", size=35, icon=sac.BsIcon("house-door",color="blue"))
    MarkdownStreamlitPage(
        "README.md", mode="native", page_title="PVApp Home"
    ).render_native_with_mermaid(
        mermaid_theme="dark",  # "dark", "forest", "neutral", "base"
        mermaid_height=None,  # None = altezza stimata automaticamente
    )  # st.markdown(content, unsafe_allow_html=True)
    # if readme_path.exists():
    #     with readme_path.open("r", encoding="utf-8") as f:
    #         content = f.read()
    # else:
    #     st.warning("README.md non trovato.")
