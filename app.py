import streamlit as st
import hashlib
import json
from application_database import save_applicant
from recording_database import save_recording

# -----------------------------------
# Page Settings
# -----------------------------------

st.set_page_config(
    page_title="Lovinity Academy -ENGLISH- 英語講師採用審査",
    page_icon="🎓",
    layout="centered"
)

# -----------------------------------
# Session State
# -----------------------------------

if "english_score" not in st.session_state:
    st.session_state.english_score = None

if "english_answers" not in st.session_state:
    st.session_state.english_answers = None

# -----------------------------------
# Header
# -----------------------------------

st.title("Lovinity Academy -ENGLISH-")
st.subheader("英語講師採用審査")



st.write(
    "Welcome to the LOVINITY ENGLISH "
    "Instructor Assessment."
)

st.write(
    "Please complete all assessment sections "
    "following the instructions."
)

st.info(
    "Your answers and recordings will be submitted for recruitment review "
    "when you select Submit Application at the end."
)

# -----------------------------------
# Applicant Information
# -----------------------------------

st.divider()
st.header("Applicant Information")

st.write(
    "Please enter your information "
    "before starting the assessment."
)

applicant_name = st.text_input(
    "Full Name",
    placeholder="Enter your full name",
    key="applicant_name"
)

applicant_email = st.text_input(
    "Email Address",
    placeholder="example@email.com",
    key="applicant_email"
)

st.caption(
    "Your information will be used "
    "for instructor recruitment assessment."
)

# -----------------------------------
# English Proficiency Test
# -----------------------------------

st.divider()
st.header("1. English Proficiency Test")

questions = [
    {
        "question": "She ___ English every day.",
        "options": [
            "study",
            "studies",
            "studying",
            "studied"
        ],
        "answer": "studies"
    },
    {
        "question": "If I ___ more time, I would travel.",
        "options": [
            "have",
            "had",
            "will have",
            "having"
        ],
        "answer": "had"
    },
    {
        "question": "He has lived in Japan ___ 2020.",
        "options": [
            "for",
            "since",
            "during",
            "from"
        ],
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

    st.write(
        "Choose the correct answer for each question."
    )

    answers = []

    for i, q in enumerate(questions):

        answer = st.radio(
            f"Q{i + 1}. {q['question']}",
            ["Select an answer"] + q["options"],
            key=f"english_q{i}"
        )

        answers.append(answer)

    submitted = st.form_submit_button(
        "Submit Answers"
    )

if submitted:

    if "Select an answer" in answers:

        st.session_state.english_score = None
        st.session_state.english_answers = None

        st.warning(
            "Please answer all questions."
        )

    else:

        score = sum(
            answers[i] == q["answer"]
            for i, q in enumerate(questions)
        )

        st.session_state.english_score = score
        st.session_state.english_answers = answers.copy()

        st.success(
            "English proficiency test completed!"
        )

if st.session_state.english_score is not None:
    st.success("English proficiency test: Completed")
    st.caption(
        "Your answers are recorded for internal recruitment review. "
        "Scores and selection decisions are not displayed to applicants. "
        "This short quiz is not an official language proficiency certification."
    )

    # Changes after submission of the quiz require the answers to be re-submitted.
    if answers != st.session_state.english_answers:
        st.warning(
            "Your answers have changed. Please click Submit Answers again "
            "before submitting your application."
        )

# -----------------------------------
# Pronunciation Assessment
# -----------------------------------

st.divider()
st.header("2. Pronunciation Assessment")

st.write(
    "Read each sentence aloud clearly "
    "and naturally."
)

st.caption(
    "Different English accents are welcome. "
    "The focus is on clear communication."
)

sentences = [
    (
        "Learning English opens doors to "
        "new opportunities around the world."
    ),
    (
        "Effective communication is essential "
        "for building trust and understanding."
    ),
    (
        "As an English teacher, I always "
        "encourage students to speak "
        "with confidence."
    )
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

        st.caption("You can play back your recording before final submission.")

# -----------------------------------
# Speaking Assessment
# -----------------------------------

st.divider()
st.header("3. Speaking Assessment")

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
            "How would you explain the difference "
            "between 'I have been to London' "
            "and 'I went to London' "
            "to a beginner?"
        )
    },
    {
        "title": "Classroom Situation",
        "question": (
            "A student is afraid of making "
            "mistakes when speaking English. "
            "How would you encourage them?"
        )
    }
]

for i, task in enumerate(speaking_tasks):

    st.subheader(
        f"Speaking Task {i + 1}: {task['title']}"
    )

    st.info(task["question"])

    st.write(
        "Recommended speaking time: 1-2 minutes."
    )

    recording = st.audio_input(
        f"Record your answer - Task {i + 1}",
        key=f"speaking_{i}"
    )

    if recording is not None:

        st.success(
            "Answer recorded successfully!"
        )

        st.audio(recording)

        st.caption("You can play back your recording before final submission.")

# -----------------------------------
# Teaching Demonstration
# -----------------------------------

st.divider()
st.header("4. Teaching Demonstration")

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

    st.success(
        "Teaching demonstration recorded!"
    )

    st.audio(demo_recording)

    st.caption("You can play back your recording before final submission.")

# -----------------------------------
# End of Assessment
# -----------------------------------

st.divider()

st.subheader("End of Assessment")

if st.session_state.english_score is not None:

    st.success(
        "English proficiency test: Completed"
    )

else:

    st.warning(
        "English proficiency test: Not completed"
    )

st.info(
    "Before submitting, please review your answers and recordings. "
    "Submission is complete only after a confirmation message and application ID appear below."
)

st.caption("Lovinity Academy -ENGLISH- | 英語講師採用審査")

# -----------------------------------
# Final Submission
# -----------------------------------

st.divider()
st.header("Final Application Submission")

required_recordings = [
    f"pronunciation_{i}" for i in range(3)
] + [
    f"speaking_{i}" for i in range(3)
] + [
    "teaching_demo"
]

completed_recordings = sum(
    st.session_state.get(key) is not None
    for key in required_recordings
)

st.write(
    f"Recordings completed: "
    f"{completed_recordings}/7"
)

english_completed = (
    st.session_state.english_score is not None
    and st.session_state.english_answers is not None
    and answers == st.session_state.english_answers
)

name_completed = bool(applicant_name.strip())

email_completed = (
    bool(applicant_email.strip())
    and "@" in applicant_email
    and "." in applicant_email.split("@")[-1]
)

st.subheader("Privacy Notice / 個人情報の取り扱い")
with st.expander("Read the Privacy Notice / 個人情報の取り扱いを確認する", expanded=True):
    st.markdown("""
**Lovinity Academy —English Instructor Recruitment Privacy Notice**

**Information collected:** Your name, email address, English test answers and results, pronunciation/speaking/teaching demonstration audio recordings, and recruitment assessment results.

**Purpose:** To assess your English proficiency and teaching skills, make recruitment decisions, communicate the outcome, and, if hired, complete necessary contract procedures.

**Retention:** For unsuccessful applicants, application information, assessment results and recordings will be deleted 90 days after the recruitment decision is finalized. For successful applicants, information needed for contract and operational administration will be retained for as long as necessary for those purposes, subject to applicable requirements.

**Access and inquiries:** Access is restricted to authorized recruitment personnel. For inquiries about access, correction, or deletion of your personal information, please contact the Lovinity Academy recruitment team through the contact channel provided by the organization.

---

**取得する情報：** 氏名、メールアドレス、英語テストの回答・得点、発音・スピーキング・模擬授業の録音、採用評価結果。

**利用目的：** 英語力・指導力の審査、採用可否の判断、選考結果の連絡、採用後の契約手続き。

**保存期間：** 不採用者の応募情報・評価結果・録音は、選考終了から90日後に削除します。採用者については、契約・業務管理に必要な情報を、必要な期間保管します。

**アクセス・お問い合わせ：** 権限を持つ採用担当者が取り扱います。情報の確認・訂正・削除等は、Lovinity Academyの採用担当窓口へお問い合わせください。
""")

consent = st.checkbox(
    "I have read and understood the Privacy Notice and agree to the "
    "collection and use of my application information and audio recordings "
    "for recruitment assessment. / 上記の個人情報の取り扱いを確認し、同意します。"
)

ready_to_submit = all([
    name_completed,
    email_completed,
    english_completed,
    completed_recordings == 7,
    consent
])

if not ready_to_submit:
    st.warning(
        "Please complete all required sections "
        "before submitting your application."
    )


if "application_submitted" not in st.session_state:
    st.session_state.application_submitted = False

if "application_id" not in st.session_state:
    st.session_state.application_id = None

if st.session_state.application_submitted:
    st.success("Application submitted successfully!")
    st.write(
        "Application ID:",
        st.session_state.application_id
    )

# Keep a stable application ID during retries within the same browser session.
# This does not prevent duplicates after the browser session is lost.
submission_fingerprint = hashlib.sha256(json.dumps({
    "name": applicant_name.strip(),
    "email": applicant_email.strip().lower(),
    "answers": st.session_state.english_answers,
    "score": st.session_state.english_score,
}, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

if st.session_state.application_id and not st.session_state.application_submitted:
    st.info("A previous submission was interrupted. You can retry in this browser session without creating a new applicant record, provided your information has not changed.")

if st.button(
    "Submit Application",
    type="primary",
    disabled=not ready_to_submit or st.session_state.application_submitted,
):
    with st.spinner("Submitting your application..."):
        try:
            if st.session_state.application_id is None:
                application_id = save_applicant(
                    applicant_name, applicant_email,
                    st.session_state.english_answers,
                    st.session_state.english_score,
                )
                st.session_state.application_id = application_id
                st.session_state.application_fingerprint = submission_fingerprint
            else:
                application_id = st.session_state.application_id
                if st.session_state.get("application_fingerprint") != submission_fingerprint:
                    raise ValueError("Applicant details changed after partial submission. Contact the administrator before retrying.")

            recording_tasks = [
                ("pronunciation", 1, "pronunciation_0"),
                ("pronunciation", 2, "pronunciation_1"),
                ("pronunciation", 3, "pronunciation_2"),
                ("speaking", 1, "speaking_0"),
                ("speaking", 2, "speaking_1"),
                ("speaking", 3, "speaking_2"),
                ("teaching_demo", 1, "teaching_demo"),
            ]
            for recording_type, task_number, key in recording_tasks:
                save_recording(application_id, recording_type, task_number,
                               st.session_state[key])

            st.session_state.application_submitted = True
            st.success("Your application has been submitted!")
            st.write("Application ID:", application_id)
        except Exception:
            st.error(
                "Submission could not be completed. Your application may be partially saved. "
                "If this browser session is still open, you may retry once after checking your connection. "
                "If the error persists, contact the administrator and provide your Application ID."
            )
            if st.session_state.application_id:
                st.write("Application ID:", st.session_state.application_id)
