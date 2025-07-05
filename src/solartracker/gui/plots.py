import streamlit as st
import plotly.express as px


def plot_energy(df):
    fig = px.line(df, x="timestamp", y="energy", title="Energy Collected")
    st.plotly_chart(fig, use_container_width=True)


def plot_angles(df):
    fig = px.line(
        df, x="timestamp", y=["zenith_angle", "azimuth_angle"], title="Tracking Angles"
    )
    st.plotly_chart(fig, use_container_width=True)
