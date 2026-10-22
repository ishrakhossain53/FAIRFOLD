"""Resume upload completion (REQ-SEC-012, batch 1.20).

The completion endpoint is where the server looks at what actually arrived: the
object's real size, and its type from libmagic rather than the browser's
declaration. These tests cover the checks, the rejection reasons, the queueing
of the scan, and the permission/ownership boundary.

Scanning itself is `tests/candidates/test_resume_scan.py`; nothing here needs a
ClamAV daemon.
"""

from __future__ import annotations

import pytest
from kombu.exceptions import OperationalError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from candidates.models import CandidateProfile, CandidateResume

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures("resume_storage"),
]

# Enough of a PDF for libmagic; it is never parsed by this batch.
PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
)

# A 1x1 PNG header. libmagic needs the IHDR chunk to name the type; the eight
# signature bytes alone are reported as text/plain.
PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
)


def api_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


def complete_url(resume) -> str:
    return f"/api/v1/candidates/resumes/{resume.id}/complete/"


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
    )


@pytest.fixture(autouse=True)
def queued(monkeypatch):
    """Record `scan_resume.delay` calls; never contact the broker."""
    calls = []
    monkeypatch.setattr(
        "candidates.api_views.scan_resume.delay",
        lambda resume_id: calls.append(resume_id),
    )
    return calls


def post(profile, resume):
    return api_client(profile.user).post(complete_url(resume))


class TestAccess:
    def test_anonymous_is_401(self, resume, queued):
        response = APIClient().post(complete_url(resume))

        assert response.status_code == 401
        assert queued == []

    @pytest.mark.parametrize("role", ["employer_hr", "employer_manager", "interviewer"])
    def test_an_authenticated_non_candidate_is_403(
        self, make_user, resume, queued, role
    ):
        response = api_client(make_user(role)).post(complete_url(resume))

        assert response.status_code == 403
        assert queued == []

    def test_a_platform_admin_is_403(self, make_user, resume, queued):
        response = api_client(make_user(is_staff=True)).post(complete_url(resume))

        assert response.status_code == 403
        assert queued == []

    def test_an_unknown_id_is_404(self, profile, queued):
        response = api_client(profile.user).post(
            "/api/v1/candidates/resumes/00000000-0000-0000-0000-000000000000/complete/"
        )

        assert response.status_code == 404
        assert queued == []

    def test_another_candidates_resume_is_404_and_untouched(
        self, make_user, profile, resume, queued
    ):
        other_user = make_user("candidate")
        other_profile = CandidateProfile.objects.create(user=other_user)

        response = api_client(other_user).post(complete_url(resume))

        assert response.status_code == 404
        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.PENDING
        assert queued == []
        # The caller's own profile is irrelevant; only the row's owner matters.
        assert other_profile.user == other_user


class TestStoredObjectChecks:
    def test_a_valid_pdf_is_queued_for_scanning(
        self, profile, resume, put_object, queued
    ):
        put_object(resume.file_key, PDF)

        response = post(profile, resume)

        assert response.status_code == 202
        assert set(response.data) == {"id", "status", "status_reason"}
        assert response.data["status"] == CandidateResume.Status.SCANNING
        assert response.data["status_reason"] == ""
        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.SCANNING
        assert queued == [str(resume.id)]

    def test_a_missing_object_is_409_and_stays_pending(self, profile, resume, queued):
        response = post(profile, resume)

        assert response.status_code == 409
        assert "detail" in response.data
        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.PENDING
        assert queued == []

    def test_an_empty_object_is_rejected(
        self, profile, resume, put_object, queued, resume_storage
    ):
        put_object(resume.file_key, b"")

        response = post(profile, resume)

        assert response.status_code == 200
        assert response.data["status"] == CandidateResume.Status.REJECTED
        assert response.data["status_reason"] == "empty file"
        assert not (resume_storage / resume.file_key).exists()
        assert queued == []

    def test_an_oversize_object_is_rejected(
        self, profile, resume, put_object, queued, settings, resume_storage
    ):
        settings.MAX_UPLOAD_SIZE_BYTES = 50
        put_object(resume.file_key, PDF)

        response = post(profile, resume)

        assert response.status_code == 200
        assert response.data["status"] == CandidateResume.Status.REJECTED
        assert "larger" in response.data["status_reason"]
        assert not (resume_storage / resume.file_key).exists()
        assert queued == []

    @pytest.mark.parametrize(
        "data",
        [
            b"PK\x03\x04" + b"\x00" * 64,
            b"just some plain text, not a resume",
        ],
    )
    def test_a_type_outside_the_allow_list_is_rejected(
        self, profile, resume, put_object, queued, data
    ):
        put_object(resume.file_key, data)

        response = post(profile, resume)

        assert response.status_code == 200
        assert response.data["status"] == CandidateResume.Status.REJECTED
        assert "not allowed" in response.data["status_reason"]
        assert queued == []

    def test_a_declared_type_that_does_not_match_the_bytes_is_rejected(
        self, profile, resume, put_object, queued, settings
    ):
        # Add a second allowed type so the file passes the allow-list and the
        # mismatch check is what rejects it.
        settings.RESUME_ALLOWED_MIME_TYPES = {
            **settings.RESUME_ALLOWED_MIME_TYPES,
            "image/png": ".png",
        }
        put_object(resume.file_key, PNG)

        response = post(profile, resume)

        assert response.status_code == 200
        assert response.data["status"] == CandidateResume.Status.REJECTED
        assert "declared" in response.data["status_reason"]
        assert queued == []

    def test_a_rejection_reason_never_contains_the_filename(
        self, profile, resume, put_object, queued
    ):
        put_object(resume.file_key, b"PK\x03\x04" + b"\x00" * 64)

        response = post(profile, resume)

        assert response.data["status"] == CandidateResume.Status.REJECTED
        assert "Ada" not in response.data["status_reason"]
        assert resume.original_filename not in response.data["status_reason"]


class TestIdempotency:
    @pytest.mark.parametrize(
        "state",
        [
            CandidateResume.Status.SCANNING,
            CandidateResume.Status.CLEAN,
            CandidateResume.Status.REJECTED,
        ],
    )
    def test_a_settled_or_in_flight_resume_is_returned_not_rescanned(
        self, profile, resume, queued, state
    ):
        resume.status = state
        resume.status_reason = (
            "malware detected: Test-Signature" if state == "rejected" else ""
        )
        resume.save(update_fields=["status", "status_reason"])

        response = post(profile, resume)

        assert response.status_code == 200
        assert response.data["status"] == state
        assert queued == []
        resume.refresh_from_db()
        assert resume.status == state

    @pytest.mark.parametrize(
        "state",
        [
            CandidateResume.Status.PROCESSING,
            CandidateResume.Status.EXTRACTED,
            CandidateResume.Status.EMBEDDED,
            CandidateResume.Status.FAILED,
        ],
    )
    def test_a_phase_two_state_is_409(self, profile, resume, queued, state):
        resume.status = state
        resume.save(update_fields=["status"])

        response = post(profile, resume)

        assert response.status_code == 409
        assert response.data["status"] == state
        assert queued == []

    def test_a_queue_failure_reverts_to_pending(
        self, profile, resume, put_object, monkeypatch, queued
    ):
        put_object(resume.file_key, PDF)

        def broker_down(_resume_id):
            raise OperationalError("broker down")

        monkeypatch.setattr("candidates.api_views.scan_resume.delay", broker_down)

        response = post(profile, resume)

        assert response.status_code == 503
        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.PENDING
        assert resume.status_reason == ""
