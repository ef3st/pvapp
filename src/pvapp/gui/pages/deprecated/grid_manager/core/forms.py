from contextlib import contextmanager
import streamlit as st


@contextmanager
def grid_change(flag_key: str = "modified"):
    try:
        yield
    finally:
        st.session_state[flag_key] = True
