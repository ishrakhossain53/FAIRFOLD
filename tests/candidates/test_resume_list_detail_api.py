"""Resume list and detail API (REQ-FR-010, batch 1.21).

Complete Doc §C.12:

    GET /api/v1/candidates/resumes/      # List resumes
    GET /api/v1/candidates/resumes/{id}/ # Get resume details

What these tests pin down:

* **owner-only, both verbs.** Another candidate's id is indistinguishable from
  an id that exists nowhere, so a 404 cannot be used to enumerate rows. A
  non-candidate is 403 and an anonymous caller 401 on both routes.
* **metadata, not storage.** The body is a fixed set of keys; the storage key,
  a URL and the extracted text are absent. The key is asserted against the raw
  response body, not just the parsed keys, so a nested or renamed field would
  still fail.
* **shape consistency.** A detail entry and a list entry carry the same fields,
  so a client that has an id from the list needs no second parser.
* **state is visible.** A `rejected` resume reaches its owner with the reason
  that `test_resume_completion_api.py` produced, and a `pending` row -- an
  upload that never landed -- stays listed so the candidate can retry it.
* **pagination is the project one.** `page_size` works and the 100-row ceiling
  from `core.pagination.StandardPagination` is not bypassed.

The serializer is the contract here; nothing in this file touches storage.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from candidates.models import CandidateProfile, CandidateResume
from candidates.services import RESUME_AUDIT_RESOURCE_TYPE, RESUME_DELETED_ACTION
from core.models import AuditLogEntry

pytestmark = pytest.mark.django_db

URL = "/api/v1/candidates/resumes/"

# The fields §C.12's two reads may return. Written out rather than imported so a
# silent widening of the serializer fails here instead of passing automatically.
EXPECTED_FIELDS = {
    "id",
    "original_filename",
    "file_size",
    "mime_type",
    "status",
    "status_reason",
    "created_at",
    "processed_at",
}


def api_client(user) -> APIClient:
    """A real JWT client for `user`; no forced authentication."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


def detail_url(resume) -> str:
    return f"{URL}{resume.id}/"


@pytest.fixture
def profile(make_user):
    """A candidate who has completed onboarding."""
    user = make_user("candidate")
    return CandidateProfile.objects.create(user=user)


def make_resume(profile, **overrides) -> CandidateResume:
    """A resume row with the minimum the model requires."""
    fields = {
        "candidate": profile,
        "file_key": f"resumes/{profile.id}/{uuid.uuid4().hex}.pdf",
        "original_filename": "Ada Lovelace CV.pdf",
        "file_size": 2048,
        "mime_type": "application/pdf",
    }
    fields.update(overrides)
    return CandidateResume.objects.create(**fields)


class TestListAccess:
    def test_anonymous_is_401(self):
        response = APIClient().get(URL)

        assert response.status_code == 401
        assert "results" not in response.json()

    @pytest.mark.parametrize("role", ["employer_hr", "employer_manager", "interviewer"])
    def test_an_authenticated_non_candidate_is_403(self, make_user, role):
        user = make_user(role)

        response = api_client(user).get(URL)

        assert response.status_code == 403

    def test_a_platform_admin_is_403(self, make_user):
        user = make_user(is_staff=True)

        response = api_client(user).get(URL)

        assert response.status_code == 403

    def test_a_candidate_without_a_profile_is_404(self, make_user):
        """Onboarding comes first (REQ-FR-009); "no profile" is not "no rows"."""
        user = make_user("candidate")

        response = api_client(user).get(URL)

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "No candidate profile yet. Complete onboarding first."
        )


class TestList:
    def test_a_candidate_with_no_resumes_gets_an_empty_page(self, profile):
        response = api_client(profile.user).get(URL)

        assert response.status_code == 200
        assert response.json()["count"] == 0
        assert response.json()["results"] == []

    def test_only_the_callers_resumes_are_returned(self, profile, make_user):
        mine = [make_resume(profile), make_resume(profile)]

        other_profile = CandidateProfile.objects.create(user=make_user("candidate"))
        theirs = make_resume(other_profile)

        body = api_client(profile.user).get(URL).json()

        returned = {row["id"] for row in body["results"]}
        assert returned == {str(resume.id) for resume in mine}
        assert str(theirs.id) not in returned
        assert body["count"] == 2

    def test_newest_first(self, profile):
        older = make_resume(profile)
        newer = make_resume(profile)
        CandidateResume.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        body = api_client(profile.user).get(URL).json()

        assert [row["id"] for row in body["results"]] == [
            str(newer.id),
            str(older.id),
        ]

    def test_the_body_is_metadata_and_nothing_else(self, profile):
        resume = make_resume(profile)

        response = api_client(profile.user).get(URL)
        row = response.json()["results"][0]

        assert set(row) == EXPECTED_FIELDS
        assert row["id"] == str(resume.id)
        assert row["original_filename"] == "Ada Lovelace CV.pdf"
        assert row["status"] == "pending"

        # Storage detail must not leak, even under another name. Checking the
        # raw body catches a key the parsed assertion would miss if the field
        # were nested or renamed.
        raw = response.content.decode()
        assert resume.file_key not in raw
        assert "file_key" not in raw
        assert "http" not in raw
        assert "extracted_text" not in raw

    def test_a_rejected_resume_reaches_its_owner_with_the_reason(self, profile):
        resume = make_resume(
            profile,
            status=CandidateResume.Status.REJECTED,
            status_reason="clamav unavailable",
        )

        row = api_client(profile.user).get(URL).json()["results"][0]

        assert row["status"] == resume.Status.REJECTED
        assert row["status_reason"] == "clamav unavailable"

    def test_a_pending_resume_is_listed_so_the_upload_can_be_retried(self, profile):
        """Batch 1.20 leaves an unfinished upload `pending`; hiding it would
        make a failed upload vanish without the candidate seeing anything."""
        make_resume(profile, status=CandidateResume.Status.PENDING)

        body = api_client(profile.user).get(URL).json()

        assert body["count"] == 1
        assert body["results"][0]["status"] == "pending"

    def test_page_size_is_honoured(self, profile):
        for _ in range(3):
            make_resume(profile)

        body = api_client(profile.user).get(f"{URL}?page_size=1").json()

        assert body["count"] == 3
        assert body["page_size"] == 1
        assert len(body["results"]) == 1
        assert body["next"] is not None

    def test_page_size_is_capped_at_the_project_ceiling(self, profile):
        make_resume(profile)

        body = api_client(profile.user).get(f"{URL}?page_size=1000").json()

        assert body["page_size"] == 100


class TestDetailAccess:
    def test_anonymous_is_401(self, profile):
        resume = make_resume(profile)

        response = APIClient().get(detail_url(resume))

        assert response.status_code == 401

    @pytest.mark.parametrize("role", ["employer_hr", "employer_manager", "interviewer"])
    def test_an_authenticated_non_candidate_is_403(self, make_user, profile, role):
        user = make_user(role)
        resume = make_resume(profile)

        response = api_client(user).get(detail_url(resume))

        assert response.status_code == 403

    def test_a_platform_admin_is_403(self, make_user, profile):
        user = make_user(is_staff=True)
        resume = make_resume(profile)

        response = api_client(user).get(detail_url(resume))

        assert response.status_code == 403


class TestDetail:
    def test_the_owner_gets_the_same_shape_as_a_list_entry(self, profile):
        resume = make_resume(profile, file_size=4096)

        response = api_client(profile.user).get(detail_url(resume))
        body = response.json()

        assert response.status_code == 200
        assert set(body) == EXPECTED_FIELDS
        assert body["id"] == str(resume.id)
        assert body["file_size"] == 4096

        list_entry = api_client(profile.user).get(URL).json()["results"][0]
        assert set(body) == set(list_entry)

    def test_the_storage_key_is_not_in_the_body(self, profile):
        resume = make_resume(profile)

        raw = api_client(profile.user).get(detail_url(resume)).content.decode()

        assert resume.file_key not in raw
        assert "file_key" not in raw
        assert "http" not in raw

    def test_another_candidates_resume_is_404(self, profile, make_user):
        other_profile = CandidateProfile.objects.create(user=make_user("candidate"))
        theirs = make_resume(other_profile)

        response = api_client(profile.user).get(detail_url(theirs))

        assert response.status_code == 404
        assert response.json()["detail"] == "Resume not found."

    def test_an_unknown_id_is_404(self, profile):
        response = api_client(profile.user).get(f"{URL}{uuid.uuid4()}/")

        assert response.status_code == 404

    def test_a_malformed_id_is_404(self, profile):
        """The `<uuid:pk>` converter rejects it before the view runs."""
        response = api_client(profile.user).get(f"{URL}not-a-uuid/")

        assert response.status_code == 404

    def test_a_resume_in_any_status_is_readable(self, profile):
        """No lifecycle column exists (§5.1), so the read endpoints return
        whatever row the owner has, filtered by nothing but ownership."""
        resume = make_resume(profile, status=CandidateResume.Status.CLEAN)

        response = api_client(profile.user).get(detail_url(resume))

        assert response.status_code == 200
        assert response.json()["status"] == "clean"


class TestDeleteAccess:
    def test_anonymous_is_401(self, profile):
        resume = make_resume(profile)

        response = APIClient().delete(detail_url(resume))

        assert response.status_code == 401
        assert CandidateResume.objects.filter(pk=resume.pk).exists()

    @pytest.mark.parametrize("role", ["employer_hr", "employer_manager", "interviewer"])
    def test_an_authenticated_non_candidate_is_403(self, make_user, profile, role):
        user = make_user(role)
        resume = make_resume(profile)

        response = api_client(user).delete(detail_url(resume))

        assert response.status_code == 403
        assert CandidateResume.objects.filter(pk=resume.pk).exists()

    def test_a_platform_admin_is_403(self, make_user, profile):
        user = make_user(is_staff=True)
        resume = make_resume(profile)

        response = api_client(user).delete(detail_url(resume))

        assert response.status_code == 403
        assert CandidateResume.objects.filter(pk=resume.pk).exists()


class TestDelete:
    def test_the_owner_deletes_the_row_and_the_stored_object(self, profile, put_object):
        resume = make_resume(profile)
        stored = put_object(resume.file_key, b"%PDF-1.4\n%%EOF\n")

        response = api_client(profile.user).delete(detail_url(resume))

        assert response.status_code == 204
        assert response.content == b""
        assert not CandidateResume.objects.filter(pk=resume.pk).exists()
        assert not stored.exists()

    def test_the_deletion_is_audited_without_pii(self, profile, resume_storage):
        resume = make_resume(profile, status=CandidateResume.Status.CLEAN)

        api_client(profile.user).delete(detail_url(resume))

        entry = AuditLogEntry.objects.get(action=RESUME_DELETED_ACTION)
        assert entry.actor == profile.user
        assert entry.resource_type == RESUME_AUDIT_RESOURCE_TYPE
        assert entry.resource_id == resume.pk
        assert entry.result == "success"
        assert entry.details == {"status": "clean"}

        # The trail is what survives the erasure (REQ-FR-041), so it must not
        # contain the file, its name or the key.
        audit_text = f"{entry.action} {entry.details}"
        assert resume.file_key not in audit_text
        assert resume.original_filename not in audit_text

    def test_another_candidates_resume_is_404_and_survives(self, profile, make_user):
        other_profile = CandidateProfile.objects.create(user=make_user("candidate"))
        theirs = make_resume(other_profile)

        response = api_client(profile.user).delete(detail_url(theirs))

        assert response.status_code == 404
        assert CandidateResume.objects.filter(pk=theirs.pk).exists()
        assert not AuditLogEntry.objects.filter(action=RESUME_DELETED_ACTION).exists()

    def test_a_second_delete_is_404(self, profile, resume_storage):
        resume = make_resume(profile)
        client = api_client(profile.user)

        assert client.delete(detail_url(resume)).status_code == 204
        assert client.delete(detail_url(resume)).status_code == 404

        assert AuditLogEntry.objects.filter(action=RESUME_DELETED_ACTION).count() == 1

    def test_a_resume_in_any_status_may_be_deleted(self, profile, resume_storage):
        """Including `scanning`: the queued task re-reads the row and returns
        quietly when it is gone (candidates/tasks.py), so no scan can resurrect
        a deleted resume."""
        resume = make_resume(profile, status=CandidateResume.Status.SCANNING)

        response = api_client(profile.user).delete(detail_url(resume))

        assert response.status_code == 204
        assert not CandidateResume.objects.filter(pk=resume.pk).exists()

    def test_a_missing_object_does_not_block_the_deletion(
        self, profile, resume_storage
    ):
        """`discard_object` is best effort: the row is the record, and an object
        already gone from the bucket must not turn a delete into a 500."""
        resume = make_resume(profile)

        response = api_client(profile.user).delete(detail_url(resume))

        assert response.status_code == 204
        assert not CandidateResume.objects.filter(pk=resume.pk).exists()

    def test_the_deleted_resume_disappears_from_the_list(self, profile, resume_storage):
        kept = make_resume(profile)
        deleted = make_resume(profile)

        api_client(profile.user).delete(detail_url(deleted))

        body = api_client(profile.user).get(URL).json()

        assert body["count"] == 1
        assert body["results"][0]["id"] == str(kept.id)
