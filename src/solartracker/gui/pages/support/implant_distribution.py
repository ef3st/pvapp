import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.graph_objects as go
import math
import numpy as np
from geopy.distance import geodesic
import streamlit.components.v1 as components


def implant_distribution():
    implant_map()
    status_panels()


def status_panels():

    # Simulazione dati
    N_STRINGS = 10
    MODULES_PER_STRING = 5
    PARAMS = ["Voltage", "Current", "Power", "Temperature"]

    # Genera dati fittizi per ciascun modulo
    data = []
    for s in range(N_STRINGS):
        for m in range(MODULES_PER_STRING):
            data.append(
                {
                    "string": s,
                    "module": m,
                    "Voltage": np.random.uniform(30, 40),
                    "Current": np.random.uniform(5, 10),
                    "Power": np.random.uniform(150, 400),
                    "Temperature": np.random.uniform(20, 60),
                }
            )
    df = pd.DataFrame(data)

    # --- Layout Streamlit ---
    st.title("Realtime Monitoring Inverter")

    # Inverter Info
    with st.expander("Inverter Info: 🟢 Online"):
        st.markdown(
            """
        - **Modello:** ABC123  
        - **Stato:** 🟢 Online  
        - **Potenza Totale:** {:.1f} W  
        - **Ultimo aggiornamento:** {}
        """.format(
                df["Power"].sum(), pd.Timestamp.now().strftime("%H:%M:%S")
            )
        )

    # Parametro selezionato per la colorazione
    selected_param = st.selectbox("Seleziona parametro per la visualizzazione", PARAMS)

    # Calcolo dei colori in base al parametro
    min_val = df[selected_param].min()
    max_val = df[selected_param].max()

    def get_color(val):
        norm = (val - min_val) / (max_val - min_val + 1e-6)
        return f"rgba({int(255 * (1 - norm))}, {int(255 * norm)}, 100, 0.8)"

    # Layout dei moduli con parametri laterali
    st.markdown("### Stato dei Moduli")

    cols = st.columns(
        int(N_STRINGS / 2)
    )  # 3 colonne per ogni stringa (sinistra | modulo | destra)

    for pair in range(0, N_STRINGS, 2):  # s and s+1
        left_str = df[df["string"] == pair]
        right_str = df[df["string"] == pair + 1]
        with cols[int(pair / 2)]:
            # cols = st.columns([1, 2, 2, 1])  # sinistra | stringa s | stringa s+1 | destra
            left, center_l, center_r, right = st.columns([1, 2, 2, 1])
            for m in range(MODULES_PER_STRING):
                left_mod = left_str[left_str["module"] == m].iloc[0]
                right_mod = right_str[right_str["module"] == m].iloc[0]

                color_l = get_color(left_mod[selected_param])
                color_r = get_color(right_mod[selected_param])

                # Parametri modulo sinistro (prima colonna)
                with left:
                    st.markdown(
                        f"<div style='font-size:12px; text-align:right'>"
                        f"V:{left_mod['Voltage']:.1f}<br>"
                        f"I:{left_mod['Current']:.1f}<br>"
                        f"P:{left_mod['Power']:.0f}<br>"
                        f"T:{left_mod['Temperature']:.0f}</div>",
                        unsafe_allow_html=True,
                    )

                # Modulo stringa sinistra
                with center_l:
                    st.markdown(
                        f"<div style='height:78px; background-color:{color_l}; "
                        f"border:1px solid #333; text-align:center; font-size:12px;'>S{pair}-M{m}</div>",
                        unsafe_allow_html=True,
                    )

                # Modulo stringa destra
                with center_r:
                    st.markdown(
                        f"<div style='height:78px; background-color:{color_r}; "
                        f"border:1px solid #333; text-align:center; font-size:12px;'>S{pair+1}-M{m}</div>",
                        unsafe_allow_html=True,
                    )

                # Parametri modulo destro (quarta colonna)
                with right:
                    st.markdown(
                        f"<div style='font-size:12px; text-align:left'>"
                        f"V:{right_mod['Voltage']:.1f}<br>"
                        f"I:{right_mod['Current']:.1f}<br>"
                        f"P:{right_mod['Power']:.0f}<br>"
                        f"T:{right_mod['Temperature']:.0f}</div>",
                        unsafe_allow_html=True,
                    )


def status_panel():

    pass


def implant_map():

    df = pd.DataFrame(
        [
            {"lat": 44.3602, "lon": 12.2144},
            {"lat": 44.3602, "lon": 12.2145},
            {"lat": 44.3602, "lon": 12.2146},
            {"lat": 44.3602, "lon": 12.2147},
            {"lat": 44.3602, "lon": 12.2148},
            {"lat": 44.3602, "lon": 12.2149},
            {"lat": 44.3602, "lon": 12.2150},
            {"lat": 44.3602, "lon": 12.2151},
            {"lat": 44.3602, "lon": 12.2152},
            {"lat": 44.3603, "lon": 12.2144},
            {"lat": 44.3603, "lon": 12.2145},
            {"lat": 44.3603, "lon": 12.2146},
            {"lat": 44.3603, "lon": 12.2147},
            {"lat": 44.3603, "lon": 12.2148},
            {"lat": 44.3603, "lon": 12.2149},
            {"lat": 44.3603, "lon": 12.2150},
            {"lat": 44.3603, "lon": 12.2151},
            {"lat": 44.3603, "lon": 12.2152},
            {"lat": 44.3605, "lon": 12.2144},
            {"lat": 44.3605, "lon": 12.2145},
            {"lat": 44.3605, "lon": 12.2146},
            {"lat": 44.3605, "lon": 12.2147},
            {"lat": 44.3605, "lon": 12.2148},
            {"lat": 44.3605, "lon": 12.2149},
            {"lat": 44.3605, "lon": 12.2150},
            {"lat": 44.3605, "lon": 12.2151},
            {"lat": 44.3605, "lon": 12.2152},
            {"lat": 44.3606, "lon": 12.2144},
            {"lat": 44.3606, "lon": 12.2145},
            {"lat": 44.3606, "lon": 12.2146},
            {"lat": 44.3606, "lon": 12.2147},
            {"lat": 44.3606, "lon": 12.2148},
            {"lat": 44.3606, "lon": 12.2149},
            {"lat": 44.3606, "lon": 12.2150},
            {"lat": 44.3606, "lon": 12.2151},
            {"lat": 44.3606, "lon": 12.2152},
        ]
    )
    view = pdk.ViewState(
        latitude=44.3604,
        longitude=12.2144,
        zoom=17,
    )

    layer1 = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[lon, lat]",
        get_color="[255, 0, 0, 160]",
        get_radius=50,
        radius_scale=2,  # Aumenta/diminuisce con lo zoom
        radius_min_pixels=3,  # Dimensione minima visibile
        radius_max_pixels=5,  # Dimensione massima visibile
    )

    polygon = [
        (12.2143, 44.3601),
        (12.2156, 44.3601),
        (12.2153, 44.3607),
        (12.2143, 44.3607),
        (12.2143, 44.3601),
    ]

    layer2 = pdk.Layer(
        "PolygonLayer",
        data=[{"polygon": polygon, "name": "Area impianto"}],
        get_polygon="polygon",
        get_fill_color="[0, 0, 255, 100]",  # Rosso semitrasparente
        pickable=True,
        auto_highlight=True,
    )
    deck = pdk.Deck(
        layers=[layer2, layer1],
        initial_view_state=view,
        tooltip={"text": "📍 Posizione"},
    )

    st.pydeck_chart(deck, use_container_width=False, height=300)


def visulization_implant():
    fig = go.Figure()

    # Add a tilted panel
    # --- Vertici del pannello inclinato ---
    panel_x, panel_y, panel_z = get_panel_vertices(
        tilt_deg=0, azimuth_deg=270, width=1, height=1, center=(0, 0, 0.5)  # Sud
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
    floor_x = [-6, 8, 8, -8]
    floor_y = [-6, -8, 8, 8]
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
            color="lightgreen",
            opacity=0.5,
            name="Surface",
        )
    )
    # === Assi cardinali come coni ===
    fig.add_trace(
        go.Cone(
            x=[floor_x[2]],
            y=[floor_y[2]],
            z=[0.05],
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
            x=[floor_x[2]],
            y=[floor_y[2]],
            z=[0.05],
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
            x=[floor_x[2]],
            y=[floor_y[2]],
            z=[0.05],
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
            x=[floor_x[2]],
            y=[floor_y[2]],
            z=[0.05],
            u=[0],
            v=[-1],
            w=[0],
            sizemode="absolute",
            sizeref=0.5,
            name="South",
            showscale=False,
        )
    )

    # === Etichette "N", "S", "E", "O" sul pavimento ===
    labels = go.Scatter3d(
        x=[
            floor_x[2],
            floor_x[2],
            floor_x[2] + 0.5,
            floor_x[2] - 0.5,
        ],  # Est-Ovest sui +X/-X
        y=[
            floor_y[2] + 0.8,
            floor_y[2] - 0.8,
            floor_y[2],
            floor_y[2],
        ],  # Nord-Sud sui +Y/-Y
        z=[0.03, 0.03, 0.03, 0.03],  # Pavimento (z=0)
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
            xaxis=dict(visible=False),  # Nasconde l'asse X
            yaxis=dict(visible=False),  # Nasconde l'asse Y
            zaxis=dict(visible=False),  # Nasconde l'asse Z
            xaxis_showgrid=False,
            yaxis_showgrid=False,
            zaxis_showgrid=False,
        ),
        scene_camera=dict(
            eye=dict(
                x=0.8, y=0.8, z=0.5
            )  # Valori più alti = zoom out, più bassi = zoom in
        ),
        height=1000,
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


def geodetic_to_cartesian(lat_deg, lon_deg, R=6371):
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    x = R * np.cos(lat) * np.cos(lon)
    y = R * np.cos(lat) * np.sin(lon)
    z = R * np.sin(lat)
    return np.array([x, y, z])


def three_point_angle(A, B, C, geographic=True):
    if geographic:
        A = geodetic_to_cartesian(A[0], A[1])
        B = geodetic_to_cartesian(B[0], B[1])
        C = geodetic_to_cartesian(C[0], C[1])
    BA = np.array(A) - np.array(B)
    BC = np.array(C) - np.array(B)
    cos_angolo = np.dot(BA, BC) / (np.linalg.norm(BA) * np.linalg.norm(BC))
    angolo_rad = np.arccos(
        np.clip(cos_angolo, -1.0, 1.0)
    )  # clip per stabilità numerica
    return np.degrees(angolo_rad)
