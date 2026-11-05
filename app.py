
import streamlit as st

st.set_page_config(
    page_title="LOVINITY Instructor Assessment",
    page_icon="🎓",
    layout="centered"
)

st.title("LOVINITY ENGLISH")
st.subheader("Instructor Assessment System")

st.info("講師採用審査システム｜開発テスト版")

questions = [
    {
        "question": "She ___ English every day.",
        "options": ["study", "studies", "studying", "studied"],
        "answer": "studies"
    },
    {
        "question": "If I ___ more time, I would travel.",
        "options": ["have", "had", "will have", "having"],
        "answer": "had"
    },
    {
        "question": "He has lived in Japan ___ 2020.",
        "options": ["for", "since", "during", "from"],
        "answer": "since"
    },
    {
        "question": "Choose the correct sentence.",
        "options": [
            "She suggested to go home.",
            "She suggested going home.",
            "She suggested go home.",
            "She suggested went home."
        ],
        "answer": "She suggested going home."
    },
    {
        "question": "The word 'reliable' means:",
        "options": [
            "easy to forget",
            "able to be trusted",
            "very expensive",
            "difficult to understand"
        ],
        "answer": "able to be trusted"
    }
]

with st.form("english_test"):
    st.header("English Proficiency Test")
    st.write("各問題について、正しい答えを選んでください。")

    answers = []

    for i, q in enumerate(questions):
        answer = st.radio(
            f"Q{i + 1}. {q['question']}",
            ["選択してください"] + q["options"],
            key=f"q{i}",
        )
        answers.append(answer)

    submitted = st.form_submit_button("Submit Answers")

if submitted:
    if "選択してください" in answers:
        st.warning("すべての問題に回答してください。")
    else:
        score = sum(
            answers[i] == q["answer"]
            for i, q in enumerate(questions)
        )

        st.success("テストが完了しました！")
        st.metric("English Test Score", f"{score}/5")
        st.progress(score / len(questions))

        st.caption(
            "このテストは開発確認用です。"
            "正式な英語力認定や採用合否には使用できません。"
        )

# -----------------------------------
# Pronunciation Assessment
# -----------------------------------

st.divider()

st.header("Pronunciation Assessment")

st.write(
    "Read the following sentence aloud "
    "clearly and naturally."
)

sentences = [
    "Learning English opens doors to new opportunities around the world.",
    "Effective communication is essential for building trust and understanding.",
    "As an English teacher, I always encourage students to speak with confidence."
]

for i, sentence in enumerate(sentences):
    st.subheader(f"Reading Task {i + 1}")
    st.info(sentence)

    audio = st.audio_input(
        f"Record your voice - Task {i + 1}",
        key=f"pronunciation_{i}"
    )

    if audio is not None:
        st.success("Recording completed!")
        st.audio(audio)
        st.caption(
            "Recording is available for playback. "
            "AI pronunciation scoring is not enabled yet."
        )

# -----------------------------------
# Speaking Assessment
# -----------------------------------

st.divider()

st.header("Speaking Assessment")

st.write(
    "Answer each question in English. "
    "Speak clearly and provide detailed answers."
)

speaking_tasks = [
    {
        "title": "Self Introduction",
        "question": (
            "Please introduce yourself and explain "
            "your experience with English."
        )
    },
    {
        "title": "Teaching Explanation",
        "question": (
            "How would you explain the difference between "
            "'I have been to London' and "
            "'I went to London' to a beginner?"
        )
    },
    {
        "title": "Classroom Situation",
        "question": (
            "A student is afraid of making mistakes "
            "when speaking English. "
            "How would you encourage them?"
        )
    }
]

for i, task in enumerate(speaking_tasks):
    st.subheader(
        f"Speaking Task {i + 1}: {task['title']}"
    )

    st.info(task["question"])

    st.write("Recommended speaking time: 1-2 minutes.")

    recording = st.audio_input(
        f"Record your answer - Task {i + 1}",
        key=f"speaking_{i}"
    )

    if recording is not None:
        st.success("Answer recorded successfully!")
        st.audio(recording)
        st.caption(
            "Your answer has been recorded for "
            "playback in this session. "
            "It has not been submitted to an examiner."
        )

# -----------------------------------
# Teaching Demonstration
# -----------------------------------

st.divider()

st.header("Teaching Demonstration")

st.write(
    "Show us how you would teach "
    "a beginner-level adult English learner."
)

st.subheader("Scenario: Ordering Coffee")

st.info(
    "You are teaching an adult beginner "
    "who wants to order coffee at a cafe."
)

st.markdown(
    """
    **Your mini lesson should include:**

    1. A simple explanation
    2. Two useful English expressions
    3. One example conversation
    4. An encouraging closing statement
    """
)

st.write("Suggested duration: 3-5 minutes.")

demo_recording = st.audio_input(
    "Record your teaching demonstration",
    key="teaching_demo"
)

if demo_recording is not None:
    st.success("Teaching demonstration recorded!")
    st.audio(demo_recording)
    st.caption(
        "Recording is available for playback "
        "during this session. "
        "It has not been submitted or saved "
        "for administrator review."
    )
