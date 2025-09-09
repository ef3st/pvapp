import pydeck as pdk
import plotly.graph_objects as go
import numpy as np
import streamlit as st
import math
import plotly.express as px
from ..translation.traslator import translate
import pandas as pd


def pv3d(tilt, azimuth):
    fig = go.Figure()

    # Add a tilted panel
    # --- Vertici del pannello inclinato ---
    panel_x, panel_y, panel_z = get_panel_vertices(
        tilt_deg=tilt, azimuth_deg=azimuth, width=2, height=1, center=(0, 0, 0.5)  # Sud
    )

    # --- Facce per il pannello (2 triangoli per lato) ---
    faces = [0, 1, 2, 0, 2, 3]

    fig = go.Figure()

    # === Pannello inclinato (lato sopra) ===
    fig.add_trace(
        go.Mesh3d(
            x=panel_x,
            y=panel_y,
            z=panel_z,
            i=faces[0::3],
            j=faces[1::3],
            k=faces[2::3],
            opacity=0.9,
            name="PV",
        )
    )

    # === Pavimento ===
    floor_x = [-2, 2, 2, -2]
    floor_y = [-2, -2, 2, 2]
    floor_z = [0, 0, 0, 0]  # tutto a livello terra

    # Facce per il pavimento (2 triangoli)
    floor_faces = [0, 1, 2, 0, 2, 3]

    fig.add_trace(
        go.Mesh3d(
            x=floor_x,
            y=floor_y,
            z=floor_z,
            i=floor_faces[0::3],
            j=floor_faces[1::3],
            k=floor_faces[2::3],
            color="darkslategray",
            opacity=0.5,
            name="Surface",
        )
    )
    # === Assi cardinali come coni ===
    fig.add_trace(
        go.Cone(
            x=[0],
            y=[0],
            z=[0],
            u=[1],
            v=[0],
            w=[0],
            sizemode="absolute",
            sizeref=0.5,
            name="East",
            showscale=False,
        )
    )
    fig.add_trace(
        go.Cone(
            x=[0],
            y=[0],
            z=[0],
            u=[-1],
            v=[0],
            w=[0],
            sizemode="absolute",
            sizeref=0.5,
            name="West",
            showscale=False,
        )
    )
    fig.add_trace(
        go.Cone(
            x=[0],
            y=[0],
            z=[0],
            u=[0],
            v=[1],
            w=[0],
            sizemode="absolute",
            sizeref=0.5,
            name="North",
            showscale=False,
        )
    )
    fig.add_trace(
        go.Cone(
            x=[0],
            y=[0],
            z=[0],
            u=[0],
            v=[-1],
            w=[0],
            sizemode="absolute",
            sizeref=0.5,
            name="South",
            showscale=False,
        )
    )

    # --- labels "N", "S", "E", "O" on ground ---
    labels = go.Scatter3d(
        x=[0, 0, 1.5, -1.5],  # Est-West on +X/-X
        y=[0.8, -0.8, 0, 0],  # North-South on +Y/-Y
        z=[0, 0, 0, 0],  # Pavimento (z=0)
        mode="text",
        text=["S", "N", "E", "O"],
        textposition="top center",
        textfont=dict(size=20, color="red"),
        showlegend=False,
    )
    fig.add_trace(labels)

    # === Layout ===
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            xaxis_showgrid=False,
            yaxis_showgrid=False,
            zaxis_showgrid=False,
        ),
        scene_camera=dict(
            eye=dict(
                x=0.8, y=0.8, z=0.5
            )  # higher values -> zoom out, lower values -> zoom in
        ),
    )

    st.plotly_chart(fig)


def get_panel_vertices(tilt_deg, azimuth_deg, width=2.0, height=1.0, center=(0, 0, 0)):
    # Convert to radians
    tilt = math.radians(tilt_deg)
    azimuth = math.radians(azimuth_deg)

    # Half-dimensions
    w, h = width / 2, height / 2

    # Define panel in local coordinates (flat, centered)
    points = np.array(
        [
            [-w, -h, 0],
            [w, -h, 0],
            [w, h, 0],
            [-w, h, 0],
        ]
    )

    # Rotate around X (tilt)
    tilt_matrix = np.array(
        [[1, 0, 0], [0, np.cos(tilt), -np.sin(tilt)], [0, np.sin(tilt), np.cos(tilt)]]
    )
    points = points @ tilt_matrix.T

    # Rotate around Z (azimuth)
    azimuth_matrix = np.array(
        [
            [np.cos(azimuth), -np.sin(azimuth), 0],
            [np.sin(azimuth), np.cos(azimuth), 0],
            [0, 0, 1],
        ]
    )
    points = points @ azimuth_matrix.T

    # Translate to center
    points += np.array(center)

    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    return x.tolist(), y.tolist(), z.tolist()


@st.fragment
def seasonal_plot(df_plot, page):
    st.markdown(f"### {translate(f"{page}.subtitle.periodic")}")
    col_graph, col_settings = st.columns([8, 2])

    # Fallback iniziale se non ancora impostato
    if "stat" not in st.session_state:
        st.session_state["stat"] = "sum"

    with col_settings:
        # Scelta variabile
        variable_options = df_plot["variable"].unique().tolist()
        index = (
            variable_options.index("dc_p_mp") if "dc_p_mp" in variable_options else 0
        )
        variable_selected = st.selectbox(
            translate(f"{page}.buttons.choose_variable"), variable_options, index=index
        )
        if variable_selected in translate("plots.variable_description"):
            st.info(translate("plots.variable_description")[variable_selected])
        st.markdown("---")
        if "season" in df_plot.columns:
            season_options = df_plot["season"].unique().tolist()
            default_seasons = season_options
            if "selected_seasons" in st.session_state:
                default_seasons = st.session_state["selected_seasons"]
            else:
                st.session_state["selected_seasons"] = default_seasons
            with st.expander(
                f"📅  {translate(f"{page}.buttons.periods")}", expanded=True
            ):
                selected_seasons = st.pills(
                    " ",
                    options=season_options,
                    default=season_options,
                    selection_mode="multi",
                    label_visibility="collapsed",
                    key=f"{page}_season_selected",
                )
            if st.session_state["selected_seasons"] != selected_seasons:
                st.session_state["selected_seasons"] = selected_seasons
        else:
            selected_seasons = df_plot["season"].unique().tolist()

        # Selezione stat
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                translate(f"{page}.buttons.sum"),
                type=("primary" if st.session_state["stat"] == "sum" else "secondary"),
            ):
                st.session_state["stat"] = "sum"
                st.rerun()
        with col2:
            if st.button(
                translate(f"{page}.buttons.mean"),
                type=("primary" if st.session_state["stat"] == "mean" else "secondary"),
            ):
                st.session_state["stat"] = "mean"
                st.rerun()

    stat_selected = st.session_state["stat"]

    # Filtro dati
    df_filtered = df_plot[
        (df_plot["variable"] == variable_selected)
        & (df_plot["stat"] == stat_selected)
        & (df_plot["season"].isin(selected_seasons))
    ]

    if "plant" in df_filtered.columns:
        fig = px.bar(
            df_filtered,
            x="season",
            y="value",
            color="plant",
            barmode="group",
            labels={
                "value": stat_selected,
                "plant": translate(f"{page}.plots.periodic.legend"),
                "season": translate(f"{page}.plots.periodic.x"),
            },
            height=500,
        )

    else:
        fig = px.bar(
            df_filtered,
            x="season",
            y="value",
            color="season",
            title=f"{stat_selected.upper()} - {variable_selected}",
            labels={"value": stat_selected},
            height=500,
        )

    with col_graph:
        st.plotly_chart(fig, use_container_width=True)
    if "plant" in df_filtered.columns:
        df: pd.DataFrame = df_plot[
            (df_plot["variable"] == variable_selected)
            & (df_plot["stat"] == stat_selected)
            & (df_plot["season"] == "annual")
        ]
        length = df.shape[0]
        with st.container(border=False):

            cols = st.columns(length + 1)
            mean = df["value"].sum() / length
            for i in range(length):
                s = " "
                if variable_selected in translate("plots.variable_description"):
                    s = translate("plots.variable_description")[variable_selected]
                cols[i].metric(
                    label=df["plant"].to_list()[i],
                    value=f"{round(df["value"].to_list()[i],2)} {s[1:s.find(")")]}",
                    delta=f"{round((df["value"].to_list()[i]-mean)*100/(mean),2)}%",
                    help=" 1. Nome impanto \n 2. Valore della variabile nell'anno (somma o media a seconda della selezione) \n 3. Percentuale rispetto la media dei valori mostrati sopra",
                )


@st.fragment
def time_plot(data: pd.DataFrame, default=0, page=""):
    st.markdown(f"### {translate(f"{page}.subtitle.time_distribution")}")

    # Avaiable numeric columns
    numeric_cols = data.select_dtypes(include="number").columns.tolist()
    default_var = "dc_p_mp"
    default_index = (
        numeric_cols.index(default_var) if default_var in numeric_cols else 0
    )

    left, right = st.columns([3, 1])

    with left.expander(f"⚙️ {translate(f"{page}.buttons.choose_variable")}"):
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            variable = st.selectbox(
                f"⚙️ {translate(f"{page}.buttons.choose_variable")}",
                options=numeric_cols,
                index=default_index,
            )

        with col2:
            mode = st.radio(
                f"{translate(f"{page}.buttons.option.label")}",
                translate(f"{page}.buttons.option.options"),
                index=default,
                horizontal=True,
            )

        # Prepare dataframe
        df = data.copy()
        columns_to_keep = ["timestamp", variable]
        if "plant" in df.columns:
            columns_to_keep.insert(0, "plant")

        df["timestamp"] = df.index  # assume datetime index
        df = df[columns_to_keep].dropna()

        min_date = df["timestamp"].min().date()
        max_date = df["timestamp"].max().date()

        # filter depending on mode
        if mode == translate(f"{page}.buttons.option.options")[0]:  # date interval
            start_day, end_day = st.slider(
                "📅 Intervallo date:",
                min_value=min_date,
                max_value=max_date,
                value=(min_date, max_date),
                format="DD/MM/YYYY",
            )
            mask = (df["timestamp"].dt.date >= start_day) & (
                df["timestamp"].dt.date <= end_day
            )
        else:  # single day + hours
            with col3:
                day = st.date_input(
                    f"🗓️ {translate(f"{page}.buttons.choose_date")}",
                    min_value=min_date,
                    max_value=max_date,
                    value=max_date,
                )
            start_hour, end_hour = st.slider(
                "⏰ Ore:", min_value=0, max_value=23, value=(0, 23)
            )
            mask = (
                (df["timestamp"].dt.date == day)
                & (df["timestamp"].dt.hour >= start_hour)
                & (df["timestamp"].dt.hour <= end_hour)
            )

        df_filtered = df[mask]

        if df_filtered.empty:
            st.warning("⚠️ Nessun dato disponibile nel periodo selezionato.")
            return
    if variable in translate("plots.variable_description"):
        right.info(translate("plots.variable_description")[variable])
    #
    if "plant" in df_filtered.columns:
        fig = px.line(
            df_filtered,
            x="timestamp",
            y=variable,
            color="plant",
            title=f"{variable} nel tempo",
            markers=True,
        )
    else:
        fig = px.line(
            df_filtered,
            x="timestamp",
            y=variable,
            title=f"{variable} nel tempo",
            markers=True,
        )

    fig.update_layout(xaxis_title="Timestamp", yaxis_title=variable, height=500)
    graphtab, datatab = st.tabs(tabs=["📈", "🔢"])
    with graphtab:
        st.plotly_chart(fig, use_container_width=True)
    with datatab:
        st.dataframe(df_filtered)
