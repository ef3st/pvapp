#! DEPRECATED
import streamlit as st
from pathlib import Path
import json
import pandas as pd
from pvlib.pvsystem import retrieve_sam
from simulation.simulator import Simulator
from analysis.plantanalyser import PlantAnalyser
import pydeck as pdk
from ...utils.plots import plots
from ...utils.translation.traslator import translate
from streamlit_custom_notification_box import custom_notification_box


def T(key: str) -> str | list:
    return translate(f"plant_performance.{key}")


def load_all_plants(folder: Path = Path("data/")) -> pd.DataFrame:
    data = []
    for subfolder in sorted(folder.iterdir()):
        if subfolder.is_dir():
            site_file = subfolder / "site.json"
            plant_file = subfolder / "plant.json"
            if site_file.exists() and plant_file.exists():
                try:
                    site = json.load(site_file.open())
                    plant = json.load(plant_file.open())
                    data.append(
                        {
                            "site_name": site.get("name", "Unknown"),
                            "plant_name": plant.get("name", "Unnamed"),
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
def edit_plant(subfolder: Path) -> dict:
    plant_file = subfolder / "plant.json"
    plant = json.load(plant_file.open())

    plant["name"] = st.text_input(T("buttons.plant.name"), plant["name"])

    # Module configuration
    with st.expander(f"***{T("buttons.plant.module.title")}***", icon="⚡"):
        col1, col2 = st.columns(2)
        module_origins = ["CECMod", "SandiaMod", "pvwatts", "Custom"]
        origin_index = module_origins.index(plant["module"]["origin"])
        plant["module"]["origin"] = col1.selectbox(
            T("buttons.plant.module.origin"), module_origins, index=origin_index
        )

        if plant["module"]["origin"] in ["CECMod", "SandiaMod"]:
            modules = retrieve_sam(plant["module"]["origin"])
            module_names = list(modules.columns)
            module_index = 0
            if plant["module"]["name"] in module_names:
                module_index = module_names.index(plant["module"]["name"])
            plant["module"]["name"] = col2.selectbox(
                T("buttons.plant.module.model"), module_names, index=module_index
            )

            if st.checkbox(T("buttons.plant.module.details")):
                st.code(modules[plant["module"]["name"]], language="json")

        else:
            plant["module"]["name"] = col2.text_input(
                T("buttons.plant.module.name"), plant["module"]["name"]
            )
            sub1, sub2 = st.columns(2)
            plant["module"]["model"]["pdc0"] = sub1.number_input(
                "pdc0 (W)",
                value=float(plant["module"]["model"]["pdc0"]),
                min_value=0.0,
            )
            plant["module"]["model"]["gamma_pdc"] = sub2.number_input(
                "γ_pdc (%/C)",
                value=float(plant["module"]["model"]["gamma_pdc"]),
                min_value=0.0,
            )

        plant["module"]["dc_module"] = {"CECMod": "cec", "SandiaMod": "sapm"}.get(
            plant["module"]["origin"], "pvwatts"
        )

    # Inverter configuration
    with st.expander(f"***{T("buttons.plant.inverter.title")}***", icon="🔌"):
        col1, col2 = st.columns(2)
        inverter_origins = ["cecinverter", "pvwatts", "Custom"]
        inv_index = inverter_origins.index(plant["inverter"]["origin"])
        plant["inverter"]["origin"] = col1.selectbox(
            T("buttons.plant.inverter.origin"), inverter_origins, index=inv_index
        )

        if plant["inverter"]["origin"] == "cecinverter":
            inverters = retrieve_sam("cecinverter")
            inv_names = list(inverters.columns)
            inv_name_index = 0
            if plant["inverter"]["name"] in inv_names:
                inv_name_index = inv_names.index(plant["inverter"]["name"])
            plant["inverter"]["name"] = col2.selectbox(
                T("buttons.plant.inverter.model"), inv_names, index=inv_name_index
            )

            if st.checkbox(T("buttons.plant.inverter.details")):
                st.code(inverters[plant["inverter"]["name"]], language="json")
        else:
            plant["inverter"]["name"] = col2.text_input(
                T("buttons.plant.inverter.name"), plant["inverter"]["name"]
            )
            plant["inverter"]["model"]["pdc0"] = st.number_input(
                "pdc0 (W)",
                value=float(plant["inverter"]["model"]["pdc0"]),
                min_value=0.0,
            )

        plant["inverter"]["ac_model"] = (
            "cec" if plant["inverter"]["origin"] == "cecinverter" else "pvwatts"
        )
    mount_setting(plant["mount"])
    return plant


def mount_setting(plant_mount):
    mount_opts = [
        "SingleAxisTrackerMount",
        "FixedMount",
        "ValidatedMount",
        "DevelopementMount",
    ]
    mount_index = mount_opts.index(plant_mount["type"])

    with st.expander(f"***{T("buttons.plant.mount.title")}***", icon="⚠️"):
        col1, col2 = st.columns([2, 1])
        with col1:
            plant_mount["type"] = st.selectbox(
                T("buttons.plant.mount.type"), mount_opts, index=mount_index
            )
            if plant_mount["type"] == "FixedMount":
                l, r = st.columns(2)
                value = 30
                if "surface_tilt" in plant_mount["params"]:
                    value = plant_mount["params"]["surface_tilt"]
                tilt = l.number_input("Tilt", value=value)
                plant_mount["params"]["surface_tilt"] = tilt
                value = 270
                if "surface_azimuth" in plant_mount["params"]:
                    value = plant_mount["params"]["surface_azimuth"]
                azimuth = r.number_input("Azimuth", value=value)
                plant_mount["params"]["surface_azimuth"] = azimuth
            else:
                # plant_mount["type"] == "SingleAxisTrackerMount":
                l, c, r, rr = st.columns(4)
                value = 0
                if "axis_tilt" in plant_mount["params"]:
                    value = plant_mount["params"]["axis_tilt"]
                tilt = l.number_input("Tilt", value=value)
                plant_mount["params"]["axis_tilt"] = tilt
                value = 270
                if "axis_azimuth" in plant_mount["params"]:
                    value = plant_mount["params"]["axis_azimuth"]
                azimuth = c.number_input("Azimuth", value=value)
                plant_mount["params"]["axis_azimuth"] = azimuth
                value = 45
                if "max_angle" in plant_mount["params"]:
                    value = plant_mount["params"]["max_angle"]
                max_angle = r.number_input(
                    "Max Angle inclination",
                    value=float(value),
                    min_value=0.0,
                    max_value=90.0,
                )
                plant_mount["params"]["max_angle"] = max_angle
                value = 0
                if "cross_axis_tilt" in plant_mount["params"]:
                    value = plant_mount["params"]["cross_axis_tilt"]
                cross_axis_tilt = rr.number_input(
                    "Surface angle", value=float(value), min_value=0.0, max_value=90.0
                )
                plant_mount["params"]["cross_axis_tilt"] = cross_axis_tilt
                q, _, w, _, _ = st.columns([5, 2, 5, 2, 1])

                value = 0.35
                if "gcr" in plant_mount["params"]:
                    value = plant_mount["params"]["gcr"]
                gcr = q.number_input(
                    "Ground Coverage Ratio", value=value, min_value=0.0, max_value=1.0
                )
                plant_mount["params"]["gcr"] = gcr
                value = True
                if "backtrack" in plant_mount["params"]:
                    value = plant_mount["params"]["backtrack"]
                backtrack = st.toggle("Avoid shadings (backtrack)", value=value)
                plant_mount["params"]["backtrack"] = backtrack

        with col2:
            plots.pv3d(tilt, azimuth)


def render():
    st.title("📈 " + T("title"))
    plants_df = load_all_plants()

    if plants_df.empty:
        st.warning("No valid plant folders found.")
        return

    # Select plant
    ll, rr = st.columns([3, 1])
    with ll.expander(f" 🔎 {T("subtitle.search_plant")}"):
        col1, col2 = st.columns(2)
        selected_site = col1.selectbox(
            f"🌍 {T("subtitle.site")}", sorted(plants_df["site_name"].unique())
        )
        filtered = plants_df[plants_df["site_name"] == selected_site]
        selected_plant = col2.selectbox(
            f"⚙️ {T("subtitle.plant")}", filtered["plant_name"]
        )

    selected_row = filtered[filtered["plant_name"] == selected_plant].iloc[0]
    subfolder = selected_row["subfolder"]

    # Edit and display site and plant
    with st.expander("🛠️ " + T("subtitle.plant_config")):
        site, plant = st.tabs([f"🏢 {T("subtitle.site")}", f"🧰 {T("subtitle.plant")}"])
        with site:
            site = edit_site(subfolder)
        with plant:
            plant = edit_plant(subfolder)

    # col_left, col_sep, col_right = st.columns([2, 0.1, 3])
    #
    # with col_right:
    # st.subheader(f"🧰 {T("subtitle.plant")}")
    # plant = edit_plant(subfolder)
    #
    # with col_left:
    # st.subheader(f"🏢 {T("subtitle.site")}")
    # site = edit_site(subfolder)
    _, col1, col2 = st.columns([5, 2, 2])

    with rr:
        a, b = st.columns(2)
        if a.button(f"{T("buttons.save")}", icon="💾", key="save_changes"):
            keep_mount_params = {}
            if plant["mount"]["type"] == "FixedMount":
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
            plant["mount"]["params"] = {
                k: v
                for k, v in plant["mount"]["params"].items()
                if k in keep_mount_params
            }

            json.dump(site, (subfolder / "site.json").open("w"), indent=4)
            json.dump(plant, (subfolder / "plant.json").open("w"), indent=4)
            sim_file = subfolder / "simulation.csv"
            if sim_file.exists():
                sim_file.unlink()
            # st.success("Changes saved.")

        if b.button(f"{T("buttons.simulate")}", icon="🔥"):
            st.toast("🚀Simulation running ✅")
            Simulator(subfolder).run()
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
        analyser = PlantAnalyser(subfolder)
        plots.seasonal_plot(analyser.periodic_report(), "plant_performance")
        plots.time_plot(analyser.numeric_dataframe(), page="plant_performance")
    else:
        st.warning("⚠️ Simulation not perfermed")
