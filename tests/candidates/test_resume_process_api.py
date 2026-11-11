"""Resume extraction endpoint and task (REQ-FR-012, batch 2.4).

Two halves, following the scan batch's split:

* **task** — `process_resume` called directly with a real synthetic PDF written
  into the test storage: success, each failure code, the read-error path and the
  idempotency guard;
* **endpoint** — `POST /api/v1/candidates/resumes/{id}/process/`: ownership,
  the idempotent responses, the 409 for a non-processable state, and the
  queue-failure revert.

The rule under test that matters for privacy is that the **raw extracted text is
held in memory only**: after a success the row's `extracted_text` is still empty
(the PII-stripped text is batch 2.9's job) and no marker from the PDF reaches
`status_reason`. `raw_text_hash` holds only a SHA-256 digest.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from kombu.exceptions import OperationalError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from candidates.models import CandidateProfile, CandidateResume
from candidates.tasks import process_resume

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures("resume_storage"),
]

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "resumes"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


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
    def test_success_sets_extracted_and_hashes_but_never_stores_text(
        self, resume, put_object
    ):
        put_object(resume.file_key, fixture_bytes("simple_text.pdf"))
        resume.status = CandidateResume.Status.PROCESSING
        resume.save(update_fields=["status"])

        process_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.EXTRACTED
        assert resume.status_reason == ""
        assert resume.raw_text_hash
        assert len(resume.raw_text_hash) == 64
        # The raw text is held in memory only: nothing is persisted.
        assert resume.extracted_text == ""
        assert "Backend" not in resume.status_reason

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

        # A duplicated delivery after success must not re-extract or overwrite.
        process_resume(str(resume.id))

        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.EXTRACTED
        assert resume.raw_text_hash == original_hash

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
