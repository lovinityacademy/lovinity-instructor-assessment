st.header("Assessment Scoring")
saved_assessment = assessment_lookup.get(application_id, {})
if saved_assessment:
    st.success("Previously saved assessment loaded.")
    st.metric("Saved Total Score", f"{saved_assessment.get('total_score', 0)}/100")
else:
    st.info("This applicant has not been assessed yet.")

with st.form(key=f"assessment_scoring_{application_id}"):
    pronunciation_score = st.slider(
        "Pronunciation & Intelligibility (30)", 0, 30,
        value=int(saved_assessment.get("pronunciation_score") or 0),
    )
    english_score = st.slider(
        "English Proficiency (25)", 0, 25,
        value=int(saved_assessment.get("english_score") or 0),
    )
    teaching_score = st.slider(
        "Teaching Ability (25)", 0, 25,
        value=int(saved_assessment.get("teaching_score") or 0),
    )
    communication_score = st.slider(
        "Communication (10)", 0, 10,
        value=int(saved_assessment.get("communication_score") or 0),
    )
    reliability_score = st.slider(
        "Professionalism & Reliability (10)", 0, 10,
        value=int(saved_assessment.get("reliability_score") or 0),
    )
    save_assessment = st.form_submit_button("Calculate & Save Assessment")

if save_assessment:
    total_score = (
        pronunciation_score + english_score + teaching_score
        + communication_score + reliability_score
    )
    if total_score >= 85:
        provisional_result = "pass_candidate"
    elif total_score >= 70:
        provisional_result = "further_review"
    else:
        provisional_result = "below_threshold"

    assessment_data = {
        "pronunciation_score": pronunciation_score,
        "english_score": english_score,
        "teaching_score": teaching_score,
        "communication_score": communication_score,
        "reliability_score": reliability_score,
        "provisional_result": provisional_result,
    }
    try:
        if saved_assessment:
            (
                supabase.table("instructor_assessments")
                .update(assessment_data)
                .eq("application_id", application_id)
                .execute()
            )
        else:
            (
                supabase.table("instructor_assessments")
                .insert({"application_id": application_id, **assessment_data})
                .execute()
            )
        st.session_state["assessment_saved_for"] = application_id
        st.rerun()
    except Exception:
        st.error("Assessment could not be saved.")

# Final decision
st.divider()
st.header("Final Hiring Decision")
st.caption("Final hiring decisions require human review.")
option_to_value = {
    "Pending / Further Review": "pending",
    "Pass": "passed",
    "Reject": "rejected",
}
option_labels = list(option_to_value.keys())
option_values = list(option_to_value.values())
saved_decision = saved_assessment.get("final_decision") or "pending"
default_index = option_values.index(saved_decision) if saved_decision in option_values else 0

with st.form(key=f"final_decision_{application_id}"):
    selected_decision = st.selectbox("Final Decision", option_labels, index=default_index)
    decision_notes = st.text_area(
        "Decision Notes",
        value=saved_assessment.get("decision_notes") or "",
        placeholder="Enter the reason for your decision.",
    )
    save_decision = st.form_submit_button("Save Final Decision")

if save_decision:
    if not saved_assessment:
        st.error("Please save the assessment scores before making a final decision.")
    else:
        try:
            (
                supabase.table("instructor_assessments")
                .update({
                    "final_decision": option_to_value[selected_decision],
                    "decision_notes": decision_notes.strip(),
                    "decision_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("application_id", application_id)
                .execute()
            )
            st.session_state["decision_saved_for"] = application_id
            st.rerun()
        except Exception:
            st.error("Could not save the final decision.")
