import streamlit as st
import json
from pathlib import Path
import pydeck as pdk
from geopy.geocoders import Nominatim
import pandas as pd
from pvlib.pvsystem import retrieve_sam
from simulator.simulator import Simulate
from .plots import pv3d


def load_sites_df(base_path=Path("data/")) -> pd.DataFrame:
    rows = []

    for folder in sorted(base_path.iterdir()):
        if folder.is_dir() and folder.name.isdigit():
            site_path = folder / "site.json"
            if site_path.exists():
                try:
                    with site_path.open() as f:
                        site = json.load(f)
                    row = {
                        "id": int(folder.name),
                        "name": site.get("name"),
                        "address": site.get("address"),
                        "city": site.get("city"),
                        "lat": site.get("coordinates", {}).get("lat"),
                        "lon": site.get("coordinates", {}).get("lon"),
                        "altitude": site.get("altitude"),
                        "tz": site.get("tz"),
                    }
                    rows.append(row)
                except Exception as e:
                    print(f"Errore nel file {folder}/site.json: {e}")
    if not rows:
        rows.append(
            {
                "id": "",
                "name": "",
                "address": "",
                "city": "",
                "lat": 0,
                "lon": 0,
                "altitude": 0,
                "tz": "",
            }
        )
    df = pd.DataFrame(rows).set_index("id").sort_index()
    return df


def save_implant(path=Path("data/")):
    st.session_state.adding_implant = False
    site = st.session_state.new_implant["site"]
    implant = st.session_state.new_implant["implant"]

    existing_ids = [
        int(f.name) for f in path.iterdir() if f.is_dir() and f.name.isdigit()
    ]
    next_id = max(existing_ids) + 1 if existing_ids else 0
    folder = path / str(next_id)

    folder.mkdir(parents=False, exist_ok=False)

    file_path = folder / "site.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(site, f, indent=4)

    file_path = folder / "implant.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(implant, f, indent=4)

    st.session_state.implant_step = 0
    st.session_state.new_implant = {"site": {}, "implant": {}}
    st.session_state.adding_implant = False
    st.success(f"✅ Nuovo impianto salvato in {folder}.")
    st.rerun()


def exit_button():
    if st.button("❌ Annulla", key="exit"):
        st.session_state.implant_step = 0
        st.session_state.new_implant = {"site": {}, "implant": {}}
        st.session_state.adding_implant = False
        st.rerun()


def save_and_simulate(path=Path("data/")):
    st.session_state.adding_implant = False
    site = st.session_state.new_implant["site"]
    implant = st.session_state.new_implant["implant"]

    existing_ids = [
        int(f.name) for f in path.iterdir() if f.is_dir() and f.name.isdigit()
    ]
    next_id = max(existing_ids) + 1 if existing_ids else 0
    folder = path / str(next_id)

    folder.mkdir(parents=False, exist_ok=False)

    file_path = folder / "site.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(site, f, indent=4)

    file_path = folder / "implant.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(implant, f, indent=4)

    st.session_state.implant_step = 0
    st.session_state.new_implant = {"site": {}, "implant": {}}
    st.session_state.adding_implant = False
    st.success(f"✅ Nuovo impianto salvato in {folder}.")
    Simulate(folder)

    st.rerun()


def get_coordinates(address: str):
    geolocator = Nominatim(user_agent="solartracker-app")
    location = geolocator.geocode(address)
    if location:
        return location.latitude, location.longitude
    return None, None


def init_session():
    if "implant_step" not in st.session_state:
        st.session_state.implant_step = 0
    if "new_implant" not in st.session_state:
        st.session_state.new_implant = {"site": {}, "implant": {}}


# --- Step Functions ---
def step_site():

    df = load_sites_df()

    with open("src/solartracker/gui/pages/support/districts.json") as f:
        districts_json = json.load(f)
    districts = list(districts_json.keys())

    new_implant = st.session_state.new_implant
    sites = [""] + df["name"].unique().tolist() + ["Altro"]

    name = st.selectbox("📝 Site Name", sites)

    if name == "Altro":
        name = st.text_input("🚧 New name")
    if name in ["", "Altro"]:
        default_address = ""
        default_city = ""
        default_district = districts.index("RA")
    else:
        default_address = df.loc[df["name"] == name, "address"].unique().tolist()
        if len(default_address) > 0:
            default_address = default_address[0]
        else:
            default_address = ""
        default_city = df.loc[df["name"] == name, "city"].unique().tolist()
        if len(default_city) > 0:
            default_city = default_city[0]
        else:
            default_city = "(RA)"
        default_district = districts.index(default_city[-3:-1])
    address = st.text_input("🪧 Address", value=default_address)
    city_col, district_col = st.columns([3, 1])
    city = city_col.text_input("🏙️ City", value=default_city[:-5])
    district = district_col.selectbox("District", districts, index=default_district)
    error = False
    st.markdown("---")
    col1, col2 = st.columns([1, 2])
    with col1:
        exit_button()
    with col2:
        if st.button("⏩ Next", key="site_next"):
            if name and address and city:
                new_implant["site"].update(
                    {"name": name, "address": address, "city": f"{city} ({district})"}
                )
                st.session_state.implant_step += 1
                st.rerun()
            else:
                error = True
    if error:
        st.error("Complete all fields")


def step_location():
    new_implant = st.session_state.new_implant
    site = new_implant["site"]
    lat, lon = get_coordinates(f"{site['address']}, {site['city']}, Italia")
    st.text("🗺️ Coordinates")
    lat_col, lon_col = st.columns(2)
    lat = lat_col.number_input("Latitude", value=lat or 0.0, format="%.4f")
    lon = lon_col.number_input("Longitude", value=lon or 0.0, format="%.4f")
    col1, col2 = st.columns(2)
    altitude = col1.number_input("🗻 Altitude (m)", value=0, min_value=0)
    tz = col2.text_input("🕐 Time Zone", value="Europe/Rome")

    df = pd.DataFrame([{"lat": lat, "lon": lon}])
    view = pdk.ViewState(latitude=lat, longitude=lon, zoom=12)
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position="[lon, lat]",
        get_color="[255,0,0,160]",
        get_radius=200,
    )
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view))

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        exit_button()
    with col2:
        if st.button("🔙 Back", key="loc_back"):
            st.session_state.implant_step -= 1
            st.rerun()
    with col3:
        if st.button("⏩ Next", key="loc_next"):
            if lat and lon and altitude >= 0 and tz:
                new_implant["site"].update(
                    {
                        "coordinates": {"lat": lat, "lon": lon},
                        "altitude": altitude,
                        "tz": tz,
                    }
                )
                st.session_state.implant_step += 1
                st.rerun()
            else:
                st.error("Complete all fields")


def step_module():
    new_implant = st.session_state.new_implant
    st.markdown("⚡ **Module**")
    origin = st.selectbox("Origin", ["CECMod", "SandiaMod", "pvwatts", "Custom"])
    model = {}
    name = ""
    if origin in ["CECMod", "SandiaMod"]:
        modules = retrieve_sam(origin)
        name = st.selectbox("Model", list(modules.columns))
        st.code(modules[name], language="json")
    else:
        name = st.text_input("Custom Module Name")
        pdc = st.number_input("pdc0 (W)", min_value=0.)
        gamma = st.number_input("γ_pdc (%/C)", min_value=0.)
        model = {"pdc0": pdc, "gamma": gamma}

    navigation_buttons(
        2,
        "module_next",
        new_implant,
        "implant",
        {
            "module": {
                "origin": origin,
                "name": name,
                "model": model,
                "dc_model": {"CECMod": "cec", "SandiaMod": "sapm"}.get(
                    origin, "pvwatts"
                ),
            }
        },
    )


def step_inverter():
    new_implant = st.session_state.new_implant
    st.markdown("🔌 **Inverter**")
    origin = st.selectbox("Origin", ["cecinverter", "pvwatts", "Custom"])
    model = {}
    name = ""
    if origin == "cecinverter":
        inverters = retrieve_sam(origin)
        name = st.selectbox("Model", list(inverters.columns))
        st.code(inverters[name], language="json")
        st.warning("⚠️ THIS INVERTER CANNOT BE SIMULATED⚠️")
    else:
        name = st.text_input("Custom Inverter Name")
        pdc = st.number_input("pdc0 (W)", min_value=0.)
        model = {"pdc0": pdc}

    navigation_buttons(
        3,
        "inv_next",
        new_implant,
        "implant",
        {
            "inverter": {
                "origin": origin,
                "name": name,
                "model": model,
                "ac_model": "cec" if origin == "cecinverter" else "pvwatts",
            }
        },
    )


def step_mount():
    new_implant = st.session_state.new_implant
    st.markdown("⚠️ **Mount**")
    mount = st.selectbox(
        "Select Mount Type",
        ["SingleAxisTrackerMount", "FixedMount", "ValidatedMount", "DevelopementMount"],
    )
    params = {}
    if mount == "FixedMount":
        l, r = st.columns(2)
        tilt = l.number_input("Tilt", value=30)
        params["surface_tilt"] = tilt
        azimuth = r.number_input("Azimuth", value=180)
        params["surface_azimuth"] = azimuth
    else:
        # implant_mount["type"] == "SingleAxisTrackerMount":
        l, c = st.columns(2)
        r, rr = st.columns(2)
        tilt = l.number_input("Tilt", value=30)
        params["axis_tilt"] = tilt
        azimuth = c.number_input("Azimuth", value=180)
        params["axis_azimuth"] = azimuth
        max_angle = r.number_input("Max Angle inclination", value=45., min_value=0., max_value=90.)
        params["max_angle"] = max_angle
        cross_axis_tilt = rr.number_input("Surface angle", value=0., min_value=0., max_value=90.)
        params["cross_axis_tilt"] = cross_axis_tilt

        gcr = st.number_input("Ground Coverage Ratio", value=0.35, min_value=0., max_value=1.)
        params["gcr"] = gcr
        backtrack = st.checkbox("Avoid shadings (backtrack)", value=False)
        params["backtrack"] = backtrack
    pv3d(tilt, azimuth)

    navigation_buttons(
        4,
        "mount_next",
        new_implant,
        "implant",
        {"mount": {"type": mount, "params": {}}},
    )


def navigation_buttons(step_back, next_key, target_dict, section_key, update_dict):
    col1, col2, col3 = st.columns(3)
    with col1:
        exit_button()
    with col2:
        if st.button("🔙 Back", key=f"{next_key}_back"):
            st.session_state.implant_step = step_back - 1
            st.rerun()
    with col3:
        if st.button("⏩ Next", key=next_key):
            target_dict[section_key].update(update_dict)
            st.session_state.implant_step = step_back + 1
            st.rerun()

@st.fragment
def render():
    st.title("➕ New Implant")
    init_session()
    step = st.session_state.implant_step
    if step == 0:
        step_site()
    elif step == 1:
        step_location()
    elif step == 2:
        step_module()
    elif step == 3:
        step_inverter()
    elif step == 4:
        step_mount()
    elif step == 5:
        new_implant = st.session_state.new_implant
        st.markdown("### 🧾 Riepilogo")
        st.markdown("🏢 **Site**")
        st.json(new_implant["site"])
        st.markdown("🧰 **Implant**")
        name = st.text_input("Give a name to this implant", value="New Implant")
        new_implant["implant"]["name"] = name
        st.json(new_implant["implant"])
        col1, col2, col3 = st.columns(3)
        if col1.button("✅ Save Implant"):
            save_implant()
        with col2:
            exit_button()
        if col3.button("🌩️ Save and Simulate"):
            save_and_simulate()
