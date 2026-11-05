import hmac
import streamlit as st

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
# Assessment Scoring
# -----------------------------------

st.header("Assessment Scoring")

st.caption(
    "Prototype: scores are not permanently stored."
)

with st.form("assessment_scoring_admin"):
    pronunciation_score = st.slider(
        "Pronunciation & Intelligibility (30)",
        min_value=0, max_value=30, value=0
    )

    english_score = st.slider(
        "English Proficiency (25)",
        min_value=0, max_value=25, value=0
    )

    teaching_score = st.slider(
        "Teaching Ability (25)",
        min_value=0, max_value=25, value=0
    )

    communication_score = st.slider(
        "Communication (10)",
        min_value=0, max_value=10, value=0
    )

    reliability_score = st.slider(
        "Professionalism & Reliability (10)",
        min_value=0, max_value=10, value=0
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
