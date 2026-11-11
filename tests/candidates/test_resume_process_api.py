"""Resume extraction and PII-stripping endpoint and task (REQ-FR-011, REQ-FR-012, REQ-FR-057, batches 2.4, 2.9).

Two halves, following the scan batch's split:

* **task** — `process_resume` called directly with a real synthetic PDF written
  into the test storage: success (sanitised text persisted in `extracted_text`,
  SHA-256 of raw text in `raw_text_hash`, and one `resume.pii_stripped`
  `AuditLogEntry` with category counts and zero PII), planted-PII leak test,
  each failure code, the read-error path and the idempotency guard;
* **endpoint** — `POST /api/v1/candidates/resumes/{id}/process/`: ownership,
  the idempotent responses, the 409 for a non-processable state, and the
  queue-failure revert.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from kombu.exceptions import OperationalError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from candidates.models import CandidateProfile, CandidateResume
from candidates.tasks import RESUME_PII_STRIPPED_ACTION, process_resume
from core.models import AuditLogEntry

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures("resume_storage"),
]

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "resumes"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def build_pdf_bytes(lines: list[str]) -> bytes:
    """Build a minimal valid 1-page PDF containing ``lines`` in Helvetica."""
    cmds = ["BT", "/F1 11 Tf", "50 740 Td"]
    for idx, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if idx > 0:
            cmds.append("0 -16 Td")
        cmds.append(f"({escaped}) Tj")
    cmds.append("ET")
    stream = "\n".join(cmds).encode("latin-1")
    objs = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        ),
        (
            f"4 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream\nendobj\n"
        ),
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for obj in objs:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode("latin-1"))
    for off in offsets:
        out.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
    out.extend(
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(
            "latin-1"
        )
    )
    return bytes(out)


def api_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


def process_url(resume) -> str:
    return f"/api/v1/candidates/resumes/{resume.id}/process/"


@pytest.fixture
def profile(make_user):
    user = make_user("candidate")
    return CandidateProfile.objects.create(user=user)


@pytest.fixture
def resume(profile):
    return CandidateResume.objects.create(
        candidate=profile,
        file_key=f"resumes/{profile.id}/0123456789abcdef0123456789abcdef.pdf",
        original_filename="Ada Lovelace CV.pdf",
        file_size=2048,
        mime_type="application/pdf",
        status=CandidateResume.Status.CLEAN,
    )


@pytest.fixture
def queued(monkeypatch):
    """Record `process_resume.delay` calls; never contact the broker."""
    calls = []
    monkeypatch.setattr(
        "candidates.services.process_resume.delay",
        lambda resume_id: calls.append(resume_id),
    )
    return calls


class TestTask:
    def test_success_persists_sanitised_text_and_writes_audit_entry(
        self, resume, put_object
    ):
        put_object(resume.file_key, fixture_bytes("simple_text.pdf"))
        resume.status = CandidateResume.Status.PROCESSING
        resume.save(update_fields=["status"])

        ret = process_resume(str(resume.id))

        assert ret is None
        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.EXTRACTED
        assert resume.status_reason == ""
        assert resume.raw_text_hash
        assert len(resume.raw_text_hash) == 64
        assert "Backend Developer" in resume.extracted_text
        assert "Python, Django, PostgreSQL, Docker" in resume.extracted_text
        assert "Backend" not in resume.status_reason

        entries = AuditLogEntry.objects.filter(
            action=RESUME_PII_STRIPPED_ACTION,
            resource_id=resume.id,
        )
        assert entries.count() == 1
        entry = entries.first()
        assert entry is not None
        assert entry.actor_id == resume.candidate.user_id
        assert entry.resource_type == "candidate_resume"
        assert entry.result == "success"
        assert entry.details["raw_text_hash"] == resume.raw_text_hash
        assert isinstance(entry.details["counts"], dict)
        assert entry.details["total_redactions"] == sum(
            entry.details["counts"].values()
        )

    def test_planted_pii_markers_never_appear_in_db_logs_audit_or_task_result(
        self, profile, resume, put_object, caplog
    ):
        profile.user.first_name = "Tanvir"
        profile.user.last_name = "MarkerName991"
        profile.user.save(update_fields=["first_name", "last_name"])
        profile.location = "BananiMarker991"
        profile.save(update_fields=["location"])

        planted_markers = [
            "MarkerName991",
            "tanvir.marker991@example.com",
            "+880 1711-991882",
            "19952699918827766",
            "14 June 1995",
            "BananiMarker991",
            "tanvir-marker991",
            "tanvir_marker991_headshot.jpg",
            "North South University",
            "bKash Limited",
        ]
        pdf_bytes = build_pdf_bytes(
            [
                "Tanvir MarkerName991 | ![Photo](tanvir_marker991_headshot.jpg)",
                "Email: tanvir.marker991@example.com | Phone: +880 1711-991882",
                "Address: House 14, Road 7, BananiMarker991, Dhaka-1213",
                "NID: 19952699918827766 | DOB: 14 June 1995",
                "LinkedIn: https://linkedin.com/in/tanvir-marker991",
                "Education: B.Sc. in Computer Science from North South University. Graduated in 2019.",
                "Experience: Senior Backend Engineer at bKash Limited (2021 - 2025) for 4 years.",
                "Skills: Python, Django, PostgreSQL, Docker, Celery, Redis.",
            ]
        )
        put_object(resume.file_key, pdf_bytes)
        resume.status = CandidateResume.Status.PROCESSING
        resume.save(update_fields=["status"])

        with caplog.at_level(logging.DEBUG):
            task_result = process_resume(str(resume.id))

        # 1. Celery task result is None
        assert task_result is None

        # 2. CandidateResume columns carry sanitised placeholders + keep-set, zero markers
        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.EXTRACTED
        for marker in planted_markers:
            assert marker not in resume.extracted_text
            assert marker not in resume.status_reason
            assert marker not in resume.raw_text_hash
            assert marker not in resume.file_key

        for placeholder in (
            "[CANDIDATE_NAME]",
            "[CANDIDATE_EMAIL]",
            "[CANDIDATE_PHONE]",
            "[CANDIDATE_LOCATION]",
            "[NATIONAL_ID]",
            "[DATE]",
            "[URL]",
            "[PHOTO]",
            "[INSTITUTION]",
            "[EMPLOYER]",
        ):
            assert placeholder in resume.extracted_text

        for keep_span in (
            "B.Sc. in Computer Science",
            "Senior Backend Engineer",
            "4 years",
            "Python",
            "Django",
            "PostgreSQL",
        ):
            assert keep_span in resume.extracted_text

        # 3. AuditLogEntry holds category counts and raw_text_hash, zero markers or text
        entries = list(
            AuditLogEntry.objects.filter(
                action=RESUME_PII_STRIPPED_ACTION,
                resource_id=resume.id,
            )
        )
        assert len(entries) == 1
        audit = entries[0]
        audit_blob = json.dumps(
            {
                "action": audit.action,
                "resource_type": audit.resource_type,
                "result": audit.result,
                "details": audit.details,
            }
        )
        for marker in planted_markers:
            assert marker not in audit_blob

        counts = audit.details["counts"]
        for cat in (
            "name",
            "email",
            "phone",
            "address",
            "national_id",
            "age_date",
            "url",
            "photo",
            "institution",
            "employer",
        ):
            assert counts[cat] >= 1, f"expected redaction count >= 1 for {cat}"
        assert audit.details["total_redactions"] >= 10

        # 4. Captured log records contain zero planted PII markers
        for marker in planted_markers:
            assert marker not in caplog.text
            for record in caplog.records:
                assert marker not in record.getMessage()

    def test_a_scan_without_text_fails_with_the_code(self, resume, put_object):
        put_object(resume.file_key, fixture_bytes("scanned_no_text.pdf"))
        resume.status = CandidateResume.Status.PROCESSING
        resume.save(update_fields=["status"])

        process_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.FAILED
        assert resume.status_reason == "no_text_layer"

    def test_a_password_protected_pdf_fails_with_the_code(self, resume, put_object):
        put_object(resume.file_key, fixture_bytes("encrypted.pdf"))
        resume.status = CandidateResume.Status.PROCESSING
        resume.save(update_fields=["status"])

        process_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.FAILED
        assert resume.status_reason == "password_protected"

    def test_an_unreadable_object_fails_with_the_reason(self, resume):
        # No object written at the key: the storage read fails before extraction.
        resume.status = CandidateResume.Status.PROCESSING
        resume.save(update_fields=["status"])

        process_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.FAILED
        assert resume.status_reason == "stored file could not be read"

    def test_is_idempotent_after_extracted(self, resume, put_object):
        put_object(resume.file_key, fixture_bytes("simple_text.pdf"))
        resume.status = CandidateResume.Status.PROCESSING
        resume.save(update_fields=["status"])
        process_resume(str(resume.id))
        resume.refresh_from_db()
        original_hash = resume.raw_text_hash

        # A duplicated delivery after success must not re-extract, overwrite, or double-audit.
        process_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.EXTRACTED
        assert resume.raw_text_hash == original_hash
        assert (
            AuditLogEntry.objects.filter(
                action=RESUME_PII_STRIPPED_ACTION,
                resource_id=resume.id,
            ).count()
            == 1
        )

    def test_is_a_noop_outside_processing(self, resume, put_object):
        put_object(resume.file_key, fixture_bytes("simple_text.pdf"))

        process_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.CLEAN
        assert resume.raw_text_hash == ""


class TestEndpoint:
    def test_a_clean_resume_moves_to_processing_and_queues(
        self, profile, resume, queued
    ):
        response = api_client(profile.user).post(process_url(resume))

        assert response.status_code == 202
        assert response.data["status"] == CandidateResume.Status.PROCESSING
        assert queued == [str(resume.id)]
        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.PROCESSING

    @pytest.mark.parametrize(
        "state",
        [
            CandidateResume.Status.EXTRACTED,
            CandidateResume.Status.EMBEDDED,
        ],
    )
    def test_an_already_finished_resume_is_200_and_not_requeued(
        self, profile, resume, queued, state
    ):
        resume.status = state
        resume.save(update_fields=["status"])

        response = api_client(profile.user).post(process_url(resume))

        assert response.status_code == 200
        assert response.data["status"] == state
        assert queued == []

    def test_an_in_flight_resume_is_202_and_not_requeued(self, profile, resume, queued):
        resume.status = CandidateResume.Status.PROCESSING
        resume.save(update_fields=["status"])

        response = api_client(profile.user).post(process_url(resume))

        assert response.status_code == 202
        assert queued == []

    @pytest.mark.parametrize(
        "state",
        [
            CandidateResume.Status.PENDING,
            CandidateResume.Status.UPLOADED,
            CandidateResume.Status.SCANNING,
            CandidateResume.Status.REJECTED,
        ],
    )
    def test_a_non_processable_state_is_409(self, profile, resume, queued, state):
        resume.status = state
        resume.save(update_fields=["status"])

        response = api_client(profile.user).post(process_url(resume))

        assert response.status_code == 409
        assert response.data["status"] == state
        assert queued == []

    def test_a_failed_resume_can_be_retried(self, profile, resume, queued):
        resume.status = CandidateResume.Status.FAILED
        resume.status_reason = "no_text_layer"
        resume.save(update_fields=["status", "status_reason"])

        response = api_client(profile.user).post(process_url(resume))

        assert response.status_code == 202
        assert queued == [str(resume.id)]
        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.PROCESSING
        assert resume.status_reason == ""

    def test_a_queue_failure_reverts_to_the_previous_state(
        self, profile, resume, monkeypatch
    ):
        def broker_down(_resume_id):
            raise OperationalError("broker down")

        monkeypatch.setattr("candidates.services.process_resume.delay", broker_down)

        response = api_client(profile.user).post(process_url(resume))

        assert response.status_code == 503
        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.CLEAN

    def test_anonymous_is_401(self, resume):
        assert APIClient().post(process_url(resume)).status_code == 401

    @pytest.mark.parametrize("role", ["employer_hr", "employer_manager", "interviewer"])
    def test_a_non_candidate_role_is_403(self, make_user, resume, role):
        response = api_client(make_user(role)).post(process_url(resume))
        assert response.status_code == 403

    def test_another_candidate_is_404(self, make_user, resume):
        other = CandidateProfile.objects.create(user=make_user("candidate"))
        assert other.id != resume.candidate.id

        response = api_client(other.user).post(process_url(resume))

        assert response.status_code == 404
