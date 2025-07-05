import streamlit as st


def render():
    st.title("📌 IMPLANT")
    
    st.subheader("🛠️ Implant Data")

    st.subheader("🔋 Performance")

    col_main, col_right = st.columns([3, 1])

    with col_main:  # Chart space
        st.line_chart([1, 2, 3, 4])

    with col_right:
        st.markdown("### ⚙️ Setup")
        data_opt = st.selectbox("Choose data", ["ac", "dc"])
