import hmac
from datetime import datetime, timezone

import streamlit as st

from application_database import get_supabase

st.set_page_config(page_title="Lovinity Academy -English- Administrator", page_icon="🔐", layout="wide")
st.title("Lovinity Academy -English-")
st.subheader("Administrator Dashboard")

# Administrator authentication
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    st.info("Administrator login required.")
    with st.form("admin_login"):
        password = st.text_input("Administrator Password", type="password")
        login = st.form_submit_button("Log In")
    if login:
        try:
            correct_password = st.secrets["ADMIN_PASSWORD"]
        except KeyError:
            st.error("Administrator password is not configured.")
            st.stop()
        if hmac.compare_digest(password.encode("utf-8"), correct_password.encode("utf-8")):
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()
    
if st.button("Log Out"):
    st.session_state.admin_authenticated = False
    st.session_state.pop("assessment_saved_for", None)
    st.session_state.pop("decision_saved_for", None)
    st.rerun()

supabase = get_supabase()


def sync_rejection_date(application_id, decision, previous_date=None):
    """Track the first confirmed rejection date for the 90-day retention rule."""
    if decision == "rejected":
        decided_at = previous_date or datetime.now(timezone.utc).isoformat()
    else:
        decided_at = None

    result = (
        supabase.table("instructor_applications")
        .update({"decided_at": decided_at})
        .eq("id", application_id)
        .execute()
    )
    if not result.data:
        raise RuntimeError("Could not update the application decision date.")
    return decided_at

# Applicant management
st.divider()
st.header("Applicant Management")

try:
    applications = (
        supabase.table("instructor_applications")
        .select("*")
        .order("submitted_at", desc=True)
        .limit(100)
        .execute()
        .data or []
    )

    assessments = (
        supabase.table("instructor_assessments")
        .select("*")
        .limit(1000)
        .execute()
        .data or []
    )

except Exception:
    st.error("Could not load applicant data. Please check the database connection.")
    st.stop()

st.metric("Applications Loaded", len(applications))
if not applications:
    st.info("No applications found.")
    st.stop()

assessment_lookup = {item["application_id"]: item for item in assessments}
decision_labels = {"pending": "Pending", "passed": "Pass", "rejected": "Reject"}

search_col, filter_col = st.columns(2)
with search_col:
    search_query = st.text_input("Search Applicant", placeholder="Name or email...").strip().casefold()
with filter_col:
    decision_filter = st.selectbox(
        "Filter by Final Decision",
        ["All Applicants", "Pass", "Pending", "Reject", "Not Assessed"],
    )

rows = []
for app in applications:
    assessment = assessment_lookup.get(app["id"], {})
    total = assessment.get("total_score")
    decision = (
        decision_labels.get(assessment.get("final_decision") or "pending", "Pending")
        if assessment else "Not Assessed"
    )
    rows.append({
        "Applicant": app.get("applicant_name") or "",
        "Email": app.get("applicant_email") or "",
        "Assessment Score": f"{total}/100" if total is not None else "Not Assessed",
        "Final Decision": decision,
        "Application ID": app["id"],
    })

filtered_rows = []
for row in rows:
    matches_search = (
        not search_query
        or search_query in row["Applicant"].casefold()
        or search_query in row["Email"].casefold()
    )
    matches_decision = (
        decision_filter == "All Applicants"
        or row["Final Decision"] == decision_filter
    )
    if matches_search and matches_decision:
        filtered_rows.append(row)

st.subheader("Applicant Results")
st.metric("Matching Applicants", len(filtered_rows))
if filtered_rows:
    st.dataframe(filtered_rows, use_container_width=True, hide_index=True)
else:
    st.info("No applicants match your search.")
    st.stop()

# Selected applicant
st.divider()
st.header("Applicant Details")
applicant_options = {
    f"{row['Applicant']} | {row['Email']} | {row['Application ID'][:8]}": row["Application ID"]
    for row in filtered_rows
}
selected_label = st.selectbox("Select an Applicant", list(applicant_options.keys()))
application_id = applicant_options[selected_label]
selected_app = next(app for app in applications if app["id"] == application_id)

if st.session_state.pop("assessment_saved_for", None) == application_id:
    st.success("Assessment saved successfully!")
if st.session_state.pop("decision_saved_for", None) == application_id:
    st.success("Final hiring decision saved!")

st.write("**Name:**", selected_app.get("applicant_name", ""))
st.write("**Email:**", selected_app.get("applicant_email", ""))
st.write("**Application ID:**", application_id)
st.write("**Status:**", selected_app.get("status", ""))
st.write("**Submitted At:**", selected_app.get("submitted_at", ""))
st.metric("English Test Score", f"{selected_app.get('english_score') or 0}/5")
st.subheader("English Test Answers")
english_answers = selected_app.get("english_answers")
if isinstance(english_answers, list):
    for i, answer in enumerate(english_answers, start=1):
        st.write(f"Q{i}: {answer}")
elif isinstance(english_answers, dict):
    for question, answer in english_answers.items():
        st.write(f"{question}: {answer}")
else:
    st.info("No English answers available.")

# Recordings
st.divider()
st.header("Applicant Recordings")
try:
    recordings = (
        supabase.table("instructor_recordings")
        .select("*")
        .eq("application_id", application_id)
        .order("recording_type")
        .order("task_number")
        .execute()
        .data or []
    )
    st.write(f"Recordings found: {len(recordings)}/7")
    recording_labels = {
        "pronunciation": "Pronunciation",
        "speaking": "Speaking",
        "teaching_demo": "Teaching Demonstration",
    }
    mime_types = {
        "wav": "audio/wav", "webm": "audio/webm", "ogg": "audio/ogg",
        "m4a": "audio/mp4", "mp3": "audio/mpeg",
    }
    if not recordings:
        st.info("No recordings found for this applicant.")
    for recording in recordings:
        label = recording_labels.get(recording["recording_type"], recording["recording_type"])
        st.subheader(f"{label} - Task {recording['task_number']}")
        try:
            storage_path = recording["storage_path"]
            audio_bytes = supabase.storage.from_("instructor-recordings").download(storage_path)
            extension = storage_path.rsplit(".", 1)[-1].lower()
            st.audio(audio_bytes, format=mime_types.get(extension, "audio/wav"))
        except Exception:
            st.warning("This recording could not be loaded.")
except Exception:
    st.error("Could not load recording information.")

# Detailed assessment scoring (19 criteria, 100 points)
st.divider()
st.header("Detailed Assessment Scoring")
st.caption("CEFR C1 equivalent is required. This is an internal assessment, not an official CEFR certification.")

RUBRIC = {
    "pronunciation": ("Pronunciation & Intelligibility", 30, [
        ("sounds", "Individual sounds (vowels and consonants)", 10),
        ("stress", "Word and sentence stress", 6),
        ("intonation", "Intonation and rhythm", 6),
        ("clarity", "Clarity and intelligibility", 8),
    ]),
    "english": ("English Proficiency", 25, [
        ("grammar", "Grammar accuracy", 6),
        ("vocabulary", "Vocabulary range and appropriateness", 6),
        ("fluency", "Fluency and responsiveness", 5),
        ("reasoning", "Complex explanation and reasoning", 5),
        ("comprehension", "Comprehension and paraphrasing", 3),
    ]),
    "teaching": ("Teaching Ability", 25, [
        ("explanation", "Beginner-friendly explanations", 8),
        ("feedback", "Error correction and feedback", 6),
        ("engagement", "Encouraging learner speaking", 5),
        ("structure", "Lesson structure and pacing", 4),
        ("adaptation", "Adapting to learner understanding", 2),
    ]),
    "communication": ("Communication", 10, [
        ("listening", "Active listening and responses", 4),
        ("rapport", "Supportive learning atmosphere", 3),
        ("adaptability", "Adapting communication", 3),
    ]),
    "reliability": ("Professionalism & Reliability", 10, [
        ("instructions", "Following instructions and deadlines", 5),
        ("preparation", "Preparation and professional responsibility", 5),
    ]),
}

saved_assessment = assessment_lookup.get(application_id, {})
saved_details = saved_assessment.get("detailed_scores") or {}
if not isinstance(saved_details, dict):
    saved_details = {}
if saved_assessment:
    st.metric("Previously Saved Total", f"{saved_assessment.get('total_score') or 0}/100")
    if not saved_details:
        st.warning("Legacy scores are preserved. Enter all 19 detailed scores before saving the new assessment.")
else:
    st.info("This applicant has not been assessed yet.")

c1_options = {
    "unconfirmed": "Not yet confirmed",
    "confirmed": "C1 equivalent confirmed",
    "below_standard": "Below C1 standard",
}
with st.form(key=f"detailed_scoring_{application_id}"):
    st.write("**Score each criterion using whole points from 0 to its maximum.**")
    entered = {}
    for category, (heading, maximum, criteria) in RUBRIC.items():
        st.subheader(f"{heading} ({maximum} points)")
        entered[category] = {}
        for code, label, limit in criteria:
            previous = saved_details.get(category, {})
            if not isinstance(previous, dict):
                previous = {}
            initial = max(0, min(limit, int(previous.get(code) or 0)))
            entered[category][code] = st.number_input(
                f"{label} (0–{limit})", min_value=0, max_value=limit,
                value=initial, step=1, key=f"{application_id}_{category}_{code}",
            )
    previous_c1 = saved_assessment.get("c1_status") or "unconfirmed"
    if previous_c1 not in c1_options:
        previous_c1 = "unconfirmed"
    c1_status = st.selectbox(
        "CEFR C1 Equivalent Verification",
        options=list(c1_options),
        format_func=lambda value: c1_options[value],
        index=list(c1_options).index(previous_c1),
    )
    assessment_notes = st.text_area(
        "Assessment Notes",
        value=saved_assessment.get("assessment_notes") or "",
        placeholder="Evidence supporting C1 verification and detailed scoring",
    )
    save_assessment = st.form_submit_button("Calculate & Save Detailed Assessment")

if save_assessment:
    totals = {category: sum(scores.values()) for category, scores in entered.items()}
    total_score = sum(totals.values())
    meets_requirements = (
        c1_status == "confirmed"
        and totals["pronunciation"] >= 24
        and totals["english"] >= 20
        and totals["teaching"] >= 18
    )
    # C1未確認はPending。確認済みの審査のみ自動Pass/Reject。
    if c1_status == "unconfirmed":
        provisional_result = "further_review"
        automatic_decision = "pending"
    elif total_score >= 85 and meets_requirements:
        provisional_result = "pass_candidate"
        automatic_decision = "passed"
    else:
        provisional_result = "below_threshold"
        automatic_decision = "rejected"
    assessment_data = {
        "pronunciation_score": totals["pronunciation"],
        "english_score": totals["english"],
        "teaching_score": totals["teaching"],
        "communication_score": totals["communication"],
        "reliability_score": totals["reliability"],
        "detailed_scores": entered,
        "c1_status": c1_status,
        "assessment_notes": assessment_notes.strip(),
        "provisional_result": provisional_result,
        "final_decision": automatic_decision,
        "decision_at": datetime.now(timezone.utc).isoformat() if automatic_decision != "pending" else None,
        "decision_notes": "Automatic assessment decision; administrator may override below.",
    }
    try:
        if saved_assessment:
            supabase.table("instructor_assessments").update(assessment_data).eq(
                "application_id", application_id
            ).execute()
        else:
            supabase.table("instructor_assessments").insert({
                "application_id": application_id, **assessment_data
            }).execute()
        try:
            sync_rejection_date(
                application_id,
                automatic_decision,
                selected_app.get("decided_at") if saved_assessment.get("final_decision") == "rejected" else None,
            )
        except Exception:
            st.error("Assessment was saved, but the rejection date could not be updated. Please retry or check Supabase.")
            st.stop()
        st.session_state["assessment_saved_for"] = application_id
        st.rerun()
    except Exception:
        st.error("Assessment could not be saved. Please check the database settings.")

if saved_assessment:
    current_c1 = saved_assessment.get("c1_status") or "unconfirmed"
    st.write("**C1 status:**", c1_options.get(current_c1, current_c1))
    st.write("**Provisional result:**", (saved_assessment.get("provisional_result") or "Not calculated").replace("_", " ").title())
    st.write("**Automatic decision:**", decision_labels.get(saved_assessment.get("final_decision") or "pending", "Pending"))
    st.caption("This is an internal automatic screening result. Review before notifying applicants.")

# Final hiring decision
st.divider()
st.header("Final Hiring Decision")
st.caption("Automatic result can be manually overridden. Re-saving scores recalculates the automatic decision.")
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
            new_decision = option_to_value[selected_decision]
            supabase.table("instructor_assessments").update({
                "final_decision": new_decision,
                "decision_notes": decision_notes.strip(),
                "decision_at": datetime.now(timezone.utc).isoformat() if new_decision != "pending" else None,
            }).eq("application_id", application_id).execute()
            try:
                sync_rejection_date(
                    application_id,
                    new_decision,
                    selected_app.get("decided_at") if saved_decision == "rejected" else None,
                )
            except Exception:
                st.error("Decision was saved, but the rejection date could not be updated. Please retry or check Supabase.")
                st.stop()
            st.session_state["decision_saved_for"] = application_id
            st.rerun()
        except Exception:
            st.error("Could not save the final decision.")


# Copy-only notification templates (no email delivery or SMTP required)
st.divider()
st.header("Applicant Notification Template")
st.caption("This screen does not send emails. Copy the text and send it yourself using your email service.")

current_decision = saved_assessment.get("final_decision") or "pending"
recipient_email = (selected_app.get("applicant_email") or "").strip()
applicant_name = (selected_app.get("applicant_name") or "Applicant").strip()

if current_decision == "pending":
    st.info("Decision is Pending. Confirm Pass or Reject to prepare the notification text.")
else:
    if current_decision == "passed":
        default_subject = "LOVINITY ENGLISH | 講師選考結果と次のご案内"
        default_body = f"""{applicant_name} 様

この度はLovinity Academy 英語講師選考にご応募いただき、誠にありがとうございます。

審査の結果、次の選考ステップへお進みいただきたいと考えております。
面接・今後のご案内につきましては、担当者より改めてご連絡いたします。

引き続き、どうぞよろしくお願いいたします。

Lovinity Academy
採用担当"""
    else:
        default_subject = "LOVINITY ENGLISH | 講師選考結果のご連絡"
        default_body = f"""{applicant_name} 様

この度はLovinity Academy 英語講師選考にご応募いただき、誠にありがとうございました。

慎重に選考を進めました結果、誠に残念ながら今回はご希望に添えない結果となりました。

お忙しい中、選考にご協力いただきましたことに心より感謝申し上げます。
今後のご活躍をお祈り申し上げます。

Lovinity Academy
採用担当"""

    st.write("**Decision:**", "Pass" if current_decision == "passed" else "Reject")
    st.write("**Applicant email (copy):**")
    st.code(recipient_email or "No email address registered", language=None)
    st.write("**Subject (copy):**")
    st.code(default_subject, language=None)
    st.write("**Message (copy):**")
    st.code(default_body, language=None)
    st.info("Copy the recipient, subject and message into Gmail. This app does not send emails or record them as sent.")

# Retention preview: read-only; no deletion is performed.
st.divider()
st.header("90-Day Retention Review (Preview Only)")
st.caption("Lists rejected applicants whose rejection date is at least 90 days old. No records or recordings are deleted here.")

from datetime import timedelta

if st.button("Check Records Eligible for Deletion", key="retention_preview"):
    try:
        def fetch_all(table_name, columns, rejected_only=False):
            page_size = 1000
            max_pages = 20
            records = []
            truncated = False
            for page in range(max_pages):
                query = supabase.table(table_name).select(columns)
                if rejected_only:
                    query = query.eq("final_decision", "rejected")
                batch = query.range(page * page_size, (page + 1) * page_size - 1).execute().data or []
                records.extend(batch)
                if len(batch) < page_size:
                    break
            else:
                truncated = True
            return records, truncated

        rejection_rows, assessment_truncated = fetch_all(
            "instructor_assessments", "application_id,final_decision", rejected_only=True
        )
        application_rows, application_truncated = fetch_all(
            "instructor_applications", "id,applicant_name,applicant_email,decided_at"
        )
        if assessment_truncated or application_truncated:
            st.warning("There may be more than 20,000 records. This preview may be incomplete; do not use it to authorize deletion.")

        rejected_ids = {row["application_id"] for row in rejection_rows}
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        eligible = []
        missing_dates = 0
        invalid_dates = 0
        for applicant in application_rows:
            if applicant["id"] not in rejected_ids:
                continue
            date_text = applicant.get("decided_at")
            if not date_text:
                missing_dates += 1
                continue
            try:
                decided = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
                if decided.tzinfo is None:
                    invalid_dates += 1
                    continue
            except (ValueError, TypeError):
                invalid_dates += 1
                continue
            if decided <= cutoff:
                eligible.append({
                    "Applicant": applicant.get("applicant_name") or "",
                    "Email": applicant.get("applicant_email") or "",
                    "Application ID": applicant["id"],
                    "Rejected At (UTC)": decided.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                    "Eligible Since (UTC)": (decided + timedelta(days=90)).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                })
        eligible.sort(key=lambda row: row["Eligible Since (UTC)"])
        st.metric("Eligible for Deletion (Preview)", len(eligible))
        if eligible:
            st.dataframe(eligible, use_container_width=True, hide_index=True)
        else:
            st.success("No rejected applicants are currently eligible for deletion.")
        if missing_dates:
            st.warning(f"{missing_dates} rejected applicant(s) have no decided_at date and were excluded.")
        if invalid_dates:
            st.warning(f"{invalid_dates} rejected applicant(s) have invalid dates and were excluded.")
        st.info("Read-only preview: this page does not delete applicant records, assessments, recording metadata, or audio files.")
    except Exception:
        st.error("Could not check retention records. No data was deleted.")


# Individual applicant deletion preview — read-only, no destructive actions.
st.divider()
st.header("Applicant Deletion Preview (Read Only)")
st.caption("Inspect one test applicant and all linked database records and audio paths before building deletion. Nothing is deleted here.")

preview_options = {
    f"{app.get('applicant_name') or 'Unnamed'} | {str(app['id'])[:8]}": app['id']
    for app in applications
}
preview_label = st.selectbox("Applicant to inspect", list(preview_options), key="deletion_preview_applicant")
preview_id = preview_options[preview_label]
if st.button("Preview Linked Data (No Deletion)", key="preview_linked_data"):
    try:
        preview_app = (
            supabase.table("instructor_applications")
            .select("id,applicant_name,applicant_email,decided_at,status")
            .eq("id", preview_id).execute().data or []
        )
        preview_assessments = (
            supabase.table("instructor_assessments")
            .select("application_id,final_decision,decision_at")
            .eq("application_id", preview_id).execute().data or []
        )
        preview_recordings = (
            supabase.table("instructor_recordings")
            .select("recording_type,task_number,storage_path")
            .eq("application_id", preview_id).execute().data or []
        )
        if len(preview_app) != 1:
            st.error("Applicant was not found or the result was ambiguous. Nothing was changed.")
        else:
            applicant = preview_app[0]
            st.write("**Applicant:**", applicant.get("applicant_name") or "(blank)")
            st.write("**Application ID:**", preview_id)
            st.write("**Decision:**", preview_assessments[0].get("final_decision") if len(preview_assessments) == 1 else "Not uniquely recorded")
            st.write("**Rejected at:**", applicant.get("decided_at") or "Not set")
            st.metric("Application records", len(preview_app))
            st.metric("Assessment records", len(preview_assessments))
            st.metric("Recording metadata records", len(preview_recordings))
            if preview_recordings:
                st.dataframe([
                    {"Type": item.get("recording_type"), "Task": item.get("task_number"), "Storage path": item.get("storage_path")}
                    for item in preview_recordings
                ], use_container_width=True, hide_index=True)
            st.warning("This preview checks recording database rows, not whether every Storage object exists. No data or audio files were deleted.")
    except Exception:
        st.error("Could not load deletion preview. No data was changed.")


# Restricted one-applicant deletion test. This action is irreversible.
st.divider()
st.header("Test Three — Controlled Deletion Test")
st.warning("Permanent deletion test only. The button below deletes database records and audio objects for the specified test applicant.")
TEST_ID = "6b4ad470-e1e8-4255-80ac-e3deef8f5af5"

if st.button("Verify Test Three for Deletion", key="verify_test_three_delete"):
    try:
        apps = (supabase.table("instructor_applications").select("id,applicant_name")
                .eq("id", TEST_ID).execute().data or [])
        assess = (supabase.table("instructor_assessments").select("application_id")
                  .eq("application_id", TEST_ID).execute().data or [])
        recs = (supabase.table("instructor_recordings").select("storage_path")
                .eq("application_id", TEST_ID).execute().data or [])
        paths = [r.get("storage_path", "") for r in recs]
        valid = (len(apps) == 1 and apps[0].get("applicant_name") == "Test Three"
                 and len(assess) == 1 and len(recs) == 7
                 and len(set(paths)) == 7
                 and all(isinstance(path, str) and path.startswith(TEST_ID + "/")
                         and ".." not in path for path in paths))
        if valid:
            st.session_state["test_three_verified"] = {"id": TEST_ID, "paths": paths}
            st.success("Identity, assessment, and seven recording paths verified. This does not confirm Storage object existence.")
        else:
            st.session_state.pop("test_three_verified", None)
            st.error("Verification failed. No deletion is permitted.")
    except Exception:
        st.session_state.pop("test_three_verified", None)
        st.error("Verification failed. No deletion is permitted.")

verified = st.session_state.get("test_three_verified")
if verified and verified.get("id") == TEST_ID:
    st.write("**Deletion target:** Test Three")
    st.code(TEST_ID)
    st.write("**Recording objects to delete:**")
    st.code("\n".join(verified["paths"]))
    confirmation = st.text_input("Type the full Application ID to confirm permanent deletion", key="test_three_confirmation")
    if st.button("PERMANENTLY DELETE TEST THREE", type="primary", disabled=confirmation != TEST_ID,
                 key="delete_test_three_now"):
        st.session_state.pop("test_three_verified", None)
        try:
            # Re-read immediately before deletion to avoid acting on a stale preview.
            apps = (supabase.table("instructor_applications").select("id,applicant_name")
                    .eq("id", TEST_ID).execute().data or [])
            recs = (supabase.table("instructor_recordings").select("storage_path")
                    .eq("application_id", TEST_ID).execute().data or [])
            paths = [r.get("storage_path", "") for r in recs]
            if not (len(apps) == 1 and apps[0].get("applicant_name") == "Test Three"
                    and len(recs) == 7 and set(paths) == set(verified["paths"])):
                raise RuntimeError("Applicant or recording data changed since verification")
            # Storage first: never delete metadata if object deletion raises an error.
            # Storage's response should be checked for any reported failure.
            storage_result = supabase.storage.from_("instructor-recordings").remove(paths)
            if isinstance(storage_result, dict) and storage_result.get("error"):
                raise RuntimeError("Storage reported a deletion error")
            # Verify that the objects cannot be downloaded before deleting metadata.
            for path in paths:
                try:
                    supabase.storage.from_("instructor-recordings").download(path)
                except Exception:
                    continue
                raise RuntimeError("A recording object remains accessible: " + path)
            supabase.table("instructor_recordings").delete().eq("application_id", TEST_ID).execute()
            supabase.table("instructor_assessments").delete().eq("application_id", TEST_ID).execute()
            supabase.table("instructor_applications").delete().eq("id", TEST_ID).execute()
            remaining = []
            for table, field in (("instructor_recordings", "application_id"),
                                 ("instructor_assessments", "application_id"),
                                 ("instructor_applications", "id")):
                result = supabase.table(table).select(field).eq(field, TEST_ID).execute().data or []
                if result:
                    remaining.append(table)
            if remaining:
                st.error("Deletion was partially completed. Remaining records: " + ", ".join(remaining))
            else:
                st.success("Test Three and linked audio/records were deleted. Verify in Supabase before proceeding.")
        except Exception as exc:
            st.error("Deletion stopped or was only partially completed: " + str(exc))
            st.warning("Do not retry blindly. Check Storage and all three tables before another attempt.")
