"""Draft-job edit and delete tests (REQ-FR-026, batch 1.28).

What these pin beyond the happy path:

* `PATCH` is draft-only. An active, paused or closed job answers 409 with a
  sentence instead of being silently edited -- changing live text would change
  what candidates applied to (Arch Doc §4.3, rule 3);
* `DELETE` is draft-only and hard. The cascade from `jobs` would otherwise take
  applications and interviews with it (rule 4);
* both writes are audited inside the same transaction: `job.updated` records the
  changed field *names*, `job.deleted` the title, and neither carries candidate
  data or field values;
* a no-op `PATCH` (auto-save on an untouched form) writes no entry;
* `status` and `employer` are not writable through `PATCH`;
* ownership is the caller's profile: another employer's id is a 404, the same
  answer as an id that does not exist.

`force_authenticate` is not used; the 401 and role cases run through the JWT path
the frontend uses.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from core.models import AuditLogEntry
from employers.models import EmployerProfile
from matching.models import Job

pytestmark = pytest.mark.django_db


def api_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


@pytest.fixture
def employer(make_user):
    return make_user("employer_hr")


@pytest.fixture
def profile(employer):
    return EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")


@pytest.fixture
def job(profile):
    return Job.objects.create(
        employer=profile,
        title="Backend Engineer",
        description="Build and run the screening API.",
        location="Dhaka",
        experience_level=Job.ExperienceLevel.SENIOR,
    )


def detail_url(job_id) -> str:
    return f"/api/v1/jobs/{job_id}/"


class TestGet:
    def test_the_owner_reads_the_job(self, employer, profile, job):
        response = api_client(employer).get(detail_url(job.pk))

        assert response.status_code == 200
        assert response.data["id"] == str(job.pk)
        assert response.data["title"] == "Backend Engineer"

    def test_another_employers_job_is_404(self, job, make_user):
        other = make_user("employer_hr")
        EmployerProfile.objects.create(user=other, company_name="Other Ltd")

        response = api_client(other).get(detail_url(job.pk))

        assert response.status_code == 404

    def test_an_unknown_id_is_404(self, employer, profile):
        response = api_client(employer).get(detail_url(uuid.uuid4()))

        assert response.status_code == 404

    def test_a_candidate_is_403(self, job, make_user):
        candidate = make_user("candidate")

        response = api_client(candidate).get(detail_url(job.pk))

        assert response.status_code == 403

    def test_anonymous_is_401(self, job):
        response = APIClient().get(detail_url(job.pk))

        assert response.status_code == 401

    def test_an_employer_without_a_profile_is_404(self, job, make_user):
        employer = make_user("employer_hr")

        response = api_client(employer).get(detail_url(job.pk))

        assert response.status_code == 404


class TestPatch:
    def test_a_draft_is_updated_and_persisted(self, employer, profile, job):
        response = api_client(employer).patch(
            detail_url(job.pk),
            {
                "title": "Senior Backend Engineer",
                "description": "Own the matching service.",
                "location": "Remote",
                "remote_allowed": True,
                "nice_to_have": "pgvector experience.",
            },
            format="json",
        )

        assert response.status_code == 200
        job.refresh_from_db()
        assert job.title == "Senior Backend Engineer"
        assert job.description == "Own the matching service."
        assert job.location == "Remote"
        assert job.remote_allowed is True
        assert job.nice_to_have == "pgvector experience."
        assert response.data["title"] == "Senior Backend Engineer"

    def test_a_partial_patch_leaves_other_fields_alone(self, employer, profile, job):
        response = api_client(employer).patch(
            detail_url(job.pk), {"title": "Staff Engineer"}, format="json"
        )

        assert response.status_code == 200
        job.refresh_from_db()
        assert job.title == "Staff Engineer"
        assert job.description == "Build and run the screening API."
        assert job.location == "Dhaka"

    def test_the_audit_entry_names_the_changed_fields_only(
        self, employer, profile, job
    ):
        api_client(employer).patch(
            detail_url(job.pk),
            {"title": "Staff Engineer", "location": "Remote"},
            format="json",
        )

        entry = AuditLogEntry.objects.get()
        assert entry.action == "job.updated"
        assert entry.resource_type == "job"
        assert entry.resource_id == job.pk
        assert entry.actor_id == employer.pk
        assert entry.result == "success"
        assert entry.details == {"changed": ["location", "title"]}

    def test_a_no_op_patch_writes_no_entry(self, employer, profile, job):
        """Page #36 auto-saves; an untouched form must not fill the audit table."""
        response = api_client(employer).patch(detail_url(job.pk), {}, format="json")

        assert response.status_code == 200
        assert AuditLogEntry.objects.count() == 0

    def test_patching_a_field_to_its_current_value_writes_no_entry(
        self, employer, profile, job
    ):
        response = api_client(employer).patch(
            detail_url(job.pk), {"title": "Backend Engineer"}, format="json"
        )

        assert response.status_code == 200
        assert AuditLogEntry.objects.count() == 0

    def test_the_writable_set_is_a_whitelist(self, employer, profile, job, make_user):
        other_user = make_user("employer_hr")
        other = EmployerProfile.objects.create(
            user=other_user, company_name="Other Ltd"
        )

        api_client(employer).patch(
            detail_url(job.pk),
            {"status": "active", "employer": str(other.pk), "id": str(uuid.uuid4())},
            format="json",
        )

        job.refresh_from_db()
        assert job.status == Job.Status.DRAFT
        assert job.employer == profile
        assert AuditLogEntry.objects.count() == 0

    @pytest.mark.parametrize(
        "payload",
        [
            {"title": "   "},
            {"title": "x" * 301},
            {"experience_level": "principal"},
            {"experience_level": 3},
        ],
    )
    def test_an_invalid_body_is_400_and_changes_nothing(
        self, employer, profile, job, payload
    ):
        response = api_client(employer).patch(
            detail_url(job.pk), payload, format="json"
        )

        assert response.status_code == 400
        job.refresh_from_db()
        assert job.title == "Backend Engineer"
        assert AuditLogEntry.objects.count() == 0

    @pytest.mark.parametrize(
        "status", [Job.Status.ACTIVE, Job.Status.PAUSED, Job.Status.CLOSED]
    )
    def test_a_published_job_cannot_be_edited(self, employer, profile, job, status):
        Job.objects.filter(pk=job.pk).update(status=status)

        response = api_client(employer).patch(
            detail_url(job.pk), {"title": "Renamed"}, format="json"
        )

        assert response.status_code == 409
        assert response.data["detail"] == "Only a draft job can be edited."
        job.refresh_from_db()
        assert job.title == "Backend Engineer"
        assert AuditLogEntry.objects.count() == 0

    def test_another_employers_job_is_404(self, job, make_user):
        other = make_user("employer_hr")
        EmployerProfile.objects.create(user=other, company_name="Other Ltd")

        response = api_client(other).patch(
            detail_url(job.pk), {"title": "Hijacked"}, format="json"
        )

        assert response.status_code == 404
        job.refresh_from_db()
        assert job.title == "Backend Engineer"

    def test_a_candidate_is_403(self, job, make_user):
        candidate = make_user("candidate")

        response = api_client(candidate).patch(
            detail_url(job.pk), {"title": "Hijacked"}, format="json"
        )

        assert response.status_code == 403
        job.refresh_from_db()
        assert job.title == "Backend Engineer"

    def test_anonymous_is_401(self, job):
        response = APIClient().patch(
            detail_url(job.pk), {"title": "Hijacked"}, format="json"
        )

        assert response.status_code == 401

    def test_an_employer_without_a_profile_is_404(self, job, make_user):
        employer = make_user("employer_hr")

        response = api_client(employer).patch(
            detail_url(job.pk), {"title": "Hijacked"}, format="json"
        )

        assert response.status_code == 404


class TestDelete:
    def test_a_draft_is_deleted_and_audited(self, employer, profile, job):
        response = api_client(employer).delete(detail_url(job.pk))

        assert response.status_code == 204
        assert Job.objects.count() == 0

        entry = AuditLogEntry.objects.get()
        assert entry.action == "job.deleted"
        assert entry.resource_type == "job"
        assert entry.resource_id == job.pk
        assert entry.actor_id == employer.pk
        assert entry.details == {"title": "Backend Engineer"}

    @pytest.mark.parametrize(
        "status", [Job.Status.ACTIVE, Job.Status.PAUSED, Job.Status.CLOSED]
    )
    def test_a_published_job_cannot_be_deleted(self, employer, profile, job, status):
        """The cascade would take applications with it; closing is the way out."""
        Job.objects.filter(pk=job.pk).update(status=status)

        response = api_client(employer).delete(detail_url(job.pk))

        assert response.status_code == 409
        assert response.data["detail"] == "Only a draft job can be deleted."
        assert Job.objects.filter(pk=job.pk).exists()
        assert AuditLogEntry.objects.count() == 0

    def test_deleting_twice_is_404_the_second_time(self, employer, profile, job):
        client = api_client(employer)

        assert client.delete(detail_url(job.pk)).status_code == 204
        assert client.delete(detail_url(job.pk)).status_code == 404

        assert AuditLogEntry.objects.count() == 1

    def test_another_employers_job_is_404(self, job, make_user):
        other = make_user("employer_hr")
        EmployerProfile.objects.create(user=other, company_name="Other Ltd")

        response = api_client(other).delete(detail_url(job.pk))

        assert response.status_code == 404
        assert Job.objects.filter(pk=job.pk).exists()

    def test_a_candidate_is_403(self, job, make_user):
        candidate = make_user("candidate")

        response = api_client(candidate).delete(detail_url(job.pk))

        assert response.status_code == 403
        assert Job.objects.filter(pk=job.pk).exists()

    def test_anonymous_is_401(self, job):
        response = APIClient().delete(detail_url(job.pk))

        assert response.status_code == 401

    def test_a_platform_admin_is_403(self, job):
        admin = User.objects.create_superuser("admin@example.com")

        response = api_client(admin).delete(detail_url(job.pk))

        assert response.status_code == 403
        assert Job.objects.filter(pk=job.pk).exists()
