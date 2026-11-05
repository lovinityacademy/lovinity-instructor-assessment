
import streamlit as st
from supabase import create_client

st.title("LOVINITY Supabase Connection Test")

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    supabase = create_client(url, key)

    result = (
        supabase.table("instructor_applications")
        .select("id")
        .limit(1)
        .execute()
    )

    st.success("Supabase connection successful!")


except Exception as e:
    st.error("Supabase connection failed.")
    st.write("Error type:", type(e).__name__)
    print("Supabase connection test failed:", type(e).__name__)
