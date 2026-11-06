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

# Detailed assessment scoring (19 criteria, 100 points)
st.divider()
st.header("Detailed Assessment Scoring")
st.caption("CEFR C1 equivalent is required. This is an internal assessment, not an official CEFR certification.")

RUBRIC = {
    "pronunciation": ("Pronunciation & Intelligibility", 30, [
        ("sounds", "Individual sounds (vowels and consonants)", 10),
        ("stress", "Word and sentence stress", 6),
        ("intonation", "Intonation and rhythm", 6),
        ("clarity", "Clarity and intelligibility", 8),
    ]),
    "english": ("English Proficiency", 25, [
        ("grammar", "Grammar accuracy", 6),
        ("vocabulary", "Vocabulary range and appropriateness", 6),
        ("fluency", "Fluency and responsiveness", 5),
        ("reasoning", "Complex explanation and reasoning", 5),
        ("comprehension", "Comprehension and paraphrasing", 3),
    ]),
    "teaching": ("Teaching Ability", 25, [
        ("explanation", "Beginner-friendly explanations", 8),
        ("feedback", "Error correction and feedback", 6),
        ("engagement", "Encouraging learner speaking", 5),
        ("structure", "Lesson structure and pacing", 4),
        ("adaptation", "Adapting to learner understanding", 2),
    ]),
    "communication": ("Communication", 10, [
        ("listening", "Active listening and responses", 4),
        ("rapport", "Supportive learning atmosphere", 3),
        ("adaptability", "Adapting communication", 3),
    ]),
    "reliability": ("Professionalism & Reliability", 10, [
        ("instructions", "Following instructions and deadlines", 5),
        ("preparation", "Preparation and professional responsibility", 5),
    ]),
}

saved_assessment = assessment_lookup.get(application_id, {})
saved_details = saved_assessment.get("detailed_scores") or {}
if not isinstance(saved_details, dict):
    saved_details = {}
if saved_assessment:
    st.metric("Previously Saved Total", f"{saved_assessment.get('total_score') or 0}/100")
    if not saved_details:
        st.warning("Legacy scores are preserved. Enter all 19 detailed scores before saving the new assessment.")
else:
    st.info("This applicant has not been assessed yet.")

c1_options = {
    "unconfirmed": "Not yet confirmed",
    "confirmed": "C1 equivalent confirmed",
    "below_standard": "Below C1 standard",
}
with st.form(key=f"detailed_scoring_{application_id}"):
    st.write("**Score each criterion using whole points from 0 to its maximum.**")
    entered = {}
    for category, (heading, maximum, criteria) in RUBRIC.items():
        st.subheader(f"{heading} ({maximum} points)")
        entered[category] = {}
        for code, label, limit in criteria:
            previous = saved_details.get(category, {})
            if not isinstance(previous, dict):
                previous = {}
            initial = max(0, min(limit, int(previous.get(code) or 0)))
            entered[category][code] = st.number_input(
                f"{label} (0–{limit})", min_value=0, max_value=limit,
                value=initial, step=1, key=f"{application_id}_{category}_{code}",
            )
    previous_c1 = saved_assessment.get("c1_status") or "unconfirmed"
    if previous_c1 not in c1_options:
        previous_c1 = "unconfirmed"
    c1_status = st.selectbox(
        "CEFR C1 Equivalent Verification",
        options=list(c1_options),
        format_func=lambda value: c1_options[value],
        index=list(c1_options).index(previous_c1),
    )
    assessment_notes = st.text_area(
        "Assessment Notes",
        value=saved_assessment.get("assessment_notes") or "",
        placeholder="Evidence supporting C1 verification and detailed scoring",
    )
    save_assessment = st.form_submit_button("Calculate & Save Detailed Assessment")

if save_assessment:
    totals = {category: sum(scores.values()) for category, scores in entered.items()}
    total_score = sum(totals.values())
    meets_requirements = (
        c1_status == "confirmed"
        and totals["pronunciation"] >= 24
        and totals["english"] >= 20
        and totals["teaching"] >= 18
    )
    if total_score >= 85 and meets_requirements:
        provisional_result = "pass_candidate"
    elif total_score < 70:
        provisional_result = "below_threshold"
    else:
        provisional_result = "further_review"
    assessment_data = {
        "pronunciation_score": totals["pronunciation"],
        "english_score": totals["english"],
        "teaching_score": totals["teaching"],
        "communication_score": totals["communication"],
        "reliability_score": totals["reliability"],
        "detailed_scores": entered,
        "c1_status": c1_status,
        "assessment_notes": assessment_notes.strip(),
        "provisional_result": provisional_result,
    }
    try:
        if saved_assessment:
            supabase.table("instructor_assessments").update(assessment_data).eq(
                "application_id", application_id
            ).execute()
        else:
            supabase.table("instructor_assessments").insert({
                "application_id": application_id, **assessment_data
            }).execute()
        st.session_state["assessment_saved_for"] = application_id
        st.rerun()
    except Exception as exc:
        st.error("Assessment could not be saved. Check that the SQL migration was applied.")

if saved_assessment:
    current_c1 = saved_assessment.get("c1_status") or "unconfirmed"
    st.write("**C1 status:**", c1_options.get(current_c1, current_c1))
    st.write("**Provisional result:**", (saved_assessment.get("provisional_result") or "Not calculated").replace("_", " ").title())
    st.caption("Final decisions require human review and are not automatically changed by rescoring.")

# Final hiring decision
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
            supabase.table("instructor_assessments").update({
                "final_decision": option_to_value[selected_decision],
                "decision_notes": decision_notes.strip(),
                "decision_at": datetime.now(timezone.utc).isoformat(),
            }).eq("application_id", application_id).execute()
            st.session_state["decision_saved_for"] = application_id
            st.rerun()
        except Exception:
            st.error("Could not save the final decision.")
