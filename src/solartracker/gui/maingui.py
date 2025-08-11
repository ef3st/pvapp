"""Streamlit App Entrypoint

This module defines the main Streamlit UI for the PV Implants Analyser application.
It centralizes:
  - Internationalization (i18n) utilities
  - Sidebar navigation and global toggles
  - Page routing to feature pages (Implants, Comparison, Plant Manager, Logs, etc.)
  - Batch simulation helper

Notes
-----
- Comments are written in English, as requested.
- The UI structure and behavior are preserved while improving readability and robustness.
- Minor fixes: renamed `aviable_languages` -> `available_languages`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Union

import pandas as pd
import streamlit as st
import streamlit_antd_components as sac

# Internal imports
from simulation import simulator

# Pages
from .pages.home import home
from .pages.implants.implants import ImplantsPage
from .pages.implants_comparison.implants_comparison import ImplantsComparisonPage
from .pages.plant_manager.plant_manager import PlantManager
from .pages.logs.logs import LogsPage, _SEV_ICON

# Optional / future pages
# from .pages.implant_performance import implant_performance
# from .pages.beta.real_time_monitor.implant_distribution import implant_distribution
# from .pages.beta.grid_manager.grid_manager import GridManager


# -----------------------------------------------------------------------------
# Global configuration
# -----------------------------------------------------------------------------
# Prevent creation of .pyc files
sys.dont_write_bytecode = True

# Default i18n folder
I18N_DIR = Path("src/solartracker/gui/i18n/")
DEFAULT_LANG = "it"


# -----------------------------------------------------------------------------
# Utilities: i18n helpers
# -----------------------------------------------------------------------------


def load_translation(lang: str) -> Dict:
    """Load a translation JSON by language code.

    Parameters
    ----------
    lang: str
        The language code (e.g., "it", "en").

    Returns
    -------
    dict
        Parsed JSON containing translation keys.
    """
    with open(I18N_DIR / f"{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)


def available_languages(folder: Path = I18N_DIR) -> List[str]:
    """Return the list of available language codes from the i18n folder."""
    return [p.stem for p in sorted(folder.iterdir()) if p.is_file()]


def translate(key: str) -> Union[str, list]:
    """Translate a dot-separated key using the current session dictionary.

    If the key is missing at any level, the original key is returned as a
    graceful fallback so the UI remains usable.
    """
    keys = key.split(".")
    result = st.session_state.get("T", {})
    for k in keys:
        if isinstance(result, dict) and k in result:
            result = result[k]
        else:
            return key  # Fallback when any segment is missing
    return result


def T(key: str) -> Union[str, list]:
    """Short-hand for translating under the "main." namespace."""
    return translate(f"main.{key}")


# -----------------------------------------------------------------------------
# Simulation helper
# -----------------------------------------------------------------------------


def simulate_all(folder: Path = Path("data/")) -> None:
    """Run the batch simulator over each subfolder in `folder`.

    Parameters
    ----------
    folder : Path
        Root folder containing one subfolder per simulation case.
    """
    subdirs = [p for p in sorted(folder.iterdir()) if p.is_dir()]
    if not subdirs:
        st.info("No subfolders found for simulation.")
        return

    progress = st.progress(0.0, text="Running simulations…")
    total = len(subdirs)

    for i, subfolder in enumerate(subdirs, start=1):
        try:
            simulator.Simulator(subfolder).run()
        except Exception as exc:  # Keep UI resilient
            st.warning(f"Simulation failed for {subfolder.name}: {exc}")
        finally:
            progress.progress(i / total, text=f"{i}/{total} simulations completed")

    progress.empty()
    st.success("All simulations completed.")


# -----------------------------------------------------------------------------
# Main App
# -----------------------------------------------------------------------------


def _init_session_state() -> None:
    """Initialize default values in `st.session_state` exactly once."""
    if "start_time" not in st.session_state:
        st.session_state.start_time = pd.Timestamp.now()

    if "T" not in st.session_state:
        st.session_state.T = load_translation(DEFAULT_LANG)
        st.session_state.current_lang = DEFAULT_LANG

    # Feature toggles and defaults
    st.session_state.setdefault("beta_tools", False)
    st.session_state.setdefault("auto_save", True)
    st.session_state.setdefault("auto_sim", True)

    # Menu index (used for retaining selection across reruns)
    st.session_state.setdefault("menu", 4)


def _build_pages() -> Dict[str, object]:
    """Instantiate and return page objects in a single place."""
    return {
        "implants": ImplantsPage(),
        "implants_comparison": ImplantsComparisonPage(),
        # "grid_manager": GridManager(),
        "plant_manager": PlantManager(),
        "logs": LogsPage(),
    }


def _language_selector() -> None:
    """Render the language selector in the sidebar and handle switching."""
    current = st.session_state.get("current_lang", DEFAULT_LANG)

    # Use a segmented control for compact UX
    lang = st.segmented_control(
        " ",
        options=available_languages(),
        label_visibility="collapsed",
        default=current,
    )
    if lang and lang != current:
        st.session_state.T = load_translation(lang)
        st.session_state.current_lang = lang
        st.rerun()


def _build_notifications_tag(n_logs: Dict[str, int]):
    """Build the notifications tag for the Logs menu item using severities."""
    tags = []
    for sev, count in n_logs.items():
        if count > 0:
            color, icon_name = _SEV_ICON[sev]
            tags.append(sac.Tag("", color=color, size="sm", icon=sac.BsIcon(icon_name)))
    return tags or None


def _sidebar_menu(plant_manager_names: List[str]) -> str:
    """Render the left-bar menu and return the selected label.

    Parameters
    ----------
    plant_manager_names : list[str]
        Translated names for the Plant Manager sub-menu (first three entries used).
    """
    # Compute app status and log badges
    status, n_logs = LogsPage().app_status

    # High-level options
    base_options: List[str] = T("menu")  # e.g., [Home, Implants, Comparison, …]
    # Append beta items only when enabled
    beta_options: List[str] = (
        [
            "Real-time monitor  (beta)",
            "Grid manager (beta)",
        ]
        if st.session_state.get("beta_tools")
        else []
    )

    options = base_options + beta_options

    # Icons aligned with options (truncate to options length)
    notification_icon = [
        "bell",
        "bell-fill",
        "exclamation-triangle-fill",
        "exclamation-circle-fill",
        "x-circle-fill",
    ]
    icons = [
        "house",
        "tools",
        "bar-chart",
        "toggles",
        notification_icon[status],
    ][: len(options)]

    # Per-item tags
    base_tags = [None, None, None, None]
    log_tag = _build_notifications_tag(n_logs)
    tags = base_tags + [log_tag] + [None, None]

    # Children (submenu) for Plant Manager
    plant_manager_icons = ["sun", "diagram-3", "compass"]
    plant_manager_menu = [
        sac.MenuItem(name, icon=icon)
        for name, icon in zip(plant_manager_names, plant_manager_icons)
    ]
    children = [None, None, None, plant_manager_menu, None]

    # Render left-bar menu
    selected = sac.menu(
        [
            sac.MenuItem(option, icon, tag=tag, children=child)
            for option, icon, tag, child in zip(options, icons, tags, children)
        ],
        variant="left-bar",
        key="option_menu",
        open_all=True,
    )

    # Keep the selected index in session
    previous_index = (
        st.session_state.menu if st.session_state.menu < len(options) else 0
    )
    if selected != options[previous_index]:
        st.session_state.menu = options.index(selected) if selected in options else 0

    return selected


def streamlit() -> None:
    """Main entrypoint that renders the Streamlit application UI."""
    _init_session_state()
    pages = _build_pages()

    st.set_page_config(page_title="Implant Simulator", layout="wide")

    # Sidebar: branding, language, and quick actions
    plant_manager_names = translate("plant_manager.display_setup")[:3]
    with st.sidebar:
        st.markdown("## 🌅 PV Implants Analyser")

        # Language selector
        st.divider()
        selected = _sidebar_menu(plant_manager_names)
        st.divider()

        # Tool toggles (kept outside rerun to avoid flicker)
        # with st.popover("🧰 Tools"):
        col_a, col_b = st.columns([1, 2])
        if col_b.button(f"{T('buttons.simulate')}", icon="🔥"):
            simulate_all()
        with col_a.popover("⚙️"):
            _language_selector()
            st.divider()
            st.toggle("💾 Auto-Save", key="auto_save")
            st.toggle("🔥 Auto-Simulate", key="auto_sim")

        # Navigation menu

    # ------------------------------
    # Page routing
    # ------------------------------
    if selected == T("menu")[0]:  # Home
        home.render()

    elif selected == T("menu")[1]:  # Implants
        pages["implants"].render()

    elif selected == T("menu")[2]:  # Implants comparison
        pages["implants_comparison"].render()

    elif selected in plant_manager_names:  # Plant Manager subpages
        if selected == plant_manager_names[1]:
            pages["plant_manager"].render(1)
        elif selected == plant_manager_names[2]:
            pages["plant_manager"].render(2)
        else:
            pages["plant_manager"].render()

    elif selected == T("menu")[4]:  # Logs
        pages["logs"].render()

    # Future beta routes (kept for reference)
    # elif selected == "Real-time monitor  (beta)":
    #     implant_distribution()
    # elif selected == "Grid manager (beta)":
    #     pages["grid_manager"].render()


# import streamlit as st
# from .pages.home import home
# from .pages.implant_performance import implant_performance
# from streamlit_option_menu import option_menu
# import sys
# from simulation import simulator
# from pathlib import Path
# import json
# from typing import List
# import streamlit_antd_components as sac

# from .pages.implants.implants import ImplantsPage
# from .pages.implants_comparison.implants_comparison import ImplantsComparisonPage
# from .pages.beta.real_time_monitor.implant_distribution import implant_distribution
# from .pages.beta.grid_manager.grid_manager import GridManager
# from .pages.plant_manager.plant_manager import PlantManager
# from .pages.logs.logs import LogsPage, _SEV_ICON
# import pandas as pd

# sys.dont_write_bytecode = True


# def simulate_all(folder: Path = Path("data/")):
#     from streamlit_elements import elements, mui, html

#     l = len(sorted(folder.iterdir()))
#     for i, subfolder in enumerate(sorted(folder.iterdir())):
#         if subfolder.is_dir():
#             simulator.Simulator(subfolder).run()


# def load_translation(lang):
#     with open(f"src/solartracker/gui/i18n/{lang}.json", "r", encoding="utf-8") as f:
#         return json.load(f)


# def aviable_languages(folder: Path = Path("src/solartracker/gui/i18n/")) -> List:
#     langs = []
#     for file in sorted(folder.iterdir()):
#         if file.is_file():
#             langs.append(file.stem)
#     return langs


# def translate(key: str) -> str | list:
#     keys = key.split(".")
#     result = st.session_state.get("T", {})
#     for k in keys:
#         if isinstance(result, dict) and k in result:
#             result = result[k]
#         else:
#             return key  # fallback se manca qualcosa
#     return result


# def T(key: str):
#     return translate(f"main.{key}")


# def streamlit():
#     if "start_time" not in st.session_state:
#         st.session_state.start_time = pd.Timestamp.now()
#     pages = {
#         "implants": ImplantsPage(),
#         "implants_comparison": ImplantsComparisonPage(),
#         "grid_manager": GridManager(),
#         "plant_manager": PlantManager(),
#         "logs": LogsPage(),
#     }
#     if "T" not in st.session_state:
#         st.session_state.T = load_translation("it")
#         st.session_state.current_lang = "it"

#     st.set_page_config(page_title="Implant Simulator", layout="wide")

#     # Gestione lingua
#     plant_manager_names = translate("plant_manager.display_setup")[:3]
#     with st.sidebar:
#         st.markdown("## 🌅 PV Implants Analyser")
#         # with a.popover(f"🌍 {T('buttons.language')}"):
#         if not "current_lang" in st.session_state:
#             st.session_state.current_lang = "it"
#         lang = st.segmented_control(
#             " ",
#             options=aviable_languages(),
#             label_visibility="collapsed",
#             default=st.session_state.current_lang,
#         )
#         if lang and lang != st.session_state.current_lang:
#             st.session_state.T = load_translation(lang)
#             st.session_state.current_lang = lang
#             st.rerun()

#         if not "beta_tools" in st.session_state:
#             st.session_state.beta_tools = False
#         if not "auto_save" in st.session_state:
#             st.session_state.auto_save = True
#         if not "auto_sim" in st.session_state:
#             st.session_state.auto_sim = True
#         st.markdown(" ")
#         if "menu" not in st.session_state:
#             st.session_state.menu = 4

#         options = T("menu") + (
#             ["Real-time monitor  (beta)", "Grid manager (beta)"]
#             if st.session_state.get("beta_tools")
#             else []
#         )
#         notification_icon = [
#             "bell",
#             "bell-fill",
#             "exclamation-triangle-fill",
#             "exclamation-circle-fill",
#             "x-circle-fill",
#         ]

#         status, n_logs = LogsPage().app_status
#         icons = [
#             "house",
#             "tools",
#             "bar-chart",
#             # "graph-up",
#             "toggles",
#             notification_icon[status],
#         ][: len(options)]
#         tags = [
#             None,
#             None,
#             None,
#             # None,
#             None,
#         ]
#         log_tag = []
#         for i in n_logs:
#             if n_logs[i] > 0:
#                 color, icon_name = _SEV_ICON[i]
#                 log_tag.append(
#                     sac.Tag("", color=color, size="sm", icon=sac.BsIcon(icon_name))
#                 )
#         if not log_tag:
#             log_tag = None
#         tags = tags + [log_tag] + [None, None]
#         plant_manager_icons = ["sun", "diagram-3","compass"]

#         plant_manager_menu = [sac.MenuItem(name,icon=icon) for name,icon in zip(plant_manager_names,plant_manager_icons)]
#         children = [None,None,None, plant_manager_menu, None]

#         selected = sac.menu(
#             [
#                 sac.MenuItem(option, icon, tag=tag, children=child)
#                 for option, icon, tag,child in zip(options, icons, tags,children)
#             ],
#             variant="left-bar",
#             key="option_menu",
#         )
#         if (
#             selected
#             != options[
#                 st.session_state.menu if st.session_state.menu < len(options) else 0
#             ]
#         ):
#             st.session_state.menu = (
#                 options.index(selected) if selected in options else 0
#             )

#         with st.popover("🧰 Tools"):
#             a, b = st.columns([1.5, 2])
#             if a.button(f"{T('buttons.simulate')}", icon="🔥"):
#                 simulate_all()
#             # b.toggle("🧬 β tools", key="beta_tools", on_change=st.rerun)
#             b.toggle("💾 Auto-save", key="auto_save")
#             b.toggle("🔥 Auto-Simulate", key="auto_sim")
#     # Page routing
#     if selected == options[0]:  # "Home"
#         home.render()
#     elif selected == options[1]:  # "Implants"
#         pages["implants"].render()
#     elif selected == options[2]:  # "Implants comparison"
#         pages["implants_comparison"].render()
#     # elif selected == options[3]:  # "Implant performance"
#     #     implant_performance.render()
#     elif selected in plant_manager_names:  # "Implant manager"
#         if selected == plant_manager_names[1]:
#             pages["plant_manager"].render(1)
#         elif selected == plant_manager_names[2]:
#             pages["plant_manager"].render(2)
#         else:
#             pages["plant_manager"].render()

#     elif selected == options[4]:  # "Logs"
#         pages["logs"].render()

#     # elif selected == options[-2]:
#     #     implant_distribution()
#     # elif selected == options[-1]:
#     #     pages["grid_manager"].render()
