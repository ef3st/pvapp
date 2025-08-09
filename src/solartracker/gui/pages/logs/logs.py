import streamlit_antd_components as sac
from ..page import Page
import streamlit as st
from pathlib import Path
import json
import re
import pandas as pd
from typing import Union

# --- Utility regex to strip ANSI color codes (e.g., \x1b[36m ... \x1b[0m)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# --- Regex to match the start of a log record
# Example:
# 2025-07-05 00:42:38 - solartracker - [36mDEBUG[0m - database.py:43 - message...
_LOG_RE = re.compile(
    r"^(?P<dt>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - "
    r"(?P<logger>[^-]+?) - "
    r"(?P<severity>.+?) - "
    r"(?P<origin>[^-]+?) - "
    r"(?P<msg>.*)$"
)

# --- Map plain severity -> icon + label
_SEVERITY_ICON = {
    "INFO": "ℹ️ INFO",
    "WARNING": "⚠️ WARNING",
    "ERROR": "❌ ERROR",
    "DEBUG": "🔎 DEBUG",
    "CRITICAL": "❌❌❌ CRITICAL",
}
# In cima alla classe (o come attributi di classe)
START_REGEX = re.compile(
    r"Starting\s+SolarTracker\s+GUI\s+in\s+.+?\s+mode\s+with\s+log\s+level\s+.+",
    re.IGNORECASE,
)


class LogsPage(Page):
    def __init__(self) -> None:
        super().__init__("log")
        self.logs = []
        self.path: Path = "logs/solartracker.log"

    def load_logs(self):
        try:
            with open(self.path, "r") as file:
                self.logs = file.read()  # .readlines()
        except FileNotFoundError:
            self.logs = ["No logs found."]

    def render(self):
        self.load_logs()
        if not self.logs:
            st.warning(self.T("log_not_found"))
            return

        st.title(self.T("title"))

        # --- Bottone per aggiornare manualmente
        if st.button("🔄 Update"):
            st.rerun()

        log_df = self.parse_logs_to_dataframe(self.logs, from_path=False)

        # --- Normalize datetime column
        log_df["date-time"] = pd.to_datetime(log_df["date-time"], errors="coerce")
        log_df = log_df.dropna(subset=["date-time"])
        if log_df.empty:
            st.info("Nessun record di log valido.")
            return

        # --- Bounds
        min_dt = log_df["date-time"].min()
        max_dt = log_df["date-time"].max()

        # --- Toggle: usa inizio ultima esecuzione
        use_last_run = st.toggle(
            "Usa inizio ultima esecuzione",
            value=True,
            help="Se attivo, data e ora di inizio sono impostate al (presunto) avvio dell’ultima esecuzione.",
        )

        if use_last_run:
            start_guess = st.session_state.start_time
            if start_guess is None:
                start_guess = min_dt
        else:
            start_guess = min_dt

        # --- UI Filtri
        with st.expander("Filtri", expanded=True):
            c1, c2, c3 = st.columns([1.2, 1, 1])

            with c1:
                date_range = st.date_input(
                    "Intervallo date",
                    value=(start_guess.date(), max_dt.date()),
                    min_value=min_dt.date(),
                    max_value=max_dt.date(),
                    format="DD/MM/YYYY",
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
            default_t_end = (
                max_dt.time() if end_date == max_dt.date() else time(23, 59, 59)
            )

            with c2:
                t_start = st.time_input("Ora inizio", value=default_t_start)
            with c3:
                t_end = st.time_input("Ora fine", value=default_t_end)

            severities = list(sorted(log_df["severity"].dropna().unique()))
            sel_sev = st.pills(
                "Severity",
                options=severities,
                default=severities,
                selection_mode="multi",
            )

            origins = list(sorted(log_df["origin file"].dropna().unique()))
            sel_orig = st.multiselect(
                "File di origine", options=origins, default=origins
            )
        start_dt = pd.to_datetime(dtmod.combine(start_date, t_start))
        end_dt = pd.to_datetime(dtmod.combine(end_date, t_end))
        a, b = st.columns([1, 3])
        with a:
            self.gui_tree()
        with b:
            fdf = log_df[
                (log_df["date-time"] >= start_dt)
                & (log_df["date-time"] <= end_dt)
                & (log_df["severity"].isin(sel_sev))
                & (log_df["origin file"].isin(sel_orig))
            ].copy()

            fdf.sort_values("date-time", ascending=False, inplace=True)

            st.caption(f"{len(fdf)} record su {len(log_df)} totali")
            st.dataframe(fdf, use_container_width=True)

    def gui_tree(self):
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
                                    sac.TreeItem("home.py", icon="file", tag="py"),
                                ],
                            ),
                            sac.TreeItem(
                                "implant_performance",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "implant_performance.py", icon="file", tag="py"
                                    ),
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
                                                "add_implant.py", icon="file", tag="py"
                                            ),
                                        ],
                                    ),
                                    sac.TreeItem("implants.py", icon="file", tag="py"),
                                ],
                            ),
                            sac.TreeItem(
                                "implants_comparison",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "implants_comparison.py", icon="file", tag="py"
                                    ),
                                ],
                            ),
                            sac.TreeItem(
                                "logs",
                                icon="folder",
                                children=[
                                    sac.TreeItem("logs.py", icon="file", tag="py"),
                                ],
                            ),
                            sac.TreeItem(
                                "plant_manager",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "plant_manager.py", icon="file", tag="py"
                                    ),
                                ],
                            ),
                            sac.TreeItem(
                                "grid",
                                icon="folder",
                                children=[
                                    sac.TreeItem("grid_tab.py", icon="file", tag="py"),
                                    sac.TreeItem("grid.py", icon="file", tag="py"),
                                ],
                            ),
                            sac.TreeItem(
                                "module",
                                icon="folder",
                                children=[
                                    sac.TreeItem("module.py", icon="file", tag="py"),
                                ],
                            ),
                            sac.TreeItem(
                                "site",
                                icon="folder",
                                children=[
                                    sac.TreeItem(
                                        "plant_manager.py", icon="file", tag="py"
                                    ),
                                ],
                            ),
                            sac.TreeItem("__init__.py", icon="file", tag="py"),
                            sac.TreeItem("page.py", icon="file", tag="py"),
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
                                    sac.TreeItem("plots.py", icon="file", tag="py"),
                                ],
                            ),
                        ],
                    ),
                    sac.TreeItem(
                        "translation",
                        icon="folder",
                        children=[
                            sac.TreeItem("traslator.py", icon="file", tag="py"),
                        ],
                    ),
                    sac.TreeItem("maingui.py", icon="file", tag="py"),
                ],
            )
        ]

        selected = sac.tree(
            items,
            open_all=True,
            checkbox=True,
            size="xs",
        )
        return selected

    def mount_tree(self):
        items = [
            sac.TreeItem(
                "MOUNT",
                icon="folder",
                children=[
                    sac.TreeItem(
                        "developement",
                        icon="folder",
                        children=[
                            sac.TreeItem("custommount.py", icon="file", tag="py"),
                            sac.TreeItem("tracking.py", icon="file", tag="py"),
                        ],
                    )
                ],
            ),
        ]

        selected = sac.tree(
            items,
            open_all=True,
            checkbox=True,
            size="xs",
        )

        return selected

    def _normalize_severity(self, raw: str) -> str:
        """Strip ANSI codes and normalize to the 'icon + label' format."""
        clean = _ANSI_RE.sub("", raw).strip()
        # Extract first word as canonical severity (e.g., "DEBUG", "INFO")
        m = re.match(r"([A-Za-z]+)", clean)
        if not m:
            return clean  # Fallback: return as-is if unrecognized
        key = m.group(1).upper()
        return _SEVERITY_ICON.get(key, clean)

    def parse_logs_to_dataframe(
        self, log_source: Union[str, bytes], from_path: bool = False
    ) -> pd.DataFrame:
        """
        Parse the given log text (or file) into a pandas DataFrame with columns:
        'date-time', 'name_logger', 'severity', 'origin file', 'description'.

        Parameters
        ----------
        log_source : str | bytes
            If from_path=False (default): the *log text* itself.
            If from_path=True: the *file path* of the log file.
        from_path : bool
            Whether 'log_source' is a file path.

        Returns
        -------
        pd.DataFrame
        """
        if from_path:
            with open(log_source, "rb") as f:
                content = f.read()
            # Try to decode with utf-8, fallback to latin-1 if needed
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
        current = None  # hold the last parsed record for multiline descriptions

        for raw_line in text.splitlines():
            line = raw_line.rstrip("\n")
            m = _LOG_RE.match(line)
            if m:
                # Flush previous pending record
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
                    "name_logger": logger,
                    "severity": severity,
                    "origin file": file_name,
                    "line": line_str,
                    "description": msg,  # will be extended if subsequent lines belong here
                }
            else:
                # Continuation line -> append to the last description
                if current is not None:
                    # Preserve the raw continuation line exactly
                    current["description"] += "\n" + raw_line
                else:
                    # Line before any match; you can choose to skip or collect as unknown.
                    # Here we skip stray lines.
                    continue

        # Append the final pending record
        if current is not None:
            rows.append(current)

        df = pd.DataFrame(
            rows,
            columns=[
                "date-time",
                "name_logger",
                "severity",
                "origin file",
                "line",
                "description",
            ],
        )
        return df
