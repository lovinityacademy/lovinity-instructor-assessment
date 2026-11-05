import hmac
from datetime import datetime, timezone

import streamlit as st

from application_database import get_supabase

st.set_page_config(page_title="LOVINITY Administrator", page_icon="🔐", layout="wide")
st.title("LOVINITY ENGLISH")
st.subheader("Administrator Dashboard")

# Administrator authentication
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    st.info("Administrator login required.")
    with st.form("admin_login"):
        password = st.text_input("Administrator Password", type="password")
        login = st.form_submit_button("Log In")
    if login:
        try:
            correct_password = st.secrets["ADMIN_PASSWORD"]
        except KeyError:
            st.error("Administrator password is not configured.")
            st.stop()
        if hmac.compare_digest(password.encode("utf-8"), correct_password.encode("utf-8")):
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

if st.button("Log Out"):
    st.session_state.admin_authenticated = False
    st.rerun()

supabase = get_supabase()

# Read applicants and assessments (read-only)
st.divider()
st.header("Applicant Management")
try:
    applications = (
        supabase.table("instructor_applications")
        .select("*")
        .order("submitted_at", desc=True)
        .limit(100)
        .execute()
        .data or []
    )
    assessments = (
        supabase.table("instructor_assessments")
        .select("*")
        .limit(1000)
        .execute()
        .data or []
    )
except Exception:
    st.error("Could not load applicant data. Please check the database connection.")
    st.stop()

if not applications:
    st.info("No applications found.")
    st.stop()

assessment_lookup = {item["application_id"]: item for item in assessments}
decision_labels = {"pending": "Pending", "passed": "Pass", "rejected": "Reject"}

search_col, filter_col = st.columns(2)
with search_col:
    search_query = st.text_input("Search Applicant", placeholder="Name or email...").strip().lower()
with filter_col:
    decision_filter = st.selectbox(
        "Filter by Final Decision",
        ["All Applicants", "Pass", "Pending", "Reject", "Not Assessed"],
    )

rows = []
for app in applications:
    assessment = assessment_lookup.get(app["id"], {})
    total = assessment.get("total_score")
    decision = (
        decision_labels.get(assessment.get("final_decision") or "pending", "Pending")
        if assessment else "Not Assessed"
    )
    rows.append({
        "Applicant": app["applicant_name"],
        "Email": app["applicant_email"],
        "Assessment Score": f"{total}/100" if total is not None else "Not Assessed",
        "Final Decision": decision,
        "Application ID": app["id"],
    })

filtered_rows = [
    row for row in rows
