"""Streamlit App Entrypoint

This module defines the main Streamlit UI for the PV Plants Analyser application.
It centralizes:
  - Internationalization (i18n) utilities
  - Sidebar navigation and global toggles
  - Page routing to feature pages (Plants, Comparison, Plant Manager, Logs, etc.)
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
import math
import streamlit as st
import streamlit_antd_components as sac


# Internal imports
from backend.simulation import simulator

# Pages
from .pages.home import home
from .pages.plants.plants import PlantsPage
from .pages.plants_comparison.plants_comparison import PlantsComparisonPage
from .pages.plant_manager.plant_manager import PlantManager
from .pages.logs.logs import LogsPage, _SEV_ICON
from .pages.guide import guide
from .utils.graphics.feedback_form import write_to_developer


# -----------------------------------------------------------------------------
# Global configuration
# -----------------------------------------------------------------------------
# Prevent creation of .pyc files
sys.dont_write_bytecode = True

# Default i18n folder
I18N_DIR = Path("src/pvapp/gui/i18n/")
DEFAULT_LANG = "en"


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
    sac.alert(
        "All simulations completed.",
        icon=sac.BsIcon("info-circle"),
        color="green",
        closable=True,
    )


# -----------------------------------------------------------------------------
# Main App
# -----------------------------------------------------------------------------


def _init_session_state() -> None:
    """Initialize default values in `st.session_state` exactly once."""
    if "start_time" not in st.session_state:
        st.session_state.start_time = pd.Timestamp.now()
    if "notification_time" not in st.session_state:
        st.session_state.notification_time = st.session_state.start_time

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
        "plants": PlantsPage(),
        "plants_comparison": PlantsComparisonPage(),
        # "grid_manager": GridManager(),
        "plant_manager": PlantManager(),
        "logs": LogsPage(),
    }


def flag_for(code: str) -> str:
    """
    Return an emoji flag for a language code. Fallback to 🌐 if unknown.
    Note: 'en' is mapped to 🇬🇧 by convention here; change to 🇺🇸 if you prefer.
    """
    code = (code or "").lower()
    mapping = {
        "it": "🇮🇹",
        "en": "🇬🇧",
        "es": "🇪🇸",
        "fr": "🇫🇷",
        "de": "🇩🇪",
        "pt": "🇵🇹",
        "zh": "🇨🇳",
        "ja": "🇯🇵",
        "ko": "🇰🇷",
        "ru": "🇷🇺",
        "ar": "🇸🇦",
        "hi": "🇮🇳",
    }
    return mapping.get(code, "🌐")


def flag_for(code: str) -> str:
    """Return an emoji flag for a language code. Fallback to 🌐 if unknown."""
    code = (code or "").lower()
    mapping = {
        "it": "🇮🇹",
        "en": "🇬🇧",
        "es": "🇪🇸",
        "fr": "🇫🇷",
        "de": "🇩🇪",
        "pt": "🇵🇹",
        "zh": "🇨🇳",
        "ja": "🇯🇵",
        "ko": "🇰🇷",
        "ru": "🇷🇺",
        "ar": "🇸🇦",
        "hi": "🇮🇳",
    }
    return mapping.get(code, "🌐")


def _language_selector(max_per_group: int = 5) -> None:
    """
    Split languages across multiple segmented controls (max `max_per_group` each),
    but behave like a single global selector (only one selected at a time).
    """
    current = st.session_state.get("current_lang", DEFAULT_LANG)

    # Build canonical lists
    codes = available_languages()
    labels = [f"{flag_for(c)} {c.upper()}" for c in codes]
    code2label = dict(zip(codes, labels))
    label2code = dict(zip(labels, codes))

    # Helper: chunk lists maintaining pairing
    def chunks(seq, n):
        for i in range(0, len(seq), n):
            yield seq[i : i + n]

    code_groups = list(chunks(codes, max_per_group))
    label_groups = list(chunks(labels, max_per_group))

    # Ensure current exists; fallback if not
    if current not in codes and codes:
        current = codes[0]
        st.session_state["current_lang"] = current

    current_label = code2label.get(current)

    # We’ll track if user changed a group this run
    new_lang = None

    for gi, (g_codes, g_labels) in enumerate(zip(code_groups, label_groups)):
        group_key = f"lang_selector_{gi}"

        # If current is in this group -> show it selected.
        # For all other groups, we "clear" their widget state before rendering
        # so they don't keep a stale selection.
        if current in g_codes:
            default_label = current_label
        else:
            # remove any stale selection stored by Streamlit for this group
            if group_key in st.session_state:
                st.session_state.pop(group_key, None)
            default_label = None  # render without explicit default

        # Render the segmented control
        # Note: only pass `default` when we actually want a pre-selected button.
        if default_label is not None and default_label in g_labels:
            sel_label = st.segmented_control(
                group_key,
                options=g_labels,
                label_visibility="collapsed",
                default=default_label,
            )
        else:
            sel_label = st.segmented_control(
                group_key,
                options=g_labels,
                label_visibility="collapsed",
            )

        # If user clicked something in this group, we’ll pick it up here
        # (only consider a change if the selection differs from current)
        sel_code = label2code.get(sel_label)
        if sel_code and sel_code != current:
            new_lang = sel_code

    # Apply language change if any
    if new_lang and new_lang != current:
        st.session_state.T = load_translation(new_lang)
        st.session_state.current_lang = new_lang
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
    """Render the left-bar menu and return the selected ROUTE KEY (stable)."""
    sidebar_mode = st.session_state.get("sidebar", "main")
    if sidebar_mode == "main":
        # ---------- App status & log badges ----------
        status, n_logs = LogsPage().app_status
        notification_icon = [
            "app",
            "app-indicator",
            "exclamation-triangle-fill",
            "exclamation-circle-fill",
            "x-circle-fill",
        ]
        log_color = ["#467146", "#6170d5", "#dfbe6a", "#df6a6a", "#ea36cf"]

        # ---------- Translated labels ----------
        base_options: List[str] = T("menu")
        if not isinstance(base_options, list) or len(base_options) < 6:
            base_options = [
                "Home",
                "Plants",
                "Comparison",
                "Plant Manager",
                "Guide",
                "Logs",
            ]

        beta_enabled = st.session_state.get("beta_tools", False)
        beta_options = (
            ["Real-time monitor  (beta)", "Grid manager (beta)"] if beta_enabled else []
        )
        options = base_options + beta_options

        # ---------- Stable keys (same order as options) ----------
        base_keys = ["home", "plants", "compare", "plant_manager", "guide", "logs"]
        beta_keys = ["realtime_beta", "grid_beta"] if beta_enabled else []
        route_keys = base_keys[: len(base_options)] + beta_keys

        # ---------- Icons / colors ----------
        icons = [
            "house",
            "buildings",
            "bar-chart-steps",
            "building-fill-gear",
            "journal-text",
            notification_icon[status],
        ]
        icons = icons[: len(base_options)] + (
            ["activity", "diagram-3"] if beta_enabled else []
        )
        color_map = {
            "home": "green",
            "plants": "white",
            "compare": "skyblue",
            "plant_manager": "orange",
            "guide": "green",
            "logs": log_color[status],
            "realtime_beta": "blue",
            "grid_beta": "blue",
        }

        # ---------- Plant Manager children ----------
        if isinstance(plant_manager_names, str):
            plant_manager_names = [plant_manager_names]
        elif not isinstance(plant_manager_names, list):
            plant_manager_names = []
        pm_labels = (plant_manager_names + ["", "", ""])[:3]
        pm_keys = ["pm_setup", "pm_topology", "pm_geo"]
        pm_icons = ["sun", "diagram-3", "compass"]
        pm_children = [
            sac.MenuItem(lbl, icon=ico) for lbl, ico in zip(pm_labels, pm_icons)
        ]

        # ---------- Children aligned with options ----------
        children = []
        for key in route_keys:
            children.append(pm_children if key == "plant_manager" else None)

        # ---------- Build label<->key maps ----------
        label2key = {lbl: key for lbl, key in zip(options, route_keys)}
        key2label = {key: lbl for lbl, key in zip(options, route_keys)}
        for lbl, k in zip(pm_labels, pm_keys):
            if lbl:
                label2key[lbl] = k
                key2label[k] = lbl

        # ---------- Session init ----------
        st.session_state.setdefault("route_key", "home")  # stable route we control
        ui_key = "option_menu"  # component stores LABEL here
        st.session_state.setdefault(ui_key, base_options[0])
        # track language to detect changes
        curr_lang = st.session_state.get("current_lang", DEFAULT_LANG)
        last_lang = st.session_state.get("last_lang", curr_lang)

        # ---------- Sync ONLY on language change or invalid label ----------
        need_resync = False
        if last_lang != curr_lang:
            need_resync = True
        elif st.session_state.get(ui_key) not in label2key:
            need_resync = True

        if st.session_state["route_key"] not in key2label:
            # route_key has no label in this language -> fallback
            st.session_state["route_key"] = "home"

        if need_resync:
            desired_label = key2label[st.session_state["route_key"]]
            st.session_state[ui_key] = desired_label
            st.session_state["last_lang"] = curr_lang  # update tracker

        # ---------- Accent color ----------
        current_key = st.session_state["route_key"]
        parent_for_color = "plant_manager" if current_key in pm_keys else current_key
        accent = color_map.get(parent_for_color, "blue")

        # ---------- Render (component returns a LABEL) ----------
        selected_label = sac.menu(
            [
                sac.MenuItem(
                    lbl,
                    icon=ico,
                    tag=(
                        _build_notifications_tag(n_logs)
                        if (lbl == base_options[5])
                        else None
                    ),
                    children=child,
                )
                for lbl, ico, child in zip(options, icons, children)
            ],
            variant="left-bar",
            key=ui_key,  # component reads/writes a LABEL
            open_all=True,
            color=accent,
            return_index=False,  # returns LABEL
        )

        # Map LABEL -> stable KEY, update our stable key
        selected_key = label2key.get(selected_label, "home")
        if selected_key != st.session_state["route_key"]:
            st.session_state["route_key"] = selected_key
    else:
        selected_key = sac.menu(**guide.menu_kwargs())
    return selected_key


def streamlit() -> None:
    """Main entrypoint that renders the Streamlit application UI."""
    _init_session_state()
    pages = _build_pages()

    st.set_page_config(page_title="Plant Simulator", layout="wide")

    # Sidebar: branding, language, and quick actions
    plant_manager_names = translate("plant_manager.display_setup")[:3]
    with st.sidebar:
        st.markdown("## 🌅 PVApp")

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

        write_to_developer()

        # Navigation menu

    # ------------------------------
    # Page routing (uses STABLE KEYS)
    # ------------------------------
    sidebar_mode = st.session_state.get("sidebar", "main")

    if sidebar_mode == "main":
        route_key = selected  # stable key from _sidebar_menu
        if route_key == "home":
            home.render()

        elif route_key == "plants":
            pages["plants"].render()

        elif route_key == "compare":
            pages["plants_comparison"].render()

        elif route_key in {"pm_setup", "pm_topology", "pm_geo"}:
            pm_index = {"pm_setup": 0, "pm_topology": 1, "pm_geo": 2}[route_key]
            pages["plant_manager"].render(pm_index)

        elif route_key == "plant_manager":
            # Click sul parent: apri la prima sottopagina di default
            pages["plant_manager"].render(0)

        elif route_key == "guide":
            st.session_state["sidebar"] = "guide"
            st.rerun()

        elif route_key == "logs":
            pages["logs"].render()

        elif route_key in {"realtime_beta", "grid_beta"}:
            st.info("Beta features coming soon.")

        else:
            st.error(f"Unknown route: {route_key}")

    elif sidebar_mode == "guide":
        # placeholder = st.container()
        # with placeholder:
        #     guide_selected = sac.menu(**guide.menu_kwargs())  # returns index or None
        guide_selected = selected
        if guide_selected == 0:
            st.session_state["sidebar"] = "main"
            st.rerun()
        elif guide_selected is None:
            sac.result(
                "**GUIDE**",
                description="*Select a document in the sidebar on the left*",
                icon=sac.BsIcon("journal-text", color="teal"),
            )
        else:
            guide.render(guide_selected)
    else:
        st.error("ERROR IN MENU SELECTION")


# """Streamlit App Entrypoint

# This module defines the main Streamlit UI for the PV Plants Analyser application.
# It centralizes:
#   - Internationalization (i18n) utilities
#   - Sidebar navigation and global toggles
#   - Page routing to feature pages (Plants, Comparison, Plant Manager, Logs, etc.)
#   - Batch simulation helper

# Notes
# -----
# - Comments are written in English, as requested.
# - The UI structure and behavior are preserved while improving readability and robustness.
# - Minor fixes: renamed `aviable_languages` -> `available_languages`.
# """

# from __future__ import annotations

# import json
# import sys
# from pathlib import Path
# from typing import Dict, List, Union

# import pandas as pd
# import streamlit as st
# import streamlit_antd_components as sac

# # Internal imports
# from simulation import simulator

# # Pages
# from .pages.home import home
# from .pages.plants.plants import PlantsPage
# from .pages.plants_comparison.plants_comparison import PlantsComparisonPage
# from .pages.plant_manager.plant_manager import PlantManager
# from .pages.logs.logs import LogsPage, _SEV_ICON
# from .pages.guide import guide


# # -----------------------------------------------------------------------------
# # Global configuration
# # -----------------------------------------------------------------------------
# # Prevent creation of .pyc files
# sys.dont_write_bytecode = True

# # Default i18n folder
# I18N_DIR = Path("src/pvapp/gui/i18n/")
# DEFAULT_LANG = "it"


# # -----------------------------------------------------------------------------
# # Utilities: i18n helpers
# # -----------------------------------------------------------------------------
# def load_translation(lang: str) -> Dict:
#     """Load a translation JSON by language code."""
#     with open(I18N_DIR / f"{lang}.json", "r", encoding="utf-8") as f:
#         return json.load(f)


# def available_languages(folder: Path = I18N_DIR) -> List[str]:
#     """Return the list of available language codes from the i18n folder."""
#     return [p.stem for p in sorted(folder.iterdir()) if p.is_file()]


# def translate(key: str) -> Union[str, list]:
#     """Translate a dot-separated key using the current session dictionary.

#     If the key is missing, return the key (graceful fallback).
#     """
#     keys = key.split(".")
#     result = st.session_state.get("T", {})
#     for k in keys:
#         if isinstance(result, dict) and k in result:
#             result = result[k]
#         else:
#             return key
#     return result


# def T(key: str) -> Union[str, list]:
#     """Short-hand for translating under the 'main.' namespace."""
#     return translate(f"main.{key}")


# # -----------------------------------------------------------------------------
# # Simulation helper
# # -----------------------------------------------------------------------------
# def simulate_all(folder: Path = Path("data/")) -> None:
#     """Run the batch simulator over each subfolder in `folder`."""
#     subdirs = [p for p in sorted(folder.iterdir()) if p.is_dir()]
#     if not subdirs:
#         st.info("No subfolders found for simulation.")
#         return

#     progress = st.progress(0.0, text="Running simulations…")
#     total = len(subdirs)

#     for i, subfolder in enumerate(subdirs, start=1):
#         try:
#             simulator.Simulator(subfolder).run()
#         except Exception as exc:
#             st.warning(f"Simulation failed for {subfolder.name}: {exc}")
#         finally:
#             progress.progress(i / total, text=f"{i}/{total} simulations completed")

#     progress.empty()
#     sac.alert(
#         "All simulations completed.",
#         icon=sac.BsIcon("info-circle"),
#         color="green",
#         closable=True,
#     )


# # -----------------------------------------------------------------------------
# # Main App
# # -----------------------------------------------------------------------------
# def _init_session_state() -> None:
#     """Initialize default values in `st.session_state` exactly once."""
#     if "start_time" not in st.session_state:
#         st.session_state.start_time = pd.Timestamp.now()
#     if "notification_time" not in st.session_state:
#         st.session_state.notification_time = st.session_state.start_time

#     if "T" not in st.session_state:
#         st.session_state.T = load_translation(DEFAULT_LANG)
#         st.session_state.current_lang = DEFAULT_LANG

#     # Feature toggles and defaults
#     st.session_state.setdefault("beta_tools", False)
#     st.session_state.setdefault("auto_save", True)
#     st.session_state.setdefault("auto_sim", True)

#     # Stable menu selection key (route id, NOT translated label)
#     st.session_state.setdefault("option_menu", "home")
#     st.session_state.setdefault("sidebar", "main")


# def _build_pages() -> Dict[str, object]:
#     """Instantiate and return page objects in a single place."""
#     return {
#         "plants": PlantsPage(),
#         "plants_comparison": PlantsComparisonPage(),
#         # "grid_manager": GridManager(),
#         "plant_manager": PlantManager(),
#         "logs": LogsPage(),
#     }


# def _language_selector() -> None:
#     """Render the language selector in the sidebar and handle switching."""
#     current = st.session_state.get("current_lang", DEFAULT_LANG)

#     lang = st.segmented_control(
#         " ",
#         options=available_languages(),
#         label_visibility="collapsed",
#         default=current,
#     )
#     if lang and lang != current:
#         # Update translations but KEEP stable menu keys
#         st.session_state.T = load_translation(lang)
#         st.session_state.current_lang = lang
#         st.rerun()


# def _build_notifications_tag(n_logs: Dict[str, int]):
#     """Build the notifications tag for the Logs menu item using severities."""
#     tags = []
#     for sev, count in n_logs.items():
#         if count > 0:
#             color, icon_name = _SEV_ICON[sev]
#             tags.append(sac.Tag("", color=color, size="sm", icon=sac.BsIcon(icon_name)))
#     return tags or None


# def _sidebar_menu(plant_manager_names: List[str]) -> str:
#     """Render the left-bar menu and return the selected ROUTE KEY (stable).
#     Works with older streamlit-antd-components that don't support kv=.
#     """

#     # ---------- App status & log badges ----------
#     status, n_logs = LogsPage().app_status
#     notification_icon = [
#         "app",
#         "app-indicator",
#         "exclamation-triangle-fill",
#         "exclamation-circle-fill",
#         "x-circle-fill",
#     ]

#     # ---------- Translated labels (Home, Plants, Comparison, Plant Manager, Guide, Logs) ----------
#     labels: List[str] = T("menu")
#     if not isinstance(labels, list) or len(labels) < 6:
#         labels = ["Home", "Plants", "Comparison", "Plant Manager", "Guide", "Logs"]

#     # ---------- Stable top-level route keys (DO NOT TRANSLATE) ----------
#     MAIN_ROUTES = [
#         ("home",          labels[0], "house"),
#         ("plants",        labels[1], "buildings"),
#         ("compare",       labels[2], "bar-chart-steps"),
#         ("plant_manager", labels[3], "building-fill-gear"),
#         ("guide",         labels[4], "journal-text"),
#         ("logs",          labels[5], notification_icon[status]),
#     ]

#     COLOR_MAP = {
#         "home": "red",
#         "plants": "white",
#         "compare": "blue",
#         "plant_manager": "orange",
#         "guide": "green",
#         "logs": "red",
#     }

#     # ---------- Plant Manager children ----------
#     pm_keys   = ["pm_setup", "pm_topology", "pm_geo"]
#     pm_icons  = ["sun", "diagram-3", "compass"]
#     pm_labels = (plant_manager_names + ["", "", ""])[:3]  # safe padding

#     pm_children = [sac.MenuItem(lbl, icon=ico) for lbl, ico in zip(pm_labels, pm_icons)]

#     # ---------- Build items and mappings ----------
#     items: List[sac.MenuItem] = []
#     # label -> key
#     label2key: Dict[str, str] = {}
#     # key -> label (for current language)
#     key2label: Dict[str, str] = {}

#     for key, label, icon in MAIN_ROUTES:
#         children = pm_children if key == "plant_manager" else None
#         tag = _build_notifications_tag(n_logs) if key == "logs" else None
#         items.append(sac.MenuItem(label, icon=icon, tag=tag, children=children))
#         label2key[label] = key
#         key2label[key] = label

#     # children mappings
#     for k, lbl in zip(pm_keys, pm_labels):
#         if lbl:  # ignore padded empties
#             label2key[lbl] = k
#             key2label[k] = lbl

#     # ---------- Session init & validation ----------
#     # Stable route key we control
#     route_key_ss = "route_key"
#     st.session_state.setdefault(route_key_ss, "home")

#     # UI state used by the component (stores *label*, not key)
#     ui_key = "option_menu"

#     # If current stable key has no label in this language (e.g., missing translation), fallback to 'home'
#     if st.session_state[route_key_ss] not in key2label:
#         st.session_state[route_key_ss] = "home"

#     # Keep the component's stored label in sync with our stable key.
#     # This prevents ValueError on language change because the label always exists in current labels.
#     desired_label = key2label[st.session_state[route_key_ss]]
#     if st.session_state.get(ui_key) != desired_label:
#         st.session_state[ui_key] = desired_label

#     # ---------- Accent color ----------
#     current_key = st.session_state[route_key_ss]
#     color_route = "plant_manager" if current_key in pm_keys else current_key
#     accent = COLOR_MAP.get(color_route, "blue")

#     # ---------- Render (component returns a *label*) ----------
#     selected_label = sac.menu(
#         items=items,
#         variant="left-bar",
#         key=ui_key,         # component reads/writes a LABEL here
#         open_all=True,
#         color=accent,
#         return_index=False, # returns label (since kv is not supported)
#         index=0,
#     )

#     # Map label -> stable key, update our stable key in session
#     selected_key = label2key.get(selected_label, "plants")
#     if selected_key != st.session_state[route_key_ss]:
#         st.session_state[route_key_ss] = selected_key

#     return selected_key


# def streamlit() -> None:
#     """Main entrypoint that renders the Streamlit application UI."""
#     _init_session_state()
#     pages = _build_pages()

#     st.set_page_config(page_title="Plant Simulator", layout="wide")

#     # Sidebar: branding, language, and quick actions
#     raw_pm_names = translate("plant_manager.display_setup")[:3]
#     if isinstance(raw_pm_names, str):
#         plant_manager_names = [raw_pm_names]
#     elif isinstance(raw_pm_names, list):
#         plant_manager_names = [str(x) for x in raw_pm_names]
#     else:
#         plant_manager_names = []
#     with st.sidebar:
#         st.markdown("## 🌅 PVApp")
#         st.divider()

#         selected = _sidebar_menu(plant_manager_names)
#         st.divider()

#         # Actions & toggles
#         col_a, col_b = st.columns([1, 2])
#         if col_b.button(f"{T('buttons.simulate')}", icon="🔥"):
#             simulate_all()
#         with col_a.popover("⚙️"):
#             _language_selector()
#             st.divider()
#             st.toggle("💾 Auto-Save", key="auto_save")
#             st.toggle("🔥 Auto-Simulate", key="auto_sim")

#     # ------------------------------
#     # Page routing by STABLE KEYS
#     # ------------------------------
#     sidebar_mode = st.session_state.get("sidebar", "main")
#     route_key = selected  # <- stable key returned by _sidebar_menu

#     if sidebar_mode == "main":
#         st.error(f"No sidebar mode{route_key}")
#         if route_key == "home":
#             home.render()

#         elif route_key == "plants":
#             pages["plants"].render()

#         elif route_key == "compare":
#             pages["plants_comparison"].render()

#         elif route_key in {"pm_setup", "pm_topology", "pm_geo"}:
#             idx = {"pm_setup": 0, "pm_topology": 1, "pm_geo": 2}[route_key]
#             pages["plant_manager"].render(idx)

#         elif route_key == "plant_manager":
#             # se clicchi il parent senza scegliere il figlio, apri default
#             pages["plant_manager"].render(0)

#         elif route_key == "guide":
#             st.session_state["sidebar"] = "guide"
#             st.rerun()

#         elif route_key == "logs":
#             pages["logs"].render()

#         else:
#             st.error(f"Unknown route: {route_key}")

#     elif sidebar_mode == "guide":
#         placeholder = st.container()
#         with placeholder:
#             guide_selected = sac.menu(**guide.menu_kwargs())
#         if guide_selected == 0:
#             st.session_state["sidebar"] = "main"
#             st.rerun()
#         elif guide_selected is None:
#             sac.result(
#                 "**GUIDE**",
#                 description="*Select a document in the sidebar on the left*",
#                 icon=sac.BsIcon("journal-text", color="teal"),
#             )
#         else:
#             guide.render(guide_selected)

# // -------------------------------------------------------------- --------
# Future beta routes (kept for reference)
# elif selected == "Real-time monitor  (beta)":
#     plant_distribution()
# elif selected == "Grid manager (beta)":
#     pages["grid_manager"].render()


# import streamlit as st
# from .pages.home import home
# from .pages.plant_performance import plant_performance
# from streamlit_option_menu import option_menu
# import sys
# from simulation import simulator
# from pathlib import Path
# import json
# from typing import List
# import streamlit_antd_components as sac

# from .pages.plants.plants import PlantsPage
# from .pages.plants_comparison.plants_comparison import PlantsComparisonPage
# from .pages.beta.real_time_monitor.plant_distribution import plant_distribution
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
#     with open(f"src/pvapp/gui/i18n/{lang}.json", "r", encoding="utf-8") as f:
#         return json.load(f)


# def aviable_languages(folder: Path = Path("src/pvapp/gui/i18n/")) -> List:
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
#         "plants": PlantsPage(),
#         "plants_comparison": PlantsComparisonPage(),
#         "grid_manager": GridManager(),
#         "plant_manager": PlantManager(),
#         "logs": LogsPage(),
#     }
#     if "T" not in st.session_state:
#         st.session_state.T = load_translation("it")
#         st.session_state.current_lang = "it"

#     st.set_page_config(page_title="Plant Simulator", layout="wide")

#     # Gestione lingua
#     plant_manager_names = translate("plant_manager.display_setup")[:3]
#     with st.sidebar:
#         st.markdown("## 🌅 PV Plants Analyser")
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
#     elif selected == options[1]:  # "Plants"
#         pages["plants"].render()
#     elif selected == options[2]:  # "Plants comparison"
#         pages["plants_comparison"].render()
#     # elif selected == options[3]:  # "Plant performance"
#     #     plant_performance.render()
#     elif selected in plant_manager_names:  # "Plant manager"
#         if selected == plant_manager_names[1]:
#             pages["plant_manager"].render(1)
#         elif selected == plant_manager_names[2]:
#             pages["plant_manager"].render(2)
#         else:
#             pages["plant_manager"].render()

#     elif selected == options[4]:  # "Logs"
#         pages["logs"].render()

#     # elif selected == options[-2]:
#     #     plant_distribution()
#     # elif selected == options[-1]:
#     #     pages["grid_manager"].render()
