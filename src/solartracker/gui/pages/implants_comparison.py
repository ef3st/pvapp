import streamlit as st
import json
from pathlib import Path
import pandas as pd
from analysis.implantanalyser import ImplantAnalyser
import plotly.express as px
from .page import Page
from .support import plots
from .support.traslator import translate


def T(key: str) -> str | list:
    return translate(f"implants_comparison.{key}")


class ImplantsComparisonPage(Page):
    def __init__(self):
        self.df_implants = pd.DataFrame()
        self.df_selected = pd.DataFrame()
        self.df_total = pd.DataFrame()
        self.selected_seasons = []
        self.variable_selected = ""
        self.stat_selected = "sum"

    def load_all_implants(self, folder: Path = Path("data/")) -> pd.DataFrame:
        data = []
        for subfolder in sorted(folder.iterdir()):
            if subfolder.is_dir():
                site_file = subfolder / "site.json"
                implant_file = subfolder / "implant.json"
                simulation_file = subfolder / "simulation.csv"
                if site_file.exists() and implant_file.exists() and simulation_file.exists():
                    try:
                        site = json.load(site_file.open())
                        implant = json.load(implant_file.open())
                        data.append(
                            {
                                "site_name": site.get("name", "Unknown"),
                                "implant_name": implant.get("name", "Unnamed"),
                                "subfolder": subfolder,
                                "id": subfolder.name,
                            }
                        )
                    except Exception as e:
                        st.error(f"Error reading {subfolder.name}: {e}")
        return pd.DataFrame(data)

    def select_implants(self):
        with st.expander("\U0001f4da " + T("subtitle.select_implants")):
            df = self.df_implants
            df["label"] = df["site_name"] + " - " + df["implant_name"]

            if "implant_selection" not in st.session_state:
                st.session_state.implant_selection = {
                    row["id"]: True for _, row in df.iterrows()
                }
            a, b, _ = st.columns([1, 1, 7])
            with a:
                if st.button(T("buttons.select_all")):
                    for imp_id in df["id"]:
                        st.session_state.implant_selection[imp_id] = True
            with b:
                if st.button(T("buttons.deselect_all")):
                    for imp_id in df["id"]:
                        st.session_state.implant_selection[imp_id] = False

            col1, col2, col3 = st.columns(3)
            i = -1
            l = df.shape[0] / 3
            
            for _, row in df.iterrows():
                i += 1
                imp_id = row["id"]
                label = row["label"]
                if i < l:
                    with col1:
                        st.session_state.implant_selection[imp_id] = st.checkbox(
                            label,
                            value=st.session_state.implant_selection.get(imp_id, False),
                            key=f"checkbox_{imp_id}",
                        )
                elif i < 2 * l:
                    with col2:
                        st.session_state.implant_selection[imp_id] = st.checkbox(
                            label,
                            value=st.session_state.implant_selection.get(imp_id, False),
                            key=f"checkbox_{imp_id}",
                        )
                else:
                    with col3:
                        st.session_state.implant_selection[imp_id] = st.checkbox(
                            label,
                            value=st.session_state.implant_selection.get(imp_id, False),
                            key=f"checkbox_{imp_id}",
                        )

            selected_ids = [
                imp_id
                for imp_id, selected in st.session_state.implant_selection.items()
                if selected
            ]
            self.df_selected = df[df["id"].isin(selected_ids)]

    def render(self):
        st.title("\U0001f3ad " + T("title"))
        self.df_implants = self.load_all_implants()
        self.select_implants()

        if self.df_selected.empty:
            st.info("\u2139\ufe0f Nessun impianto selezionato")
            return
        st.markdown("---")
        dfs = []
        for row in self.df_selected.itertuples(index=True):
            if (row.subfolder / "simulation.csv").exists():
                df = ImplantAnalyser(row.subfolder).periodic_report()
                df["implant"] = row.label
                dfs.append(df)

        self.df_total = pd.concat(dfs, ignore_index=True)
        st.subheader("\U0001f4ca " + T("subtitle.plots"))
        plots.seasonal_plot(self.df_total, "implants_comparison")
        st.markdown("---")
        dfs = []
        for row in self.df_selected.itertuples(index=True):
            if (row.subfolder / "simulation.csv").exists():
                df = ImplantAnalyser(row.subfolder).numeric_dataframe()
                df["implant"] = row.label
                dfs.append(df)

        dfs = pd.concat(dfs)
        plots.time_plot(dfs, 1, "implants_comparison")
