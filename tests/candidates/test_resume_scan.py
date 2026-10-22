"""The ClamAV scan task (REQ-SEC-012, gap P, batch 1.20).

Two kinds of test:

* **unit** — the task's decisions with `scan_stream` stubbed: clean, malware,
  daemon down, unreadable object, and the idempotency guard;
* **integration** — the real clamd service from `docker compose`/CI, including
  the EICAR test file. These skip when the daemon is unreachable, because a skip
  says "not exercised", which is true, while passing would be a lie.

The rule under test is fail-closed: only an explicit OK from clamd produces
`clean`; a missing file, an unreachable daemon and a signature match all end in
`rejected` with a reason.
"""

from __future__ import annotations

import io

import pytest

from candidates import scanner
from candidates.models import CandidateProfile, CandidateResume
from candidates.scanner import MalwareDetected, ScanUnavailable
from candidates.tasks import scan_resume

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures("resume_storage"),
]

PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
)

# The standard 68-byte antivirus test string. It is not malware; ClamAV ships a
# signature for it so that an end-to-end scan can be proved without a sample.
EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


@pytest.fixture
def profile(make_user):
    return CandidateProfile.objects.create(user=make_user("candidate"))


@pytest.fixture
def resume(profile):
    return CandidateResume.objects.create(
        candidate=profile,
        file_key=f"resumes/{profile.id}/0123456789abcdef0123456789abcdef.pdf",
        original_filename="Ada Lovelace CV.pdf",
        file_size=2048,
        mime_type="application/pdf",
        status=CandidateResume.Status.SCANNING,
    )


@pytest.fixture
def clamd():
    """Skip when no daemon is reachable; CI and Compose both provide one."""
    try:
        scanner.scan_stream(io.BytesIO(b"clean"))
    except scanner.ScanUnavailable:
        pytest.skip("ClamAV is not reachable at CLAMD_HOST:CLAMD_PORT")


class TestUnit:
    def test_an_ok_from_clamd_marks_the_resume_clean(
        self, resume, put_object, monkeypatch
    ):
        put_object(resume.file_key, PDF)
        monkeypatch.setattr("candidates.tasks.scan_stream", lambda handle: None)

        scan_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.CLEAN
        assert resume.status_reason == ""

    def test_a_signature_match_rejects_and_discards_the_bytes(
        self, resume, put_object, monkeypatch, resume_storage
    ):
        put_object(resume.file_key, PDF)

        def infected(_handle):
            raise MalwareDetected("Eicar-Test-Signature")

        monkeypatch.setattr("candidates.tasks.scan_stream", infected)

        scan_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.REJECTED
        assert resume.status_reason == "malware detected: Eicar-Test-Signature"
        assert not (resume_storage / resume.file_key).exists()

    def test_an_unreachable_daemon_rejects_rather_than_passing(
        self, resume, put_object, monkeypatch, resume_storage
    ):
        put_object(resume.file_key, PDF)

        def down(_handle):
            raise ScanUnavailable("antivirus unavailable")

        monkeypatch.setattr("candidates.tasks.scan_stream", down)

        scan_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.REJECTED
        assert resume.status_reason == "antivirus unavailable"
        assert not (resume_storage / resume.file_key).exists()

    def test_an_unreadable_object_is_rejected(self, resume, monkeypatch):
        def should_not_run(_handle):
            raise AssertionError("scan_stream must not run without bytes")

        monkeypatch.setattr("candidates.tasks.scan_stream", should_not_run)

        scan_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.REJECTED
        assert resume.status_reason == "stored file could not be read"

    def test_a_resume_that_is_not_scanning_is_left_alone(
        self, resume, put_object, monkeypatch
    ):
        resume.status = CandidateResume.Status.PENDING
        resume.save(update_fields=["status"])
        put_object(resume.file_key, PDF)

        def should_not_run(_handle):
            raise AssertionError("a pending resume is not ready to scan")

        monkeypatch.setattr("candidates.tasks.scan_stream", should_not_run)

        scan_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.PENDING

    def test_a_clean_verdict_is_not_overwritten_by_a_retry(
        self, resume, put_object, monkeypatch
    ):
        resume.status = CandidateResume.Status.CLEAN
        resume.save(update_fields=["status"])
        put_object(resume.file_key, PDF)

        def infected(_handle):
            raise MalwareDetected("should not run")

        monkeypatch.setattr("candidates.tasks.scan_stream", infected)

        scan_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.CLEAN
        assert resume.status_reason == ""

    def test_an_unknown_id_is_a_no_op(self):
        scan_resume("00000000-0000-0000-0000-000000000000")

    def test_a_malformed_id_is_a_no_op(self, resume):
        scan_resume("not-a-uuid")

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.SCANNING


class TestRealClamAV:
    def test_a_clean_pdf_is_marked_clean(self, resume, put_object, clamd):
        put_object(resume.file_key, PDF)

        scan_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.CLEAN
        assert resume.status_reason == ""

    def test_the_eicar_test_file_is_rejected(self, resume, put_object, clamd):
        assert len(EICAR) == 68
        # Stored bare on purpose. clamd does not report the test string when it
        # is appended after a PDF trailer, and the task must reject whatever the
        # daemon flags rather than assume a type.
        put_object(resume.file_key, EICAR)

        scan_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.REJECTED
        assert resume.status_reason.startswith("malware detected:")
        assert "eicar" in resume.status_reason.lower()
