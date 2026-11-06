import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def save_applicant(name, email, answers, score):
    supabase = get_supabase()
    result = supabase.table("instructor_applications").insert({
        "applicant_name": name.strip(),
        "applicant_email": email.strip(),
        "english_answers": answers,
        "english_score": score,
        "status": "submitted",
    }).execute()
    if not result.data or not result.data[0].get("id"):
        raise RuntimeError("Applicant data could not be confirmed as saved.")
    return result.data[0]["id"]
