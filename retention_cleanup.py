
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

from supabase import create_client

BUCKET = "instructor-recordings"
LIVE = os.getenv("RETENTION_DELETE_ENABLED", "false").lower() == "true"
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
    date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if date.tzinfo is None:
        return None
    return date


def main():
    db = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    print("MODE:", "LIVE" if LIVE else "DRY RUN", flush=True)

    apps = fetch_all(db, "instructor_applications", "id,decided_at")
    assessments = fetch_all(
        db, "instructor_assessments", "application_id,final_decision"
    )
    recordings = fetch_all(
        db,
        "instructor_recordings",
        "application_id,recording_type,task_number,storage_path",
    )

    assessment_counts = Counter(
        a["application_id"] for a in assessments
    )
    assessments_by_id = {
        a["application_id"]: a for a in assessments
    }

    recordings_by_id = {}
    path_counts = Counter()
    for row in recordings:
        aid = row["application_id"]
        recordings_by_id.setdefault(aid, []).append(row)
        if row.get("storage_path"):
            path_counts[row["storage_path"]] += 1

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    eligible = 0
    protected = 0
    review = 0
    deleted = 0
    errors = 0

    for app in apps:
        aid = app["id"]

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
            print(f"REVIEW {aid}: missing or invalid decision date")
            continue

        if decided > cutoff:
            protected += 1
            continue

        rows = recordings_by_id.get(aid, [])
        tasks = {
            (r["recording_type"], r["task_number"]) for r in rows
        }
        paths = [r.get("storage_path") for r in rows]

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
            print(f"REVIEW {aid}: invalid recording records")
            continue

        eligible += 1
        print(f"ELIGIBLE {aid}")

        if not LIVE:
            continue

        try:
            # Recheck the current decision before deleting anything.
            current_app = (
                db.table("instructor_applications")
                .select("decided_at")
                .eq("id", aid)
                .single()
                .execute()
                .data
            )
            current_assessments = (
                db.table("instructor_assessments")
                .select("final_decision")
                .eq("application_id", aid)
                .execute()
                .data or []
            )

            current_date = parse_date(current_app.get("decided_at"))
            if (
                len(current_assessments) != 1
                or current_assessments[0]["final_decision"] != "rejected"
                or current_date is None
                or current_date > datetime.now(timezone.utc)
                - timedelta(days=90)
            ):
                print(f"SKIP {aid}: decision changed")
                continue

            # Verify Storage contains exactly the expected seven files.
            objects = db.storage.from_(BUCKET).list(path=aid)
            found = {
                f"{aid}/{obj['name']}"
                for obj in objects
                if obj.get("name")
                and obj.get("id") is not None
            }

            if found != set(paths):
                print(f"REVIEW {aid}: Storage mismatch")
                review += 1
                continue

            # Remove recordings first.
            db.storage.from_(BUCKET).remove(paths)

            remaining = db.storage.from_(BUCKET).list(path=aid)
            remaining_files = [
                obj for obj in remaining if obj.get("id") is not None
            ]
            if remaining_files:
                raise RuntimeError("Storage files still exist")

            # Database deletion is performed by the guarded SQL function.
            result = db.rpc(
                "delete_expired_rejected_application",
                {"p_application_id": aid},
            ).execute()

            if result.data is not True:
                raise RuntimeError("Database deletion was not confirmed")

            deleted += 1
            print(f"DELETED {aid}")

        except Exception as exc:
            errors += 1
            print(f"ERROR {aid}: {type(exc).__name__}: {exc}")

    print("----- RETENTION SUMMARY -----")
    print(f"Eligible: {eligible}")
    print(f"Protected: {protected}")
    print(f"Needs Manual Review: {review}")
    print(f"Deleted: {deleted}")
    print(f"Errors: {errors}")
    print("MODE:", "LIVE" if LIVE else "DRY RUN")

    if errors:
        raise RuntimeError(f"{errors} cleanup operations failed")


if __name__ == "__main__":
    main()
