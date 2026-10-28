"""The Apply button on page #5 (REQ-FR-022, batch 1.37).

The API tests in `tests/matching/test_apply_api.py` pin the JSON contract. These
pin the browser path: the four states design.md S05 calls for (guest, candidate
with a profile, candidate without one, already applied), the POST/Redirect/Get
confirmation, and the guard order.

The two apply controls (desktop sticky card and mobile bottom bar) are asserted
by counting the form action. A page that wires only one of them looks correct at
one viewport and dead at the other, which is exactly the failure this batch is
meant to close.
"""

from __future__ import annotations

import pytest
from django.test import Client

from candidates.models import CandidateProfile
from employers.models import EmployerProfile
from matching.models import Application, Job

pytestmark = pytest.mark.django_db


@pytest.fixture
def employer(make_user):
    return EmployerProfile.objects.create(
        user=make_user("employer_hr"),
        company_name="Acme Ltd",
    )


@pytest.fixture
def job(employer):
    return Job.objects.create(
        employer=employer,
        title="Backend Engineer",
        status=Job.Status.ACTIVE,
    )


@pytest.fixture
def candidate(make_user):
    user = make_user("candidate", email="apply-ui@example.com")
    return CandidateProfile.objects.create(user=user, title="Backend developer")


def detail_url(job: Job) -> str:
    return f"/jobs/{job.pk}/"


def apply_url(job: Job) -> str:
    return f"/jobs/{job.pk}/apply/"


# ------------------------------------------------------------------- states


def test_a_guest_is_prompted_to_log_in(job):
    response = Client().get(detail_url(job))
    body = response.content

    assert response.status_code == 200
    assert b"Log in to apply" in body
    assert b"disabled" not in body


def test_a_candidate_with_a_profile_gets_a_real_submit_form(job, candidate):
    client = Client()
    client.force_login(candidate.user)

    response = client.get(detail_url(job))
    body = response.content

    assert response.status_code == 200
    assert body.count(f'action="{apply_url(job)}"'.encode()) == 2
    assert b"csrfmiddlewaretoken" in body
    assert b"Complete your profile" not in body


def test_a_candidate_without_a_profile_is_sent_to_onboarding(job, make_user):
    user = make_user("candidate")
    client = Client()
    client.force_login(user)

    response = client.get(detail_url(job))
    body = response.content

    assert response.status_code == 200
    assert b"Complete your profile to apply" in body
    assert f'action="{apply_url(job)}"'.encode() not in body


def test_an_employer_is_told_that_candidates_apply(job, make_user):
    client = Client()
    client.force_login(make_user("employer_hr"))

    response = client.get(detail_url(job))

    assert b"Applications are submitted by candidate accounts." in response.content


# ------------------------------------------------------------------ success


def test_a_candidate_applies_and_sees_the_confirmation(job, candidate):
    client = Client()
    client.force_login(candidate.user)

    response = client.post(apply_url(job), follow=True)

    assert response.status_code == 200
    assert Application.objects.filter(job=job, candidate=candidate).count() == 1
    assert b"Application sent." in response.content
    assert b"Application sent" in response.content
    assert b"Your application" in response.content
    # The form is gone: the page now describes the row, it does not offer to
    # create a second one.
    assert f'action="{apply_url(job)}"'.encode() not in response.content


def test_the_already_applied_state_shows_the_date(job, candidate):
    Application.objects.create(job=job, candidate=candidate)
    client = Client()
    client.force_login(candidate.user)

    response = client.get(detail_url(job))

    assert b"Application sent" in response.content
    assert b"You applied" in response.content
    assert f'action="{apply_url(job)}"'.encode() not in response.content


# ---------------------------------------------------------------- refusals


def test_a_duplicate_click_is_information_not_an_error(job, candidate):
    client = Client()
    client.force_login(candidate.user)

    client.post(apply_url(job))
    response = client.post(apply_url(job), follow=True)

    assert response.status_code == 200
    assert Application.objects.count() == 1
    assert b"You have already applied to this job." in response.content


def test_a_candidate_without_a_profile_is_redirected_to_onboarding(job, make_user):
    user = make_user("candidate")
    client = Client()
    client.force_login(user)

    response = client.post(apply_url(job))

    assert response.status_code == 302
    assert response.url == "/candidate/onboarding/"
    assert Application.objects.count() == 0


def test_a_closed_job_cannot_be_applied_to(job, candidate):
    job.status = Job.Status.CLOSED
    job.save(update_fields=["status"])
    client = Client()
    client.force_login(candidate.user)

    response = client.post(apply_url(job))

    assert response.status_code == 404
    assert Application.objects.count() == 0


def test_a_draft_job_cannot_be_applied_to(job, candidate):
    job.status = Job.Status.DRAFT
    job.save(update_fields=["status"])
    client = Client()
    client.force_login(candidate.user)

    response = client.post(apply_url(job))

    assert response.status_code == 404
    assert Application.objects.count() == 0


def test_an_anonymous_post_is_redirected_to_login(job):
    response = Client().post(apply_url(job))

    assert response.status_code == 302
    assert response.url.startswith("/login/")
    assert Application.objects.count() == 0


@pytest.mark.parametrize("role", ["employer_hr", "employer_manager", "interviewer"])
def test_a_non_candidate_post_is_forbidden(job, make_user, role):
    client = Client()
    client.force_login(make_user(role))

    response = client.post(apply_url(job))

    assert response.status_code == 403
    assert Application.objects.count() == 0


def test_a_platform_admin_post_is_forbidden(job, make_user):
    client = Client()
    client.force_login(make_user(is_staff=True))

    response = client.post(apply_url(job))

    assert response.status_code == 403
    assert Application.objects.count() == 0


def test_get_is_not_allowed_on_the_apply_action(job, candidate):
    client = Client()
    client.force_login(candidate.user)

    response = client.get(apply_url(job))

    assert response.status_code == 405
    assert Application.objects.count() == 0


def test_the_post_is_csrf_protected(job, candidate):
    client = Client(enforce_csrf_checks=True)
    client.force_login(candidate.user)

    response = client.post(apply_url(job))

    assert response.status_code == 403
    assert Application.objects.count() == 0
