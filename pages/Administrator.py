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


filtered_rows = []

for row in rows:
    name_match = search_query in row["Applicant"].lower()
    email_match = search_query in row["Email"].lower()

    search_match = (
        not search_query
        or name_match
        or email_match
    )

    decision_match = (
        decision_filter == "All Applicants"
        or row["Final Decision"] == decision_filter
    )

    if search_match and decision_match:
        filtered_rows.append(row)

# -----------------------------------
# Display Applicant Results
# -----------------------------------

st.divider()
st.subheader("Applicant Results")

st.metric("Matching Applicants", len(filtered_rows))

if filtered_rows:
    st.dataframe(
        filtered_rows,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No applicants match your search.")

# -----------------------------------
# Applicant Details
# -----------------------------------

st.divider()
st.header("Applicant Details")

if filtered_rows:
    applicant_options = {
        f"{row['Applicant']} | {row['Email']} | {row['Application ID'][:8]}": row["Application ID"]
        for row in filtered_rows
    }

    selected_label = st.selectbox(
        "Select an Applicant",
        list(applicant_options.keys())
    )

    application_id = applicant_options[selected_label]

    selected_app = next(
        app for app in applications
        if app["id"] == application_id
    )

    st.write("**Name:**", selected_app["applicant_name"])
    st.write("**Email:**", selected_app["applicant_email"])
    st.write("**Application ID:**", application_id)
    st.write("**Status:**", selected_app["status"])
    st.write("**Submitted At:**", selected_app["submitted_at"])

    st.metric(
        "English Test Score",
        f"{selected_app.get('english_score', 0)}/5"
    )

    st.subheader("English Test Answers")

    english_answers = selected_app.get("english_answers")

    if isinstance(english_answers, list):
        for i, answer in enumerate(english_answers):
            st.write(f"Q{i + 1}: {answer}")

    elif isinstance(english_answers, dict):
        for question, answer in english_answers.items():
            st.write(f"{question}: {answer}")

# -----------------------------------
# Applicant Recordings
# -----------------------------------

st.divider()
st.header("Applicant Recordings")

if filtered_rows:
    try:
        recording_result = (
            supabase.table("instructor_recordings")
            .select("*")
            .eq("application_id", application_id)
            .order("recording_type")
            .order("task_number")
            .execute()
        )

        recordings = recording_result.data or []

        st.write(f"Recordings found: {len(recordings)}/7")

        recording_labels = {
            "pronunciation": "Pronunciation",
            "speaking": "Speaking",
            "teaching_demo": "Teaching Demonstration"
        }

        if not recordings:
            st.info("No recordings found for this applicant.")

        for recording in recordings:
            recording_type = recording["recording_type"]
            task_number = recording["task_number"]
            storage_path = recording["storage_path"]

            label = recording_labels.get(
                recording_type,
                recording_type
            )

            st.subheader(f"{label} - Task {task_number}")

            try:
                audio_bytes = (
                    supabase.storage
                    .from_("instructor-recordings")
                    .download(storage_path)
                )

                extension = storage_path.rsplit(".", 1)[-1].lower()

                mime_types = {
                    "wav": "audio/wav",
                    "webm": "audio/webm",
                    "ogg": "audio/ogg",
                    "m4a": "audio/mp4",
                    "mp3": "audio/mpeg"
                }

                st.audio(
                    audio_bytes,
                    format=mime_types.get(extension, "audio/wav")
                )

            except Exception:
                st.warning("This recording could not be loaded.")

    except Exception:
        st.error("Could not load recording information.")

else:
    st.info("Select a matching applicant to view recordings.")

