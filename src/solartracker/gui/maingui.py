import streamlit as st
from .pages import home, implant_performance, implants, implants_comparison
from streamlit_option_menu import option_menu
import sys
from simulator.simulator import Simulate
from pathlib import Path

sys.dont_write_bytecode = True


def simulate_all(folder: Path = Path("data/")):
    for subfolder in sorted(folder.iterdir()):
        if subfolder.is_dir():
            Simulate(subfolder)


def streamlit():
    st.set_page_config(page_title="Solar Tracker", layout="wide")
    # st.sidebar.title("🌞 Solar Tracker")

    with st.sidebar:
        selected = option_menu(
            "☀️ Menu \n Solar Tracker ",
            ["Home", "Implants", "Implants comparison", "Implant performance"],
            icons=["house", "tools", "bar-chart", "graph-up"],
            menu_icon="cast",
            default_index=1,
        )
        selected
        st.markdown("---")
        if st.button("🔥 Simulate All"):
            simulate_all()

    # menu = st.sidebar.radio("Menu", ["Home", "Implants", "Implants comparison","Implant performance"])

    if selected == "Home":
        home.render()
    elif selected == "Implants":
        implants.render()
    elif selected == "Implants comparison":
        implants_comparison.render()
    elif selected == "Implant performance":
        implant_performance.render()

    # render_layout()


# def gui(df: pd.DataFrame):
#     df = df[["timestamp", "dc_p_mp", "period", "Implant_name"]]
#     df = df.rename(columns={"dc_p_mp": "p_mp"})
#     df = df[(df["p_mp"].notna()) & (df["p_mp"] != 0)]

#     # Create matplotlib figure
#     fig, ax = plt.subplots()
#     sns.boxplot(x="period", y="p_mp", hue="Implant_name", data=df, ax=ax)
#     sns.despine(offset=10, trim=True)

#     # Show in Streamlit
#     st.pyplot(fig)
