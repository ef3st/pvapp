# * =============================
# *             HOME
# * =============================

"""
Home page for the Streamlit PVApp.

Features
--------
- Displays main README content (markdown with images + mermaid support).
- Provides decorative header with icons and dividers.
"""

from pathlib import Path
import os

import streamlit as st
import streamlit_antd_components as sac

from gui.utils.graphics.md_render import MarkdownStreamlitPage


# * =========================================================
# *                       CONSTANTS
# * =========================================================
DOCS_PATH = Path("docs/")
GUI_PATH = Path("docs/gui/")
SIM_PATH = Path("docs/simulation")
PVLIB_PATH = Path("docs/pvlib")
PPOWER_PATH = Path("docs/pandapower")

# Main menu: index → (doc file, icon)
MENU_MAP = {
    0: ("README.md", "house-door-fill"),
    1: (None, "mortarboard-fill"),
}
labels = ["Main"]


# * =========================================================
# *                        RENDER
# * =========================================================
def render() -> None:
    """
    Render the Home page.

    Notes:
        - Displays a green sun icon divider.
        - Renders README.md as advanced markdown (images + mermaid).
    """
    sac.divider(
        "",
        align="center",
        color="green",
        icon=sac.BsIcon("sun", color="green", size=80),
        variant="dashed",
    )

    MarkdownStreamlitPage("README.md", page_title="PVApp Home").render_advanced(
        inline_images=True,
        enable_mermaid=True,
    )

    # // Old design code (kept for reference):
    # // sac.result("PVApp", description="***PV Plant Simulator and Analyser***", icon=sac.BsIcon("sun", color="green", size=50))
    # // sac.divider("HOME", align="center", icon=sac.BsIcon("house-door"))
    # // if readme_path.exists():
    # //     with readme_path.open("r", encoding="utf-8") as f:
    # //         content = f.read()
    # // else:
    # //     st.warning("README.md not found.")
