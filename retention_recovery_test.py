
"""LOVINITY ENGLISH - Retention recovery simulation.

No Supabase connection, credentials, network calls, or real file deletion.
Run: python retention_recovery_test.py
"""

from uuid import uuid4

EXPECTED_FILES = (
    "pronunciation_1.wav",
    "pronunciation_2.wav",
    "pronunciation_3.wav",
    "speaking_1.wav",
    "speaking_2.wav",
    "speaking_3.wav",
    "teaching_demo_1.wav",
)


def expected_paths(application_id):
    return {
        f"{application_id}/{filename}"
        for filename in EXPECTED_FILES
    }


def resume_cleanup(application_id, remaining_files, allowed_files):
    """Simulate deletion, rejecting files outside the approved set."""
    if not remaining_files.issubset(allowed_files):
        raise ValueError("Unexpected file detected: cleanup stopped")

    for path in sorted(remaining_files):
        if not path.startswith(f"{application_id}/"):
            raise ValueError("Application folder mismatch")
        remaining_files.remove(path)

    return len(remaining_files) == 0


def run_tests():
    applicant_a = str(uuid4())
    applicant_b = str(uuid4())

    files_a = expected_paths(applicant_a)
    files_b = expected_paths(applicant_b)

    # Test 1: simulate interruption after three deletions
    remaining_a = set(files_a)
    for path in sorted(files_a)[:3]:
        remaining_a.remove(path)

    assert len(remaining_a) == 4
    print("PASS 1: Interrupted after 3 of 7 files")

    # Test 2: resume and delete the four remaining files
    assert resume_cleanup(applicant_a, remaining_a, files_a)
    assert len(remaining_a) == 0
    print("PASS 2: Remaining 4 files cleaned up")

    # Test 3: another applicant's files remain untouched
    assert len(files_b) == 7
    assert files_a.isdisjoint(files_b)
    print("PASS 3: Other applicant protected")

    # Test 4: reject unexpected files
    unexpected = {f"{applicant_a}/unknown.wav"}
    try:
        resume_cleanup(applicant_a, unexpected, files_a)
    except ValueError:
        assert len(unexpected) == 1
        print("PASS 4: Unexpected file blocked")
    else:
        raise AssertionError("Unexpected file was not blocked")

    print()
    print("ALL SIMULATION TESTS PASSED")
    print("No real files or database records were modified.")


if __name__ == "__main__":
    run_tests()
