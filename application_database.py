
import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


def save_applicant(name, email, answers, score):
    supabase = get_supabase()

    application_data = {
        "applicant_name": name.strip(),
        "applicant_email": email.strip(),
        "english_answers": answers,
        "english_score": score,
        "status": "submitted"
    }

    result = (
        supabase.table("instructor_applications")
        .insert(application_data)
        .execute()
    )

    if not result.data:
        raise RuntimeError(
            "Applicant data was not saved."
        )

    return result.data[0]["id"]
