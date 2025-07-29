import streamlit as st
from ..utils.translation.traslator import translate

class Page:
    def __init__(self, pagename) -> None:
        self.lang = st.session_state.get("language", "it")
        self.page_name = pagename
        
    def T(self, key: str) -> str | list:
        return translate(f"{self.page_name}.{key}")