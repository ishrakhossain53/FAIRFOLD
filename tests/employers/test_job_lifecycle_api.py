"""Job state-transition tests (REQ-FR-027, batch 1.29).

Arch Doc §4.3 is the contract under test:

* `draft` and `paused` activate; `active` pauses; `active` and `paused` close;
* acting on a job already in the target state is a no-op -- `200`, no new audit
  entry -- so a double-clicked button or a retried request is safe;
* every other off-matrix transition is `409` with a sentence, and the job does
  not move;
* one `job.<verbed>` entry per effective transition, with `{"from", "to"}` and
  nothing else: no candidate data, no rationale text, no field values;
* the action endpoints write `status` only, so they cannot be used to edit
  content past the draft-only rule on `PATCH`;
* ownership is the caller's profile; another employer's id is 404.

`force_authenticate` is not used; the 401 and role cases run through the JWT path.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from core.models import AuditLogEntry
from employers.models import EmployerProfile
from matching.models import Job

pytestmark = pytest.mark.django_db

ACTIVATE = "activate"
PAUSE = "pause"
CLOSE = "close"


def api_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


def action_url(job_id, action: str) -> str:
    return f"/api/v1/jobs/{job_id}/{action}/"


@pytest.fixture
def employer(make_user):
    return make_user("employer_hr")


@pytest.fixture
def profile(employer):
    return EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")


def make_job(profile, status=Job.Status.DRAFT) -> Job:
    return Job.objects.create(
        employer=profile,
        title="Backend Engineer",
        description="Build and run the screening API.",
        status=status,
    )


class TestActivate:
    def test_a_draft_becomes_active_and_is_audited(self, employer, profile):
        job = make_job(profile)

        response = api_client(employer).post(action_url(job.pk, ACTIVATE))

        assert response.status_code == 200
        assert response.data["status"] == "active"
        job.refresh_from_db()
        assert job.status == Job.Status.ACTIVE

        entry = AuditLogEntry.objects.get()
        assert entry.action == "job.activated"
        assert entry.resource_type == "job"
        assert entry.resource_id == job.pk
        assert entry.actor_id == employer.pk
        assert entry.details == {"from": "draft", "to": "active"}

    def test_a_paused_job_can_resume(self, employer, profile):
        job = make_job(profile, Job.Status.PAUSED)

        response = api_client(employer).post(action_url(job.pk, ACTIVATE))

        assert response.status_code == 200
        job.refresh_from_db()
        assert job.status == Job.Status.ACTIVE

    def test_activating_an_active_job_is_a_no_op(self, employer, profile):
        job = make_job(profile, Job.Status.ACTIVE)

        response = api_client(employer).post(action_url(job.pk, ACTIVATE))

        assert response.status_code == 200
        assert response.data["status"] == "active"
        assert AuditLogEntry.objects.count() == 0

    def test_a_closed_job_cannot_be_reactivated(self, employer, profile):
        job = make_job(profile, Job.Status.CLOSED)

        response = api_client(employer).post(action_url(job.pk, ACTIVATE))

        assert response.status_code == 409
        assert "closed" in response.data["detail"].lower()
        job.refresh_from_db()
        assert job.status == Job.Status.CLOSED
        assert AuditLogEntry.objects.count() == 0


class TestPause:
    def test_an_active_job_is_paused_and_audited(self, employer, profile):
        job = make_job(profile, Job.Status.ACTIVE)

        response = api_client(employer).post(action_url(job.pk, PAUSE))

        assert response.status_code == 200
        assert response.data["status"] == "paused"
        job.refresh_from_db()
        assert job.status == Job.Status.PAUSED
        assert AuditLogEntry.objects.get().details == {
            "from": "active",
            "to": "paused",
        }

    def test_pausing_a_paused_job_is_a_no_op(self, employer, profile):
        job = make_job(profile, Job.Status.PAUSED)

        response = api_client(employer).post(action_url(job.pk, PAUSE))

        assert response.status_code == 200
        assert AuditLogEntry.objects.count() == 0

    @pytest.mark.parametrize("status", [Job.Status.DRAFT, Job.Status.CLOSED])
    def test_a_job_that_was_not_published_cannot_be_paused(
        self, employer, profile, status
    ):
        """A draft has nothing to pause; a closed job is terminal."""
        job = make_job(profile, status)

        response = api_client(employer).post(action_url(job.pk, PAUSE))

        assert response.status_code == 409
        job.refresh_from_db()
        assert job.status == status
        assert AuditLogEntry.objects.count() == 0


class TestClose:
    @pytest.mark.parametrize("status", [Job.Status.ACTIVE, Job.Status.PAUSED])
    def test_a_published_job_is_closed_and_audited(self, employer, profile, status):
        job = make_job(profile, status)

        response = api_client(employer).post(action_url(job.pk, CLOSE))

        assert response.status_code == 200
        assert response.data["status"] == "closed"
        job.refresh_from_db()
        assert job.status == Job.Status.CLOSED
        assert AuditLogEntry.objects.get().details == {"from": status, "to": "closed"}

    def test_closing_a_closed_job_is_a_no_op(self, employer, profile):
        job = make_job(profile, Job.Status.CLOSED)

        response = api_client(employer).post(action_url(job.pk, CLOSE))

        assert response.status_code == 200
        assert AuditLogEntry.objects.count() == 0

    def test_a_draft_is_deleted_rather_than_closed(self, employer, profile):
        job = make_job(profile)

        response = api_client(employer).post(action_url(job.pk, CLOSE))

        assert response.status_code == 409
        job.refresh_from_db()
        assert job.status == Job.Status.DRAFT
        assert AuditLogEntry.objects.count() == 0


class TestActionBoundary:
    def test_an_action_writes_status_only(self, employer, profile):
        """A body smuggled into the POST must not edit content."""
        job = make_job(profile, Job.Status.ACTIVE)

        api_client(employer).post(
            action_url(job.pk, PAUSE),
            {"title": "Renamed", "description": "x"},
            format="json",
        )

        job.refresh_from_db()
        assert job.title == "Backend Engineer"
        assert job.description == "Build and run the screening API."

    def test_the_entry_carries_no_application_data(self, employer, profile):
        job = make_job(profile)

        api_client(employer).post(action_url(job.pk, ACTIVATE))

        assert set(AuditLogEntry.objects.get().details) == {"from", "to"}


class TestOwnership:
    @pytest.mark.parametrize("action", [ACTIVATE, PAUSE, CLOSE])
    def test_another_employers_job_is_404(self, profile, make_user, action):
        job = make_job(profile, Job.Status.ACTIVE)
        other = make_user("employer_hr")
        EmployerProfile.objects.create(user=other, company_name="Other Ltd")

        response = api_client(other).post(action_url(job.pk, action))

        assert response.status_code == 404
        job.refresh_from_db()
        assert job.status == Job.Status.ACTIVE
        assert AuditLogEntry.objects.count() == 0

    @pytest.mark.parametrize("action", [ACTIVATE, PAUSE, CLOSE])
    def test_a_candidate_is_403(self, profile, make_user, action):
        job = make_job(profile, Job.Status.ACTIVE)

        response = api_client(make_user("candidate")).post(action_url(job.pk, action))

        assert response.status_code == 403
        job.refresh_from_db()
        assert job.status == Job.Status.ACTIVE

    def test_an_interviewer_is_403(self, profile, make_user):
        job = make_job(profile, Job.Status.ACTIVE)

        response = api_client(make_user("interviewer")).post(action_url(job.pk, PAUSE))

        assert response.status_code == 403

    def test_anonymous_is_401(self, profile):
        job = make_job(profile)

        response = APIClient().post(action_url(job.pk, ACTIVATE))

        assert response.status_code == 401
        job.refresh_from_db()
        assert job.status == Job.Status.DRAFT

    def test_an_employer_without_a_profile_is_404(self, profile, make_user):
        job = make_job(profile)

        response = api_client(make_user("employer_hr")).post(
            action_url(job.pk, ACTIVATE)
        )

        assert response.status_code == 404
        assert Job.objects.get(pk=job.pk).status == Job.Status.DRAFT

    def test_an_unknown_id_is_404(self, employer, profile):
        response = api_client(employer).post(
            action_url("00000000-0000-0000-0000-000000000000", ACTIVATE)
        )

        assert response.status_code == 404
