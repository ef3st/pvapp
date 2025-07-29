import streamlit as st
from pathlib import Path
import json
import pandas as pd
from pvlib.pvsystem import retrieve_sam
from simulation.simulator import Simulate
from analysis.implantanalyser import ImplantAnalyser
import pydeck as pdk
import plotly.graph_objects as go
from ...utils.plots import plots
from ...utils.translation.traslator import translate
from streamlit_custom_notification_box import custom_notification_box


def T(key: str) -> str | list:
    return translate(f"implant_performance.{key}")


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
                        }
                    )
                except Exception as e:
                    st.error(f"Error reading {subfolder.name}: {e}")
    return pd.DataFrame(data)


@st.fragment
def edit_site(subfolder: Path) -> dict:
    site_file = subfolder / "site.json"
    site = json.load(site_file.open())

    site["name"] = st.text_input(T("buttons.site.name"), site["name"])
    with st.expander(f" 🏠 {T("subtitle.address")}"):
        site["address"] = st.text_input(T("buttons.site.address"), site["address"])
        site["city"] = st.text_input(T("buttons.site.city"), site["city"])

    with st.expander(f" 🗺️ {T("subtitle.coordinates")}"):
        col1, col2 = st.columns(2)
        site["coordinates"]["lat"] = col1.number_input(
            T("buttons.site.lat"),
            value=site["coordinates"]["lat"],
            format="%.4f",
            step=0.0001,
        )
        site["coordinates"]["lon"] = col2.number_input(
            T("buttons.site.lon"),
            value=site["coordinates"]["lon"],
            format="%.4f",
            step=0.0001,
        )
        df = pd.DataFrame(
            [{"lat": site["coordinates"]["lat"], "lon": site["coordinates"]["lon"]}]
        )
        view = pdk.ViewState(
            latitude=site["coordinates"]["lat"],
            longitude=site["coordinates"]["lon"],
            zoom=12,
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position="[lon, lat]",
            get_color="[255, 0, 0, 160]",
            get_radius=50,
            radius_scale=2,  # Aumenta/diminuisce con lo zoom
            radius_min_pixels=3,  # Dimensione minima visibile
            radius_max_pixels=10,  # Dimensione massima visibile
        )

        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip={"text": "📍 Posizione"},
        )

        st.pydeck_chart(deck, use_container_width=False, height=300)

    with st.expander(f" 🕐 {T("subtitle.altitude_tz")}"):
        site["altitude"] = st.number_input(
            f"{T("buttons.site.altitude")} (m)",
            value=site["altitude"],
            min_value=0,
            icon="🗻",
        )
        site["tz"] = st.text_input(
            f"{T("buttons.site.timezone")}", site["tz"], icon="🕐"
        )

    return site


@st.fragment
def edit_implant(subfolder: Path) -> dict:
    implant_file = subfolder / "implant.json"
    implant = json.load(implant_file.open())

    implant["name"] = st.text_input(T("buttons.implant.name"), implant["name"])

    # Module configuration
    with st.expander(f"***{T("buttons.implant.module.title")}***", icon="⚡"):
        col1, col2 = st.columns(2)
        module_origins = ["CECMod", "SandiaMod", "pvwatts", "Custom"]
        origin_index = module_origins.index(implant["module"]["origin"])
        implant["module"]["origin"] = col1.selectbox(
            T("buttons.implant.module.origin"), module_origins, index=origin_index
        )

        if implant["module"]["origin"] in ["CECMod", "SandiaMod"]:
            modules = retrieve_sam(implant["module"]["origin"])
            module_names = list(modules.columns)
            module_index = 0
            if implant["module"]["name"] in module_names:
                module_index = module_names.index(implant["module"]["name"])
            implant["module"]["name"] = col2.selectbox(
                T("buttons.implant.module.model"), module_names, index=module_index
            )

            if st.checkbox(T("buttons.implant.module.details")):
                st.code(modules[implant["module"]["name"]], language="json")

        else:
            implant["module"]["name"] = col2.text_input(
                T("buttons.implant.module.name"), implant["module"]["name"]
            )
            sub1, sub2 = st.columns(2)
            implant["module"]["model"]["pdc0"] = sub1.number_input(
                "pdc0 (W)",
                value=float(implant["module"]["model"]["pdc0"]),
                min_value=0.0,
            )
            implant["module"]["model"]["gamma_pdc"] = sub2.number_input(
                "γ_pdc (%/C)",
                value=float(implant["module"]["model"]["gamma_pdc"]),
                min_value=0.0,
            )

        implant["module"]["dc_module"] = {"CECMod": "cec", "SandiaMod": "sapm"}.get(
            implant["module"]["origin"], "pvwatts"
        )

    # Inverter configuration
    with st.expander(f"***{T("buttons.implant.inverter.title")}***", icon="🔌"):
        col1, col2 = st.columns(2)
        inverter_origins = ["cecinverter", "pvwatts", "Custom"]
        inv_index = inverter_origins.index(implant["inverter"]["origin"])
        implant["inverter"]["origin"] = col1.selectbox(
            T("buttons.implant.inverter.origin"), inverter_origins, index=inv_index
        )

        if implant["inverter"]["origin"] == "cecinverter":
            inverters = retrieve_sam("cecinverter")
            inv_names = list(inverters.columns)
            inv_name_index = 0
            if implant["inverter"]["name"] in inv_names:
                inv_name_index = inv_names.index(implant["inverter"]["name"])
            implant["inverter"]["name"] = col2.selectbox(
                T("buttons.implant.inverter.model"), inv_names, index=inv_name_index
            )

            if st.checkbox(T("buttons.implant.inverter.details")):
                st.code(inverters[implant["inverter"]["name"]], language="json")
        else:
            implant["inverter"]["name"] = col2.text_input(
                T("buttons.implant.inverter.name"), implant["inverter"]["name"]
            )
            implant["inverter"]["model"]["pdc0"] = st.number_input(
                "pdc0 (W)",
                value=float(implant["inverter"]["model"]["pdc0"]),
                min_value=0.0,
            )

        implant["inverter"]["ac_model"] = (
            "cec" if implant["inverter"]["origin"] == "cecinverter" else "pvwatts"
        )
    mount_setting(implant["mount"])
    return implant


def mount_setting(implant_mount):
    mount_opts = [
        "SingleAxisTrackerMount",
        "FixedMount",
        "ValidatedMount",
        "DevelopementMount",
    ]
    mount_index = mount_opts.index(implant_mount["type"])

    with st.expander(f"***{T("buttons.implant.mount.title")}***", icon="⚠️"):
        col1, col2 = st.columns([2, 1])
        with col1:
            implant_mount["type"] = st.selectbox(
                T("buttons.implant.mount.type"), mount_opts, index=mount_index
            )
            if implant_mount["type"] == "FixedMount":
                l, r = st.columns(2)
                value = 30
                if "surface_tilt" in implant_mount["params"]:
                    value = implant_mount["params"]["surface_tilt"]
                tilt = l.number_input("Tilt", value=value)
                implant_mount["params"]["surface_tilt"] = tilt
                value = 270
                if "surface_azimuth" in implant_mount["params"]:
                    value = implant_mount["params"]["surface_azimuth"]
                azimuth = r.number_input("Azimuth", value=value)
                implant_mount["params"]["surface_azimuth"] = azimuth
            else:
                # implant_mount["type"] == "SingleAxisTrackerMount":
                l, c, r, rr = st.columns(4)
                value = 0
                if "axis_tilt" in implant_mount["params"]:
                    value = implant_mount["params"]["axis_tilt"]
                tilt = l.number_input("Tilt", value=value)
                implant_mount["params"]["axis_tilt"] = tilt
                value = 270
                if "axis_azimuth" in implant_mount["params"]:
                    value = implant_mount["params"]["axis_azimuth"]
                azimuth = c.number_input("Azimuth", value=value)
                implant_mount["params"]["axis_azimuth"] = azimuth
                value = 45
                if "max_angle" in implant_mount["params"]:
                    value = implant_mount["params"]["max_angle"]
                max_angle = r.number_input(
                    "Max Angle inclination",
                    value=float(value),
                    min_value=0.0,
                    max_value=90.0,
                )
                implant_mount["params"]["max_angle"] = max_angle
                value = 0
                if "cross_axis_tilt" in implant_mount["params"]:
                    value = implant_mount["params"]["cross_axis_tilt"]
                cross_axis_tilt = rr.number_input(
                    "Surface angle", value=float(value), min_value=0.0, max_value=90.0
                )
                implant_mount["params"]["cross_axis_tilt"] = cross_axis_tilt
                q, _, w, _, _ = st.columns([5, 2, 5, 2, 1])

                value = 0.35
                if "gcr" in implant_mount["params"]:
                    value = implant_mount["params"]["gcr"]
                gcr = q.number_input(
                    "Ground Coverage Ratio", value=value, min_value=0.0, max_value=1.0
                )
                implant_mount["params"]["gcr"] = gcr
                value = True
                if "backtrack" in implant_mount["params"]:
                    value = implant_mount["params"]["backtrack"]
                backtrack = st.toggle("Avoid shadings (backtrack)", value=value)
                implant_mount["params"]["backtrack"] = backtrack

        with col2:
            plots.pv3d(tilt, azimuth)


def render():
    st.title("📈 " + T("title"))
    implants_df = load_all_implants()

    if implants_df.empty:
        st.warning("No valid implant folders found.")
        return

    # Select implant
    ll, rr = st.columns([3, 1])
    with ll.expander(f" 🔎 {T("subtitle.search_implant")}"):
        col1, col2 = st.columns(2)
        selected_site = col1.selectbox(
            f"🌍 {T("subtitle.site")}", sorted(implants_df["site_name"].unique())
        )
        filtered = implants_df[implants_df["site_name"] == selected_site]
        selected_implant = col2.selectbox(
            f"⚙️ {T("subtitle.implant")}", filtered["implant_name"]
        )

    selected_row = filtered[filtered["implant_name"] == selected_implant].iloc[0]
    subfolder = selected_row["subfolder"]

    # Edit and display site and implant
    with st.expander("🛠️ " + T("subtitle.implant_config")):
        site, implant = st.tabs(
            [f"🏢 {T("subtitle.site")}", f"🧰 {T("subtitle.implant")}"]
        )
        with site:
            site = edit_site(subfolder)
        with implant:
            implant = edit_implant(subfolder)

    # col_left, col_sep, col_right = st.columns([2, 0.1, 3])
    #
    # with col_right:
    # st.subheader(f"🧰 {T("subtitle.implant")}")
    # implant = edit_implant(subfolder)
    #
    # with col_left:
    # st.subheader(f"🏢 {T("subtitle.site")}")
    # site = edit_site(subfolder)
    _, col1, col2 = st.columns([5, 2, 2])

    with rr:
        a, b = st.columns(2)
        if a.button(f"{T("buttons.save")}", icon="💾", key="save_changes"):
            keep_mount_params = {}
            if implant["mount"]["type"] == "FixedMount":
                keep_mount_params = {"surface_tilt", "surface_azimuth"}
            else:
                keep_mount_params = {
                    "axis_tilt",
                    "axis_azimuth",
                    "max_angle",
                    "backtrack",
                    "gcr",
                    "cross_axis_tilt",
                }
            implant["mount"]["params"] = {
                k: v
                for k, v in implant["mount"]["params"].items()
                if k in keep_mount_params
            }

            json.dump(site, (subfolder / "site.json").open("w"), indent=4)
            json.dump(implant, (subfolder / "implant.json").open("w"), indent=4)
            sim_file = subfolder / "simulation.csv"
            if sim_file.exists():
                sim_file.unlink()
            # st.success("Changes saved.")

        if b.button(f"{T("buttons.simulate")}", icon="🔥"):
            st.toast("🚀Simulation running ✅")
            Simulate(subfolder)
            st.toast("Simulation completed ✅")

    import streamlit_antd_components as sac

    sac.divider(
        label="Analysis",
        icon=sac.BsIcon("clipboard2-data", 20),
        align="center",
        color="gray",
        variant="dashed",
    )
    # Output chart
    st.subheader("🔋 " + T("subtitle.performance"))
    if (subfolder / "simulation.csv").exists():
        analyser = ImplantAnalyser(subfolder)
        plots.seasonal_plot(analyser.periodic_report(), "implant_performance")
        plots.time_plot(analyser.numeric_dataframe(), page="implant_performance")
    else:
        st.warning("⚠️ Simulation not perfermed")
