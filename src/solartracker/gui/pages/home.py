import streamlit as st
from pathlib import Path

def render():
    st.title("🏠 Home")

    readme_path = Path("README.md")

    if readme_path.exists():
        with readme_path.open("r", encoding="utf-8") as f:
            content = f.read()
        st.markdown(content, unsafe_allow_html=True)
    else:
        st.warning("README.md non trovato.")