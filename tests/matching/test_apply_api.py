"""Apply-to-a-job API (REQ-FR-022, batch 1.36).

The endpoint is the first candidate write that creates an employer-visible row,
so the tests cover more than the happy path:

* only `active` is appliable (Arch Doc §4.3 rule 5), and a draft is a 404 rather
  than a 409 because it was never public;
* a duplicate is a 409 from the database constraint, not from a pre-check that a
  race could slip past;
* the applicant is always the caller -- a `candidate` key in the body is ignored;
* the response carries no candidate identity (REQ-FR-029, REQ-FR-054);
* the role gate is `candidate` only.

The service exceptions are also exercised directly: the rule is HTTP-free and
batch 1.37's page must be able to reuse it without a second status check.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from candidates.models import CandidateProfile
from employers.models import EmployerProfile
from matching.models import Application, Job
from matching.services import (
    ALREADY_APPLIED,
    JOB_NOT_OPEN,
    DuplicateApplication,
    JobNotOpen,
    apply_to_job,
)

pytestmark = pytest.mark.django_db


def api_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


@pytest.fixture
def employer(make_user):
    return EmployerProfile.objects.create(
        user=make_user("employer_hr"),
        company_name="Acme Ltd",
    )


@pytest.fixture
def candidate(make_user):
    user = make_user(
        "candidate",
        email="apply-candidate@example.com",
        first_name="Zubaida",
        last_name="Rahman",
    )
    return CandidateProfile.objects.create(user=user, title="Backend developer")


@pytest.fixture
def job(employer):
    return Job.objects.create(
        employer=employer,
        title="Backend Engineer",
        status=Job.Status.ACTIVE,
    )


def apply_url(job: Job) -> str:
    return f"/api/v1/jobs/{job.pk}/apply/"


# ------------------------------------------------------------------ success


def test_a_candidate_applies_to_an_active_job(candidate, job):
    response = api_client(candidate.user).post(apply_url(job))

    assert response.status_code == 201
    assert response.json()["job_id"] == str(job.pk)
    assert response.json()["status"] == Application.Status.APPLIED
    assert set(response.json()) == {"id", "job_id", "status", "created_at"}

    application = Application.objects.get()
    assert application.job == job
    assert application.candidate == candidate


def test_the_response_carries_no_candidate_identity(candidate, job):
    response = api_client(candidate.user).post(apply_url(job))
    body = response.content.decode()
    user = candidate.user

    assert str(candidate.pk) not in body
    assert str(user.pk) not in body
    assert user.email not in body
    assert user.first_name not in body
    assert user.last_name not in body


def test_a_body_cannot_name_another_candidate(candidate, job, make_user):
    other = CandidateProfile.objects.create(user=make_user("candidate"))

    response = api_client(candidate.user).post(
        apply_url(job),
        {"candidate": str(other.pk)},
        format="json",
    )

    assert response.status_code == 201
    assert Application.objects.get().candidate == candidate


def test_two_candidates_may_apply_to_the_same_job(candidate, job, make_user):
    other = CandidateProfile.objects.create(user=make_user("candidate"))

    assert api_client(candidate.user).post(apply_url(job)).status_code == 201
    assert api_client(other.user).post(apply_url(job)).status_code == 201
    assert Application.objects.filter(job=job).count() == 2


# ---------------------------------------------------------------- refusals


def test_a_duplicate_application_is_a_conflict(candidate, job):
    client = api_client(candidate.user)

    assert client.post(apply_url(job)).status_code == 201
    response = client.post(apply_url(job))

    assert response.status_code == 409
    assert response.json()["detail"] == ALREADY_APPLIED
    assert Application.objects.count() == 1


@pytest.mark.parametrize("job_status", [Job.Status.PAUSED, Job.Status.CLOSED])
def test_a_non_active_published_job_is_a_conflict(candidate, job, job_status):
    job.status = job_status
    job.save(update_fields=["status"])

    response = api_client(candidate.user).post(apply_url(job))

    assert response.status_code == 409
    assert response.json()["detail"] == JOB_NOT_OPEN
    assert Application.objects.count() == 0


def test_a_draft_job_is_not_found_rather_than_conflicted(candidate, job):
    """A draft was never public (REQ-FR-025); 409 would confirm it exists."""
    job.status = Job.Status.DRAFT
    job.save(update_fields=["status"])

    response = api_client(candidate.user).post(apply_url(job))

    assert response.status_code == 404
    assert Application.objects.count() == 0


def test_an_unknown_job_is_not_found(candidate):
    response = api_client(candidate.user).post(
        "/api/v1/jobs/00000000-0000-0000-0000-000000000000/apply/"
    )

    assert response.status_code == 404
    assert Application.objects.count() == 0


def test_a_candidate_without_a_profile_is_a_conflict(make_user, job):
    user = make_user("candidate")

    response = api_client(user).post(apply_url(job))

    assert response.status_code == 409
    assert "candidate profile" in response.json()["detail"].lower()
    assert Application.objects.count() == 0


def test_an_anonymous_caller_is_unauthenticated(job):
    response = APIClient().post(apply_url(job))

    assert response.status_code == 401
    assert Application.objects.count() == 0


@pytest.mark.parametrize("role", ["employer_hr", "employer_manager", "interviewer"])
def test_a_non_candidate_role_is_forbidden(make_user, job, role):
    response = api_client(make_user(role)).post(apply_url(job))

    assert response.status_code == 403
    assert Application.objects.count() == 0


def test_a_platform_admin_is_forbidden(make_user, job):
    response = api_client(make_user(is_staff=True)).post(apply_url(job))

    assert response.status_code == 403
    assert Application.objects.count() == 0


# ----------------------------------------------------------------- service


def test_the_service_creates_an_applied_application(candidate, job):
    application = apply_to_job(candidate=candidate, job=job)

    assert application.status == Application.Status.APPLIED
    assert application.pk is not None


def test_the_service_refuses_a_non_active_job(candidate, job):
    job.status = Job.Status.CLOSED
    job.save(update_fields=["status"])

    with pytest.raises(JobNotOpen):
        apply_to_job(candidate=candidate, job=job)


def test_the_service_translates_the_unique_constraint(candidate, job):
    apply_to_job(candidate=candidate, job=job)

    with pytest.raises(DuplicateApplication):
        apply_to_job(candidate=candidate, job=job)
