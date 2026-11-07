
"""LOVINITY ENGLISH - rejected applicant retention worker.

Production deletion is disabled unless explicitly enabled.
Only rejected applications at least 90 days past decided_at
may be processed. All destructive transitions are guarded
by existing Supabase database RPCs.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import UUID

from supabase import create_client

BUCKET = "instructor-recordings"
FILES = {
    *(f"pronunciation_{i}.wav" for i in range(1, 4)),
    *(f"speaking_{i}.wav" for i in range(1, 4)),
    "teaching_demo_1.wav",
}
PAGE_SIZE = 500


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def rows(response):
    return response.data or []


def fetch_all(query_factory):
    result = []
    offset = 0
    while True:
        batch = rows(
            query_factory().range(
                offset, offset + PAGE_SIZE - 1
            ).execute()
        )
        result.extend(batch)
        if len(batch) < PAGE_SIZE:
            return result
        offset += PAGE_SIZE


def storage_names(bucket, uid):
    entries = bucket.list(uid, {"limit": 1000}) or []
    names = [item.get("name") for item in entries]
    require(
        len(entries) < 1000
        and all(names)
        and len(names) == len(set(names)),
        "Unsafe Storage listing",
    )
    return set(names)


def rpc(db, function, uid):
    result = db.rpc(
        function, {"p_application_id": uid}
    ).execute()
    require(
        result.data is True,
        f"Database refused: {function}",
    )


def validate(db, uid):
    UUID(uid)

    apps = rows(
        db.table("instructor_applications")
        .select("id,status,decided_at")
        .eq("id", uid).execute()
    )
    require(len(apps) == 1, "Application missing")

    app = apps[0]
    require(app["status"] == "rejected", "Not rejected")
    require(app["decided_at"], "Missing decision date")

    decided = datetime.fromisoformat(
        app["decided_at"].replace("Z", "+00:00")
    )
    require(
        decided.tzinfo is not None
        and decided <= datetime.now(timezone.utc)
        - timedelta(days=90),
        "Retention period not reached",
    )

    assessments = rows(
        db.table("instructor_assessments")
        .select("final_decision")
        .eq("application_id", uid).execute()
    )
    require(
        len(assessments) == 1
        and assessments[0]["final_decision"] == "rejected",
        "Assessment mismatch",
    )

    recordings = rows(
        db.table("instructor_recordings")
        .select("storage_path")
        .eq("application_id", uid).execute()
    )
    expected = {f"{uid}/{name}" for name in FILES}
    require(
        len(recordings) == 7
        and {r["storage_path"] for r in recordings}
        == expected,
        "Recording metadata mismatch",
    )


def job_status(db, uid):
    jobs = rows(
        db.table("instructor_retention_jobs")
        .select("status")
        .eq("application_id", uid).execute()
    )
    require(len(jobs) <= 1, "Duplicate jobs")
    return jobs[0]["status"] if jobs else None


def process(db, uid):
    validate(db, uid)
    bucket = db.storage.from_(BUCKET)
    status = job_status(db, uid)

    if status is None:
        require(
            storage_names(bucket, uid) == FILES,
            "Expected seven Storage files",
        )
        rpc(db, "reserve_expired_rejected_application", uid)
        status = "pending"

    if status == "pending":
        require(
            storage_names(bucket, uid) == FILES,
            "Pending job has incomplete Storage",
        )
        rpc(db, "start_retention_storage_cleanup", uid)
        status = "processing"

    if status == "processing":
        remaining = storage_names(bucket, uid)
        require(
            remaining.issubset(FILES),
            "Unexpected Storage files",
        )

        validate(db, uid)

        if remaining:
            bucket.remove(
                [f"{uid}/{name}" for name in sorted(remaining)]
            )

        require(
            not storage_names(bucket, uid),
            "Storage deletion incomplete",
        )
        rpc(db, "mark_retention_storage_deleted", uid)
        status = "storage_deleted"

    if status == "storage_deleted":
        require(
            not storage_names(bucket, uid),
            "Storage not empty",
        )
        validate(db, uid)
        rpc(db, "delete_expired_rejected_application", uid)
        print("DELETED:", uid)
        return

    raise RuntimeError(f"Unsupported job status: {status}")


def candidates(db):
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=90)
    ).isoformat()

    eligible = fetch_all(
        lambda: db.table("instructor_applications")
        .select("id")
        .eq("status", "rejected")
        .lte("decided_at", cutoff)
        .order("id")
    )

    unfinished = fetch_all(
        lambda: db.table("instructor_retention_jobs")
        .select("application_id")
        .in_(
            "status",
            ["pending", "processing", "storage_deleted", "error"],
        )
        .order("application_id")
    )

    return sorted(
        {item["id"] for item in eligible}
        | {item["application_id"] for item in unfinished}
    )


def main():
    db = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    ids = candidates(db)
    print("Candidates:", len(ids))

    if os.getenv(
        "RETENTION_DELETE_ENABLED", "false"
    ).lower() != "true":
        print("DRY RUN: no data deleted")
        return

    failures = []

    for uid in ids:
        try:
            process(db, uid)
        except Exception as exc:
            print(
                f"MANUAL REVIEW {uid}: {exc}",
                file=sys.stderr,
            )
            failures.append(uid)

            try:
                if job_status(db, uid) == "processing":
                    db.rpc(
                        "record_retention_cleanup_error",
                        {
                            "p_application_id": uid,
                            "p_error_message": str(exc)[:1000],
                        },
                    ).execute()
            except Exception as log_error:
                print(
                    f"Error logging failed: {log_error}",
                    file=sys.stderr,
                )

    if failures:
        raise RuntimeError(
            f"{len(failures)} application(s) require review"
        )

    print("Retention cleanup completed")


if __name__ == "__main__":
    main()
