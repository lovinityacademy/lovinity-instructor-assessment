
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from supabase import create_client


BUCKET_NAME = "instructor-recordings"

EXPECTED_TASKS = {
    ("pronunciation", 1),
    ("pronunciation", 2),
    ("pronunciation", 3),
    ("speaking", 1),
    ("speaking", 2),
    ("speaking", 3),
    ("teaching_demo", 1),
}

ACTIVE_JOB_STATUSES = {
    "pending",
    "processing",
    "storage_deleted",
    "error",
}


def fetch_all(db, table, columns):
    rows = []
    offset = 0

    while True:
        query = db.table(table).select(columns)

        if table == "instructor_applications":
            query = query.order("id")
        elif table == "instructor_recordings":
            query = query.order("application_id").order("id")
        else:
            query = query.order("application_id")

        batch = (
            query.range(offset, offset + 999)
            .execute()
            .data or []
        )

        rows.extend(batch)

        if len(batch) < 1000:
            return rows

        offset += 1000


def parse_date(value):
    if not isinstance(value, str):
        return None

    try:
        result = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
        return result if result.tzinfo else None
    except ValueError:
        return None


def expected_path(application_id, recording_type, task_number):
    return (
        f"{application_id}/"
        f"{recording_type}_{task_number}.wav"
    )

def validate_recordings(application_id, rows, global_path_counts):
    if len(rows) != 7:
        return False, "recording count is not 7"

    tasks = set()
    paths = set()

    for row in rows:
        recording_type = row.get("recording_type")
        task_number = row.get("task_number")
        path = row.get("storage_path")

        task = (recording_type, task_number)

        if task not in EXPECTED_TASKS:
            return False, "unexpected recording task"

        if task in tasks:
            return False, "duplicate recording task"

        tasks.add(task)

        if path != expected_path(
            application_id,
            recording_type,
            task_number,
        ):
            return False, "unexpected storage path"

        if path in paths:
            return False, "duplicate storage path"

        if global_path_counts[path] != 1:
            return False, "storage path shared by multiple records"

        paths.add(path)

    if tasks != EXPECTED_TASKS:
        return False, "missing recording task"

    return True, "valid"


def verify_storage_files(db, application_id, recording_rows):
    expected_paths = {
        row["storage_path"] for row in recording_rows
    }

    actual_paths = set()
    pending_folders = [application_id]
    visited_folders = set()

    bucket = db.storage.from_(BUCKET_NAME)

    while pending_folders:
        folder = pending_folders.pop()

        if folder in visited_folders:
            return False, "repeated Storage folder"

        visited_folders.add(folder)
        offset = 0

        while True:
            batch = bucket.list(
                folder,
                {"limit": 100, "offset": offset},
            )

            if not isinstance(batch, list):
                raise RuntimeError("Unexpected Storage response")

            for item in batch:
                name = item.get("name")

                if (
                    not isinstance(name, str)
                    or not name
                    or name in (".", "..")
                    or "/" in name
                ):
                    return False, "invalid Storage item"

                path = f"{folder}/{name}"

                if item.get("id") is None:
                    pending_folders.append(path)
                else:
                    if path in actual_paths:
                        return False, "duplicate Storage listing"

                    actual_paths.add(path)

            if len(batch) < 100:
                break

            offset += 100

    if actual_paths != expected_paths:
        return False, (
            f"Storage mismatch: "
            f"expected={len(expected_paths)}, "
            f"actual={len(actual_paths)}"
        )

    return True, "verified"


def main():
    # Hard safety lock: deletion is never permitted.
    if os.getenv(
        "RETENTION_DELETE_ENABLED", "false"
    ).strip().lower() != "false":
        raise RuntimeError(
            "Deletion is disabled. "
            "RETENTION_DELETE_ENABLED must be false."
        )

    db = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    apps = fetch_all(
        db,
        "instructor_applications",
        "id,decided_at",
    )

    assessments = fetch_all(
        db,
        "instructor_assessments",
        "application_id,final_decision",
    )

    recordings = fetch_all(
        db,
        "instructor_recordings",
        "id,application_id,recording_type,task_number,storage_path",
    )

    jobs = fetch_all(
        db,
        "instructor_retention_jobs",
        "application_id,status",
    )

    assessment_counts = Counter(
        row["application_id"]
        for row in assessments
    )

    assessments_by_id = {
        row["application_id"]: row
        for row in assessments
    }

    recordings_by_id = defaultdict(list)
    global_path_counts = Counter()

    for row in recordings:
        aid = row["application_id"]
        recordings_by_id[aid].append(row)

        path = row.get("storage_path")
        if isinstance(path, str):
            global_path_counts[path] += 1

    jobs_by_id = {
        row["application_id"]: row["status"]
        for row in jobs
    }

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    eligible = 0
    protected = 0
    review = 0
    existing_jobs = 0
    errors = 0

    for app in apps:
        aid = app["id"]

        if aid in jobs_by_id:
            existing_jobs += 1
            status = jobs_by_id[aid]
            print(f"EXISTING JOB {aid}: {status}")

            if status in ACTIVE_JOB_STATUSES:
                errors += 1
                print(
                    f"ERROR {aid}: active retention job "
                    "requires manual inspection"
                )

            continue

        if assessment_counts[aid] != 1:
            review += 1
            print(f"REVIEW {aid}: assessment count")
            continue

        if assessments_by_id[aid]["final_decision"] != "rejected":
            protected += 1
            continue

        decided = parse_date(app.get("decided_at"))

        if decided is None:
            review += 1
            print(f"REVIEW {aid}: invalid decision date")
            continue

        if decided > cutoff:
            protected += 1
            continue

        rows = recordings_by_id.get(aid, [])

        valid, reason = validate_recordings(
            aid,
            rows,
            global_path_counts,
        )

        if not valid:
            review += 1
            print(f"REVIEW {aid}: {reason}")
            continue

        try:
            storage_ok, reason = verify_storage_files(
                db,
                aid,
                rows,
            )
        except Exception as exc:
            errors += 1
            print(
                f"ERROR {aid}: Storage verification failed "
                f"({type(exc).__name__})"
            )
            continue

        if not storage_ok:
            review += 1
            print(f"REVIEW {aid}: {reason}")
            continue

        eligible += 1
        print(f"ELIGIBLE {aid}: all 7 files verified")

    print("----- RETENTION SUMMARY -----")
    print(f"Eligible: {eligible}")
    print(f"Protected: {protected}")
    print(f"Needs Manual Review: {review}")
    print(f"Existing Retention Jobs: {existing_jobs}")
    print("Deleted: 0")
    print(f"Errors: {errors}")
    print("MODE: DRY RUN")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
