"""Where notifications are written (REQ-FR-022, REQ-FR-023, batch 1.43).

The requirements are two short sentences -- "candidate and employer notified" for
an application, "notification sent" for a status change -- and almost everything
that can go wrong is in the wiring:

* **one notification per event, not per surface.** The rows are written in
  `matching.services`, so the apply page and the apply endpoint both produce one
  pair, and a decision produces one message;
* **nothing is notified when nothing happened.** A duplicate apply, a repeated
  decision, a refused transition and another employer's row all leave the table
  untouched;
* **the employer's copy is alias-only** (REQ-FR-029/054): no name, no email, no
  internal candidate UUID, in any column or in the raw row text;
* **the email is queued after the commit**, with the notification id as the only
  payload.

`transaction=True` on the module: the dispatch runs from `transaction.on_commit`,
which never fires inside the wrapped test transaction.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from candidates.models import CandidateAlias, CandidateProfile
from employers.models import EmployerProfile
from matching.models import Application, Job
from notifications.models import Notification
from notifications.tasks import send_notification_email

pytestmark = pytest.mark.django_db(transaction=True)

Status = Application.Status
Gate = Application.AssessmentGateStatus


def api_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


def apply_url(job) -> str:
    return f"/api/v1/jobs/{job.pk}/apply/"


def shortlist_url(application) -> str:
    return f"/api/v1/applications/{application.pk}/shortlist/"


def reject_url(application) -> str:
    return f"/api/v1/applications/{application.pk}/reject/"


def recipient_notifications(user):
    return Notification.objects.filter(recipient=user).order_by("created_at")


@pytest.fixture
def dispatched(monkeypatch):
    """Record the ids `notify()` asks Celery to deliver."""
    sent: list[str] = []

    def _delay(notification_id):
        sent.append(notification_id)

    monkeypatch.setattr(send_notification_email, "delay", _delay)
    return sent


@pytest.fixture
def employer(make_user):
    return make_user("employer_hr")


@pytest.fixture
def profile(employer):
    return EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")


@pytest.fixture
def other_employer(make_user):
    return make_user("employer_hr")


@pytest.fixture
def other_profile(other_employer):
    return EmployerProfile.objects.create(user=other_employer, company_name="Beta Ltd")


@pytest.fixture
def job(profile):
    return Job.objects.create(
        employer=profile,
        title="Backend Engineer",
        status=Job.Status.ACTIVE,
    )


@pytest.fixture
def candidate_user(make_user):
    """An account whose identity is recognisable in a raw row."""
    return make_user(
        "candidate",
        email="distinctive-candidate@example.com",
        first_name="Zubaida",
        last_name="Rahman",
    )


@pytest.fixture
def candidate(candidate_user):
    return CandidateProfile.objects.create(
        user=candidate_user,
        title="Backend developer",
        location="Dhaka",
        skills=["Python"],
    )


@pytest.fixture
def application(job, candidate):
    return Application.objects.create(job=job, candidate=candidate)


# ------------------------------------------------------------- application


def test_applying_notifies_the_candidate_and_the_employer(
    candidate, profile, job, dispatched
):
    response = api_client(candidate.user).post(apply_url(job))

    assert response.status_code == 201
    application = Application.objects.get(job=job, candidate=candidate)

    candidate_rows = recipient_notifications(candidate.user)
    assert candidate_rows.count() == 1
    candidate_row = candidate_rows.get()
    assert candidate_row.notification_type == Notification.Type.APPLICATION_UPDATE
    assert candidate_row.title == "Application received"
    assert "Backend Engineer" in candidate_row.message
    assert candidate_row.url == f"/candidate/applications/{application.pk}/"
    assert candidate_row.read is False

    employer_rows = recipient_notifications(profile.user)
    assert employer_rows.count() == 1
    employer_row = employer_rows.get()
    assert employer_row.notification_type == Notification.Type.APPLICATION_UPDATE
    assert employer_row.title == "New application"
    assert "Backend Engineer" in employer_row.message
    assert employer_row.url == f"/employer/applications/{application.pk}/"

    # Two rows, two emails, ids only.
    assert len(dispatched) == 2
    assert set(dispatched) == {str(candidate_row.pk), str(employer_row.pk)}


def test_the_employer_copy_names_the_alias(candidate, profile, job):
    api_client(candidate.user).post(apply_url(job))

    alias = CandidateAlias.objects.get(employer=profile, candidate=candidate).alias
    row = recipient_notifications(profile.user).get()

    assert alias in row.message
    # The alias exists because the message needed one, not because a page ran.
    assert alias.startswith("C-")


def test_the_employer_copy_carries_no_candidate_identity(candidate, profile, job):
    api_client(candidate.user).post(apply_url(job))

    row = recipient_notifications(profile.user).get()
    rendered = f"{row.title} {row.message} {row.url}"

    assert "Zubaida" not in rendered
    assert "Rahman" not in rendered
    assert candidate.user.email not in rendered
    assert str(candidate.pk) not in rendered


def test_a_duplicate_apply_notifies_nobody(candidate, profile, job, dispatched):
    client = api_client(candidate.user)
    assert client.post(apply_url(job)).status_code == 201

    assert client.post(apply_url(job)).status_code == 409

    assert Notification.objects.count() == 2
    assert len(dispatched) == 2


def test_a_paused_job_notifies_nobody(candidate, job, dispatched):
    job.status = Job.Status.PAUSED
    job.save(update_fields=["status"])

    response = api_client(candidate.user).post(apply_url(job))

    assert response.status_code == 409
    assert not Notification.objects.exists()
    assert dispatched == []


# ---------------------------------------------------------------- decision


def test_shortlisting_notifies_the_candidate(application, profile, dispatched):
    response = api_client(profile.user).post(shortlist_url(application))

    assert response.status_code == 200
    row = recipient_notifications(application.candidate.user).get()
    assert row.title == "Your application was shortlisted"
    assert "Backend Engineer" in row.message
    assert "shortlisted" in row.message
    assert row.url == f"/candidate/applications/{application.pk}/"
    assert dispatched == [str(row.pk)]
    # The employer made the decision; they are not notified about their own click.
    assert not Notification.objects.filter(recipient=profile.user).exists()


def test_rejecting_notifies_the_candidate(application, profile):
    response = api_client(profile.user).post(reject_url(application))

    assert response.status_code == 200
    row = recipient_notifications(application.candidate.user).get()
    assert row.title == "Your application was rejected"
    assert "rejected" in row.message


def test_rejecting_a_not_matched_application_notifies_once(application, profile):
    application.status = Status.NOT_MATCHED
    application.save(update_fields=["status"])

    response = api_client(profile.user).post(reject_url(application))

    assert response.status_code == 200
    assert recipient_notifications(application.candidate.user).count() == 1


def test_a_repeated_decision_notifies_once(application, profile, dispatched):
    client = api_client(profile.user)
    assert client.post(shortlist_url(application)).status_code == 200

    assert client.post(shortlist_url(application)).status_code == 200

    assert recipient_notifications(application.candidate.user).count() == 1
    assert len(dispatched) == 1


def test_a_refused_decision_notifies_nobody(application, profile, dispatched):
    application.status = Status.HIRED
    application.save(update_fields=["status"])

    response = api_client(profile.user).post(reject_url(application))

    assert response.status_code == 409
    assert not Notification.objects.exists()
    assert dispatched == []


def test_a_gate_blocked_shortlist_notifies_nobody(application, profile, dispatched):
    application.assessment_gate_status = Gate.PENDING
    application.save(update_fields=["assessment_gate_status"])

    response = api_client(profile.user).post(shortlist_url(application))

    assert response.status_code == 409
    assert not Notification.objects.exists()
    assert dispatched == []


def test_another_employers_decision_notifies_nobody(
    application, other_profile, dispatched
):
    response = api_client(other_profile.user).post(shortlist_url(application))

    assert response.status_code == 404
    assert not Notification.objects.exists()
    assert dispatched == []


# ------------------------------------------------------------- the mailbox


def test_the_queued_ids_are_the_notification_ids(candidate, profile, job, dispatched):
    api_client(candidate.user).post(apply_url(job))

    assert set(dispatched) == {
        str(pk) for pk in Notification.objects.values_list("pk", flat=True)
    }
