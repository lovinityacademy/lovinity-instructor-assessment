
import os
from datetime import datetime, timedelta, timezone
from supabase import create_client

DRY_RUN = os.getenv("RETENTION_DELETE_ENABLED", "false").lower() != "true"


def fetch_all(client, table, columns="*"):
    rows = []
    start = 0
    while True:
        batch = (
            client.table(table)
            .select(columns)
            .range(start, start + 999)
            .execute()
            .data or []
        )
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
        start += 1000


def main():
    if not DRY_RUN:
        raise RuntimeError(
            "Live deletion is not enabled in this audit version. "
            "Keep RETENTION_DELETE_ENABLED=false."
        )

    db = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    print("MODE: DRY RUN - no data will be deleted", flush=True)

    applications = fetch_all(
        db, "instructor_applications", "id,decided_at"
    )
    assessments = fetch_all(
        db, "instructor_assessments",
        "application_id,final_decision"
    )
    recordings = fetch_all(
        db, "instructor_recordings",
        "application_id,recording_type,task_number,storage_path"
    )

    print(
        f"Loaded {len(applications)} applications, "
        f"{len(assessments)} assessments, "
        f"{len(recordings)} recording records",
        flush=True,
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    expected_tasks = (
        {("pronunciation", n) for n in (1, 2, 3)}
        | {("speaking", n) for n in (1, 2, 3)}
        | {("teaching_demo", 1)}
    )

    eligible = 0
    protected = 0
    manual_review = 0

    for app in applications:
        aid = app["id"]
        ass = [
            a for a in assessments
            if a["application_id"] == aid
        ]

        if len(ass) != 1:
            manual_review += 1
            print(f"MANUAL REVIEW: {aid} - assessment count")
            continue

        if ass[0]["final_decision"] != "rejected":
            protected += 1
            continue

        decided_at = app.get("decided_at")
        if not decided_at:
            manual_review += 1
            print(f"MANUAL REVIEW: {aid} - missing decision date")
            continue

        decided = datetime.fromisoformat(
            decided_at.replace("Z", "+00:00")
        )

        if decided.tzinfo is None:
            manual_review += 1
            continue

        if decided > cutoff:
            protected += 1
            continue

        rows = [
            r for r in recordings
            if r["application_id"] == aid
        ]
        tasks = {
            (r["recording_type"], r["task_number"])
            for r in rows
        }
        paths = [r.get("storage_path") for r in rows]

        valid = (
            len(rows) == 7
            and tasks == expected_tasks
            and all(isinstance(p, str) for p in paths)
            and len(set(paths)) == 7
            and all(
                p.startswith(f"{aid}/") and ".." not in p
                for p in paths
            )
            and not any(
                r["application_id"] != aid
                and r.get("storage_path") in paths
                for r in recordings
            )
        )

        if not valid:
            manual_review += 1
            print(f"MANUAL REVIEW: {aid} - recording validation")
            continue

        eligible += 1
        print(f"ELIGIBLE: {aid} - rejected over 90 days ago")

    print("----- RETENTION AUDIT SUMMARY -----")
    print(f"Eligible: {eligible}")
    print(f"Protected: {protected}")
    print(f"Needs Manual Review: {manual_review}")
    print("DRY RUN COMPLETE - NOTHING DELETED")


if __name__ == "__main__":
    main()

