import streamlit as st


def user_inputs():
    location = st.selectbox("Location", ["Rome", "Madrid", "Berlin"])
    tilt = st.slider("Tilt (°)", 0, 90, 30)
    azimuth = st.slider("Azimuth (°)", 0, 360, 180)
    tracker_type = st.selectbox("Tracker Type", ["Fixed", "Single Axis", "Dual Axis"])

    return {
        "location": location,
        "tilt": tilt,
        "azimuth": azimuth,
        "tracker_type": tracker_type,
    }
