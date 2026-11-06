
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

from supabase import create_client


BUCKET_NAME = "instructor-recordings"

EXPECTED = {
    ("pronunciation", 1),
    ("pronunciation", 2),
    ("pronunciation", 3),
    ("speaking", 1),
    ("speaking", 2),
    ("speaking", 3),
    ("teaching_demo", 1),
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
    if not value:
        return None

    try:
        date = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
        return date if date.tzinfo else None

    except (ValueError, TypeError, AttributeError):
        return None


def verify_storage_files(db, application_id, recording_rows):
    expected_paths = {
        row["storage_path"]
        for row in recording_rows
    }

    if len(expected_paths) != 7:
        return False

    bucket = db.storage.from_(BUCKET_NAME)
    actual_paths = set()
    pending_folders = [application_id]
    visited_folders = set()

    try:
        while pending_folders:
            folder = pending_folders.pop()

            if folder in visited_folders:
                return False

            visited_folders.add(folder)
            offset = 0

            while True:
                batch = bucket.list(
                    folder,
                    {
                        "limit": 100,
                        "offset": offset,
                    },
                )

                for item in batch:
                    name = item.get("name")

                    if not name or name in (".", ".."):
                        return False

                    path = f"{folder}/{name}"

                    if item.get("id") is None:
                        pending_folders.append(path)
                    else:
                        actual_paths.add(path)

                if len(batch) < 100:
                    break

                offset += 100

        return actual_paths == expected_paths

    except Exception as exc:
        print(
            f"STORAGE CHECK ERROR {application_id}: "
            f"{type(exc).__name__}"
        )
        return False


def main():
    # Safety lock: LIVE deletion is disabled.
    if os.getenv(
        "RETENTION_DELETE_ENABLED", "false"
    ).lower() == "true":
        raise RuntimeError(
            "LIVE deletion is disabled until safety testing is complete."
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

    recordings_by_id = {}
    path_counts = Counter()

    for row in recordings:
        aid = row["application_id"]
        recordings_by_id.setdefault(aid, []).append(row)

        path = row.get("storage_path")

        if isinstance(path, str):
            path_counts[path] += 1

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

        job_status = jobs_by_id.get(aid)

        if job_status is not None:
            existing_jobs += 1
            print(f"EXISTING JOB {aid}: {job_status}")
            continue

        if assessment_counts[aid] != 1:
            review += 1
            print(f"REVIEW {aid}: assessment count")
            continue

        assessment = assessments_by_id[aid]

        if assessment["final_decision"] != "rejected":
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

        tasks = {
            (row["recording_type"], row["task_number"])
            for row in rows
        }

        paths = [
            row.get("storage_path")
            for row in rows
        ]

        valid = (
            len(rows) == 7
            and tasks == EXPECTED
            and len(set(paths)) == 7
            and all(
                isinstance(path, str)
                and path.startswith(f"{aid}/")
                and ".." not in path
                and path_counts[path] == 1
                for path in paths
            )
        )

        if not valid:
            review += 1
            print(f"REVIEW {aid}: invalid recordings")
            continue

        if not verify_storage_files(db, aid, rows):
            review += 1
            print(f"REVIEW {aid}: storage mismatch")
            continue

        eligible += 1
        print(f"ELIGIBLE {aid}: storage verified")

    print("----- RETENTION SUMMARY -----")
    print(f"Eligible: {eligible}")
    print(f"Protected: {protected}")
    print(f"Needs Manual Review: {review}")
    print(f"Existing Retention Jobs: {existing_jobs}")
    print("Deleted: 0")
    print(f"Errors: {errors}")
    print("MODE: DRY RUN")


if __name__ == "__main__":
    main()
