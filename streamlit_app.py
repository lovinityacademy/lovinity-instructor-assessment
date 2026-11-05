
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

connection_test = st.Page(
    "supabase_test.py",
    title="Connection Test",
    icon="🔧"
)

navigation = st.navigation(
    [applicant, administrator, connection_test]
)

navigation.run()
