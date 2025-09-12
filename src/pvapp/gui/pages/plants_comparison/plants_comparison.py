import json
from pathlib import Path

import pandas as pd
import plotly.express as px  # noqa: F401
import streamlit as st

from analysis.plantanalyser import PlantAnalyser
from gui.pages import Page
from gui.utils.plots import plots


# * =============================
# *     PLANTS COMPARISON PAGE
# * =============================
class PlantsComparisonPage(Page):
    """
    Streamlit page for comparing multiple PV plants.

    Attributes:
        df_plants (pd.DataFrame): Metadata of all plants found in data folders.
        df_selected (pd.DataFrame): Subset of selected plants.
        df_total (pd.DataFrame): Aggregated data from selected plants.
        selected_seasons (list[str]): Seasons selected for comparison.
        variable_selected (str): Selected variable for visualization.
        stat_selected (str): Selected statistic ("sum" or "mean").

    Methods:
        load_all_plants: Scan folder and load all available plants.
        select_plants: Render UI for selecting plants.
        render: Render the entire Streamlit page (entrypoint).
    """

    # * =========================================================
    # *                      LIFECYCLE
    # * =========================================================
    def __init__(self) -> None:
        """Initialize empty state and default values."""
        super().__init__("plants_comparison")
        self.df_plants = pd.DataFrame()
        self.df_selected = pd.DataFrame()
        self.df_total = pd.DataFrame()
        self.selected_seasons: list[str] = []
        self.variable_selected: str = ""
        self.stat_selected: str = "sum"

    # * =========================================================
    # *                     DATA LOADING
    # * =========================================================
    def load_all_plants(self, folder: Path = Path("data/")) -> pd.DataFrame:
        """
        Scan subfolders for valid plants and collect metadata.

        Args:
            folder (Path): Root folder containing subfolders with plant data.

        Returns:
            pd.DataFrame: Table with columns: site_name, plant_name, subfolder, id.
        """
        data = []
        for subfolder in sorted(folder.iterdir()):
            if subfolder.is_dir():
                site_file = subfolder / "site.json"
                plant_file = subfolder / "plant.json"
                simulation_file = subfolder / "simulation.csv"
                if (
                    site_file.exists()
                    and plant_file.exists()
                    and simulation_file.exists()
                ):
                    try:
                        site = json.load(site_file.open())
                        plant = json.load(plant_file.open())
                        data.append(
                            {
                                "site_name": site.get("name", "Unknown"),
                                "plant_name": plant.get("name", "Unnamed"),
                                "subfolder": subfolder,
                                "id": subfolder.name,
                            }
                        )
                    except Exception as e:
                        st.error(f"Error reading {subfolder.name}: {e}")
        return pd.DataFrame(data)

    # * =========================================================
    # *                     UI: SELECTION
    # * =========================================================
    def select_plants(self) -> None:
        """
        Render a plant selection panel with checkboxes.

        Notes:
        - Maintains state in `st.session_state["plant_selection"]`.
        - Supports select all / deselect all actions.
        """
        with st.expander("📚 " + self.T("subtitle.select_plants")):
            df = self.df_plants
            df["label"] = df["site_name"] + " - " + df["plant_name"]

            if "plant_selection" not in st.session_state:
                st.session_state.plant_selection = {
                    row["id"]: True for _, row in df.iterrows()
                }

            a, b, _ = st.columns([1, 1, 7])
            with a:
                if st.button(self.T("buttons.select_all"), key="select_all"):
                    for imp_id in df["id"]:
                        st.session_state.plant_selection[imp_id] = True
                    st.rerun()
            with b:
                if st.button(self.T("buttons.deselect_all"), key="deselect_all"):
                    for imp_id in df["id"]:
                        st.session_state.plant_selection[imp_id] = False
                    st.rerun()

            col1, col2, col3 = st.columns(3)
            i = -1
            l = df.shape[0] / 3

            for _, row in df.iterrows():
                i += 1
                imp_id = row["id"]
                label = row["label"]
                if i < l:
                    with col1:
                        st.session_state.plant_selection[imp_id] = st.checkbox(
                            label,
                            value=st.session_state.plant_selection.get(imp_id, False),
                            key=f"checkbox_{imp_id}",
                        )
                elif i < 2 * l:
                    with col2:
                        st.session_state.plant_selection[imp_id] = st.checkbox(
                            label,
                            value=st.session_state.plant_selection.get(imp_id, False),
                            key=f"checkbox_{imp_id}",
                        )
                else:
                    with col3:
                        st.session_state.plant_selection[imp_id] = st.checkbox(
                            label,
                            value=st.session_state.plant_selection.get(imp_id, False),
                            key=f"checkbox_{imp_id}",
                        )

            selected_ids = [
                imp_id
                for imp_id, selected in st.session_state.plant_selection.items()
                if selected
            ]
            self.df_selected = df[df["id"].isin(selected_ids)]

    # * =========================================================
    # *                        RENDER
    # * =========================================================
    def render(self) -> None:
        """
        Render the full Streamlit page for plant comparison.

        Notes:
        - Displays plant selection, seasonal plots, and instant time-series plots.
        """
        import streamlit_antd_components as sac

        sac.alert(
            self.T("title"),
            variant="quote",
            color="skyblue",
            size=35,
            icon=sac.BsIcon("bar-chart-steps", color="lime"),
        )

        self.df_plants = self.load_all_plants()
        if self.df_plants.empty:
            messages = self.T("messages.no_plant_found")
            sac.result(messages[0], description=messages[1], status="empty")
            return

        self.select_plants()
        if self.df_selected.empty:
            st.info("ℹ️ No plant selected")
            return

        sac.divider(
            label="Analysis",
            icon=sac.BsIcon("clipboard2-data", 20),
            align="center",
            color="gray",
            variant="dashed",
        )

        dfs = []
        for row in self.df_selected.itertuples(index=True):
            if (row.subfolder / "simulation.csv").exists():
                df = PlantAnalyser(row.subfolder).periodic_report(0)
                df["plant"] = row.label
                dfs.append(df)
        self.df_total = pd.concat(dfs, ignore_index=True)

        st.subheader("📊 " + self.T("subtitle.plots"))
        plots.seasonal_plot(self.df_total, "plants_comparison")

        sac.divider(
            label="Instant measures",
            icon=sac.BsIcon("clock", 20),
            align="center",
            color="gray",
            variant="dashed",
        )

        dfs = []
        for row in self.df_selected.itertuples(index=True):
            if (row.subfolder / "simulation.csv").exists():
                df = PlantAnalyser(row.subfolder).numeric_dataframe(array=0)
                df["plant"] = row.label
                dfs.append(df)

        dfs = pd.concat(dfs)
        plots.time_plot(dfs, 1, "plants_comparison")
