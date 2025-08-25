import json
import re
from pathlib import Path
from typing import List, Optional, Union, Iterable

import pandas as pd
import streamlit as st
import streamlit_antd_components as sac
from enum import IntEnum
from gui.pages import Page


# ============================================================
# Constants & Regular Expressions
# ============================================================

# ANSI color codes (e.g., "\x1b[36m ... \x1b[0m")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Log record pattern example:
# 2025-07-05 00:42:38 - pvapp - [36mDEBUG[0m - database.py:43 - message...
_LOG_RE = re.compile(
    r"^(?P<dt>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - "
    r"(?P<logger>[^-]+?) - "
    r"(?P<severity>.+?) - "
    r"(?P<origin>[^-]+?) - "
    r"(?P<msg>.*)$"
)

# Severity mapping -> icon + label
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


class Status(IntEnum):
    """Enum to represent the status of a log record."""

    OK = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


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


def _unique_tags(tags: List[sac.Tag]) -> List[sac.Tag]:
    """Deduplicate Tag objects by their meaningful properties."""
    seen = set()
    unique_list: List[sac.Tag] = []
    for tag in tags:
        key = (tag.label, tag.color, tag.size, getattr(tag.icon, "name", None))
        if key not in seen:
            seen.add(key)
            unique_list.append(tag)
    return unique_list


def _dir_contains_py(path: Path) -> bool:
    """Return True if directory contains at least one .py file (recursively)."""
    try:
        next(path.rglob("*.py"))
        return True
    except StopIteration:
        return False


def _iter_tree_items_for_dir(
    root: Path,
    df: pd.DataFrame,
    rel_start: Optional[Path] = None,
) -> List[sac.TreeItem]:
    """
    Recursively build sac.TreeItem list for a given directory.
    - Folders are included only if they (recursively) contain at least one .py file.
    - Files are included if they end with .py.
    - Tagging is computed from df using the file basename (origin file in logs).
    """
    items: List[sac.TreeItem] = []
    rel_here = rel_start if rel_start is not None else Path("")

    # Files directly under current directory
    files = sorted([p for p in root.iterdir() if p.is_file() and p.suffix == ".py"])
    for f in files:
        basename = f.name  # logs use only basename (e.g. database.py)
        tag = _file_tag_from_df(df, basename)
        items.append(sac.TreeItem(basename, icon="file", tag=tag))

    # Child directories with at least one .py inside
    dirs = sorted(
        [
            d
            for d in root.iterdir()
            if d.is_dir() and d.name != "__pycache__" and _dir_contains_py(d)
        ]
    )
    for d in dirs:
        children = _iter_tree_items_for_dir(d, df, rel_here / d.name)
        # Only add folder if it has visible children
        if children:
            items.append(sac.TreeItem(d.name, icon="folder", children=children))

    return items


def _count_tree_nodes(items: List[sac.TreeItem]) -> int:
    """Return total number of nodes (folders + files) for sac.tree index preselection."""
    total = 0
    stack: List[sac.TreeItem] = items[:]
    while stack:
        node = stack.pop()
        total += 1
        for ch in getattr(node, "children", []) or []:
            stack.append(ch)
    return total


def _file_tag_from_df(df: pd.DataFrame, filename: str):
    """
    Build the per-file Tag(s):
      - Red/orange icon tag(s) for WARNING/ERROR/CRITICAL
      - Otherwise None (default look)
    """
    # Compute present severities for that filename
    sub = df.loc[df["origin file"] == filename, "severity_raw"]
    if sub.empty:
        return None

    sevs = sorted(set(s for s in sub if s in _SEV_ORDER))
    if not sevs:
        return None

    tags = []
    for sev in sevs:
        if sev in _SEV_ICON:
            color, icon_name = _SEV_ICON[sev]
            tags.append(sac.Tag("", color=color, size="xs", icon=sac.BsIcon(icon_name)))
    return _unique_tags(tags)


# ============================================================
# Logs Page
# ============================================================


class LogsPage(Page):
    """
    Streamlit page to visualize and filter application logs.

    Key improvements:
    - Robust session_state use
    - Robust origin split (rsplit)
    - Severity handled with raw + label columns (filter on raw, show label)
    - Dynamic trees per src/pvapp/{analysis,backend,gui,tools}
    """

    def __init__(self) -> None:
        super().__init__("log")
        self.logs: Union[str, List[str]] = []
        self.path: Path = Path("logs/pvapp.log")
        self.code_base: Path = Path("src/pvapp")  # root code folder

    # -----------------------------
    # Data Loading & Parsing
    # -----------------------------
    def load_logs(self) -> None:
        """Load the log file content into self.logs as a string."""
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                self.logs = file.read()
        except FileNotFoundError:
            self.logs = "No logs found."

    def _normalize_severity_label(self, raw: str) -> str:
        """Strip ANSI codes and map to 'icon + label' format."""
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
        columns = ['date-time', 'logger name', 'severity_raw', 'severity_label',
                   'origin file', 'line', 'description'].
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
                severity_label = self._normalize_severity_label(m.group("severity"))
                origin = m.group("origin").strip()
                msg = m.group("msg")

                # robust split: handle paths with ':' (e.g., Windows)
                try:
                    file_name, line_str = origin.rsplit(":", 1)
                except ValueError:
                    file_name, line_str = origin, ""

                # raw level for filtering
                severity_raw = _extract_caps_severity(severity_label) or "DEBUG"

                current = {
                    "date-time": dt,
                    "logger name": logger,
                    "severity_raw": severity_raw,
                    "severity_label": severity_label,
                    "origin file": Path(file_name).name,
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
                "severity_raw",
                "severity_label",
                "origin file",
                "line",
                "description",
            ],
        )

    # -----------------------------
    # Dynamic Trees (analysis / backend / gui / tools)
    # -----------------------------
    def _build_category_tree(
        self, df: pd.DataFrame, category: str, key_suffix: str
    ) -> List[str]:
        """
        Build a tree for a given top-level category under src/pvapp/{category}.
        Returns the selected file basenames ('.py') from the tree.
        """
        base = self.code_base / category
        if not base.exists() or not base.is_dir():
            st.info(f"Folder '{category}' not found under {self.code_base}.")
            return []

        # root items for the category
        items = _iter_tree_items_for_dir(base, df)

        if not items:
            st.caption(f"No .py files found under '{category}'.")
            return []

        total_nodes = _count_tree_nodes(items)
        # Pre-select all nodes (like original behavior)
        selected = sac.tree(
            [sac.TreeItem(category.upper(), icon="folder", children=items)],
            open_all=True,
            checkbox=True,
            size="xs",
            index=list(range(total_nodes + 1)),  # +1 for the category root
            on_change=self.load_logs,
            key=f"tree_{key_suffix}",
        )

        # Keep only basenames ending with .py
        selected_files = [
            s for s in selected if isinstance(s, str) and s.endswith(".py")
        ]
        return selected_files

    # -----------------------------
    # Rendering
    # -----------------------------
    def render(self) -> None:
        """Render the Logs page with filters, trees, and log table."""
        self.load_logs()
        if not self.logs:
            st.warning(self.T("log_not_found"))
            return
        log_color = ["#3BC83B", "#4F66FF", "#f7c036", "#d03d3d", "#c700ea"]
        sac.alert(
            self.T("title"),
            variant="quote",
            color=log_color[self.app_status[0]],
            size=35,
            icon=sac.BsIcon("menu-up", color="red", size=30),
        )

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

        notif = st.session_state.get("notification_time")
        notif = pd.to_datetime(notif, errors="coerce") if notif is not None else pd.NaT

        if use_last_run and pd.notna(notif):
            start_guess = notif
        else:
            start_guess = min_dt

        # -----------------------------
        # Filters UI
        # -----------------------------
        a, b = st.columns([1, 3])

        with b:
            l, r = st.columns([1, 3])

            # Severity pills — filter on raw, display label later
            severities = list(sorted(log_df["severity_raw"].dropna().unique()))
            sel_sev = l.pills(
                "Severity",
                options=severities,
                default=severities,
                selection_mode="multi",
                on_change=self.load_logs,
                key="log_severity",
            )

            # Time filter expander
            with r.expander("Time Filter", icon="🕐", expanded=True):
                c1, c2 = st.columns([1.2, 1])

                with c1:
                    date_range = st.date_input(
                        "Date range",
                        value=(start_guess.date(), max_dt.date()),
                        min_value=min_dt.date(),
                        max_value=max_dt.date(),
                        format="DD/MM/YYYY",
                        on_change=self.load_logs,
                        key="log_date_range",
                    )
                    if isinstance(date_range, tuple):
                        start_date, end_date = date_range
                    else:
                        start_date = end_date = date_range

                from datetime import time, datetime as dtmod

                default_t_start = (
                    start_guess.time()
                    if start_date == start_guess.date()
                    else time(0, 0, 0)
                )

                with c2:
                    t_start = st.time_input(
                        "Start Time",
                        value=default_t_start,
                        on_change=self.load_logs,
                        key="log_start_time_filter",
                    )

            start_dt = pd.to_datetime(dtmod.combine(start_date, t_start))

        # -----------------------------
        # Trees per category (tabs)
        # -----------------------------
        with a:
            tabs = st.tabs(["analysis", "backend", "gui", "tools"], width="stretch")

            # We restrict logs to those >= start_guess for tree tagging to reflect latest run
            start_for_tags = notif if pd.notna(notif) else min_dt
            last_logs = log_df[(log_df["date-time"] >= start_for_tags)].copy()

            selected_files_all: List[str] = []

            with tabs[0]:
                sel_analysis = self._build_category_tree(
                    last_logs, "analysis", "analysis"
                )
                selected_files_all.extend(sel_analysis)

            with tabs[1]:
                sel_backend = self._build_category_tree(last_logs, "backend", "backend")
                selected_files_all.extend(sel_backend)

            with tabs[2]:
                sel_gui = self._build_category_tree(last_logs, "gui", "gui")
                selected_files_all.extend(sel_gui)

            with tabs[3]:
                sel_tools = self._build_category_tree(last_logs, "tools", "tools")
                selected_files_all.extend(sel_tools)

        # Ensure stable session state for filters (without end time for now)
        if "log_filters" not in st.session_state:
            st.session_state["log_filters"] = (
                start_dt,
                tuple(sel_sev),
                tuple(sorted(set(selected_files_all))),
            )
        if (
            start_dt,
            tuple(sel_sev),
            tuple(sorted(set(selected_files_all))),
        ) != st.session_state["log_filters"]:
            st.session_state["log_filters"] = (
                start_dt,
                tuple(sel_sev),
                tuple(sorted(set(selected_files_all))),
            )
            st.rerun()

        # Apply filters
        if selected_files_all:
            filtered_logs_df = log_df[
                (log_df["date-time"] >= start_dt)
                & (log_df["severity_raw"].isin(sel_sev))
                & (log_df["origin file"].isin(selected_files_all))
            ].copy()
        else:
            # If nothing selected, show nothing (explicit)
            filtered_logs_df = log_df.iloc[0:0].copy()

        # -----------------------------
        # Display
        # -----------------------------
        with b:
            filtered_logs_df.sort_values("date-time", ascending=False, inplace=True)
            st.caption(f"{len(filtered_logs_df)} records out of {len(log_df)} total")

            # Show friendly label but keep raw for internal logic
            display_df = filtered_logs_df.copy()
            display_df["severity"] = display_df["severity_label"]
            display_df = display_df.drop(columns=["severity_raw", "severity_label"])

            st.dataframe(display_df, use_container_width=True)

            if st.button("Clean logs"):
                st.session_state["notification_time"] = pd.Timestamp.now()
                st.toast("Filtro spostato all'istante attuale")
                st.rerun()

    # -----------------------------
    # App Status
    # -----------------------------
    @property
    def app_status(self) -> tuple[Status, dict[str, int]]:
        """Return (overall Status, counts per CRITICAL/ERROR/WARNING) since last notification_time."""
        self.load_logs()
        log_df = self.parse_logs_to_dataframe(self.logs, from_path=False).copy()
        log_df["date-time"] = pd.to_datetime(log_df["date-time"], errors="coerce")
        log_df = log_df.dropna(subset=["date-time"])

        # start may be missing or not set yet
        start = pd.to_datetime(
            st.session_state.get("notification_time"), errors="coerce"
        )
        if pd.isna(start):
            if log_df.empty:
                return Status.OK, {"CRITICAL": 0, "ERROR": 0, "WARNING": 0}
            start = log_df["date-time"].min()

        last_logs = log_df[log_df["date-time"] >= start].copy()

        # Compute levels from severity_label (already normalized)
        levels = last_logs["severity_raw"].astype(str).str.upper()
        if levels.empty:
            return Status.OK, {"CRITICAL": 0, "ERROR": 0, "WARNING": 0}

        counts = levels.value_counts().reindex(
            ["CRITICAL", "ERROR", "WARNING"], fill_value=0
        )
        n_logs = {
            "CRITICAL": int(counts["CRITICAL"]),
            "ERROR": int(counts["ERROR"]),
            "WARNING": int(counts["WARNING"]),
        }

        priority = {"CRITICAL": 4, "ERROR": 3, "WARNING": 2, "INFO": 1, "DEBUG": 0}
        worst = int(levels.map(priority).max())

        if worst >= priority["CRITICAL"]:
            return Status.CRITICAL, n_logs
        if worst >= priority["ERROR"]:
            return Status.ERROR, n_logs
        if worst >= priority["WARNING"]:
            return Status.WARNING, n_logs
        if worst >= priority["INFO"]:
            return Status.INFO, n_logs
        return Status.OK, n_logs
