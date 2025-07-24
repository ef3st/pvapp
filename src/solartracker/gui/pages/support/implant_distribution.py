import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.graph_objects as go
import math
import numpy as np
from geopy.distance import geodesic
import streamlit.components.v1 as components
import plotly.graph_objects as go
import time
from ..beta import network_classes as net
from streamlit_elements import elements, mui, html


def implant_distribution():
    if "plant" not in st.session_state:
        st.session_state.plant = {
            "name": "Test_1",
            "network": net.Network(),
            "status": "war",
            "messages": [
                {
                    "status": "⚠️",
                    "from": "Inverter X",
                    "severity": "warning",
                    "message": "Too hight temperature",
                    "suggestion": "Turn off inverter",
                },
                {
                    "status": "‼️",
                    "from": "Module C",
                    "severity": "error",
                    "message": "Too hight temperature",
                    "suggestion": "Change module angle",
                },
                {
                    "status": "ℹ️",
                    "from": "Implant",
                    "severity": "info",
                    "message": "No energy aviable",
                    "suggestion": "Switch off house lights",
                },
            ],
        }

    current = st.session_state.plant
    a, b = st.columns(2)
    with a.container(border=False):
        left, center, right, rr = st.columns([1, 1, 2, 3])
        left.button("Expand All")
        center.button("Collaps All")
        right.button("Switch OFF All")
        status = rr.segmented_control(
            " ", options=["Operative", "Warning", "Error"], label_visibility="collapsed"
        )
        implant_report(current["messages"])
    with b:
        top_display(status)
        implant_map()
    buildnet, monitoring, manager = st.tabs(
        ["🏗️ Implant Network", "💻 Monitoring", "⚙️ Manager"],
    )
    with buildnet:
        build_network(current["network"])
    with monitoring:
        monitor(current["network"])
    #     # stremlit_test()

    # tests()
    # network_status()
    # new_status_panels()


def send_mail(message):
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import smtplib

    """
        Invio del contenuto del widget Text tramite email.
        """
    recipient_email = (
        "pepa.lorenzo.01@gmail.com"  # Cambia con l'indirizzo del destinatario
    )
    subject = "Message from PV Implant"
    body = message

    # Configurazione del messaggio email
    msg = MIMEMultipart()
    msg["From"] = "r.revival.music@gmail.com"
    msg["To"] = "pepa.lorenzo.01@gmail.com"
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    # Connessione al server SMTP
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()  # Abilita la crittografia TLS
        server.login(msg["From"], "ujlu tbty vwcz qnbj ")
        server.sendmail(msg["From"], recipient_email, msg.as_string())


def top_display(status):
    with elements("implant_report"):
        if status == "Operative":
            mui.Alert("Everything is going well", severity="success")
        if status == "Warning":
            mui.Alert(
                "Something requires attenction", severity="warning", variant="outlined"
            )
            send_mail("Something requires attenction")
        if status == "Error":
            mui.Alert("Something worng", severity="error", variant="filled")
            send_mail("Something wrong")


def implant_report(messages):
    with st.expander("📃 Implant Report", expanded=True):
        df = pd.DataFrame(messages)
        st.data_editor(df)


@st.fragment
def build_network(network: net.Network):
    if not network.nodes:
        st.title("➕ New Implant Network:")
        left, right = st.columns(2)
        with left:
            inverters = st.number_input("Inverter_Number", min_value=0, step=1)
            st.text_input("Inverters Model")
        with right:
            modules = st.number_input("Module_Number", min_value=0, step=1)
            st.text_input("Modules Model")
        if st.button("Create Network"):
            new_net = net.Network()
            for i in range(0, inverters):
                new_net.add_node(net.Inverter(f"Inverter_{i}"))
            for i in range(0, modules):
                new_net.add_node(net.Modulo(f"Module_{i}"))
                if i < (modules / 2):
                    new_net.link_nodes("Inverter_0", f"Module_{i}")
                else:
                    if i == modules / 2:
                        new_net.link_nodes("Inverter_1", f"Module_{i}")
                    else:
                        new_net.link_nodes(f"Module_{i-1}", f"Module_{i}")

            st.session_state.plant["network"] = new_net
            st.rerun(scope="fragment")
    else:
        # st.plotly_chart(visualizza_plotly(network))
        html = network.show_net()
        components.html(html, height=600, width=1000, scrolling=False)


def monitor(network):
    inverters()
    panels()
    # inverter_display()


def inverters():
    with st.container(border=True):
        st.title("🔌 Inverters")


def panels():
    with st.container(border=True):
        st.title("⚡ Modules")
        panels = [
            {
                "name": "Module_1",
                "Power": 250,
                "Temperature": 10,
                "status": "ok",
                "n_messages": 0,
                "on": True,
                "Tilt": 30,
            },
            {
                "name": "Module_2",
                "Power": 250,
                "Temperature": 20,
                "status": "war",
                "n_messages": 1,
                "on": True,
                "Tilt": 30,
            },
            {
                "name": "Module_7",
                "Power": 250,
                "Temperature": 30,
                "status": "err",
                "n_messages": 3,
                "on": True,
                "Tilt": 30,
            },
            {
                "name": "Module_3",
                "Power": 250,
                "Temperature": 40,
                "status": "ok",
                "n_messages": 0,
                "on": True,
                "Tilt": 30,
            },
            {
                "name": "Module_4",
                "Power": 250,
                "Temperature": 50,
                "status": "ok",
                "n_messages": 2,
                "on": True,
                "Tilt": 30,
            },
            {
                "name": "Module_5",
                "Power": 250,
                "Temperature": 60,
                "status": "ok",
                "n_messages": 5,
                "on": False,
                "Tilt": 30,
            },
            {
                "name": "Module_6",
                "Power": 250,
                "Temperature": 70,
                "status": "ok",
                "n_messages": 5,
                "on": True,
                "Tilt": 30,
            },
        ]

        cols = st.columns(len(panels), gap=None, border=False)
        with st.container(border=True):
            for i, panel in enumerate(panels):
                with cols[i]:
                    new_panel_display(panel, False)


def inverter_display():
    with st.expander("🔌 Inverter X"):
        with st.expander("🟩 Inverter status"):
            st.markdown(
                """
        - **Model:** ABC123  
        - **Status:** 🟢 Online  
        - **Total Power:** {:.1f} W  
        - **last update:** {}
        """.format(
                    250, pd.Timestamp.now().strftime("%H:%M:%S")
                )
            )
        with st.expander("Serie 1"):
            general = {"Tilt": None}
            with st.expander("⚙️ Settings"):
                general["on"] = st.toggle("On/Off", value=True, key="a")
                general["on"] = st.number_input(
                    "Tilt", key="aa", on_change=st.rerun, value=30
                )
            panels = [
                {
                    "name": "Test_1",
                    "Power": 250,
                    "Temperature": 10,
                    "status": "ok",
                    "n_messages": 0,
                    "on": st.session_state.a,
                    "Tilt": st.session_state.aa,
                },
                {
                    "name": "Test_2",
                    "Power": 250,
                    "Temperature": 20,
                    "status": "war",
                    "n_messages": 1,
                    "on": st.session_state.a,
                    "Tilt": st.session_state.aa,
                },
                {
                    "name": "Test_7",
                    "Power": 250,
                    "Temperature": 30,
                    "status": "err",
                    "n_messages": 3,
                    "on": st.session_state.a,
                    "Tilt": st.session_state.aa,
                },
                {
                    "name": "Test_3",
                    "Power": 250,
                    "Temperature": 40,
                    "status": "ok",
                    "n_messages": 0,
                    "on": st.session_state.a,
                    "Tilt": st.session_state.aa,
                },
                {
                    "name": "Test_4",
                    "Power": 250,
                    "Temperature": 50,
                    "status": "ok",
                    "n_messages": 2,
                    "on": st.session_state.a,
                    "Tilt": st.session_state.aa,
                },
                {
                    "name": "Test_5",
                    "Power": 250,
                    "Temperature": 60,
                    "status": "ok",
                    "n_messages": 5,
                    "on": st.session_state.a,
                    "Tilt": st.session_state.aa,
                },
                {
                    "name": "Test_6",
                    "Power": 250,
                    "Temperature": 70,
                    "status": "ok",
                    "n_messages": 5,
                    "on": st.session_state.a,
                    "Tilt": st.session_state.aa,
                },
            ]

            cols = st.columns(len(panels), gap=None, border=False)
            with st.container(border=False):
                for i, panel in enumerate(panels):
                    with cols[i]:
                        panel_display(panel, False)


def panel_display(panel_data, options):
    with st.container(border=options):
        top, bottom = st.columns(
            [25, 1],
            vertical_alignment="top",
            border=options,
            gap="small",
        )
        with top:
            with elements(f"{panel_data["name"]}"):
                module_card(panel_data, "test")
        if options:
            a, b, c = bottom.columns(3)

            def open_info():
                st.session_state.info_panel = "info"
                st.rerun()

            def change_angle():
                st.session_state.info_panel = "change_angle"
                st.rerun()

            a.button("ℹ️", key=f"a{panel_data["name"]}", on_click=open_info)
            c.toggle("🔛", label_visibility="collapsed", key=f"b{panel_data["name"]}")
            b.button("📐", key=f"c{panel_data["name"]}", on_click=change_angle)


def new_panel_display(panel_data, options):
    with st.container(border=options):
        top, bottom = st.columns(
            [25, 1],
            vertical_alignment="top",
            border=options,
            gap="small",
        )
        with top:
            with elements(f"{panel_data["name"]}"):
                module_card(panel_data, "test")


def new_status_panels():
    from streamlit_elements import elements, mui, html
    from streamlit_elements import dashboard
    from itertools import product

    N_STRINGS = 2
    MODULES_PER_STRING = 2
    df = generate_data(N_STRINGS, MODULES_PER_STRING)

    with elements("dashboard"):
        layout = [
            dashboard.Item(
                f"{i}_{j}", x=j + 2, y=0, w=1, h=1, isDraggable=True, isResizable=True
            )
            for i, j in product(range(N_STRINGS), range(MODULES_PER_STRING))
        ]
        with dashboard.Grid(layout):
            for pair in range(N_STRINGS):
                str_df = df[df["string"] == pair]
                for m in range(MODULES_PER_STRING):
                    mod = str_df[str_df["module"] == m].iloc[0]

                    module_card(mod, f"{pair}_{m}")


def ciao():
    st.info("Switch ON")


def rgba(temp):
    if temp < 20:
        norm = (1 - temp / 20) if (temp >= 0 and temp < 20) else 1
        return f"rgba(0,0,{255*norm},0.8)"
    else:
        norm = (temp - 20) / (80 - 20)
        return f"rgba({255*norm},{255*(1-norm)},0,0.5)"


def module_card(panel_data, key):
    from streamlit_elements import lazy, sync

    with mui.Card(
        key=key,
        sx={
            "backgroundColor": rgba(panel_data["Temperature"]),
            "color": "white",
            "border": "1px solid #00acc1",
            "minWidth": "150px",
            "maxWidth": "150px",
        },
    ):
        # with mui.CardActionArea(onClick=lazy(alert)):
        with mui.CardContent():
            mui.Typography(f'{panel_data["name"]}', variant="h6")
            mui.Typography(f"Inverter: X", color="text.secondary")
            # mui.Typography(f'Power: {round(panel_data["Power"])}W', color="text.secondary")
            mui.Chip(label=f"{round(panel_data["Power"])}W", size="small")
            mui.Chip(label=f"{round(panel_data["Temperature"])}°C", size="small")
            mui.Slider(
                label="Custom marks",
                defaultValue={panel_data["Tilt"]},
                marks=True,
                valueLabelDisplay="auto",
                min={0.0},
                max={180.0},
            )
            with mui.Box(
                sx={"border": "1px dashed grey", "backgroundColor": "rgba(0,0,0,0.8)"}
            ):
                if panel_data["status"] == "ok":
                    if panel_data["on"]:
                        mui.Chip(label="ON ", color="success", size="small")
                    else:
                        mui.Chip(
                            label="OFF",
                            variant="outlined",
                            color="success",
                            size="small",
                        )

                    mui.Radio(label="On", color="success", checked=True, size="small")
                    if panel_data["n_messages"]:
                        mui.Badge(
                            "ℹ️", badgeContent={panel_data["n_messages"]}, key=f"b{key}"
                        )
                    else:
                        mui.Badge("✅", key=f"b{key}")

                if panel_data["status"] == "war":
                    if panel_data["on"]:
                        mui.Chip(label="ON", color="warning", size="small")
                    else:
                        mui.Chip(
                            label="OFF",
                            variant="outlined",
                            color="warning",
                            size="small",
                        )
                    mui.Radio(label="On", color="warning", checked=True, size="small")
                    if panel_data["n_messages"]:
                        mui.Badge(
                            "⚠️", badgeContent={panel_data["n_messages"]}, key=f"b{key}"
                        )

                if panel_data["status"] == "err":
                    if panel_data["on"]:
                        mui.Chip(label="ON", color="error", size="small")
                    else:
                        mui.Chip(
                            label="OFF", variant="outlined", color="error", size="small"
                        )
                    mui.Radio(label="On", color="error", checked=True, size="small")
                    if panel_data["n_messages"]:
                        mui.Badge(
                            "‼️", badgeContent={panel_data["n_messages"]}, key=f"b{key}"
                        )


# streamlit-graphic test
def stremlit_test():
    st.segmented_control(
        " ",
        options=["Monitoring", "Settings"],
        label_visibility="collapsed",
        default="Monitoring",
        key="monitoring",
    )
    if "info_panel" not in st.session_state:
        st.session_state.info_panel = None
    if st.session_state.info_panel == "info":
        with st.container(border=True):
            st.markdown("Ciao")

            def close():
                st.session_state.info_panel = None

            st.button("Close", icon="❌", on_click=close)
    elif st.session_state.info_panel == "change_angle":

        st.button("Close", icon="❌", on_click=close)

    aa, bb, _ = st.columns([1, 1, 5], gap=None, border=True)
    with aa.container(border=False):
        general = {"Tilt": None}
        with st.expander("⚙️ Settings"):
            general["on"] = st.toggle("On/Off", value=True, key="a")
            general["on"] = st.number_input("Tilt", key="aa", on_change=st.rerun)
        panel_display(
            {
                "name": "Test_1",
                "Power": 250,
                "Temperature": 10,
                "status": "ok",
                "n_messages": 0,
                "on": st.session_state.a,
                "Tilt": st.session_state.aa,
            }
        )
        panel_display(
            {
                "name": "Test_2",
                "Power": 250,
                "Temperature": 20,
                "status": "war",
                "n_messages": 1,
                "on": st.session_state.a,
                "Tilt": st.session_state.aa,
            }
        )
        panel_display(
            {
                "name": "Test_7",
                "Power": 250,
                "Temperature": 30,
                "status": "err",
                "n_messages": 3,
                "on": st.session_state.a,
                "Tilt": st.session_state.aa,
            }
        )
        panel_display(
            {
                "name": "Test_3",
                "Power": 250,
                "Temperature": 40,
                "status": "ok",
                "n_messages": 0,
                "on": st.session_state.a,
                "Tilt": st.session_state.aa,
            }
        )
        panel_display(
            {
                "name": "Test_4",
                "Power": 250,
                "Temperature": 50,
                "status": "ok",
                "n_messages": 2,
                "on": st.session_state.a,
                "Tilt": st.session_state.aa,
            }
        )
        panel_display(
            {
                "name": "Test_5",
                "Power": 250,
                "Temperature": 60,
                "status": "ok",
                "n_messages": 5,
                "on": st.session_state.a,
                "Tilt": st.session_state.aa,
            }
        )
        panel_display(
            {
                "name": "Test_6",
                "Power": 250,
                "Temperature": 70,
                "status": "ok",
                "n_messages": 5,
                "on": st.session_state.a,
                "Tilt": st.session_state.aa,
            }
        )
    # with bb.container(border=False):
    #     general = {}
    #     with st.expander("⚙️ Settings"):
    #         general["on"] = st.toggle("On/Off",value= True, key="b")
    #         general["Tilt"] = st.number_input("Tilt", key="ba")
    #     panel_display({"name": "test", "Power": 250, "Temperature":80, "on":general["on"], "Tilt": general["Tilt"]})
    #     panel_display({"name": "tes3", "Power": 250, "Temperature":15, "on":general["on"], "Tilt": general["Tilt"]})


####


def panel_display_old(panel_data):
    borders = False if st.session_state.monitoring == "Monitoring" else True
    with st.container(border=borders):
        top, bottom = st.columns(
            [25, 1],
            vertical_alignment="top",
            border=borders,
            gap="small",
        )
        with top:
            with elements(f"{panel_data["name"]}"):
                module_card(panel_data, "test")
        if st.session_state.monitoring != "Monitoring":
            a, b, c = bottom.columns(3)

            def open_info():
                st.session_state.info_panel = "info"
                st.rerun()

            def change_angle():
                st.session_state.info_panel = "change_angle"
                st.rerun()

            a.button("ℹ️", key=f"a{panel_data["name"]}", on_click=open_info)
            c.toggle("🔛", label_visibility="collapsed", key=f"b{panel_data["name"]}")
            b.button("📐", key=f"c{panel_data["name"]}", on_click=change_angle)


def generate_data(n_strings, modules_per_string):
    # Simulazione dati
    n_strings = 6
    modules_per_string = 9
    PARAMS = ["Voltage", "Current", "Power", "Temperature"]

    # Genera dati fittizi per ciascun modulo
    data = []
    for s in range(n_strings):
        for m in range(modules_per_string):
            data.append(
                {
                    "module": m,
                    "string": s,
                    "name": f"M{m} S{s}",
                    "Voltage": np.random.uniform(30, 40),
                    "Current": np.random.uniform(5, 10),
                    "Power": np.random.uniform(150, 400),
                    "Temperature": np.random.uniform(10, 80),
                }
            )
    return pd.DataFrame(data)


def build_net():
    if not "net" in st.session_state:
        st.session_state.net = net.Network()

    network = st.session_state.net
    with st.popover("Add inverter"):
        with st.form("Add Inverter"):
            inv_name = st.text_input("Invertername")
            if st.form_submit_button("ADD Inverter"):
                node = net.Inverter(inv_name)
                network.add_node(node)
    with st.popover("Add Module"):
        with st.form("Add Module"):
            inv_name = st.text_input("Module ername")
            if st.form_submit_button("ADD Module"):
                node = net.Modulo(inv_name)
                network.add_node(node)

    a = st.selectbox("first node", options=list(network.nodes.keys()))
    b = st.selectbox("second node", options=list(network.nodes.keys()))
    if st.button("Create link"):
        network.link_nodes(a, b)
    st.plotly_chart(visualizza_plotly(network))
    # html = network.show_net()
    # components.html(html, height=600, width=1000, scrolling=False)
    pass


def visualizza_plotly(network):
    import networkx as nx

    G = nx.Graph()

    for nodo in network.nodes.values():
        G.add_node(nodo.id, tipo=type(nodo).__name__)
    for nodo in network.nodes.values():
        for conn in nodo.connections:
            G.add_edge(nodo.id, conn.id)

    pos = nx.spectral_layout(G)

    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    node_x = []
    node_y = []
    node_color = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        tipo = G.nodes[node]["tipo"]
        node_color.append("green" if tipo == "Modulo" else "orange")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            line=dict(width=1, color="gray"),
            hoverinfo="none",
            mode="lines",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            marker=dict(
                size=20, color=node_color, symbol="circle"
            ),  # o 'square', 'diamond'
            text=[f"{id}" for id in G.nodes],
            hovertext=[f"{G.nodes[nodo]['tipo']}<br>ID: {nodo}" for nodo in G.nodes],
            hoverinfo="text",
            textposition="bottom center",
        )
    )

    fig.update_layout(
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
    )
    return fig


def tests():
    from streamlit_elements import elements, mui, html

    with elements("dashboard"):

        # You can create a draggable and resizable dashboard using
        # any element available in Streamlit Elements.

        from streamlit_elements import dashboard

        # First, build a default layout for every element you want to include in your dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("first_item", 0, 0, 2, 2),
            dashboard.Item("second_item", 2, 0, 2, 2, isDraggable=False, moved=False),
            dashboard.Item("third_item", 0, 2, 1, 1, isResizable=False),
        ]

        # Next, create a dashboard layout using the 'with' syntax. It takes the layout
        # as first parameter, plus additional properties you can find in the GitHub links below.

        with dashboard.Grid(layout):
            mui.Paper("First item", key="first_item")
            mui.Paper("Second item (cannot drag)", key="second_item")
            mui.Paper("Third item (cannot resize)", key="third_item")

        # If you want to retrieve updated layout values as the user move or resize dashboard items,
        # you can pass a callback to the onLayoutChange event parameter.

        def handle_layout_change(updated_layout):
            # You can save the layout in a file, or do anything you want with it.
            # You can pass it back to dashboard.Grid() if you want to restore a saved layout.
            print(updated_layout)

        with dashboard.Grid(layout, onLayoutChange=handle_layout_change):
            mui.Paper("First item", key="first_item")
            mui.Paper("Second item (cannot drag)", key="second_item")
            mui.Paper("Third item (cannot resize)", key="third_item")

    st.button("Test_", type="primary")
    st.button("Test_1", type="secondary", help="HELP")
    st.button("Test_2", type="tertiary")
    with st.form("my_form"):
        st.write("Inside the form")
        slider_val = st.slider("Form slider")
        checkbox_val = st.checkbox("Form checkbox")

        # Every form must have a submit button.
        submitted = st.form_submit_button("Submit")
        if submitted:
            st.write("slider", slider_val, "checkbox", checkbox_val)
    st.write("Outside the form")

    uploaded_file = st.file_uploader("Choose a file")
    st.link_button("ansa", "https://www.ansa.it/")
    st.badge("Ciao")

    progress_text = "Operation in progress. Please wait."
    my_bar = st.progress(0, text=progress_text)

    options = ["North", "East", "South", "West"]
    selection = st.segmented_control("Directions", options, selection_mode="multi")
    st.markdown(f"Your selected options")

    tab1, tab2 = st.tabs(["📈 Chart", "🗃 Data"])
    data = np.random.randn(10, 1)

    tab1.subheader("A tab with a chart")
    tab1.line_chart(data)

    tab2.subheader("A tab with the data")
    tab2.write(data)

    for percent_complete in range(100):
        time.sleep(0.01)
        my_bar.progress(percent_complete + 1, text=progress_text)
    time.sleep(1)
    my_bar.empty()
    progress_text = "Operation in progress. Please wait."
    my_bar = st.progress(0, text=progress_text)

    for percent_complete in range(100):
        time.sleep(0.01)
        my_bar.progress(percent_complete + 1, text=progress_text)
    time.sleep(1)


def status_panels():

    # Simulazione dati
    N_STRINGS = 6
    MODULES_PER_STRING = 9
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
                left_panel = st.container()
                with left_panel:
                    with left:
                        infos = st.popover("ℹ️")
                        infos.markdown(
                            f"<div style='font-size:12px; text-align:right'>"
                            f"V:{left_mod['Voltage']:.1f}<br>"
                            f"I:{left_mod['Current']:.1f}<br>"
                            f"P:{left_mod['Power']:.0f}<br>"
                            f"T:{left_mod['Temperature']:.0f}</div>",
                            unsafe_allow_html=True,
                        )
                        a, b = st.columns(2)
                        panel_on = b.toggle(
                            f"S{pair}-M{m}", label_visibility="collapsed", value=True
                        )
                        if panel_on:
                            a.badge("🟩")
                        else:
                            a.badge("🟥")
                        st.markdown("---")

                    # Modulo stringa sinistra
                    with center_l:
                        st.markdown(
                            f"<div style='height:105px; background-color:{color_l}; "
                            f"border:1px solid #333; text-align:center; font-size:30px;'>S{pair}-M{m}</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown("---")

                # Modulo stringa destra
                with center_r:
                    st.markdown(
                        f"<div style='height:105px; background-color:{color_r}; "
                        f"border:1px solid #333; text-align:center; font-size:30px;'>S{pair+1}-M{m}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown("---")

                # Parametri modulo destro (quarta colonna)
                with right:
                    infos = st.popover("ℹ️")
                    infos.markdown(
                        f"<div style='font-size:12px; text-align:right'>"
                        f"V:{right_mod['Voltage']:.1f}<br>"
                        f"I:{right_mod['Current']:.1f}<br>"
                        f"P:{right_mod['Power']:.0f}<br>"
                        f"T:{right_mod['Temperature']:.0f}</div>",
                        unsafe_allow_html=True,
                    )
                    a, b = st.columns(2)
                    panel_on = b.toggle(
                        f"S{pair+1}-M{m}", label_visibility="collapsed", value=True
                    )
                    if panel_on:
                        a.badge("🟩")
                    else:
                        a.badge("🟥")

                    st.markdown("---")


def network_status():

    data = [
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
    arcs = []
    for i, j in enumerate(data):
        if i < len(data) - 1:
            arc = {
                "from_lat": data[i]["lat"],
                "from_lon": data[i]["lon"],
                "to_lat": data[i + 1]["lat"],
                "to_lon": data[i + 1]["lon"],
            }
        arcs.append(arc)

    arc_data = pd.DataFrame(arcs)
    points_data = pd.DataFrame(data)

    arc_layer = pdk.Layer(
        "ArcLayer",
        data=arc_data,
        get_source_position="[from_lon, from_lat]",
        get_target_position="[to_lon, to_lat]",
        get_source_color=[0, 128, 200],
        get_target_color=[200, 0, 80],
        auto_highlight=True,
        width_scale=0.5,
        get_width=5,
        pickable=True,
    )
    layer1 = pdk.Layer(
        "ScatterplotLayer",
        data=points_data,
        get_position="[lon, lat]",
        get_color="[255, 0, 0, 160]",
        get_radius=50,
        radius_scale=2,  # Aumenta/diminuisce con lo zoom
        radius_min_pixels=3,  # Dimensione minima visibile
        radius_max_pixels=5,  # Dimensione massima visibile
    )
    view_state = pdk.ViewState(
        latitude=44.3602, longitude=12.2152, zoom=18, bearing=0, pitch=30
    )

    deck = pdk.Deck(
        layers=[layer1, arc_layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/light-v9",
        tooltip={"text": "Flusso da {from_lat}, {from_lon} a {to_lat}, {to_lon}"},
    )

    st.pydeck_chart(deck)


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
