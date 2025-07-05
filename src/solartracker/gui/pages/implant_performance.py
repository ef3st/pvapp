import streamlit as st
from pathlib import Path
import json
import pandas as pd
from pvlib.pvsystem import retrieve_sam


def load_all_implants(folder: Path = Path("data/")) -> pd.DataFrame:
    rows = []

    for subfolder in sorted(folder.iterdir()):
        if not subfolder.is_dir():
            continue

        site_path = subfolder / "site.json"
        implant_path = subfolder / "implant.json"

        if not site_path.exists() or not implant_path.exists():
            continue  # ignora cartelle incomplete

        try:
            with site_path.open() as f:
                site = json.load(f)
            with implant_path.open() as f:
                implant = json.load(f)

            row = {
                "site_name": site["name"],
                "implant_name": implant["name"],
                "subfolder": subfolder
            }
            rows.append(row)

        except Exception as e:
            print(f"Errore nella cartella {subfolder.name}: {e}")
            continue

    return pd.DataFrame(rows)

def show_site(subfolder):
    site_path = subfolder / "site.json"
    try:
        with site_path.open() as f:
            site = json.load(f)
        site["name"] = st.text_input("Site name", site["name"])
        site["address"] = st.text_input("Address", site["address"])
        site["city"] = st.text_input("City", site["city"])
        st.text("Coordinates:")
        col1, col2 = st.columns(2)
        with col1:
            site["coordinates"]["lat"] = st.number_input("Latitude", value=site["coordinates"]["lat"])
        with col2:
            site["coordinates"]["lon"] = st.number_input("Longitude", value=site["coordinates"]["lon"])
        site["altitude"] = st.number_input("Altitude (m)", value=site["altitude"])
        site["tz"] = st.text_input("Jat lag", site["tz"])
        return site    
    except Exception as e:
        print(f"Error in folder {subfolder.name}: {e}")
    
def show_implant(subfolder):
    implant_path = subfolder / "implant.json"
    try:
        with implant_path.open() as f:
            implant = json.load(f)
        implant["name"] = st.text_input("Impant name", implant["name"])
        st.text("Module:")
        col1,col2 = st.columns(2)
        with col1:
            opts = ["CECMod","SandiaMod","pvwatts","Custom"]
            index = opts.index(implant["module"]["origin"])
            implant["module"]["origin"] = st.selectbox("Nrigin",options=opts,index=index)
        with col2:       
            if implant["module"]["origin"] in ["CECMod","SandiaMod"]:
                modules = retrieve_sam(implant["module"]["origin"])
                opts = list(modules.columns)
                index = 0
                if implant["module"]["origin"] in opts:
                    index = opts.index(implant["module"]["name"])
                implant["module"]["name"] = st.selectbox("Name", options=opts,index=index)
            elif implant["module"]["origin"] in ["pvwatts","Custom"]:
                implant["module"]["name"] = st.text_input("name", implant["module"]["name"])
                cola, colb = st.columns(2)
                with cola:
                    implant["module"]["model"]["pdc0"] = st.text_input("pdc0 (W)", implant["module"]["model"]["pdc0"])
                with colb:
                    implant["module"]["model"]["gamma_pdc"] = st.text_input("gamma_pdc (%/°C)", implant["module"]["model"]["gamma_pdc"])
        if (implant["module"]["origin"] in ["CECMod","SandiaMod"]) and st.checkbox("📄 Show module description"):
            st.code(modules[implant["module"]["name"]], language="json")
        if implant["module"]["origin"] == "CECMod":
            implant["module"]["dc_module"] = "cec"
        elif implant["module"]["origin"] == "SandiaMod":
            implant["module"]["dc_module"] = "sapm"
        else:
            implant["module"]["dc_module"] = "pvwatts"
                
        
        
        st.text("Inverter:")
        col1,col2 = st.columns(2)
        with col1:
            opts = ["cecinverter","pvwatts","Custom"]
            index = opts.index(implant["inverter"]["origin"])
            implant["inverter"]["origin"] = st.selectbox("Origin",options=opts,index=index)
        with col2:
            if implant["inverter"]["origin"] in ["CECMod"]:
                inverters = retrieve_sam(implant["inverter"]["origin"])
                opts = list(inverters.columns)
                index = 0
                if implant["inverter"]["origin"] in opts:
                    index = opts.index(implant["inverter"]["name"])
                implant["inverter"]["name"] = st.selectbox("Origin", options=opts,index=index)
                
            elif implant["inverter"]["origin"] in ["pvwatts","Custom"]:
                implant["inverter"]["name"] = st.text_input("Name", implant["inverter"]["name"])
                implant["inverter"]["model"]["pdc0"] = st.text_input("pdc0 (W)", implant["inverter"]["model"]["pdc0"])
        
        if (implant["inverter"]["origin"] in ["CECMod"]) and st.checkbox("📄 Show implant description"):
            st.code(inverters[implant["inverter"]["name"]], language="json")
        if implant["inverter"]["origin"] == "cecinverter":
            implant["inverter"]["ac_model"] = "cec"
        else:
            implant["inverter"]["ac_model"] = "pvwatts"
        
        opts = ["SingleAxisTrackerMount", "FixedMount","Custom"]
        index = opts.index(implant["mount"]["type"])
        implant["mount"]["type"] = st.selectbox("origin",options=opts,index=index)
        
        return implant

    except Exception as e:
        st.error(f"❌ Errore nel caricamento del file implant.json in {subfolder.name}: {e}")
        return None
    

def render():
    st.title("📌 IMPLANT")
    implants = load_all_implants()
    
    col1, col2 = st.columns(2)
    with col1:
        selected_site = st.selectbox("🌍 Site name", sorted(implants["site_name"].unique()))
        filtered_df = implants[implants["site_name"] == selected_site]
    with col2:
        selected_implant = st.selectbox("⚙️ Implant name", filtered_df["implant_name"])
        selected_row = filtered_df[filtered_df["implant_name"] == selected_implant].iloc[0]
        subfolder = selected_row["subfolder"]
    

    st.success(f"📁 Implant selected: `{subfolder}`")
    
    st.subheader("🛠️ Implant Data")
    col1, col_sep, col2 = st.columns([2, 0.1, 3])
    with col1:
        st.subheader("🏢 Site data")
        site = show_site(subfolder)
        
    with col_sep:
        st.markdown(
            """
            <div style="height: 100%; border-left: 1px solid #ccc;"></div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.subheader("🧰 Implant setup")
        implant = show_implant(subfolder)
    if st.button("💾 Salva modifiche"):
        with open(subfolder / "site.json", "w") as f:
            json.dump(site, f, indent=4)
        with open(subfolder / "implant.json", "w") as f:
            json.dump(implant, f, indent=4)
        st.success("✅ Modifiche salvate!")
    
    
    st.subheader("🔋 Performance")
    
    
    
    

    col_main, col_right = st.columns([3, 1])

    with col_main:  # Chart space
        st.line_chart([1, 2, 3, 4])

    with col_right:
        st.markdown("### ⚙️ Setup")
        data_opt = st.selectbox("Choose data", ["ac", "dc"])
