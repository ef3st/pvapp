import streamlit as st
import json
from pathlib import Path
import pandas as pd
from analysis.implantanalyser import ImplantAnalyser
import plotly.express as px

def load_all_implants(folder: Path = Path("data/")) -> pd.DataFrame:
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
                            "id": subfolder.name
                        }
                    )
                except Exception as e:
                    st.error(f"Error reading {subfolder.name}: {e}")
    return pd.DataFrame(data)

def select_implants(df: pd.DataFrame):
    st.markdown("### Selezione impianti da confrontare")

    # Colonne che identificano ogni impianto
    df["label"] = df["site_name"] + " - " + df["implant_name"]

    # Inizializza lo stato se non ancora presente
    if "implant_selection" not in st.session_state:
        st.session_state.implant_selection = {row["id"]: True for _, row in df.iterrows()}

    # Pulsanti per selezionare / deselezionare tutti
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Seleziona tutti"):
            for imp_id in df["id"]:
                st.session_state.implant_selection[imp_id] = True
    with col2:
        if st.button("Deseleziona tutti"):
            for imp_id in df["id"]:
                st.session_state.implant_selection[imp_id] = False

    # Mostra checkbox per ogni impianto
    for _, row in df.iterrows():
        imp_id = row["id"]
        label = row["label"]
        st.session_state.implant_selection[imp_id] = st.checkbox(
            label,
            value=st.session_state.implant_selection.get(imp_id, False),
            key=f"checkbox_{imp_id}"
        )

    # Restituisce solo gli ID selezionati
    selected_ids = [imp_id for imp_id, selected in st.session_state.implant_selection.items() if selected]
    return df[df["id"].isin(selected_ids)]


def render():
    st.title("IMPLANTS COMPARISON")
    
    df_implants = load_all_implants()
    df_selected = select_implants(df_implants)

    st.write("Impianti selezionati:")
    st.dataframe(df_selected)
    
    dfs = []
    for row in df_selected.itertuples(index=True):
        df = ImplantAnalyser(row.subfolder).periodic_report()
        df["implant"] = row.label
        dfs.append(df)
        
    df_total = pd.concat(dfs, ignore_index=True)
    sum_mean_plot(df_total)



def sum_mean_plot(df_plot):
    st.markdown("### Periodic stats")

    col_graph, col_settings = st.columns([8, 2])

    # Inizializza stato stat se non presente
    if "stat" not in st.session_state:
        st.session_state["stat"] = "sum"

    with col_settings:
        # Variabile da tracciare
        variable_options = df_plot["variable"].unique().tolist()
        index = variable_options.index("dc_p_mp") if "dc_p_mp" in variable_options else 0
        variable_selected = st.selectbox("Choose variable:", variable_options, index=index)

        # Selettori impianti e stagioni
        implant_options = df_plot["implant"].unique().tolist()
        selected_implants = st.multiselect("Scegli impianti:", implant_options, default=implant_options)

        season_options = df_plot["season"].unique().tolist()
        selected_seasons = st.multiselect("Scegli periodi:", season_options, default=season_options)

        # Bottoni stat
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Sum",
                type=("primary" if st.session_state["stat"] == "sum" else "secondary"),
            ):
                st.session_state["stat"] = "sum"

        with col2:
            if st.button(
                "Mean",
                type=("primary" if st.session_state["stat"] == "mean" else "secondary"),
            ):
                st.session_state["stat"] = "mean"

    stat_selected = st.session_state["stat"]

    # Filtro dati
    df_filtered = df_plot[
        (df_plot["variable"] == variable_selected) &
        (df_plot["stat"] == stat_selected) &
        (df_plot["implant"].isin(selected_implants)) &
        (df_plot["season"].isin(selected_seasons))
    ]

    with col_graph:
        fig = px.bar(
            df_filtered,
            x="season",
            y="value",
            color="implant",
            barmode="group",
            title=f"{stat_selected.upper()} of {variable_selected}",
            labels={"value": stat_selected, "implant": "Impianto", "season": "Periodo"},
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)