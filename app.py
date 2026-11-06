import streamlit as st
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

st.title("Lovinity Academy -ENGLISH CLASS-")
st.subheader("英語講師採用審査")



st.write(
    "Welcome to the Lovinity Academy "
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

    score = st.session_state.english_score

    st.metric(
        "English Test Score",
        f"{score}/5"
    )

    st.progress(score / len(questions))

    st.caption(
        "This five-question quiz is one part of the internal recruitment assessment, "
        "not an official language proficiency certification."
    )

    # If answers are changed, the previous
    # score is not treated as the final result.
    if answers != st.session_state.english_answers:
        st.warning(
            "Your answers have changed. "
            "Please click Submit Answers again "
            "to update your score."
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

st.caption("LOVINITY ENGLISH | Instructor Assessment System")

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

consent = st.checkbox(
    "I agree to the processing of my "
    "application information and recordings "
    "for instructor recruitment assessment."
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

if st.button(
    "Submit Application",
    type="primary",
    disabled=(
        not ready_to_submit
        or st.session_state.application_submitted
    )
):
    with st.spinner("Submitting your application..."):
        application_id = None

        try:
            # Save applicant information and test results.
            application_id = save_applicant(
                applicant_name,
                applicant_email,
                st.session_state.english_answers,
                st.session_state.english_score
            )

            # Save all seven recordings.
            recording_tasks = [
                ("pronunciation", 1, "pronunciation_0"),
                ("pronunciation", 2, "pronunciation_1"),
                ("pronunciation", 3, "pronunciation_2"),
                ("speaking", 1, "speaking_0"),
                ("speaking", 2, "speaking_1"),
                ("speaking", 3, "speaking_2"),
                ("teaching_demo", 1, "teaching_demo")
            ]

            for recording_type, task_number, key in recording_tasks:
                save_recording(
                    application_id,
                    recording_type,
                    task_number,
                    st.session_state[key]
                )

            st.session_state.application_submitted = True
            st.session_state.application_id = application_id

            st.success(
                "Your application has been submitted!"
            )

            st.write("Application ID:", application_id)

        except Exception:
            st.error(
                "Submission could not be confirmed. Some information may already "
                "have been saved. Please contact the administrator before retrying "
                "to avoid a duplicate application."
            )
