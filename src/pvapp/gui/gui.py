# * =============================
# *         STREAMLIT GUI
# * =============================

"""
Streamlit App Entrypoint

This module defines the main Streamlit UI for the PV Plants Analyser application.
It centralizes:
  - Internationalization (i18n) utilities
  - Sidebar navigation and global toggles
  - Page routing to feature pages (Plants, Comparison, Plant Manager, Logs, etc.)
  - Batch simulation helper

---
Notes:
- Comments are written in English.
- The UI structure and behavior are preserved while improving readability and robustness.
"""

from __future__ import annotations

import sys
import json
import math
from pathlib import Path
from typing import Dict, List, Union

import pandas as pd
import streamlit as st
import streamlit_antd_components as sac

from backend.simulation import simulator

# Pages
from .pages.home import home
from .pages.plants.plants import PlantsPage
from .pages.plants_comparison.plants_comparison import PlantsComparisonPage
from .pages.plant_manager.plant_manager import PlantManager
from .pages.logs.logs import LogsPage, _SEV_ICON
from .pages.guide import guide
from .utils.graphics.feedback_form import write_to_developer


# * =========================================================
# *                     GLOBAL CONFIG
# * =========================================================
sys.dont_write_bytecode = True  # Prevent .pyc files

I18N_DIR = Path("src/pvapp/gui/i18n/")
DEFAULT_LANG = "en"
DEFAULT_AUTOSAVE = True
DEFAULT_AUTOSIMULATE = False


# * =========================================================
# *                     I18N UTILITIES
# * =========================================================
def load_translation(lang: str) -> Dict:
    """
    Load a translation JSON by language code.

    Args:
        lang (str): Language code (e.g., "it", "en").

    Returns:
        dict: Parsed JSON containing translation keys.
    """
    with open(I18N_DIR / f"{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)


def available_languages(folder: Path = I18N_DIR) -> List[str]:
    """
    Return the list of available language codes from the i18n folder.

    Args:
        folder (Path): Path to the i18n directory.

    Returns:
        list[str]: Available language codes.
    """
    return [p.stem for p in sorted(folder.iterdir()) if p.is_file()]


def translate(key: str) -> Union[str, list]:
    """
    Translate a dot-separated key using the current session dictionary.

    Args:
        key (str): Key path, e.g. "main.menu".

    Returns:
        Union[str, list]: Translation or original key if missing.
    """
    keys = key.split(".")
    result = st.session_state.get("T", {})
    for k in keys:
        if isinstance(result, dict) and k in result:
            result = result[k]
        else:
            return key  # Fallback when missing
    return result


def T(key: str) -> Union[str, list]:
    """
    Shortcut for translating under the "main." namespace.

    Args:
        key (str): Key path relative to "main.".

    Returns:
        Union[str, list]: Translation result or fallback key.
    """
    return translate(f"main.{key}")


# * =========================================================
# *                SIMULATION HELPER (BATCH)
# * =========================================================
def simulate_all(folder: Path = Path("data/")) -> None:
    """
    Run the batch simulator over each subfolder in `folder`.

    Args:
        folder (Path): Root folder containing one subfolder per simulation case.
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
        except Exception as e:
            st.warning(f"Simulation failed for {subfolder.name}: {e}")
        finally:
            progress.progress(i / total, text=f"{i}/{total} simulations completed")
            st.toast(f"Simulation completed for {subfolder.name}", icon="✅")

    progress.empty()
    sac.alert(
        "All simulations completed.",
        icon=sac.BsIcon("info-circle"),
        color="green",
        closable=True,
    )


# * =========================================================
# *                    SESSION STATE INIT
# * =========================================================
def _init_session_state() -> None:
    """
    Initialize default values in `st.session_state` exactly once.
    """
    if "start_time" not in st.session_state:
        st.session_state.start_time = pd.Timestamp.now()
    if "notification_time" not in st.session_state:
        st.session_state.notification_time = st.session_state.start_time

    if "T" not in st.session_state:
        st.session_state.T = load_translation(DEFAULT_LANG)
        st.session_state.current_lang = DEFAULT_LANG

    st.session_state.setdefault("beta_tools", False)
    st.session_state.setdefault("auto_save", DEFAULT_AUTOSAVE)
    st.session_state.setdefault("auto_sim", DEFAULT_AUTOSIMULATE)
    st.session_state.setdefault("menu", 4)


def _build_pages() -> Dict[str, object]:
    """
    Instantiate and return page objects in a single place.

    Returns:
        dict[str, object]: Mapping of route key to page instance.
    """
    return {
        "plants": PlantsPage(),
        "plants_comparison": PlantsComparisonPage(),
        "plant_manager": PlantManager(),
        "logs": LogsPage(),
    }


# * =========================================================
# *                  LANGUAGE SELECTOR (UI)
# * =========================================================
def flag_for(code: str) -> str:
    """
    Return an emoji flag for a language code. Fallback to 🌐 if unknown.

    Args:
        code (str): Language code (e.g., "en", "it").

    Returns:
        str: Emoji flag.
    """
    code = (code or "").lower()
    mapping = {
        "it": "🇮🇹",
        "en": "🇬🇧",  # convention: en→UK flag
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
    Render a segmented control language selector.

    Args:
        max_per_group (int): Max languages per segmented control.
    """
    current = st.session_state.get("current_lang", DEFAULT_LANG)
    codes = available_languages()
    labels = [f"{flag_for(c)} {c.upper()}" for c in codes]
    code2label = dict(zip(codes, labels))
    label2code = dict(zip(labels, codes))

    def chunks(seq, n):
        for i in range(0, len(seq), n):
            yield seq[i : i + n]

    code_groups = list(chunks(codes, max_per_group))
    label_groups = list(chunks(labels, max_per_group))

    if current not in codes and codes:
        current = codes[0]
        st.session_state["current_lang"] = current

    current_label = code2label.get(current)
    new_lang = None

    for gi, (g_codes, g_labels) in enumerate(zip(code_groups, label_groups)):
        group_key = f"lang_selector_{gi}"

        if current in g_codes:
            default_label = current_label
        else:
            if group_key in st.session_state:
                st.session_state.pop(group_key, None)
            default_label = None

        if default_label and default_label in g_labels:
            sel_label = st.segmented_control(
                group_key,
                options=g_labels,
                label_visibility="collapsed",
                default=default_label,
            )
        else:
            sel_label = st.segmented_control(
                group_key, options=g_labels, label_visibility="collapsed"
            )

        sel_code = label2code.get(sel_label)
        if sel_code and sel_code != current:
            new_lang = sel_code

    if new_lang and new_lang != current:
        st.session_state.T = load_translation(new_lang)
        st.session_state.current_lang = new_lang
        st.rerun()


# * =========================================================
# *                SIDEBAR MENU & ROUTING
# * =========================================================
def _build_notifications_tag(n_logs: Dict[str, int]):
    """
    Build the notifications tag for the Logs menu item using severities.

    Args:
        n_logs (dict[str, int]): Severity → count.

    Returns:
        list or None: Tags for menu rendering.
    """
    tags = []
    for sev, count in n_logs.items():
        if count > 0:
            color, icon_name = _SEV_ICON[sev]
            tags.append(sac.Tag("", color=color, size="sm", icon=sac.BsIcon(icon_name)))
    return tags or None


def _sidebar_menu(plant_manager_names: List[str]) -> str:
    """
    Render the left sidebar menu and return the selected ROUTE KEY (stable).

    Args:
        plant_manager_names (list[str]): Labels for Plant Manager subpages.

    Returns:
        str: Selected route key.
    """
    sidebar_mode = st.session_state.get("sidebar", "main")
    if sidebar_mode == "main":
        status, n_logs = LogsPage().app_status

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
            ["Real-time monitor (beta)", "Grid manager (beta)"] if beta_enabled else []
        )
        options = base_options + beta_options

        base_keys = ["home", "plants", "compare", "plant_manager", "guide", "logs"]
        beta_keys = ["realtime_beta", "grid_beta"] if beta_enabled else []
        route_keys = base_keys[: len(base_options)] + beta_keys

        icons = [
            "house",
            "buildings",
            "bar-chart-steps",
            "building-fill-gear",
            "journal-text",
            [
                "app",
                "app-indicator",
                "exclamation-triangle-fill",
                "exclamation-circle-fill",
                "x-circle-fill",
            ][status],
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
            "logs": ["#467146", "#6170d5", "#dfbe6a", "#df6a6a", "#ea36cf"][status],
            "realtime_beta": "blue",
            "grid_beta": "blue",
        }

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

        children = []
        for key in route_keys:
            children.append(pm_children if key == "plant_manager" else None)

        label2key = {lbl: key for lbl, key in zip(options, route_keys)}
        key2label = {key: lbl for lbl, key in zip(options, route_keys)}
        for lbl, k in zip(pm_labels, pm_keys):
            if lbl:
                label2key[lbl] = k
                key2label[k] = lbl

        st.session_state.setdefault("route_key", "home")
        ui_key = "option_menu"
        st.session_state.setdefault(ui_key, base_options[0])

        curr_lang = st.session_state.get("current_lang", DEFAULT_LANG)
        last_lang = st.session_state.get("last_lang", curr_lang)

        need_resync = (
            last_lang != curr_lang or st.session_state.get(ui_key) not in label2key
        )

        if st.session_state["route_key"] not in key2label:
            st.session_state["route_key"] = "home"

        if need_resync:
            desired_label = key2label[st.session_state["route_key"]]
            st.session_state[ui_key] = desired_label
            st.session_state["last_lang"] = curr_lang

        current_key = st.session_state["route_key"]
        parent_for_color = "plant_manager" if current_key in pm_keys else current_key
        accent = color_map.get(parent_for_color, "blue")

        selected_label = sac.menu(
            [
                sac.MenuItem(
                    lbl,
                    icon=ico,
                    tag=(
                        _build_notifications_tag(n_logs)
                        if lbl == base_options[5]
                        else None
                    ),
                    children=child,
                )
                for lbl, ico, child in zip(options, icons, children)
            ],
            variant="left-bar",
            key=ui_key,
            open_all=True,
            color=accent,
            return_index=False,
        )

        selected_key = label2key.get(selected_label, "home")
        if selected_key != st.session_state["route_key"]:
            st.session_state["route_key"] = selected_key
    else:
        selected_key = sac.menu(**guide.menu_kwargs())
    return selected_key


# * =========================================================
# *                      MAIN ENTRYPOINT
# * =========================================================
def streamlit() -> None:
    """
    Main entrypoint that renders the Streamlit application UI.
    """
    _init_session_state()
    pages = _build_pages()
    st.set_page_config(page_title="Plant Simulator", layout="wide")

    plant_manager_names = translate("plant_manager.display_setup")[:3]
    with st.sidebar:
        st.markdown("## 🌅 PVApp")

        st.divider()
        selected = _sidebar_menu(plant_manager_names)
        st.divider()

        col_a, col_b = st.columns([1, 2])
        if col_b.button(f"{T('buttons.simulate')}", icon="🔥"):
            simulate_all()
        with col_a.popover("⚙️"):
            _language_selector()
            st.divider()
            st.toggle("💾 Auto-Save", key="auto_save")
            st.toggle("🔥 Auto-Simulate", key="auto_sim")

        if st.button("Download Guide", icon="📃"):
            from pvapp.tools.documentation.docbuilder import (
                _run_streamlit,
                DocBundler,
                DocBundlerConfig,
            )

            @st.dialog("📃Download Guide", width="large")
            def download_form():
                _run_streamlit()

            try:
                download_form()
            except ModuleNotFoundError:
                cfg = DocBundlerConfig(project_root=Path.cwd())
                bundler = DocBundler(cfg)
                html = bundler.build_html_string()
                Path("bundle_preview.html").write_text(html, encoding="utf-8")
                print(
                    "Created bundle_preview.html — open it manually or via Streamlit."
                )

        # write_to_developer()
        st.error("The feedback form is not included in this distribution. Please, contact pepa.lorenzo.01@gmail.com")

    sidebar_mode = st.session_state.get("sidebar", "main")
    if sidebar_mode == "main":
        route_key = selected
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
