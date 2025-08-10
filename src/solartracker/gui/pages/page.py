import streamlit as st
from ..utils.translation.traslator import translate
from utils.logger import get_logger


class Page:
    def __init__(self, pagename) -> None:
        self.lang = st.session_state.get("language", "it")
        self.page_name = pagename
        self.logger = get_logger("solartracker")

    def T(self, key: str) -> str | list:
        return translate(f"{self.page_name}.{key}")
