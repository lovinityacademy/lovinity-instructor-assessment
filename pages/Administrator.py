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
    st.session_state.pop("assessment_saved_for", None)
    st.session_state.pop("decision_saved_for", None)
    st.rerun()

supabase = get_supabase()

# Applicant management
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

    except Exception:
    st.error("Could not load applicant data. Please check the database connection.")
    st.stop()

st.metric("Applications Loaded", len(applications))
if not applications:
    st.info("No applications found.")
    st.stop()

assessment_lookup = {item["application_id"]: item for item in assessments}
decision_labels = {"pending": "Pending", "passed": "Pass", "rejected": "Reject"}

search_col, filter_col = st.columns(2)
with search_col:
    search_query = st.text_input("Search Applicant", placeholder="Name or email...").strip().casefold()
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
        "Applicant": app.get("applicant_name") or "",
        "Email": app.get("applicant_email") or "",
        "Assessment Score": f"{total}/100" if total is not None else "Not Assessed",
        "Final Decision": decision,
        "Application ID": app["id"],
    })

filtered_rows = []
for row in rows:
    matches_search = (
        not search_query
        or search_query in row["Applicant"].casefold()
        or search_query in row["Email"].casefold()
    )
    matches_decision = (
        decision_filter == "All Applicants"
        or row["Final Decision"] == decision_filter
    )
    if matches_search and matches_decision:
        filtered_rows.append(row)

st.subheader("Applicant Results")
st.metric("Matching Applicants", len(filtered_rows))
if filtered_rows:
    st.dataframe(filtered_rows, use_container_width=True, hide_index=True)
else:
    st.info("No applicants match your search.")
    st.stop()

# Selected applicant
st.divider()
st.header("Applicant Details")
applicant_options = {
    f"{row['Applicant']} | {row['Email']} | {row['Application ID'][:8]}": row["Application ID"]
    for row in filtered_rows
}
selected_label = st.selectbox("Select an Applicant", list(applicant_options.keys()))
application_id = applicant_options[selected_label]
selected_app = next(app for app in applications if app["id"] == application_id)

if st.session_state.pop("assessment_saved_for", None) == application_id:
    st.success("Assessment saved successfully!")
if st.session_state.pop("decision_saved_for", None) == application_id:
    st.success("Final hiring decision saved!")

st.write("**Name:**", selected_app.get("applicant_name", ""))
st.write("**Email:**", selected_app.get("applicant_email", ""))
st.write("**Application ID:**", application_id)
st.write("**Status:**", selected_app.get("status", ""))
st.write("**Submitted At:**", selected_app.get("submitted_at", ""))
st.metric("English Test Score", f"{selected_app.get('english_score') or 0}/5")
st.subheader("English Test Answers")
english_answers = selected_app.get("english_answers")
if isinstance(english_answers, list):
    for i, answer in enumerate(english_answers, start=1):
        st.write(f"Q{i}: {answer}")
elif isinstance(english_answers, dict):
    for question, answer in english_answers.items():
        st.write(f"{question}: {answer}")
else:
    st.info("No English answers available.")

# Recordings
st.divider()
st.header("Applicant Recordings")
try:
    recordings = (
        supabase.table("instructor_recordings")
        .select("*")
        .eq("application_id", application_id)
        .order("recording_type")
        .order("task_number")
        .execute()
        .data or []
    )
    st.write(f"Recordings found: {len(recordings)}/7")
    recording_labels = {
        "pronunciation": "Pronunciation",
        "speaking": "Speaking",
        "teaching_demo": "Teaching Demonstration",
    }
    mime_types = {
        "wav": "audio/wav", "webm": "audio/webm", "ogg": "audio/ogg",
        "m4a": "audio/mp4", "mp3": "audio/mpeg",
    }
  if not recordings:
        st.info("No recordings found for this applicant.")
    for recording in recordings:
        label = recording_labels.get(recording["recording_type"], recording["recording_type"])
        st.subheader(f"{label} - Task {recording['task_number']}")
        try:
            storage_path = recording["storage_path"]
            audio_bytes = supabase.storage.from_("instructor-recordings").download(storage_path)
            extension = storage_path.rsplit(".", 1)[-1].lower()
            st.audio(audio_bytes, format=mime_types.get(extension, "audio/wav"))
        except Exception:
            st.warning("This recording could not be loaded.")
except Exception:
    st.error("Could not load recording information.")

# Assessment scoring
st.divider()
st.header("Assessment Scoring")
saved_assessment = assessment_lookup.get(application_id, {})
if saved_assessment:
    st.success("Previously saved assessment loaded.")
    st.metric("Saved Total Score", f"{saved_assessment.get('total_score', 0)}/100")
else:
    st.info("This applicant has not been assessed yet.")

with st.form(key=f"assessment_scoring_{application_id}"):
    pronunciation_score = st.slider(
        "Pronunciation & Intelligibility (30)", 0, 30,
        value=int(saved_assessment.get("pronunciation_score") or 0),
    )
    english_score = st.slider(
        "English Proficiency (25)", 0, 25,
        value=int(saved_assessment.get("english_score") or 0),
    )
    teaching_score = st.slider(
        "Teaching Ability (25)", 0, 25,
        value=int(saved_assessment.get("teaching_score") or 0),
    )
    communication_score = st.slider(
        "Communication (10)", 0, 10,
        value=int(saved_assessment.get("communication_score") or 0),
    )
    reliability_score = st.slider(
        "Professionalism & Reliability (10)", 0, 10,
        value=int(saved_assessment.get("reliability_score") or 0),
    )
    save_assessment = st.form_submit_button("Calculate & Save Assessment")

if save_assessment:
    total_score = (
        pronunciation_score + english_score + teaching_score
        + communication_score + reliability_score
    )
    if total_score >= 85:
        provisional_result = "pass_candidate"
    elif total_score >= 70:
        provisional_result = "further_review"
    else:
        provisional_result = "below_threshold"
        
    assessment_data = {
        "pronunciation_score": pronunciation_score,
        "english_score": english_score,
        "teaching_score": teaching_score,
        "communication_score": communication_score,
        "reliability_score": reliability_score,
        "provisional_result": provisional_result,
    }
    try:
        if saved_assessment:
            (
                supabase.table("instructor_assessments")
                .update(assessment_data)
                .eq("application_id", application_id)
                .execute()
            )
        else:
            (
                supabase.table("instructor_assessments")
                .insert({"application_id": application_id, **assessment_data})
                .execute()
            )
        st.session_state["assessment_saved_for"] = application_id
        st.rerun()
    except Exception:
        st.error("Assessment could not be saved.")

# Final decision
st.divider()
st.header("Final Hiring Decision")
st.caption("Final hiring decisions require human review.")
option_to_value = {
    "Pending / Further Review": "pending",
    "Pass": "passed",
    "Reject": "rejected",
}
option_labels = list(option_to_value.keys())
option_values = list(option_to_value.values())
saved_decision = saved_assessment.get("final_decision") or "pending"
default_index = option_values.index(saved_decision) if saved_decision in option_values else 0

with st.form(key=f"final_decision_{application_id}"):
    selected_decision = st.selectbox("Final Decision", option_labels, index=default_index)
    decision_notes = st.text_area(
        "Decision Notes",
        value=saved_assessment.get("decision_notes") or "",
        placeholder="Enter the reason for your decision.",
    )
    save_decision = st.form_submit_button("Save Final Decision")

if save_decision:
    if not saved_assessment:
        st.error("Please save the assessment scores before making a final decision.")
    else:
        try:
            (
                supabase.table("instructor_assessments")
                .update({
                    "final_decision": option_to_value[selected_decision],
                    "decision_notes": decision_notes.strip(),
                    "decision_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("application_id", application_id)
                .execute()
            )
            st.session_state["decision_saved_for"] = application_id
            st.rerun()
        except Exception:
            st.error("Could not save the final decision.")
