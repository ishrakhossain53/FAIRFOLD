"""Draft-job creation API tests (REQ-FR-025, batch 1.27).

What these pin beyond the happy path:

* the endpoint creates a **draft** and nothing else -- `status` in the body cannot
  publish a job, because activation is a separate audited action (REQ-FR-027);
* the owner comes from the caller's profile, never from the body, so one employer
  cannot create a job under another's name;
* employer-only: candidate, interviewer and platform admin get 403, an anonymous
  caller gets 401, and an employer who has not onboarded gets 404;
* the response carries the `id` the later `PATCH`/`activate/` calls need;
* one `job.created` audit entry, with employer content and no candidate data.

`force_authenticate` is not used, for the same reason as the profile API tests:
the 401 and role cases must run through the JWT path the frontend uses.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from core.models import AuditLogEntry
from employers.models import EmployerProfile
from matching.models import Job

pytestmark = pytest.mark.django_db

URL = "/api/v1/jobs/"

EXPECTED_KEYS = {
    "id",
    "title",
    "description",
    "responsibilities",
    "requirements",
    "nice_to_have",
    "location",
    "remote_allowed",
    "experience_level",
    "status",
    "screening_questions",
    "screening_config_version",
    "created_at",
    "updated_at",
}


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


def job_payload(**overrides) -> dict:
    payload = {
        "title": "Backend Engineer",
        "description": "Build and run the screening API.",
        "responsibilities": "Own the matching service.",
        "requirements": "Four years with Django.",
        "nice_to_have": "pgvector experience.",
        "location": "Dhaka",
        "remote_allowed": True,
        "experience_level": "senior",
    }
    payload.update(overrides)
    return payload


class TestCreate:
    def test_an_employer_creates_a_draft_job(self, employer, profile):
        response = api_client(employer).post(URL, job_payload(), format="json")

        assert response.status_code == 201
        job = Job.objects.get()
        assert job.title == "Backend Engineer"
        assert job.description == "Build and run the screening API."
        assert job.employer == profile
        assert job.status == Job.Status.DRAFT

    def test_the_response_returns_the_job_contract(self, employer, profile):
        response = api_client(employer).post(URL, job_payload(), format="json")

        assert set(response.data) == EXPECTED_KEYS
        assert response.data["status"] == "draft"
        assert response.data["screening_questions"] == []
        assert response.data["screening_config_version"] == 1

    def test_the_response_id_is_the_row_id(self, employer, profile):
        """The client needs it for PATCH and activation; a client that has to
        search for the job it just created will eventually pick the wrong one."""
        response = api_client(employer).post(URL, job_payload(), format="json")

        assert response.data["id"] == str(Job.objects.get().pk)

    def test_unset_optional_fields_keep_their_defaults(self, employer, profile):
        response = api_client(employer).post(
            URL, {"title": "Data Engineer"}, format="json"
        )

        assert response.status_code == 201
        job = Job.objects.get()
        assert job.description == ""
        assert job.location == ""
        assert job.remote_allowed is False
        assert job.experience_level == ""

    def test_a_draft_may_have_no_description(self, employer, profile):
        """The DDL allows it, and page #36 auto-saves a draft while typing."""
        response = api_client(employer).post(
            URL, {"title": "Draft without a description"}, format="json"
        )

        assert response.status_code == 201


class TestAudit:
    def test_creation_writes_one_job_created_entry(self, employer, profile):
        response = api_client(employer).post(URL, job_payload(), format="json")
        job = Job.objects.get()

        entry = AuditLogEntry.objects.get()
        assert entry.action == "job.created"
        assert entry.resource_type == "job"
        assert entry.resource_id == job.pk
        assert entry.actor_id == employer.pk
        assert entry.result == "success"
        assert entry.details == {"title": "Backend Engineer", "status": "draft"}
        assert response.status_code == 201

    def test_the_entry_carries_no_candidate_data(self, employer, profile):
        """The audit table is retained. Job titles are employer content; a
        candidate identifier must never reach it."""
        api_client(employer).post(URL, job_payload(), format="json")

        details = AuditLogEntry.objects.get().details
        assert set(details) == {"title", "status"}


class TestValidation:
    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"description": "No title"},
            {"title": "   "},
            {"title": "x" * 301},
            {"title": "Backend", "experience_level": "principal"},
            {"title": "Backend", "experience_level": 3},
        ],
    )
    def test_an_invalid_body_is_400_and_creates_nothing(
        self, employer, profile, payload
    ):
        response = api_client(employer).post(URL, payload, format="json")

        assert response.status_code == 400
        assert Job.objects.count() == 0
        assert AuditLogEntry.objects.count() == 0


class TestOwnership:
    def test_status_in_the_body_cannot_publish_a_job(self, employer, profile):
        """REQ-FR-027 makes activation its own action. Otherwise this endpoint is
        an unaudited publishing path."""
        response = api_client(employer).post(
            URL, job_payload(status="active"), format="json"
        )

        assert response.status_code == 201
        assert Job.objects.get().status == Job.Status.DRAFT

    def test_another_employers_id_in_the_body_is_ignored(
        self, employer, profile, make_user
    ):
        other_user = make_user("employer_hr")
        other = EmployerProfile.objects.create(
            user=other_user, company_name="Other Ltd"
        )

        api_client(employer).post(
            URL,
            job_payload(
                employer=str(other.pk), id="00000000-0000-0000-0000-000000000000"
            ),
            format="json",
        )

        job = Job.objects.get()
        assert job.employer == profile
        assert job.employer != other


class TestPermissions:
    def test_anonymous_is_401(self):
        response = APIClient().post(URL, job_payload(), format="json")

        assert response.status_code == 401

    def test_a_candidate_is_403(self, make_user):
        candidate = make_user("candidate")

        response = api_client(candidate).post(URL, job_payload(), format="json")

        assert response.status_code == 403
        assert Job.objects.count() == 0

    def test_an_interviewer_is_403(self, make_user):
        """`interviewer` may read an assigned interview, not manage jobs."""
        interviewer = make_user("interviewer")

        response = api_client(interviewer).post(URL, job_payload(), format="json")

        assert response.status_code == 403
        assert Job.objects.count() == 0

    def test_a_platform_admin_without_an_employer_role_is_403(self):
        """D-2: `admin` is `is_staff`, not an employer role."""
        admin = User.objects.create_superuser("admin@example.com")

        response = api_client(admin).post(URL, job_payload(), format="json")

        assert response.status_code == 403
        assert Job.objects.count() == 0

    def test_an_employer_without_a_profile_is_404(self, make_user):
        employer = make_user("employer_hr")

        response = api_client(employer).post(URL, job_payload(), format="json")

        assert response.status_code == 404
        assert "onboarding" in response.data["detail"].lower()
        assert Job.objects.count() == 0
