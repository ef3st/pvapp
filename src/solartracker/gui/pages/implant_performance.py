import streamlit as st
from pathlib import Path
import json
import pandas as pd
from pvlib.pvsystem import retrieve_sam
from simulator.simulator import Simulate
from analysis.implantanalyser import ImplantAnalyser
import plotly.express as px

def translate(key: str) -> str | list:
    keys = key.split(".")
    result = st.session_state.get("T", {})
    for k in keys:
        if isinstance(result, dict) and k in result:
            result = result[k]
        else:
            return key  # fallback se manca qualcosa
    return result


def T(key: str) -> str | list:
    return translate(f"implants_performance.{key}")




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


def edit_site(subfolder: Path) -> dict:
    site_file = subfolder / "site.json"
    site = json.load(site_file.open())

    site["name"] = st.text_input(T("buttons.site.name"), site["name"])
    site["address"] = st.text_input(T("buttons.site.address"), site["address"])
    site["city"] = st.text_input(T("buttons.site.city"), site["city"])

    st.markdown(f"🗺️ ***{T("buttons.site.coordinates")}***")
    col1, col2 = st.columns(2)
    site["coordinates"]["lat"] = col1.number_input(
        T("buttons.site.lat"), value=site["coordinates"]["lat"],
        format="%.4f"
    )
    site["coordinates"]["lon"] = col2.number_input(
        T("buttons.site.lon"), value=site["coordinates"]["lon"],
        format="%.4f"
    )

    site["altitude"] = st.number_input(f"🗻 {T("buttons.site.altitude")} (m)", value=site["altitude"])
    site["tz"] = st.text_input(f"🕐 {T("buttons.site.timezone")}", site["tz"])

    return site


def edit_implant(subfolder: Path) -> dict:
    implant_file = subfolder / "implant.json"
    implant = json.load(implant_file.open())

    implant["name"] = st.text_input(T("buttons.implant.name"), implant["name"])

    # Module configuration
    st.markdown(f"⚡ ***{T("buttons.implant.module.title")}***")
    col1, col2 = st.columns(2)
    module_origins = ["CECMod", "SandiaMod", "pvwatts", "Custom"]
    origin_index = module_origins.index(implant["module"]["origin"])
    implant["module"]["origin"] = col1.selectbox(
        T("buttons.implant.module.origin"), module_origins, index=origin_index
    )

    if implant["module"]["origin"] in ["CECMod", "SandiaMod"]:
        modules = retrieve_sam(implant["module"]["origin"])
        module_names = list(modules.columns)
        module_index = module_names.index(implant["module"]["name"])
        implant["module"]["name"] = col2.selectbox(
            T("buttons.implant.module.model"), module_names, index=module_index
        )

        if st.checkbox(T("buttons.implant.module.details")):
            st.code(modules[implant["module"]["name"]], language="json")

    else:
        implant["module"]["name"] = col2.text_input(T("buttons.implant.module.name"), implant["module"]["name"])
        sub1, sub2 = st.columns(2)
        implant["module"]["model"]["pdc0"] = sub1.number_input(
            "pdc0 (W)", value=implant["module"]["model"]["pdc0"]
        )
        implant["module"]["model"]["gamma_pdc"] = sub2.number_input(
            "γ_pdc (%/C)", value=implant["module"]["model"]["gamma_pdc"]
        )

    implant["module"]["dc_module"] = {"CECMod": "cec", "SandiaMod": "sapm"}.get(
        implant["module"]["origin"], "pvwatts"
    )

    # Inverter configuration
    st.markdown(f"🔌 ***{T("buttons.implant.inverter.title")}***")
    col1, col2 = st.columns(2)
    inverter_origins = ["cecinverter", "pvwatts", "Custom"]
    inv_index = inverter_origins.index(implant["inverter"]["origin"])
    implant["inverter"]["origin"] = col1.selectbox(
        T("buttons.implant.inverter.origin"), inverter_origins, index=inv_index
    )

    if implant["inverter"]["origin"] == "cecinverter":
        inverters = retrieve_sam("cecinverter")
        inv_names = list(inverters.columns)
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
            "pdc0 (W)", value=implant["inverter"]["model"]["pdc0"]
        )

    implant["inverter"]["ac_model"] = (
        "cec" if implant["inverter"]["origin"] == "cecinverter" else "pvwatts"
    )

    # Mount configuration
    st.markdown(f"⚠️ ***{T("buttons.implant.mount.title")}***")
    mount_opts = ["SingleAxisTrackerMount", "FixedMount", "Custom"]
    mount_index = mount_opts.index(implant["mount"]["type"])
    implant["mount"]["type"] = st.selectbox(T("buttons.implant.mount.type"), mount_opts, index=mount_index)

    return implant


def render():
    st.title("📌 " + T("title"))
    implants_df = load_all_implants()

    if implants_df.empty:
        st.warning("No valid implant folders found.")
        return

    # Select implant
    col1, col2 = st.columns(2)
    selected_site = col1.selectbox(f"🌍 {T("subtitle.site")}", sorted(implants_df["site_name"].unique()))
    filtered = implants_df[implants_df["site_name"] == selected_site]
    selected_implant = col2.selectbox(f"⚙️ {T("subtitle.implant")}", filtered["implant_name"])

    selected_row = filtered[filtered["implant_name"] == selected_implant].iloc[0]
    subfolder = selected_row["subfolder"]
    st.markdown("---")


    # Edit and display site and implant
    st.subheader("🛠️ "+T("subtitle.implant_config"))
    col_left, col_sep, col_right = st.columns([2, 0.1, 3])

    with col_left:
        st.subheader(f"🏢 {T("subtitle.site")}")
        site = edit_site(subfolder)
        spacer, col1, col2 = st.columns([5, 2, 2])

        if col2.button(f"🔥 {T("buttons.simulate")}"):
            Simulate(subfolder)

    with col_sep:
        st.markdown(
            "<div style='height:100%;border-left:1px solid #ccc;'></div>",
            unsafe_allow_html=True,
        )

    with col_right:
        st.subheader(f"🧰 {T("subtitle.implant")}")
        implant = edit_implant(subfolder)

    
    if col1.button(f"💾 {T("buttons.save")}"):
        json.dump(site, (subfolder / "site.json").open("w"), indent=4)
        json.dump(implant, (subfolder / "implant.json").open("w"), indent=4)
        st.success("Changes saved.")
        st.rerun()
   
    st.markdown("---")
    # Output chart
    st.subheader("🔋 "+ T("subtitle.performance"))
    analyser = ImplantAnalyser(subfolder)
    sum_mean_plot(analyser.periodic_report())
    plot_time_series(analyser.numeric_dataframe())


def sum_mean_plot(df_plot):
    st.markdown(f"### {T("subtitle.periodic")}")

    col_graph, col_settings = st.columns([8, 1])
    with col_settings:
        variable_options = df_plot["variable"].unique().tolist()
        index = variable_options.index("dc_p_mp")
        variable_selected = st.selectbox(
            T("buttons.choose_variable"), variable_options, index=index
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                T("buttons.sum"),
                type=(
                    "primary" if st.session_state.get("stat") == "sum" else "secondary"
                ),
            ):
                st.session_state["stat"] = "sum"
                st.rerun()

        with col2:
            if st.button(
                T("buttons.mean"),
                type=(
                    "primary" if st.session_state.get("stat") == "mean" else "secondary"
                ),
            ):
                st.session_state["stat"] = "mean"
                st.rerun()

    # Fallback iniziale se non ancora impostato
    if "stat" not in st.session_state:
        st.session_state["stat"] = "sum"

    stat_selected = st.session_state["stat"]

    # Filtro dati
    filtered_df = df_plot[
        (df_plot["variable"] == variable_selected) & (df_plot["stat"] == stat_selected)
    ]

    # Costruisci il grafico
    fig = px.bar(
        filtered_df,
        x="season",
        y="value",
        color="season",
        title=f"{stat_selected.upper()} - {variable_selected}",
        labels={"value": stat_selected},
        height=500,
    )

    with col_graph:
        st.plotly_chart(fig, use_container_width=True)


def plot_time_series(data: pd.DataFrame):
    st.markdown(f"### {T("subtitle.time_distribution")}")

    numeric_cols = data.select_dtypes(include="number").columns.tolist()
    default_var = "dc_p_mp"
    default_index = (
        numeric_cols.index(default_var) if default_var in numeric_cols else 0
    )

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        variable = st.selectbox(f"⚙️ {T("buttons.choose_variable")}", options=numeric_cols, index=default_index)

    # Pulsante ON/OFF per "giorno singolo"
    with col2:
        mode = st.radio(f"{T("buttons.option.label")}", T("buttons.option.options"), index=0, horizontal=True)

    df = data.copy()
    df = df[[variable]].dropna()
    df["timestamp"] = df.index

    min_date = df["timestamp"].min().date()
    max_date = df["timestamp"].max().date()

    if mode == T("buttons.option.options")[0]:
        # Seleziona un range di giorni
        start_day, end_day = st.slider(
            "Intervallo date:",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="DD/MM/YYYY",
        )
        mask = (df["timestamp"].dt.date >= start_day) & (
            df["timestamp"].dt.date <= end_day
        )
        df_filtered = df[mask]

    else:  # Giorno singolo
        with col3:
            day = st.date_input(
                f"🗓️ {T("buttons.choose_date")}",
                min_value=min_date,
                max_value=max_date,
                value=max_date,
            )
        start_hour, end_hour = st.slider(
            "Hors:", min_value=0, max_value=23, value=(0, 23)
        )
        mask = (
            (df["timestamp"].dt.date == day)
            & (df["timestamp"].dt.hour >= start_hour)
            & (df["timestamp"].dt.hour <= end_hour)
        )
        df_filtered = df[mask]

    # Mostra grafico
    fig = px.line(
        df_filtered,
        x="timestamp",
        y=variable,
        title=f"{variable} along time",
        markers=True,
    )

    fig.update_layout(xaxis_title="Timestamp", yaxis_title=variable, height=500)

    st.plotly_chart(fig, use_container_width=True)
