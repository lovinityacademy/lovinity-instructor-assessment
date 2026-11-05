
import streamlit as st

st.set_page_config(
    page_title="LOVINITY Administrator",
    page_icon="🔐",
    layout="centered"
)

st.title("LOVINITY ENGLISH")
st.subheader("Administrator Dashboard")

st.warning(
    "Development preview only. "
    "Administrator authentication is not enabled yet."
)

st.info(
    "The assessment scoring system will be moved "
    "to this page after authentication is configured."
)
