"""LOVINITY retention worker candidate. SAFE BY DEFAULT.

Requires Supabase Python client >=2,<3 and existing database RPCs.
This is NOT a production-approved deletion worker. It only performs reads unless
RETENTION_DELETE_ENABLED=true AND RETENTION_TEST_APPLICATION_ID=<UUID> AND
RETENTION_TEST_CONFIRM=DELETE_SYNTHETIC_ONLY. It never processes other IDs in
write mode. Do not put the three enabling values in a scheduled workflow.
"""
import os
import sys
from uuid import UUID
from datetime import datetime, timezone, timedelta
from supabase import create_client

BUCKET = 'instructor-recordings'
FILES = tuple([f'pronunciation_{n}.wav' for n in (1,2,3)] +
              [f'speaking_{n}.wav' for n in (1,2,3)] + ['teaching_demo_1.wav'])


def fail(message):
    raise RuntimeError(message)


def response_data(response):
    return response.data or []


def exact_paths(uid):
    return {f'{uid}/{name}' for name in FILES}


def storage_names(bucket, uid):
    # Fail closed on nested directories and unexpected files.
    entries = bucket.list(uid, {'limit': 1000}) or []
    names = set()
    for entry in entries:
        name = entry.get('name')
        if not name or name in names:
            fail('Invalid or duplicate Storage listing')
        names.add(name)
    if len(entries) >= 1000:
        fail('Storage listing may be truncated')
    return names


def validate_recordings(db, uid):
    records = response_data(db.table('instructor_recordings').select(
        'recording_type,task_number,storage_path').eq('application_id', uid).execute())
    if len(records) != 7:
        fail('Expected exactly 7 recording rows')
    paths = [r['storage_path'] for r in records]
    if len(set(paths)) != 7 or set(paths) != exact_paths(uid):
        fail('Recording paths do not match exact 7-file allowlist')


def check_application(db, uid):
    apps = response_data(db.table('instructor_applications').select(
        'id,status,decided_at,applicant_name,applicant_email').eq('id',uid).execute())
    if len(apps) != 1 or apps[0]['status'] != 'rejected':
        fail('Application not uniquely rejected')
    decided = apps[0].get('decided_at')
    if not decided:
        fail('No decided_at')
    dt = datetime.fromisoformat(decided.replace('Z','+00:00'))
    if dt.tzinfo is None or dt > datetime.now(timezone.utc)-timedelta(days=90):
        fail('Not yet 90 days after decision')
    assessments = response_data(db.table('instructor_assessments').select(
        'id,final_decision').eq('application_id',uid).execute())
    if len(assessments) != 1 or assessments[0]['final_decision'] != 'rejected':
        fail('Assessment is not uniquely rejected')
    validate_recordings(db, uid)


def process_one(db, uid):
    bucket = db.storage.from_(BUCKET)
    check_application(db, uid)
    jobs = response_data(db.table('instructor_retention_jobs').select(
        'status').eq('application_id',uid).execute())
    if len(jobs) > 1:
        fail('Duplicate retention jobs')
    status = jobs[0]['status'] if jobs else None
   
    if status is None:
        if storage_names(bucket, uid) != set(FILES):
            fail('Storage must contain exactly seven files before reservation')
        if db.rpc('reserve_expired_rejected_application', {'p_application_id':uid}).execute().data is not True:

            fail('Reservation rejected')
        status = 'pending'
    if status == 'pending':
        # Initial cleanup must start with exactly seven existing Storage files.
        if storage_names(bucket,uid) != set(FILES):
            fail('Initial Storage set is not exactly seven files')
        if db.rpc('start_retention_storage_cleanup', {'p_application_id':uid}).execute().data is not True:
            fail('Could not claim pending job')
        status = 'processing'
    if status == 'processing':
        # A partially completed cleanup can resume only with expected files.
        remaining = storage_names(bucket,uid)
        if not remaining.issubset(set(FILES)):
            fail('Unexpected Storage object; refusing deletion')
        check_application(db,uid)
        if remaining:
            paths = [f'{uid}/{name}' for name in sorted(remaining)]
            bucket.remove(paths)
        if storage_names(bucket,uid):
            fail('Storage not empty after removal')
        if db.rpc('mark_retention_storage_deleted', {'p_application_id':uid}).execute().data is not True:
            fail('Storage-deleted transition refused')
        status = 'storage_deleted'
    if status == 'storage_deleted':
        if storage_names(bucket,uid):
            fail('Storage contains objects; refusing DB deletion')
        check_application(db,uid)
        if db.rpc('delete_expired_rejected_application', {'p_application_id':uid}).execute().data is not True:
            fail('Database final deletion refused')
        print('SYNTHETIC APPLICATION DELETED:',uid)
        return
    fail('Unsupported job status: '+str(status))


def main():
    url = os.environ['SUPABASE_URL']
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    db = create_client(url,key)
    enabled = os.getenv('RETENTION_DELETE_ENABLED','false').lower() == 'true'
    uid = os.getenv('RETENTION_TEST_APPLICATION_ID','').strip()
    if not enabled:
        print('DRY RUN ONLY: no write calls; live deletion disabled')
        print('Use the existing retention_cleanup.py for the full read-only summary.')
        return
    if os.getenv('RETENTION_TEST_CONFIRM') != 'DELETE_SYNTHETIC_ONLY' or not uid:
        fail('Write mode requires synthetic-only confirmation and exact UUID')
    try:
        uid = str(UUID(uid))
    except ValueError:
        fail('Invalid test UUID')
    apps = response_data(db.table('instructor_applications').select(
        'applicant_name,applicant_email').eq('id',uid).execute())
    if len(apps) != 1 or apps[0].get('applicant_name') != 'RETENTION_SYNTHETIC_TEST_ONLY' or apps[0].get('applicant_email') != 'retention-test@example.invalid':
        fail('Synthetic identity marker absent; refusing all writes')
    print('SYNTHETIC-ONLY write scope:',uid)
    process_one(db,uid)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('STOPPED SAFELY:',str(exc),file=sys.stderr)
        sys.exit(1)
