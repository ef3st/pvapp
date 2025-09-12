# =========================================================
#                          ADD PLANT WIZARD
# =========================================================
"""
Streamlit wizard for adding a new PV plant.

Description
-----------
Guided flow to define:
1) Site metadata (name/address/region/city)
2) Location (coordinates, altitude, timezone)
3) PV module (from SAM DB or custom)
4) Inverter (from SAM DB / PVWatts or custom)
5) Mount type and parameters
6) Save (and optionally run a simulation)

State keys used:
- st.session_state.plant_step: int in [0..5]
- st.session_state.new_plant: {"site": dict, "plant": dict}
- st.session_state.adding_plant: bool

Notes:
- Strings/comments are in English per your guidelines.
- We keep the UI behavior intact while improving typing, sections, and docstrings.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple, Optional

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit_antd_components as sac
import pydeck as pdk
from geopy.geocoders import Nominatim
import geopy.exc as geoExept
from pvlib.pvsystem import retrieve_sam

from backend.simulation import Simulator
from gui.utils.plots import pv3d


# =========================================================
#                           HELPERS
# =========================================================
def _ensure_state() -> None:
    """
    Ensure wizard session-state keys exist.

    Notes:
    - Initializes: plant_step (0), new_plant (site/plant empty), adding_plant (True by page).
    """
    st.session_state.setdefault("plant_step", 0)
    st.session_state.setdefault("new_plant", {"site": {}, "plant": {}})
    st.session_state.setdefault("adding_plant", True)


def _sam_safely(origin: str, name: str) -> Optional[dict]:
    """
    Safely retrieve a SAM record by origin and name.

    Args:
        origin (str): SAM database group (e.g., 'CECMod', 'SandiaInverter', etc.).
        name (str): Record key.

    Returns:
        Optional[dict]: SAM record if found, else None.

    Notes:
    - Origin is case-insensitive; errors are handled silently (returns None).
    """
    try:
        db = retrieve_sam(origin.lower())
        return db[name] if name in db else None
    except Exception:
        return None


# =========================================================
#                        DATA LOADING
# =========================================================
def load_sites_df(base_path: Path = Path("data/")) -> pd.DataFrame:
    """
    Load all `site.json` files from subfolders into a DataFrame.

    Args:
        base_path (Path): Root path containing numeric subfolders with site.json.

    Returns:
        pd.DataFrame: Index 'id', columns name/address/city/lat/lon/altitude/tz.
    """
    rows: list[Dict[str, Any]] = []
    for folder in sorted(base_path.iterdir()):
        if folder.is_dir() and folder.name.isdigit():
            site_path = folder / "site.json"
            if site_path.exists():
                try:
                    with site_path.open() as f:
                        site = json.load(f)
                    rows.append(
                        {
                            "id": int(folder.name),
                            "name": site.get("name"),
                            "address": site.get("address"),
                            "city": site.get("city"),
                            "lat": site.get("coordinates", {}).get("lat"),
                            "lon": site.get("coordinates", {}).get("lon"),
                            "altitude": site.get("altitude"),
                            "tz": site.get("tz"),
                        }
                    )
                except Exception as e:
                    print(f"Error in file {folder}/site.json: {e}")

    if not rows:
        rows.append(
            {
                "id": "",
                "name": "",
                "address": "",
                "city": "",
                "lat": 0.0,
                "lon": 0.0,
                "altitude": 0,
                "tz": "",
            }
        )
    df = pd.DataFrame(rows).set_index("id").sort_index()
    return df


# =========================================================
#                         SAVE ACTIONS
# =========================================================
def save_plant(path: Path = Path("data/")) -> None:
    """
    Persist current `new_plant` to a new numeric folder with site.json/plant.json.

    Args:
        path (Path): Root data folder.

    Raises:
        ValueError: If required sections are missing.

    Notes:
    - Picks the next available numeric folder (max+1 or 0).
    """
    st.session_state.adding_plant = False
    site = st.session_state.new_plant["site"]
    plant = st.session_state.new_plant["plant"]

    if not site or not plant:
        raise ValueError("Site or plant data are missing. Cannot save.")

    existing_ids = [
        int(f.name) for f in path.iterdir() if f.is_dir() and f.name.isdigit()
    ]
    next_id = max(existing_ids) + 1 if existing_ids else 0

    folder = path / str(next_id)
    folder.mkdir(parents=True, exist_ok=True)

    # -------------> Write files <--------
    file_path = folder / "site.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(site, f, indent=4)

    file_path = folder / "plant.json"
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(plant, f, indent=4)

    # Reset wizard state
    st.session_state.plant_step = 0
    st.session_state.new_plant = {"site": {}, "plant": {}}
    st.session_state.adding_plant = False
    st.success(f"✅ New plant saved to {folder}.")
    st.rerun()


def exit_button() -> None:
    """
    Render a small exit button that resets wizard state.
    """
    if st.button("❌ Exit", key="exit"):
        st.session_state.plant_step = 0
        st.session_state.new_plant = {"site": {}, "plant": {}}
        st.session_state.adding_plant = False
        st.rerun()


def save_and_simulate(path: Path = Path("data/")) -> None:
    """
    Save the plant and immediately run a simulation.

    Args:
        path (Path): Root data folder.
    """
    st.session_state.adding_plant = False
    site = st.session_state.new_plant["site"]
    plant = st.session_state.new_plant["plant"]

    if not site or not plant:
        st.error("Site or plant data are missing. Cannot save & simulate.")
        return

    existing_ids = [
        int(f.name) for f in path.iterdir() if f.is_dir() and f.name.isdigit()
    ]
    next_id = max(existing_ids) + 1 if existing_ids else 0

    folder = path / str(next_id)
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "site.json").write_text(json.dumps(site, indent=4), encoding="utf-8")
    (folder / "plant.json").write_text(json.dumps(plant, indent=4), encoding="utf-8")

    st.success(f"🌩️ Saved in {folder}. Running simulation…")
    try:
        Simulator(folder).run()
        st.success("✅ Simulation completed.")
    except Exception as e:
        st.warning(f"Simulation failed: {e}")

    st.session_state.plant_step = 0
    st.session_state.new_plant = {"site": {}, "plant": {}}
    st.session_state.adding_plant = False
    st.rerun()


# =========================================================
#                          STEPS: SITE
# =========================================================
def step_site() -> None:
    """
    Step 0 — Site metadata (name, address, city, district).

    Notes:
        - Districts loaded from `districts.json` (region/province codes).
        - If 'Other' is chosen as site name, a free text input is shown.
    """
    df = load_sites_df()

    with open(
        "src/pvapp/gui/pages/plants/add_plant/districts.json", encoding="utf-8"
    ) as f:
        districts_json = json.load(f)
    districts = list(districts_json.keys())

    new_plant = st.session_state.new_plant
    sites = [""] + df["name"].unique().tolist() + ["Other"]

    name = st.selectbox("📝 Site Name", sites)

    # ------ Default values from existing site, or blank ------
    if name == "Other":
        name = st.text_input("🚧 New Name")

    if name in ["", "Other"]:
        default_address = ""
        default_city = ""
        default_district_index = districts.index("RA") if "RA" in districts else 0
    else:
        default_address = df.loc[df["name"] == name, "address"].dropna().unique()
        default_address = default_address[0] if len(default_address) > 0 else ""
        default_city = df.loc[df["name"] == name, "city"].dropna().unique()
        default_city = default_city[0] if len(default_city) > 0 else ""
        # Try to infer district initials from city, like "(RA)"
        default_district_index = 0
        if default_city.startswith("(") and ")" in default_city:
            initials = default_city[1:3]
            if initials in districts:
                default_district_index = districts.index(initials)

    col1, col2 = st.columns(2)
    address = col1.text_input("🏠 Address", value=default_address)
    city = col2.text_input("🏙️ City (e.g., 'Ravenna' or '(RA)')", value=default_city)
    district = st.selectbox(
        "🗺️ District/Province", districts, index=default_district_index
    )

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        exit_button()
    with c2:
        if st.button("⏩ Next", key="site_next"):
            if name and address and city:
                new_plant["site"] = {
                    "name": name,
                    "address": address,
                    "city": city,
                    "district": district,
                }
                st.session_state.plant_step += 1
                st.rerun()
            else:
                st.warning("Please provide name, address, and city.")


# =========================================================
#                       STEPS: LOCATION
# =========================================================
def _geocode_address(
    address: str, city: str, district: str
) -> Tuple[Optional[float], Optional[float]]:
    """
    Geocode address using Nominatim and return (lat, lon).

    Args:
        address (str): Street and number.
        city (str): City name.
        district (str): District/Province code.

    Returns:
        tuple[Optional[float], Optional[float]]: (lat, lon)
    """
    locator = Nominatim(user_agent="pv_plant_app")
    try:
        location = locator.geocode(f"{address}, {city}, {district}, Italy")
        if location:
            return float(location.latitude), float(location.longitude)
    except geoExept.GeocoderTimedOut:
        st.warning("Geocoding timed out. Please try again.")
    except Exception as e:
        st.warning(f"Geocoding error: {e}")
    return None, None


def step_location() -> None:
    """
    Step 1 — Location: coordinates, altitude, timezone and map preview.
    """
    new_plant = st.session_state.new_plant
    site = new_plant.get("site", {})

    if not site:
        st.info("Please complete the Site step first.")
        return

    st.subheader("📍 Location")

    left, right = st.columns(2)
    with left:
        if st.button("📍 Geocode address", key="geocode"):
            lat, lon = _geocode_address(site["address"], site["city"], site["district"])
            if lat is not None and lon is not None:
                st.session_state["__latlon"] = (lat, lon)
            else:
                st.session_state["__latlon"] = None

    latlon = st.session_state.get("__latlon")
    default_lat = latlon[0] if latlon else 44.417
    default_lon = latlon[1] if latlon else 12.200

    col1, col2 = st.columns(2)
    lat = col1.number_input("Latitude", value=float(default_lat))
    lon = col2.number_input("Longitude", value=float(default_lon))
    col3, col4 = st.columns(2)
    altitude = col3.number_input("Altitude (m a.s.l.)", min_value=0, value=0)
    tz = col4.text_input("🕐 Time Zone", value="Europe/Rome")

    # Map preview
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
            st.session_state.plant_step -= 1
            st.rerun()
    with col3:
        if st.button("⏩ Next", key="loc_next"):
            if lat and lon and altitude >= 0 and tz:
                new_plant["site"].update(
                    {
                        "coordinates": {"lat": lat, "lon": lon},
                        "altitude": altitude,
                        "tz": tz,
                    }
                )
                st.session_state.plant_step += 1
                st.rerun()
            else:
                st.warning("Please set coordinates, altitude, and timezone.")


# =========================================================
#                         STEPS: MODULE
# =========================================================
def _sam_list(origin: str) -> list[str]:
    """
    List SAM keys for a given origin (safe).

    Args:
        origin (str): e.g., 'CECMod' or 'SandiaMod'.

    Returns:
        list[str]: Sorted keys.
    """
    try:
        db = retrieve_sam(origin.lower())
        return sorted(list(db.keys()))
    except Exception:
        return []


def step_module() -> None:
    """
    Step 2 — Select a PV module (SAM DB or custom).
    """
    new_plant = st.session_state.new_plant
    st.subheader("🧰 PV Module")

    origin = st.selectbox(
        "Database",
        options=["CECMod", "SandiaMod", "Custom"],
        index=0,
    )

    model = {}
    name = ""
    if origin == "Custom":
        st.info("Provide custom module parameters (dictionary).")
        name = st.text_input("Model Name", value="CustomModule")
        # ? Minimal visual placeholder
        st.warning(
            "Custom editor is minimal here. Ensure parameters match pvlib schema."
        )
        model = {
            "alpha_sc": 0.001,
            "a_ref": 1.5,
            "I_L_ref": 5.0,
            "I_o_ref": 1e-9,
            "R_sh_ref": 200.0,
            "R_s": 0.5,
            "Adjust": 8.0,
            "gamma_r": -0.003,
            "N_s": 60,
        }
        st.json(model)
    else:
        keys = _sam_list(origin)
        name = st.selectbox("Model", options=[""] + keys)
        if name:
            model = _sam_safely(origin, name) or {}
            if model:
                pv3d.module_card(model)

    if st.button("✅ Confirm Module"):
        if origin == "Custom" and not model:
            st.warning("Please provide a valid custom module model.")
        elif origin != "Custom" and not name:
            st.warning("Please pick a module from the database.")
        else:
            new_plant["plant"].setdefault("module", {})
            new_plant["plant"]["module"] = {
                "origin": origin,
                "name": name,
                "model": model,
                "dc_model": "cec",  # default
            }
            st.session_state.plant_step += 1
            st.rerun()

    st.markdown("---")
    exit_button()
    if st.button("🔙 Back", key="module_back"):
        st.session_state.plant_step -= 1
        st.rerun()


# =========================================================
#                         STEPS: INVERTER
# =========================================================
def step_inverter() -> None:
    """
    Step 3 — Select an inverter (SAM DB, PVWatts, or custom).
    """
    new_plant = st.session_state.new_plant
    st.subheader("⚡ Inverter")

    origin = st.selectbox(
        "Database",
        options=["CECInverter", "pvwatts", "Custom"],
        index=1,
    )

    model: dict[str, Any] = {}
    name = ""
    if origin == "Custom":
        st.info("Provide custom inverter parameters (dictionary).")
        name = st.text_input("Model Name", value="CustomInverter")
        model = {"Paco": 5000, "Pdco": 5200, "Vdco": 400, "C0": -1.1, "C1": 0.1}
        st.json(model)
    elif origin == "pvwatts":
        st.info("PVWatts inverter (no database lookup needed).")
        name = "pvwatts"
        model = {"eta_inv_nom": 0.96, "eta_inv_ref": 0.9637}
        st.json(model)
    else:
        keys = _sam_list("CECInverter")
        name = st.selectbox("Model", options=[""] + keys)
        if name:
            model = _sam_safely("CECInverter", name) or {}
            if model:
                pv3d.inverter_card(model)

    if st.button("✅ Confirm Inverter"):
        if origin == "Custom" and not model:
            st.warning("Please provide a valid custom inverter model.")
        elif origin == "CECInverter" and not name:
            st.warning("Please pick an inverter from the database.")
        else:
            new_plant["plant"].setdefault("inverter", {})
            new_plant["plant"]["inverter"] = {
                "origin": origin.lower() if origin != "CECInverter" else "cecinverter",
                "name": name,
                "model": model,
                "ac_model": "cec" if origin == "CECInverter" else "pvwatts",
            }
            st.session_state.plant_step += 1
            st.rerun()

    st.markdown("---")
    exit_button()
    if st.button("🔙 Back", key="inv_back"):
        st.session_state.plant_step -= 1
        st.rerun()


# =========================================================
#                         STEPS: MOUNT
# =========================================================
def step_mount() -> None:
    """
    Step 4 — Select mount type and parameters.
    """
    new_plant = st.session_state.new_plant
    st.subheader("⚠️ Mount")

    mount = st.selectbox(
        "Select Mount Type",
        ["SingleAxisTrackerMount", "FixedMount", "ValidatedMount", "DevelopementMount"],
    )
    params: dict[str, Any] = {}

    if mount == "FixedMount":
        l, r = st.columns(2)
        params["surface_tilt"] = l.number_input("Tilt (deg)", value=30)
        params["surface_azimuth"] = r.number_input(
            "Azimuth (deg, 180=South)", value=180
        )
    elif mount == "SingleAxisTrackerMount":
        l, c = st.columns(2)
        r, rr = st.columns(2)
        params["axis_tilt"] = l.number_input("Axis Tilt (deg)", value=30)
        params["axis_azimuth"] = c.number_input("Axis Azimuth (deg)", value=180)
        params["max_angle"] = r.number_input("Max Angle (deg)", value=60)
        params["gcr"] = rr.number_input(
            "Ground Coverage Ratio", min_value=0.1, max_value=0.9, value=0.35
        )
    elif mount == "ValidatedMount":
        st.info("Validated custom mount parameters")
        params["tilt"] = st.number_input("Tilt (deg)", value=30)
        params["azimuth"] = st.number_input("Azimuth (deg, 180=South)", value=180)
    elif mount == "DevelopementMount":
        st.info("Development custom mount parameters")
        params["tilt"] = st.number_input("Tilt (deg)", value=30)
        params["azimuth"] = st.number_input("Azimuth (deg, 180=South)", value=180)

    # Preview card if needed (placeholder)
    with st.expander("Preview parameters"):
        st.json({"type": mount, "params": params})

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        exit_button()
    with col2:
        if st.button("🔙 Back", key="mount_back"):
            st.session_state.plant_step -= 1
            st.rerun()
    with col3:
        if st.button("⏩ Next", key="mount_next"):
            new_plant["plant"]["mount"] = {"type": mount, "params": params}
            st.session_state.plant_step += 1
            st.rerun()


# =========================================================
#                        STEP: SAVE & REVIEW
# =========================================================
def step_review_and_save() -> None:
    """
    Step 5 — Review JSON payloads and save (or save & simulate).
    """
    new_plant = st.session_state.new_plant
    st.markdown("### 🧾 Recap")
    st.markdown("🏢 **Site**")
    st.json(new_plant["site"])
    st.markdown("🧰 **Plant**")

    name = st.text_input(
        "Give a name to this plant", value=new_plant["plant"].get("name", "New Plant")
    )
    new_plant["plant"]["name"] = name
    st.json(new_plant["plant"])

    col1, col2, col3 = st.columns(3)
    if col1.button("✅ Save Plant"):
        save_plant()
    with col2:
        exit_button()
    if col3.button("🌩️ Save and Simulate"):
        save_and_simulate()


# =========================================================
#                           SIDEBAR STEPS
# =========================================================
def _steps_sidebar() -> None:
    """
    Render vertical steps indicator in the sidebar.
    """
    titles = ["Site", "Location", "Module", "Inverter", "Mount", "Save"]
    subtitles = [
        "Site metadata",
        "Coordinates / altitude / timezone",
        "Choose module",
        "Choose inverter",
        "Choose mount",
        "Review & persist",
    ]

    # disabled/active icons per step
    step = st.session_state.plant_step
    ok = sac.BsIcon("check-circle", color="green")
    pending = sac.BsIcon("circle", color="gray")
    current = sac.BsIcon("arrow-right-circle", color="blue")

    disableds = []
    for i in range(6):
        if i < step:
            disableds.append((False, ok))
        elif i == step:
            disableds.append((False, current))
        else:
            disableds.append((True, pending))

    sac.steps(
        items=[
            sac.StepsItem(
                title=titles[0],
                disabled=disableds[0][0],
                icon=disableds[0][1],
                description=subtitles[0],
            ),
            sac.StepsItem(
                title=titles[1],
                disabled=disableds[1][0],
                icon=disableds[1][1],
                description=subtitles[1],
            ),
            sac.StepsItem(
                title=titles[2],
                disabled=disableds[2][0],
                icon=disableds[2][1],
                description=subtitles[2],
            ),
            sac.StepsItem(
                title=titles[3],
                disabled=disableds[3][0],
                icon=disableds[3][1],
                description=subtitles[3],
            ),
            sac.StepsItem(
                title=titles[4],
                disabled=disableds[4][0],
                icon=disableds[4][1],
                description=subtitles[4],
            ),
            sac.StepsItem(
                title=titles[5],
                disabled=disableds[5][0],
                icon=disableds[5][1],
                description=subtitles[5],
            ),
        ],
        placement="vertical",
        index=st.session_state.plant_step,
        dot=False,
        direction="horizontal",
    )


# =========================================================
#                         MAIN ENTRYPOINT
# =========================================================
def render() -> None:
    """
    Render the Add Plant wizard page.

    Notes:
    - This function assumes `st.session_state.adding_plant` toggled by the parent page.
    """
    _ensure_state()

    with st.sidebar:
        _steps_sidebar()

    step = st.session_state.plant_step
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
        step_review_and_save()
    else:
        st.session_state.plant_step = 0
        st.rerun()
