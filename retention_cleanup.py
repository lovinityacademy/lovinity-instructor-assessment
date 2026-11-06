"""LOVINITY ENGLISH retention auditor. READ ONLY / DRY RUN ONLY.

This script deliberately contains no delete, insert, update, or RPC calls.
It does not resume existing jobs. It never changes Supabase state.
"""
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from supabase import create_client

BUCKET = 'instructor-recordings'
TASKS = {('pronunciation', 1), ('pronunciation', 2), ('pronunciation', 3),
         ('speaking', 1), ('speaking', 2), ('speaking', 3), ('teaching_demo', 1)}
ACTIVE = {'pending', 'processing', 'storage_deleted', 'error'}
KNOWN = ACTIVE | {'completed'}


def fetch_all(db, table, columns):
    rows, offset = [], 0
    while True:
        query = db.table(table).select(columns)
        if table == 'instructor_applications':
            query = query.order('id')
        elif table == 'instructor_recordings':
            query = query.order('application_id').order('id')
        else:
            query = query.order('application_id')
        batch = query.range(offset, offset + 999).execute().data or []
        rows.extend(batch)
        if len(batch) < 1000:
            return rows
        offset += 1000


def date_utc(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None


def verify_metadata(aid, rows, global_paths):
    if len(rows) != 7:
        return False, 'recording count != 7'
    tasks = set()
    for r in rows:
        task = (r.get('recording_type'), r.get('task_number'))
        if task not in TASKS or task in tasks:
            return False, 'invalid or duplicate task'
        tasks.add(task)
        expected = f'{aid}/{task[0]}_{task[1]}.wav'
        if r.get('storage_path') != expected:
            return False, 'noncanonical .wav path'
        if global_paths[expected] != 1:
            return False, 'duplicate path across database'
    return (tasks == TASKS, 'valid' if tasks == TASKS else 'missing task')


def list_storage(db, aid):
    """Enumerate recursively; reject duplicate/ambiguous listings."""
    bucket = db.storage.from_(BUCKET)
    pending, seen_folders, files = [aid], set(), set()
    while pending:
        folder = pending.pop()
        if folder in seen_folders:
            raise RuntimeError('repeated folder')
        seen_folders.add(folder)
        offset = 0
        while True:
            batch = bucket.list(folder, {'limit': 100, 'offset': offset})
            if not isinstance(batch, list) or len(batch) > 100:
                raise RuntimeError('invalid Storage listing')
            for item in batch:
                if not isinstance(item, dict):
                    raise RuntimeError('invalid Storage item')
                name = item.get('name')
                if not isinstance(name, str) or not name or name in ('.', '..') or '/' in name:
                    raise RuntimeError('invalid Storage item name')
                path = f'{folder}/{name}'
                if item.get('id') is None:
                    pending.append(path)
                else:
                    if path in files:
                        raise RuntimeError('duplicate Storage file')
                    files.add(path)
            if len(batch) < 100:
                break
            offset += 100
    return files


def main():
    if os.getenv('RETENTION_DELETE_ENABLED', 'false').strip().lower() != 'false':
        raise RuntimeError('Safety lock: RETENTION_DELETE_ENABLED must be false')
    db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    apps = fetch_all(db, 'instructor_applications', 'id,decided_at')
    assessments = fetch_all(db, 'instructor_assessments', 'application_id,final_decision')
    recordings = fetch_all(db, 'instructor_recordings',
                           'id,application_id,recording_type,task_number,storage_path')
    jobs = fetch_all(db, 'instructor_retention_jobs', 'application_id,status,last_error,attempt_count')

    assessment_counts = Counter(x['application_id'] for x in assessments)
    assessment_by_id = {x['application_id']: x for x in assessments}
    rec_by_id = defaultdict(list)
    path_counts = Counter()
    for r in recordings:
        rec_by_id[r['application_id']].append(r)
        if isinstance(r.get('storage_path'), str):
            path_counts[r['storage_path']] += 1
    job_by_id = {x['application_id']: x for x in jobs}
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    counts = Counter()
    errors = 0

    for app in apps:
        aid = app['id']
        job = job_by_id.get(aid)
        if job is not None:
            counts['Existing Retention Jobs'] += 1
            status = job.get('status')
            print(f'EXISTING JOB {aid}: {status} (manual review; no resume)')
            if status not in KNOWN or status in ACTIVE:
                errors += 1
            continue
        if assessment_counts[aid] != 1:
            counts['Needs Manual Review'] += 1
            print(f'REVIEW {aid}: assessment count')
            continue
        if assessment_by_id[aid].get('final_decision') != 'rejected':
            counts['Protected'] += 1
            continue
        decided = date_utc(app.get('decided_at'))
        if decided is None:
            counts['Needs Manual Review'] += 1
            print(f'REVIEW {aid}: invalid decision date')
            continue
        if decided > cutoff:
            counts['Protected'] += 1
            continue
        rows = rec_by_id.get(aid, [])
        valid, reason = verify_metadata(aid, rows, path_counts)
        if not valid:
            counts['Needs Manual Review'] += 1
            print(f'REVIEW {aid}: {reason}')
            continue
        try:
            actual = list_storage(db, aid)
        except Exception as exc:
            errors += 1
            print(f'ERROR {aid}: Storage listing failed ({type(exc).__name__})')
            continue
        expected = {r['storage_path'] for r in rows}
        if actual != expected:
            counts['Needs Manual Review'] += 1
            print(f'REVIEW {aid}: Storage mismatch (expected={len(expected)}, actual={len(actual)})')
            continue
        counts['Eligible'] += 1
        print(f'ELIGIBLE {aid}: seven files verified; SIMULATED ONLY')
        print(f'  WOULD reserve job -> verify eligibility again -> remove 7 Storage files')
        print(f'  WOULD confirm absence -> mark storage_deleted -> delete DB rows')
        print(f'  ON FAILURE: stop, record error, manually inspect before retry')

    orphan_jobs = set(job_by_id) - {x['id'] for x in apps}
    if orphan_jobs:
        errors += len(orphan_jobs)
        print(f'ERROR: {len(orphan_jobs)} job(s) without application')
    print('----- RETENTION SUMMARY -----')
    for label in ('Eligible', 'Protected', 'Needs Manual Review', 'Existing Retention Jobs'):
        print(f'{label}: {counts[label]}')
    print('Deleted: 0')
    print(f'Errors: {errors}')
    print('MODE: DRY RUN')
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
