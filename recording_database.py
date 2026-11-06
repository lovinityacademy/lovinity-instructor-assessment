from application_database import get_supabase

BUCKET_NAME = "instructor-recordings"
MAX_AUDIO_SIZE = 20 * 1024 * 1024
MIME_EXTENSIONS = {
    "audio/wav": "wav", "audio/x-wav": "wav",
    "audio/webm": "webm", "audio/ogg": "ogg",
    "audio/mp4": "m4a", "audio/mpeg": "mp3",
}


def save_recording(application_id, recording_type, task_number, audio_file):
    if recording_type not in ("pronunciation", "speaking", "teaching_demo"):
        raise ValueError("Invalid recording type.")
    if (recording_type == "teaching_demo" and task_number != 1) or (
        recording_type != "teaching_demo" and task_number not in (1, 2, 3)
    ):
        raise ValueError("Invalid task number.")
    if audio_file is None:
        raise ValueError("Recording is missing.")
    audio_bytes = audio_file.getvalue()
    if not audio_bytes or len(audio_bytes) > MAX_AUDIO_SIZE:
        raise ValueError("Recording is empty or exceeds 20 MB.")
    content_type = getattr(audio_file, "type", None) or "audio/wav"
    if content_type not in MIME_EXTENSIONS:
        raise ValueError("Unsupported audio format.")

    supabase = get_supabase()
    existing = (supabase.table("instructor_recordings")
                .select("storage_path")
                .eq("application_id", application_id)
                .eq("recording_type", recording_type)
                .eq("task_number", task_number)
                .limit(1).execute().data or [])
    if existing:
        return existing[0]["storage_path"]

    storage_path = f"{application_id}/{recording_type}_{task_number}.{MIME_EXTENSIONS[content_type]}"
    supabase.storage.from_(BUCKET_NAME).upload(
        path=storage_path,
        file=audio_bytes,
        file_options={"content-type": content_type, "upsert": "false"},
    )
    try:
        supabase.table("instructor_recordings").insert({
            "application_id": application_id,
            "recording_type": recording_type,
            "task_number": task_number,
            "storage_path": storage_path,
        }).execute()
    except Exception:
        # Best effort cleanup; preserve the original error if cleanup fails.
        try:
            supabase.storage.from_(BUCKET_NAME).remove([storage_path])
        except Exception:
            pass
        raise
    return storage_path
