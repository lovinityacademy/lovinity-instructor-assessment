"""LOVINITY retention final safety check. No database writes."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def check():
    auditor = ROOT / "retention_cleanup.py"
    candidate = ROOT / ".github/workflows/retention_worker_candidate.py"
    workflow = ROOT / ".github/workflows/retention_cleanup.yml"

    for path in (auditor, candidate, workflow):
        assert path.is_file(), f"Missing: {path}"

    audit_source = auditor.read_text(encoding="utf-8")
    candidate_source = candidate.read_text(encoding="utf-8")
    workflow_source = workflow.read_text(encoding="utf-8")

    ast.parse(audit_source)
    ast.parse(candidate_source)

    assert 'RETENTION_DELETE_ENABLED: "false"' in workflow_source
    assert "python retention_cleanup.py" in workflow_source
    assert "RETENTION_TEST_APPLICATION_ID" in candidate_source
    assert "RETENTION_TEST_CONFIRM" in candidate_source
    assert "RETENTION_SYNTHETIC_TEST_ONLY" in candidate_source
    assert "retention-test@example.invalid" in candidate_source

    print("PASS: Required files exist")
    print("PASS: Python syntax valid")
    print("PASS: Scheduled deletion disabled")
    print("PASS: Synthetic-only confirmation markers present")
    print("NO DATABASE OR STORAGE DATA MODIFIED")
    print("STATIC SAFETY CHECK PASSED")

if __name__ == "__main__":
    check()
