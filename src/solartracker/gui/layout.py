import streamlit as st
from .inputs import user_inputs


def render_layout():
    st.title("Solar Tracking System")

    with st.sidebar:
        params = user_inputs()

    st.subheader("Performance Metrics")

    st.subheader("Tracking Angles")
