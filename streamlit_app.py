
import streamlit as st

applicant = st.Page(
    "app.py",
    title="Applicant Assessment",
    icon="📝",
    default=True
)

administrator = st.Page(
    "pages/Administrator.py",
    title="Administrator",
    icon="🔐"
)

navigation = st.navigation(
    [applicant, administrator]
)

navigation.run()
