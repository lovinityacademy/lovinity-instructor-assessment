import streamlit as st

st.set_page_config(
    page_title="LOVINITY Instructor Assessment",
    page_icon="🎓",
    layout="centered"
)

st.title("LOVINITY ENGLISH")
st.subheader("Instructor Assessment System")

st.write("講師採用審査システムへようこそ。")
st.info("現在、システムを開発中です。")

st.divider()

st.header("講師採用審査")

name = st.text_input("お名前（テスト用の仮名）")

if st.button("審査を開始する"):
    if name.strip():
        st.success(f"{name} さん、審査画面へようこそ！")
    else:
        st.warning("お名前を入力してください。")
