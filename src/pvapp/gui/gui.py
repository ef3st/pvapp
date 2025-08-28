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

        if st.button(
            f"Download Guide",
            icon="📃",
        ):
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
                # Fallback: quick local HTML for CLI testing
                cfg = DocBundlerConfig(project_root=Path.cwd())
                bundler = DocBundler(cfg)
                html = bundler.build_html_string()
                Path("bundle_preview.html").write_text(html, encoding="utf-8")
                print(
                    "Created bundle_preview.html — open it in the browser or use Streamlit for PDF."
                )
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
