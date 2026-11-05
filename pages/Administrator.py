
import hmac
import streamlit as st

from application_database import get_supabase

st.set_page_config(
    page_title="LOVINITY Administrator",
    page_icon="🔐",
    layout="centered"
)

st.title("LOVINITY ENGLISH")
st.subheader("Administrator Dashboard")

# -----------------------------------
# Administrator Authentication
# -----------------------------------

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    st.info("Administrator login required.")

    with st.form("admin_login"):
        password = st.text_input(
            "Administrator Password",
            type="password"
        )

        login = st.form_submit_button("Log In")

    if login:
        try:
            correct_password = st.secrets["ADMIN_PASSWORD"]
        except KeyError:
            st.error(
                "Administrator password is not configured."
            )
            st.stop()

        if hmac.compare_digest(
            password.encode("utf-8"),
            correct_password.encode("utf-8")
        ):
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    st.stop()

if st.button("Log Out"):
    st.session_state.admin_authenticated = False
    st.rerun()

st.success("Administrator authenticated.")

# -----------------------------------
# Applicant Data
# -----------------------------------

st.divider()
st.header("Applicant Applications")

supabase = get_supabase()

try:
    result = (
        supabase.table("instructor_applications")
        .select("*")
        .order("submitted_at", desc=True)
        .limit(100)
        .execute()
    )

    applications = result.data or []

except Exception:
    st.error(
        "Could not load applications. "
        "Please check the database connection."
    )
    st.stop()

st.metric("Applications Loaded", len(applications))

if not applications:
    st.info("No applications found.")
    st.stop()

application_options = {
    (
        f"{app['applicant_name']} | "
        f"{app['submitted_at']} | "
        f"{app['id'][:8]}"
    ): app
    for app in applications
}

selected_label = st.selectbox(
    "Select an Applicant",
    list(application_options.keys())
)

selected_app = application_options[selected_label]

application_id = selected_app["id"]

# -----------------------------------
# Applicant Details
# -----------------------------------

st.divider()
st.header("Applicant Details")

st.write(
    "**Name:**",
    selected_app["applicant_name"]
)

st.write(
    "**Email:**",
    selected_app["applicant_email"]
)

st.write(
    "**Application ID:**",
    application_id
)

st.write(
    "**Status:**",
    selected_app["status"]
)

st.write(
    "**Submitted At:**",
    selected_app["submitted_at"]
)

st.metric(
    "English Test Score",
    f"{selected_app['english_score']}/5"
)

st.subheader("English Test Answers")

english_answers = selected_app.get(
    "english_answers"
)

if isinstance(english_answers, list):
    for i, answer in enumerate(english_answers):
        st.write(f"Q{i + 1}: {answer}")
else:
    st.info("No English answers available.")

# -----------------------------------
# Recordings
# -----------------------------------

st.divider()
st.header("Applicant Recordings")

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

except Exception:
    st.error("Could not load recording information.")
    recordings = []

st.write(f"Recordings found: {len(recordings)}/7")

recording_labels = {
    "pronunciation": "Pronunciation",
    "speaking": "Speaking",
    "teaching_demo": "Teaching Demonstration"
}

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

        extension = storage_path.rsplit(".", 1)[-1]

        mime_types = {
            "wav": "audio/wav",
            "webm": "audio/webm",
            "ogg": "audio/ogg",
            "m4a": "audio/mp4",
            "mp3": "audio/mpeg"
        }

        audio_format = mime_types.get(
            extension,
            "audio/wav"
        )

        st.audio(
            audio_bytes,
            format=audio_format
        )

    except Exception:
        st.warning(
            "This recording could not be loaded."
        )

# -----------------------------------
# Assessment Scoring
# -----------------------------------

# Load previously saved assessment
try:
    saved_result = (
        supabase.table("instructor_assessments")
        .select("*")
        .eq("application_id", application_id)
        .limit(1)
        .execute()
    )

    saved_assessment = (
        saved_result.data[0]
        if saved_result.data
        else {}
    )

except Exception:
    st.error("Could not load saved assessment.")
    st.stop()

if saved_assessment:
    st.success("Previously saved assessment loaded.")
    st.metric(
        "Saved Total Score",
        f"{saved_assessment['total_score']}/100"
    )
    st.write(
        "**Saved Result:**",
        saved_assessment["provisional_result"]
    )
else:
    st.info("This applicant has not been assessed yet.")

st.divider()
st.header("Assessment Scoring")

st.caption(
    "Scores are calculated here but "
    "are not permanently stored yet."
)

with st.form(
    f"assessment_scoring_{application_id}"
):
    pronunciation_score = st.slider(
        "Pronunciation & Intelligibility (30)",
        min_value=0,
        max_value=30,
        value=0
    )

    english_score = st.slider(
        "English Proficiency (25)",
        min_value=0,
        max_value=25,
        value=0
    )

    teaching_score = st.slider(
        "Teaching Ability (25)",
        min_value=0,
        max_value=25,
        value=0
    )

    communication_score = st.slider(
        "Communication (10)",
        min_value=0,
        max_value=10,
        value=0
    )

    reliability_score = st.slider(
        "Professionalism & Reliability (10)",
        min_value=0,
        max_value=10,
        value=0
    )

    calculate = st.form_submit_button(
        "Calculate Score"
    )

if calculate:
    total_score = (
        pronunciation_score
        + english_score
        + teaching_score
        + communication_score
        + reliability_score
    )

    st.metric(
        "Total Assessment Score",
        f"{total_score}/100"
    )

    st.progress(total_score / 100)

    if total_score >= 85:
        st.success(
            "Provisional result: Pass candidate"
        )
    elif total_score >= 70:
        st.warning(
            "Provisional result: Further review"
        )
    else:
        st.error(
            "Provisional result: Below current threshold"
        )

    st.info(
        "Final hiring decisions require human review."
    )

# -----------------------------------
# Save Assessment to Supabase
# -----------------------------------

if calculate:
    if total_score >= 85:
        provisional_result = "pass_candidate"
    elif total_score >= 70:
        provisional_result = "further_review"
    else:
        provisional_result = "below_threshold"

    assessment_data = {
        "application_id": application_id,
        "pronunciation_score": pronunciation_score,
        "english_score": english_score,
        "teaching_score": teaching_score,
        "communication_score": communication_score,
        "reliability_score": reliability_score,
        "provisional_result": provisional_result
    }

    try:
        supabase.table("instructor_assessments").upsert(
            assessment_data,
            on_conflict="application_id"
        ).execute()

        st.success(
            "Assessment saved successfully!"
        )

    except Exception:
        st.error(
            "Assessment could not be saved. "
            "Please try again."
        )
