import json
import re
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd
import streamlit as st
import streamlit_antd_components as sac

from ..page import Page


# ============================================================
# Constants & Regular Expressions
# ============================================================

# ANSI color codes (e.g., "\x1b[36m ... \x1b[0m")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Log record pattern example:
# 2025-07-05 00:42:38 - solartracker - [36mDEBUG[0m - database.py:43 - message...
_LOG_RE = re.compile(
    r"^(?P<dt>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - "
    r"(?P<logger>[^-]+?) - "
    r"(?P<severity>.+?) - "
    r"(?P<origin>[^-]+?) - "
    r"(?P<msg>.*)$"
)

# Severity mapping -> icon + label (kept as-is to preserve UI)
_SEVERITY_ICON = {
    "INFO": "ℹ️ INFO",
    "WARNING": "⚠️ WARNING",
    "ERROR": "❌ ERROR",
    "DEBUG": "🔎 DEBUG",
    "CRITICAL": "❌❌❌ CRITICAL",
}

# Start banner detection (kept for potential future use)
START_REGEX = re.compile(
    r"Starting\s+SolarTracker\s+GUI\s+in\s+.+?\s+mode\s+with\s+log\s+level\s+.+",
    re.IGNORECASE,
)

# Helpers for per-file tag severity
_SEV_ORDER = {"CRITICAL": 4, "ERROR": 3, "WARNING": 2, "INFO": 1, "DEBUG": 0}
_SEV_ICON = {
    "WARNING": ("orange", "exclamation-triangle-fill"),
    "ERROR": ("red", "x-circle-fill"),
    "CRITICAL": ("red", "exclamation-circle-fill"),
}


# ============================================================
# Helper Functions
# ============================================================


def _extract_caps_severity(sev_text: str) -> Optional[str]:
    """
    Extract the SEVERITY word in UPPERCASE from a label string (ignoring emoji).
    Examples:
      '❌ ERROR' -> 'ERROR'
      '🔎 DEBUG' -> 'DEBUG'
    """
    if not isinstance(sev_text, str):
        return None
    m = re.search(r"\b(DEBUG|CRITICAL|ERROR|INFO|WARNING)\b", sev_text.upper())
    return m.group(1) if m else None


def _worst_severity_for_file(df: pd.DataFrame, filename: str) -> Optional[List[str]]:
    """
    Return the list of uppercase severities present for that file (preserves existing logic),
    or None if the file is not present in the DataFrame.
    """
    sub = df.loc[df["origin file"] == filename, "severity"]
    if sub.empty:
        return None
    sev_vals = [_extract_caps_severity(x) for x in sub]
    sev_vals = [s for s in sev_vals if s in _SEV_ORDER]
    if not sev_vals:
        return None
    # NOTE: The original logic returned the list, not the single worst one.
    # We keep that behavior to avoid altering the UI semantics.
    return sev_vals


def _unique_tags(tags: List[sac.Tag]) -> List[sac.Tag]:
    """
    Deduplicate Tag objects by their meaningful properties.
    """
    seen = set()
    unique_list: List[sac.Tag] = []
    for tag in tags:
        key = (tag.label, tag.color, tag.size, getattr(tag.icon, "name", None))
        if key not in seen:
            seen.add(key)
            unique_list.append(tag)
    return unique_list


def _file_tag_from_df(df: pd.DataFrame, filename: str):
    """
    Build the per-file Tag(s):
      - Red/orange icon tag(s) for WARNING/ERROR/CRITICAL (as in original logic)
      - Otherwise returns 'py' default tag (no visual change from original behavior).
    """
    sevs = _worst_severity_for_file(df, filename)
    if sevs is not None:
        tags = []
        for sev in sevs:
            if sev in _SEV_ICON:
                color, icon_name = _SEV_ICON[sev]
                tags.append(
                    sac.Tag("", color=color, size="xs", icon=sac.BsIcon(icon_name))
                )
        return _unique_tags(tags)
    # Fallback: let the component render its default (unchanged from original)
    return None


# ============================================================
# Logs Page
# ============================================================


class LogsPage(Page):
    """
    Streamlit page to visualize and filter application logs.

    Notes:
    - Logic and UI flow preserved exactly as in the original implementation.
    - Code organization, typing, and docstrings improved for clarity.
    """

    def __init__(self) -> None:
        super().__init__("log")
        self.logs: Union[str, List[str]] = []
        self.path: Path = Path("logs/solartracker.log")

    # -----------------------------
    # Data Loading & Parsing
    # -----------------------------
    def load_logs(self) -> None:
        """
        Load the log file content into self.logs as a string.
        """
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                self.logs = file.read()
        except FileNotFoundError:
            self.logs = ["No logs found."]

    def _normalize_severity(self, raw: str) -> str:
        """
        Strip ANSI codes and normalize to the 'icon + label' format.
        """
        clean = _ANSI_RE.sub("", raw).strip()
        m = re.match(r"([A-Za-z]+)", clean)
        if not m:
            return clean
        key = m.group(1).upper()
        return _SEVERITY_ICON.get(key, clean)

    def parse_logs_to_dataframe(
        self,
        log_source: Union[str, bytes],
        from_path: bool = False,
    ) -> pd.DataFrame:
        """
        Parse log text (or file) into a DataFrame:
        columns = ['date-time', 'logger name', 'severity', 'origin file', 'line', 'description'].
        """
        if from_path:
            with open(log_source, "rb") as f:
                content = f.read()
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1", errors="replace")
        else:
            text = (
                log_source.decode("utf-8")
                if isinstance(log_source, bytes)
                else str(log_source)
            )

        rows = []
        current = None  # holds the last parsed record for multiline descriptions

        for raw_line in text.splitlines():
            line = raw_line.rstrip("\n")
            m = _LOG_RE.match(line)
            if m:
                # flush previous pending record
                if current is not None:
                    rows.append(current)

                dt = m.group("dt").strip()
                logger = m.group("logger").strip()
                severity = self._normalize_severity(m.group("severity"))
                origin = m.group("origin").strip()
                msg = m.group("msg")
                file_name, line_str = origin.split(":")

                current = {
                    "date-time": dt,
                    "logger name": logger,
                    "severity": severity,
                    "origin file": file_name,
                    "line": line_str,
                    "description": msg,  # extended if subsequent lines belong here
                }
            else:
                # Continuation line -> append to the last description (preserve raw)
                if current is not None:
                    current["description"] += "\n" + raw_line
                else:
                    # Skip stray lines before any valid record
                    continue

        # append the final pending record
        if current is not None:
            rows.append(current)

        return pd.DataFrame(
            rows,
            columns=[
                "date-time",
                "logger name",
                "severity",
                "origin file",
                "line",
                "description",
            ],
        )

    # -----------------------------
    # UI Trees (GUI / BACK-END)
    # -----------------------------
    def gui_tree(self, df: pd.DataFrame) -> List[str]:
        """
        Build the GUI tree and return the selected file names.
        """
        items = [
            sac.TreeItem(
                "GUI",
                icon="folder",
                children=[
                    sac.TreeItem(
                        "pages",
                        icon="folder",
                        children=[
                            sac.TreeItem("beta", icon="folder"),
                            sac.TreeItem(
                                "home",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "home.py",
                                        icon="file",
                                        tag=_file_tag_from_df(df, "home.py"),
                                    )
                                ],
                            ),
                            sac.TreeItem(
                                "implant_performance",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "implant_performance.py",
                                        icon="file",
                                        tag=_file_tag_from_df(
                                            df, "implant_performance.py"
                                        ),
                                    )
                                ],
                            ),
                            sac.TreeItem(
                                "implants",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "add_implant",
                                        icon="folder",
                                        children=[
                                            sac.TreeItem(
                                                "add_implant.py",
                                                icon="file",
                                                tag=_file_tag_from_df(
                                                    df, "add_implant.py"
                                                ),
                                            )
                                        ],
                                    ),
                                    sac.TreeItem(
                                        "implants.py",
                                        icon="file",
                                        tag=_file_tag_from_df(df, "implants.py"),
                                    ),
                                ],
                            ),
                            sac.TreeItem(
                                "implants_comparison",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "implants_comparison.py",
                                        icon="file",
                                        tag=_file_tag_from_df(
                                            df, "implants_comparison.py"
                                        ),
                                    )
                                ],
                            ),
                            sac.TreeItem(
                                "logs",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "logs.py",
                                        icon="file",
                                        tag=_file_tag_from_df(df, "logs.py"),
                                    )
                                ],
                            ),
                            sac.TreeItem(
                                "plant_manager",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "plant_manager.py",
                                        icon="file",
                                        tag=_file_tag_from_df(df, "plant_manager.py"),
                                    )
                                ],
                            ),
                            sac.TreeItem(
                                "grid",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "grid_tab.py",
                                        icon="file",
                                        tag=_file_tag_from_df(df, "grid_tab.py"),
                                    ),
                                    sac.TreeItem(
                                        "grid.py",
                                        icon="file",
                                        tag=_file_tag_from_df(df, "grid.py"),
                                    ),
                                ],
                            ),
                            sac.TreeItem(
                                "module",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "module.py",
                                        icon="file",
                                        tag=_file_tag_from_df(df, "module.py"),
                                    )
                                ],
                            ),
                            sac.TreeItem(
                                "site",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "plant_manager.py",
                                        icon="file",
                                        tag=_file_tag_from_df(df, "plant_manager.py"),
                                    )
                                ],
                            ),
                            sac.TreeItem(
                                "__init__.py",
                                icon="file",
                                tag=_file_tag_from_df(df, "__init__.py"),
                            ),
                            sac.TreeItem(
                                "page.py",
                                icon="file",
                                tag=_file_tag_from_df(df, "page.py"),
                            ),
                        ],
                    ),
                    sac.TreeItem(
                        "utils",
                        icon="folder",
                        children=[
                            sac.TreeItem("graphics", icon="folder"),
                            sac.TreeItem(
                                "plots",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "plots.py",
                                        icon="file",
                                        tag=_file_tag_from_df(df, "plots.py"),
                                    )
                                ],
                            ),
                        ],
                    ),
                    sac.TreeItem(
                        "translation",
                        icon="folder",
                        children=[
                            sac.TreeItem(
                                "traslator.py",
                                icon="file",
                                tag=_file_tag_from_df(df, "traslator.py"),
                            )
                        ],
                    ),
                    sac.TreeItem(
                        "maingui.py",
                        icon="file",
                        tag=_file_tag_from_df(df, "maingui.py"),
                    ),
                ],
            )
        ]

        # keep same open_all, checkbox, size, and index list (31)
        selected = sac.tree(
            items, open_all=True, checkbox=True, size="xs", index=[i for i in range(31)]
        )
        return selected

    def backend_tree(self, df: pd.DataFrame) -> List[str]:
        """
        Build the BACK-END tree and return the selected file names.
        """
        mounts = [
            sac.TreeItem(
                "MOUNT",
                icon="folder",
                children=[
                    sac.TreeItem(
                        "developement",
                        icon="folder",
                        children=[
                            sac.TreeItem(
                                "custommount.py",
                                icon="file",
                                tag=_file_tag_from_df(df, "custommount.py"),
                            ),
                            sac.TreeItem(
                                "tracking.py",
                                icon="file",
                                tag=_file_tag_from_df(df, "tracking.py"),
                            ),
                        ],
                    )
                ],
            ),
        ]

        pvplantmanager = [
            sac.TreeItem(
                "PV PLANT MANAGER",
                icon="folder",
                children=[
                    sac.TreeItem(
                        "pvplantmanager.py",
                        icon="file",
                        tag=_file_tag_from_df(df, "pvplantmanager.py"),
                    )
                ],
            )
        ]

        simulation = [
            sac.TreeItem(
                "SIMULATION",
                icon="folder",
                children=[
                    sac.TreeItem(
                        "simulator.py",
                        icon="file",
                        tag=_file_tag_from_df(df, "simulator.py"),
                    ),
                    sac.TreeItem(
                        "nature.py", icon="file", tag=_file_tag_from_df(df, "nature.py")
                    ),
                ],
            )
        ]

        analysis = [
            sac.TreeItem(
                "ANALYSIS",
                icon="folder",
                children=[
                    sac.TreeItem(
                        "database.py",
                        icon="file",
                        tag=_file_tag_from_df(df, "database.py"),
                    ),
                    sac.TreeItem(
                        "implantanalyser.py",
                        icon="file",
                        tag=_file_tag_from_df(df, "implantanalyser.py"),
                    ),
                ],
            )
        ]

        utils = [
            sac.TreeItem(
                "UTILS",
                icon="folder",
                children=[
                    sac.TreeItem(
                        "implant_results_visualizer.py",
                        icon="file",
                        tag=_file_tag_from_df(df, "implant_results_visualizer.py"),
                    ),
                    sac.TreeItem(
                        "logger.py", icon="file", tag=_file_tag_from_df(df, "logger.py")
                    ),
                ],
            )
        ]

        main = [
            sac.TreeItem("main.py", icon="file", tag=_file_tag_from_df(df, "main.py"))
        ]

        items = [
            sac.TreeItem(
                "BACK-END",
                icon="folder",
                children=(
                    mounts + pvplantmanager + simulation + analysis + utils + main
                ),
            )
        ]

        # keep same open_all, checkbox, size, and index list (17)
        selected = sac.tree(
            items, open_all=True, checkbox=True, size="xs", index=[i for i in range(17)]
        )
        return selected

    # -----------------------------
    # Rendering
    # -----------------------------
    def render(self) -> None:
        """
        Render the Logs page with filters, trees, and log table.
        """
        self.load_logs()
        if not self.logs:
            st.warning(self.T("log_not_found"))
            return

        st.title(self.T("title"))

        # Parse logs and normalize datetime
        log_df = self.parse_logs_to_dataframe(self.logs, from_path=False)
        log_df["date-time"] = pd.to_datetime(log_df["date-time"], errors="coerce")
        log_df = log_df.dropna(subset=["date-time"])

        if log_df.empty:
            st.info("No valid log records.")
            return

        # Bounds
        min_dt = log_df["date-time"].min()
        max_dt = log_df["date-time"].max()

        # Use "start of last run" toggle
        use_last_run = st.toggle(
            "Use start of last run",
            value=True,
            help="If enabled, start date and time are set to the (presumed) start of the last execution",
        )

        if use_last_run:
            start_guess = st.session_state.start_time
            if start_guess is None:
                start_guess = min_dt
        else:
            start_guess = min_dt

        # -----------------------------
        # Filters UI
        # -----------------------------
        a, b = st.columns([1, 3])

        with b:
            l, r = st.columns([1, 3])

            # Severity pills (keep behavior and component as-is)
            severities = list(sorted(log_df["severity"].dropna().unique()))
            sel_sev = l.pills(
                "Severity",
                options=severities,
                default=severities,
                selection_mode="multi",
            )

            # Time filter expander (unchanged logic)
            with r.expander("Time Filter", icon="🕐", expanded=True):
                c1, c2, c3 = st.columns([1.2, 1, 1])

                with c1:
                    date_range = st.date_input(
                        "Date range",
                        value=(start_guess.date(), max_dt.date()),
                        min_value=min_dt.date(),
                        max_value=max_dt.date(),
                        format="DD/MM/YYYY",
                    )
                    if isinstance(date_range, tuple):
                        start_date, end_date = date_range
                    else:
                        start_date = end_date = date_range

                # Default times based on bounds/selection
                from datetime import time, datetime as dtmod

                default_t_start = (
                    start_guess.time()
                    if start_date == start_guess.date()
                    else time(0, 0, 0)
                )
                default_t_end = (
                    max_dt.time() if end_date == max_dt.date() else time(23, 59, 59)
                )

                with c2:
                    t_start = st.time_input("Start Time", value=default_t_start)
                with c3:
                    t_end = st.time_input("End Time", value=default_t_end)

                # Keep placeholder for origins (commented as in original)
                origins = list(sorted(log_df["origin file"].dropna().unique()))
                # sel_orig = st.multiselect("File di origine", options=origins, default=origins)

            start_dt = pd.to_datetime(dtmod.combine(start_date, t_start))
            end_dt = pd.to_datetime(dtmod.combine(end_date, t_end))

        # Trees (GUI / BACK-END)
        with a:
            backend_tab, gui_tab = st.tabs(["BACK-END", "GUI"], width="stretch")

            start = st.session_state.start_time
            if start is None:
                start = min_dt

            last_logs = log_df[(log_df["date-time"] >= start)].copy()

            with gui_tab:
                gui_selected_files = self.gui_tree(last_logs)

            with backend_tab:
                backend_selected_files = self.backend_tree(last_logs)

        # Apply filters
        fdf = log_df[
            (log_df["date-time"] >= start_dt)
            & (log_df["date-time"] <= end_dt)
            & (log_df["severity"].isin(sel_sev))
            & (log_df["origin file"].isin(gui_selected_files + backend_selected_files))
        ].copy()

        # -----------------------------
        # Display
        # -----------------------------
        with b:
            fdf.sort_values("date-time", ascending=False, inplace=True)
            st.caption(f"{len(fdf)} records out of {len(log_df)} total")
            st.dataframe(fdf, use_container_width=True)
