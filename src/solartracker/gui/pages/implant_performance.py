import streamlit as st
from pathlib import Path
import json
import pandas as pd
from pvlib.pvsystem import retrieve_sam
from simulator.simulator import Simulate


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
                    data.append({
                        "site_name": site.get("name", "Unknown"),
                        "implant_name": implant.get("name", "Unnamed"),
                        "subfolder": subfolder,
                    })
                except Exception as e:
                    print(f"Error reading {subfolder.name}: {e}")
    return pd.DataFrame(data)


def edit_site(subfolder: Path) -> dict:
    site_file = subfolder / "site.json"
    site = json.load(site_file.open())

    site["name"] = st.text_input("Site name", site["name"])
    site["address"] = st.text_input("Address", site["address"])
    site["city"] = st.text_input("City", site["city"])

    st.text("Coordinates:")
    col1, col2 = st.columns(2)
    site["coordinates"]["lat"] = col1.number_input("Latitude", value=site["coordinates"]["lat"])
    site["coordinates"]["lon"] = col2.number_input("Longitude", value=site["coordinates"]["lon"])

    site["altitude"] = st.number_input("Altitude (m)", value=site["altitude"])
    site["tz"] = st.text_input("Timezone", site["tz"])

    return site


def edit_implant(subfolder: Path) -> dict:
    implant_file = subfolder / "implant.json"
    implant = json.load(implant_file.open())

    implant["name"] = st.text_input("Implant name", implant["name"])

    # Module configuration
    st.text("Module:")
    col1, col2 = st.columns(2)
    module_origins = ["CECMod", "SandiaMod", "pvwatts", "Custom"]
    origin_index = module_origins.index(implant["module"]["origin"])
    implant["module"]["origin"] = col1.selectbox("Origin", module_origins, index=origin_index)

    if implant["module"]["origin"] in ["CECMod", "SandiaMod"]:
        modules = retrieve_sam(implant["module"]["origin"])
        module_names = list(modules.columns)
        module_index = module_names.index(implant["module"]["name"])
        implant["module"]["name"] = col2.selectbox("Model", module_names, index=module_index)

        if st.checkbox("Show module parameters"):
            st.code(modules[implant["module"]["name"]], language="json")

    else:
        implant["module"]["name"] = col2.text_input("Name", implant["module"]["name"])
        sub1, sub2 = st.columns(2)
        implant["module"]["model"]["pdc0"] = sub1.number_input("pdc0 (W)", value = implant["module"]["model"]["pdc0"])
        implant["module"]["model"]["gamma_pdc"] = sub2.number_input("gamma_pdc (%/C)", value=implant["module"]["model"]["gamma_pdc"])

    implant["module"]["dc_module"] = {
        "CECMod": "cec",
        "SandiaMod": "sapm"
    }.get(implant["module"]["origin"], "pvwatts")

    # Inverter configuration
    st.text("Inverter:")
    col1, col2 = st.columns(2)
    inverter_origins = ["cecinverter", "pvwatts", "Custom"]
    inv_index = inverter_origins.index(implant["inverter"]["origin"])
    implant["inverter"]["origin"] = col1.selectbox("Origin", inverter_origins, index=inv_index)

    if implant["inverter"]["origin"] == "cecinverter":
        inverters = retrieve_sam("cecinverter")
        inv_names = list(inverters.columns)
        inv_name_index = inv_names.index(implant["inverter"]["name"])
        implant["inverter"]["name"] = col2.selectbox("Model", inv_names, index=inv_name_index)

        if st.checkbox("Show inverter parameters"):
            st.code(inverters[implant["inverter"]["name"]], language="json")
    else:
        implant["inverter"]["name"] = col2.text_input("Name", implant["inverter"]["name"])
        implant["inverter"]["model"]["pdc0"] = st.number_input("pdc0 (W)", value = implant["inverter"]["model"]["pdc0"])

    implant["inverter"]["ac_model"] = "cec" if implant["inverter"]["origin"] == "cecinverter" else "pvwatts"

    # Mount configuration
    mount_opts = ["SingleAxisTrackerMount", "FixedMount", "Custom"]
    mount_index = mount_opts.index(implant["mount"]["type"])
    implant["mount"]["type"] = st.selectbox("Mount type", mount_opts, index=mount_index)

    return implant


def render():
    st.title("📌 PV Implant Configuration")
    implants_df = load_all_implants()

    if implants_df.empty:
        st.warning("No valid implant folders found.")
        return

    # Select implant
    col1, col2 = st.columns(2)
    selected_site = col1.selectbox("🌍 Site", sorted(implants_df["site_name"].unique()))
    filtered = implants_df[implants_df["site_name"] == selected_site]
    selected_implant = col2.selectbox("⚙️ Implant", filtered["implant_name"])

    selected_row = filtered[filtered["implant_name"] == selected_implant].iloc[0]
    subfolder = selected_row["subfolder"]

    st.success(f"Selected folder: `{subfolder}`")

    # Edit and display site and implant
    st.subheader("🛠️ Implant Configuration")
    col_left, col_sep, col_right = st.columns([2, 0.1, 3])

    with col_left:
        st.subheader("🏢 Site")
        site = edit_site(subfolder)

    with col_sep:
        st.markdown("<div style='height:100%;border-left:1px solid #ccc;'></div>", unsafe_allow_html=True)

    with col_right:
        st.subheader("🧰 Implant")
        implant = edit_implant(subfolder)

    # Save or simulate
    st.markdown("---")
    spacer, col1, col2 = st.columns([6, 1, 1])
    if col1.button("💾 Save"):
        json.dump(site, (subfolder / "site.json").open("w"), indent=4)
        json.dump(implant, (subfolder / "implant.json").open("w"), indent=4)
        st.success("Changes saved.")

    if col2.button("⚡ Simulate"):
        Simulate(subfolder)

    # Output chart
    st.subheader("🔋 Results")
    chart_col, setup_col = st.columns([4, 1])
    with chart_col:
        st.line_chart([1, 2, 3, 4])  # placeholder
    with setup_col:
        st.markdown("### Output type")
        st.selectbox("Choose data", ["ac", "dc"])
