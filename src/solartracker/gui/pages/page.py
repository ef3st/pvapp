import streamlit as st


class Page:
    def __init__(self) -> None:
        self.lang = st.session_state.get("language", "it")
