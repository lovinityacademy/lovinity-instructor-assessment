
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

from supabase import create_client

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
        batch = (
            db.table(table)
            .select(columns)
            .order("id" if table == "instructor_applications"
                   else "application_id")
            .range(offset, offset + 999)
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


def main():
    # Safety lock: LIVE deletion remains disabled.
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
        "id,decided_at"
    )

    assessments = fetch_all(
        db,
        "instructor_assessments",
        "application_id,final_decision"
    )

    recordings = fetch_all(
        db,
        "instructor_recordings",
        "application_id,recording_type,task_number,storage_path"
    )

    jobs = fetch_all(
        db,
        "instructor_retention_jobs",
        "application_id,status"
    )

    assessment_counts = Counter(
        a["application_id"] for a in assessments
    )

    assessments_by_id = {
        a["application_id"]: a
        for a in assessments
    }

    recordings_by_id = {}
    path_counts = Counter()

    for row in recordings:
        aid = row["application_id"]
        recordings_by_id.setdefault(aid, []).append(row)
        path_counts[row["storage_path"]] += 1

    jobs_by_id = {
        j["application_id"]: j["status"]
        for j in jobs
    }

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    eligible = 0
    protected = 0
    review = 0
    existing_jobs = 0

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

        tasks = {
            (r["recording_type"], r["task_number"])
            for r in rows
        }

        paths = [r["storage_path"] for r in rows]

        valid = (
            len(rows) == 7
            and tasks == EXPECTED
            and len(set(paths)) == 7
            and all(
                isinstance(p, str)
                and p.startswith(f"{aid}/")
                and ".." not in p
                and path_counts[p] == 1
                for p in paths
            )
        )

        if not valid:
            review += 1
            print(f"REVIEW {aid}: invalid recordings")
            continue

        eligible += 1
        print(f"ELIGIBLE {aid}")

    print("----- RETENTION SUMMARY -----")
    print(f"Eligible: {eligible}")
    print(f"Protected: {protected}")
    print(f"Needs Manual Review: {review}")
    print(f"Existing Retention Jobs: {existing_jobs}")
    print("Deleted: 0")
    print("Errors: 0")
    print("MODE: DRY RUN")


if __name__ == "__main__":
    main()
