import streamlit as st
import json
from pathlib import Path
import pandas as pd
from analysis.implantanalyser import ImplantAnalyser
import plotly.express as px
from .page import Page


def translate(key: str) -> str | list:
    keys = key.split(".")
    result = st.session_state.get("T", {})
    for k in keys:
        if isinstance(result, dict) and k in result:
            result = result[k]
        else:
            return key  # fallback se manca qualcosa
    return result


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
                if site_file.exists() and implant_file.exists():
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
        st.subheader("\U0001f4da " + T("subtitle.select_implants"))
        df = self.df_implants
        df["label"] = df["site_name"] + " - " + df["implant_name"]

        if "implant_selection" not in st.session_state:
            st.session_state.implant_selection = {
                row["id"]: True for _, row in df.iterrows()
            }

        col1, col2 = st.columns(2)
        with col1:
            if st.button(T("buttons.select_all")):
                for imp_id in df["id"]:
                    st.session_state.implant_selection[imp_id] = True
        with col2:
            if st.button(T("buttons.deselect_all")):
                for imp_id in df["id"]:
                    st.session_state.implant_selection[imp_id] = False

        i = 0
        l = df.shape[0] / 2
        for _, row in df.iterrows():
            imp_id = row["id"]
            label = row["label"]
            if i < l:
                with col1:
                    st.session_state.implant_selection[imp_id] = st.checkbox(
                        label,
                        value=st.session_state.implant_selection.get(imp_id, False),
                        key=f"checkbox_{imp_id}",
                    )
            else:
                with col2:
                    st.session_state.implant_selection[imp_id] = st.checkbox(
                        label,
                        value=st.session_state.implant_selection.get(imp_id, False),
                        key=f"checkbox_{imp_id}",
                    )

            i += 1

        selected_ids = [
            imp_id
            for imp_id, selected in st.session_state.implant_selection.items()
            if selected
        ]
        self.df_selected = df[df["id"].isin(selected_ids)]

    def render_plot(self):
        st.subheader("\U0001f4ca " + T("subtitle.plots"))
        col_graph, col_settings = st.columns([8, 2])

        if "stat" not in st.session_state:
            st.session_state.stat = "sum"

        with col_settings:
            variable_options = self.df_total["variable"].unique().tolist()
            index = (
                variable_options.index("dc_p_mp")
                if "dc_p_mp" in variable_options
                else 0
            )
            self.variable_selected = st.selectbox(
                T("buttons.choose_var"), variable_options, index=index
            )

            season_options = self.df_total["season"].unique().tolist()
            default = season_options
            if not self.selected_seasons == []:
                default = self.selected_seasons
            self.selected_seasons = st.multiselect(
                T("buttons.periods"), season_options, default=default
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    T("buttons.sum"),
                    type=("primary" if st.session_state.stat == "sum" else "secondary"),
                ):
                    st.session_state.stat = "sum"
                    st.rerun()
            with col2:
                if st.button(
                    T("buttons.mean"),
                    type=(
                        "primary" if st.session_state.stat == "mean" else "secondary"
                    ),
                ):
                    st.session_state.stat = "mean"
                    st.rerun()

        self.stat_selected = st.session_state.stat

        df_filtered = self.df_total[
            (self.df_total["variable"] == self.variable_selected)
            & (self.df_total["stat"] == self.stat_selected)
            & (self.df_total["season"].isin(self.selected_seasons))
        ]

        with col_graph:
            fig = px.bar(
                df_filtered,
                x="season",
                y="value",
                color="implant",
                barmode="group",
                title=f"{self.stat_selected.upper()} of {self.variable_selected}",
                labels={
                    "value": self.stat_selected,
                    "implant": T("plots.periodic.legend"),
                    "season": T("plots.periodic.x"),
                },
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)

    def render(self):
        st.title("\U0001f3ad " + T("title"))
        self.df_implants = self.load_all_implants()
        self.select_implants()

        if self.df_selected.empty:
            st.info("\u2139\ufe0f Nessun impianto selezionato")
            return

        # st.write("Impianti selezionati:")
        # st.dataframe(self.df_selected)
        st.markdown("---")
        dfs = []
        for row in self.df_selected.itertuples(index=True):
            df = ImplantAnalyser(row.subfolder).periodic_report()
            df["implant"] = row.label
            dfs.append(df)

        self.df_total = pd.concat(dfs, ignore_index=True)
        self.render_plot()
