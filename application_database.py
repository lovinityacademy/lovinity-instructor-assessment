
import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


def save_applicant(name, email):
    supabase = get_supabase()

    result = (
        supabase.table("instructor_applications")
        .insert({
            "applicant_name": name,
            "applicant_email": email,
            "status": "submitted"
        })
        .execute()
    )

    if not result.data:
        raise RuntimeError("Applicant data was not saved.")

    return result.data[0]["id"]
