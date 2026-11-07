
"""LOVINITY ENGLISH - 90-day rejected applicant retention."""
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


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def rows(response):
    return response.data or []


def storage_names(bucket, uid):
    entries = bucket.list(uid, {"limit": 1000}) or []
    names = [item["name"] for item in entries]
    require(len(entries) < 1000, "Storage listing truncated")
    require(len(names) == len(set(names)), "Duplicate Storage entries")
    return set(names)


def rpc(db, function, uid):
    result = db.rpc(
        function, {"p_application_id": uid}
    ).execute()
    require(result.data is True, f"RPC refused: {function}")


def validate(db, uid):
    UUID(uid)

    applications = rows(
        db.table("instructor_applications")
        .select("id,status,decided_at")
        .eq("id", uid).execute()
    )
    require(len(applications) == 1, "Application missing")
    app = applications[0]

    require(app["status"] == "rejected", "Not rejected")
    require(app["decided_at"], "Missing rejection date")

    decided = datetime.fromisoformat(
        app["decided_at"].replace("Z", "+00:00")
    )
    require(
        decided.tzinfo is not None
        and decided <= datetime.now(timezone.utc) - timedelta(days=90),
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
        "Assessment is not rejected",
    )

    recordings = rows(
        db.table("instructor_recordings")
        .select("storage_path")
        .eq("application_id", uid).execute()
    )
    expected = {f"{uid}/{name}" for name in FILES}
    require(
        len(recordings) == 7
        and {r["storage_path"] for r in recordings} == expected,
        "Recording metadata mismatch",
    )


def process(db, uid):
    validate(db, uid)
    bucket = db.storage.from_(BUCKET)

    jobs = rows(
        db.table("instructor_retention_jobs")
        .select("status")
        .eq("application_id", uid).execute()
    )
    require(len(jobs) <= 1, "Duplicate retention jobs")
    status = jobs[0]["status"] if jobs else None

    if status is None:
        require(
            storage_names(bucket, uid) == FILES,
            "Storage files do not match expected seven",
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
            "Unexpected Storage files found",
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
            "Storage is not empty",
        )
        validate(db, uid)
        rpc(db, "delete_expired_rejected_application", uid)
        print("DELETED:", uid)
        return

    raise RuntimeError(f"Unexpected job status: {status}")


def main():
    db = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    enabled = (
        os.getenv("RETENTION_DELETE_ENABLED", "false").lower()
        == "true"
    )

    applications = rows(
        db.table("instructor_applications")
        .select("id,status,decided_at")
        .eq("status", "rejected")
        .lte(
            "decided_at",
            (
                datetime.now(timezone.utc) - timedelta(days=90)
            ).isoformat(),
        )
        .execute()
    )

    print("Eligible candidates:", len(applications))

    if not enabled:
        print("DRY RUN: deletion disabled")
        return

    failures = []

    for app in applications:
        uid = app["id"]
        try:
            process(db, uid)
        except Exception as exc:
            print(f"SKIPPED {uid}: {exc}", file=sys.stderr)
            failures.append(uid)

    if failures:
        raise RuntimeError(
            f"{len(failures)} application(s) need manual review"
        )

    print("Retention cleanup completed")


if __name__ == "__main__":
    main()
