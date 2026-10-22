"""Presigned resume upload API (REQ-FR-010, batch 1.19).

What these tests pin down:

* candidate-only, and the caller must already have a profile -- an employer gets
  403 and an anonymous caller 401, neither of which creates a row;
* the type and size are checked **before** a row or a URL exists, so a rejected
  request leaves nothing behind;
* the key is generated server-side from the candidate id and a random UUID, with
  the extension taken from the allow-list rather than the filename;
* the presigned URL is a PUT for exactly that key and content type, with the
  configured expiry;
* a storage failure returns 503 and does not leave a `pending` row that can
  never be completed.

The boto3 client is stubbed. These tests must not need MinIO or AWS: the
integration path is `tests/core/test_storage.py`, which skips without a bucket.
"""

from __future__ import annotations

import re

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from candidates.models import CandidateProfile, CandidateResume
from core.storage import StorageError

pytestmark = pytest.mark.django_db

URL = "/api/v1/candidates/resumes/"
BUCKET = "fairfold-media"
SIZE_LIMIT = 1024 * 1024


def api_client(user) -> APIClient:
    """A real JWT client for `user`; no forced authentication."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


@pytest.fixture(autouse=True)
def upload_settings(settings):
    """The two settings the endpoint reads, with a small size limit."""
    settings.AWS_STORAGE_BUCKET_NAME = BUCKET
    settings.MAX_UPLOAD_SIZE_BYTES = SIZE_LIMIT
    settings.RESUME_PRESIGN_EXPIRES_SECONDS = 300


@pytest.fixture
def profile(make_user):
    user = make_user("candidate")
    return CandidateProfile.objects.create(user=user)


class StubS3:
    """A boto3 client that records the signing call instead of signing."""

    def __init__(self):
        self.calls = []

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
        self.calls.append(
            {"method": ClientMethod, "params": Params, "expires_in": ExpiresIn}
        )
        key = Params["Key"]
        return (
            f"https://storage.example/{Params['Bucket']}/{key}"
            f"?X-Amz-Expires={ExpiresIn}&X-Amz-Signature=stub"
        )


@pytest.fixture
def stub_s3(monkeypatch):
    stub = StubS3()
    monkeypatch.setattr("candidates.uploads.s3_client", lambda: stub)
    return stub


def payload(**overrides):
    body = {
        "content_type": "application/pdf",
        "file_size": 2048,
        "original_filename": "Ada Lovelace CV.pdf",
    }
    body.update(overrides)
    return body


def post(profile, **overrides):
    return api_client(profile.user).post(URL, payload(**overrides), format="json")


class TestAccess:
    def test_anonymous_is_401(self, stub_s3):
        response = APIClient().post(URL, payload(), format="json")

        assert response.status_code == 401
        assert not CandidateResume.objects.exists()
        assert stub_s3.calls == []

    @pytest.mark.parametrize("role", ["employer_hr", "employer_manager", "interviewer"])
    def test_an_authenticated_non_candidate_is_403(self, make_user, stub_s3, role):
        user = make_user(role)

        response = api_client(user).post(URL, payload(), format="json")

        assert response.status_code == 403
        assert not CandidateResume.objects.exists()
        assert stub_s3.calls == []

    def test_a_platform_admin_is_403(self, make_user, stub_s3):
        user = make_user(is_staff=True)

        response = api_client(user).post(URL, payload(), format="json")

        assert response.status_code == 403
        assert not CandidateResume.objects.exists()

    def test_a_candidate_without_a_profile_is_404(self, make_user, stub_s3):
        user = make_user("candidate")

        response = api_client(user).post(URL, payload(), format="json")

        assert response.status_code == 404
        assert not CandidateResume.objects.exists()
        # No profile means no owner for the row, so nothing was signed either.
        assert stub_s3.calls == []


class TestValidation:
    def test_an_allowed_pdf_creates_a_pending_row(self, profile, stub_s3):
        response = post(profile)

        assert response.status_code == 201
        resume = CandidateResume.objects.get()
        assert resume.candidate == profile
        assert resume.status == CandidateResume.Status.PENDING
        assert resume.mime_type == "application/pdf"
        assert resume.file_size == 2048
        assert resume.original_filename == "Ada Lovelace CV.pdf"
        assert re.fullmatch(
            rf"resumes/{profile.id}/[0-9a-f]{{32}}\.pdf", resume.file_key
        )

    def test_the_response_carries_the_upload_target(self, profile, stub_s3):
        response = post(profile)

        assert set(response.data) == {"id", "status", "upload"}
        assert response.data["status"] == "pending"
        assert str(response.data["id"]) == str(CandidateResume.objects.get().id)
        upload = response.data["upload"]
        assert set(upload) == {"url", "method", "headers", "expires_in"}
        assert upload["method"] == "PUT"
        assert upload["headers"] == {"Content-Type": "application/pdf"}
        assert upload["expires_in"] == 300
        assert upload["url"].startswith("https://storage.example/")

    def test_two_uploads_get_different_keys(self, profile, stub_s3):
        post(profile)
        post(profile)

        keys = list(CandidateResume.objects.values_list("file_key", flat=True))

        assert len(keys) == 2
        assert keys[0] != keys[1]

    def test_the_key_is_not_derived_from_the_filename(self, profile, stub_s3):
        response = post(
            profile,
            content_type="application/pdf",
            original_filename="../../etc/passwd.exe",
        )

        assert response.status_code == 201
        resume = CandidateResume.objects.get()
        assert resume.original_filename == "passwd.exe"
        assert "passwd" not in resume.file_key
        assert resume.file_key.endswith(".pdf")

    @pytest.mark.parametrize(
        "content_type",
        [
            "application/zip",
            "text/plain",
            "image/png",
            "application/msword",
            # A parameter is not the allow-listed value, even for the right base.
            "application/pdf; charset=binary",
        ],
    )
    def test_a_type_outside_the_allow_list_is_400(self, profile, stub_s3, content_type):
        response = post(profile, content_type=content_type)

        assert response.status_code == 400
        assert "content_type" in response.data
        assert not CandidateResume.objects.exists()
        assert stub_s3.calls == []

    def test_an_oversize_file_is_400(self, profile, stub_s3):
        response = post(profile, file_size=SIZE_LIMIT + 1)

        assert response.status_code == 400
        assert "file_size" in response.data
        assert not CandidateResume.objects.exists()
        assert stub_s3.calls == []

    def test_a_file_exactly_at_the_limit_is_accepted(self, profile, stub_s3):
        response = post(profile, file_size=SIZE_LIMIT)

        assert response.status_code == 201

    @pytest.mark.parametrize("file_size", [0, -1])
    def test_a_non_positive_size_is_400(self, profile, stub_s3, file_size):
        response = post(profile, file_size=file_size)

        assert response.status_code == 400
        assert "file_size" in response.data
        assert not CandidateResume.objects.exists()

    @pytest.mark.parametrize(
        "missing", ["content_type", "file_size", "original_filename"]
    )
    def test_every_declared_field_is_required(self, profile, stub_s3, missing):
        body = payload()
        del body[missing]

        response = api_client(profile.user).post(URL, body, format="json")

        assert response.status_code == 400
        assert missing in response.data
        assert not CandidateResume.objects.exists()

    @pytest.mark.parametrize("filename", ["   ", "/", "folder/"])
    def test_a_blank_filename_is_400(self, profile, stub_s3, filename):
        response = post(profile, original_filename=filename)

        assert response.status_code == 400
        assert "original_filename" in response.data
        assert not CandidateResume.objects.exists()

    def test_the_body_cannot_choose_the_owner_key_or_status(self, profile, stub_s3):
        other = CandidateProfile.objects.create(
            user=User.objects.create_user(
                "other@example.com", "not-used-in-these-tests"
            )
        )

        response = post(
            profile,
            candidate=str(other.id),
            file_key="resumes/chosen.pdf",
            status="clean",
        )

        assert response.status_code == 201
        resume = CandidateResume.objects.get()
        assert resume.candidate == profile
        assert resume.status == CandidateResume.Status.PENDING
        assert resume.file_key != "resumes/chosen.pdf"


class TestPresigning:
    def test_the_url_is_a_put_for_the_stored_key_and_type(self, profile, stub_s3):
        post(profile)

        resume = CandidateResume.objects.get()
        assert len(stub_s3.calls) == 1
        call = stub_s3.calls[0]
        assert call["method"] == "put_object"
        assert call["params"] == {
            "Bucket": BUCKET,
            "Key": resume.file_key,
            "ContentType": "application/pdf",
        }

    def test_the_expiry_comes_from_settings(self, profile, stub_s3, settings):
        settings.RESUME_PRESIGN_EXPIRES_SECONDS = 60

        response = post(profile)

        assert stub_s3.calls[0]["expires_in"] == 60
        assert response.data["upload"]["expires_in"] == 60
        assert "X-Amz-Expires=60" in response.data["upload"]["url"]

    def test_storage_failure_is_503_and_leaves_no_row(self, profile, monkeypatch):
        def unavailable():
            raise StorageError("AWS_STORAGE_BUCKET_NAME is not set.")

        monkeypatch.setattr("candidates.uploads.s3_client", unavailable)

        response = post(profile)

        assert response.status_code == 503
        assert "detail" in response.data
        assert not CandidateResume.objects.exists()
