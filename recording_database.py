
from application_database import get_supabase

BUCKET_NAME = "instructor-recordings"

MAX_AUDIO_SIZE = 20 * 1024 * 1024


def save_recording(
    application_id,
    recording_type,
    task_number,
    audio_file
):
    if recording_type not in (
        "pronunciation",
        "speaking",
        "teaching_demo"
    ):
        raise ValueError("Invalid recording type.")

    if recording_type == "teaching_demo":
        if task_number != 1:
            raise ValueError("Invalid task number.")
    elif task_number not in (1, 2, 3):
        raise ValueError("Invalid task number.")

    if audio_file is None:
        raise ValueError("Recording is missing.")

    audio_bytes = audio_file.getvalue()

    if not audio_bytes:
        raise ValueError("Recording is empty.")

    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise ValueError(
            "Recording exceeds the 20 MB limit."
        )

    content_type = getattr(
        audio_file,
        "type",
        "audio/wav"
    )

    if content_type not in (
        "audio/wav",
        "audio/x-wav",
        "audio/webm",
        "audio/ogg",
        "audio/mp4",
        "audio/mpeg"
    ):
        raise ValueError("Unsupported audio format.")

    extension = {
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/mp4": "m4a",
        "audio/mpeg": "mp3"
    }[content_type]

    storage_path = (
        f"{application_id}/"
        f"{recording_type}_{task_number}.{extension}"
    )

    supabase = get_supabase()

    supabase.storage.from_(
        BUCKET_NAME
    ).upload(
        path=storage_path,
        file=audio_bytes,
        file_options={
            "content-type": content_type,
            "upsert": "false"
        }
    )

    try:
        supabase.table(
            "instructor_recordings"
        ).insert({
            "application_id": application_id,
            "recording_type": recording_type,
            "task_number": task_number,
            "storage_path": storage_path
        }).execute()

    except Exception:
        # Remove the uploaded file if its
        # database record could not be saved.
        supabase.storage.from_(
            BUCKET_NAME
        ).remove([storage_path])

        raise

    return storage_path

