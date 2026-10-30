"""Phase 1 end-to-end: the browser journey from signup to a shortlist (Arch Doc §10).

This is the one test that walks the whole Phase 1 chain through the HTML
surfaces, in the order two real people use them:

    employer registers -> verifies -> onboards -> creates a job -> activates it
    candidate registers -> verifies -> builds a profile -> applies
    employer sees the alias, never the identity -> shortlists
    candidate sees the status -> both sides have notifications

**Why it exists.** Fourteen batches each tested their own surface; nothing yet
proved the seams hold: that the job the employer activates is the job the
candidate can see, that the application the candidate creates is the row the
employer decides, and that the decision reaches the candidate's tracker and
inbox. Only the role groups are seeded by a fixture; every other row is built by
the request that owns it, so a page that stopped writing its row fails here even
when its own unit test still passes.

House rules that matter here:

* **PostgreSQL only.** `tests/conftest.py` has no SQLite fallback.
* **`transaction=True`** because the email half of registration and notification
  is dispatched from `transaction.on_commit`, which never fires inside the
  wrapped test transaction (`tests/notifications/test_notification_wiring.py`
  documents the same reason).
* **`.delay` is patched on both tasks.** The assertions therefore cover the
  queue request -- the ids -- without needing a broker, which CI does not run.
* **No fabricated shortcuts.** A failure state is exercised where the journey
  meets it: an unverified account cannot sign in, and a candidate cannot take
  the employer's decision.
"""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.test import Client

from accounts.models import User
from accounts.services import make_verification_token
from accounts.tasks import send_verification_email
from candidates.models import CandidateProfile
from candidates.services import alias_for
from core.models import AuditLogEntry
from employers.models import EmployerProfile
from matching.models import Application, Job
from notifications.models import Notification
from notifications.tasks import send_notification_email

pytestmark = pytest.mark.django_db(transaction=True)

REGISTER_URL = "/register/"
CHECK_EMAIL_URL = "/register/check-email/"
VERIFY_URL = "/verify-email/"
LOGIN_URL = "/login/"

# Long enough for `AUTH_PASSWORD_VALIDATORS`, not a known breached password and
# not similar to the names below.
PASSWORD = "Wanderlust7Quartz-Meadow"

EMPLOYER_EMAIL = "hr@acme.example"
EMPLOYER_FIRST = "Imran"
EMPLOYER_LAST = "Chowdhury"

CANDIDATE_EMAIL = "secret-candidate@example.com"
CANDIDATE_FIRST = "Zubaida"
CANDIDATE_LAST = "Marchetti"

JOB_TITLE = "Backend Engineer"
JOB_DESCRIPTION = "Build and run the application screening service."


@pytest.fixture
def role_groups(db):
    """The seeded role groups, exactly as `manage.py seed` installs them.

    Repeated here rather than imported from a sibling app's `conftest.py`, which
    pytest does not share, and not hand-built: the fixture is the D-2 source of
    truth (AGENTS.md).
    """
    call_command("loaddata", "groups", verbosity=0)


def register(
    client: Client,
    *,
    role: str,
    first_name: str,
    last_name: str,
    email: str,
) -> User:
    """Register through page #6 and return the unverified account."""
    response = client.post(
        REGISTER_URL,
        {
            "role": role,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "password": PASSWORD,
            "consent": "on",
        },
    )

    assert response.status_code == 302
    assert response.url == CHECK_EMAIL_URL
    user = User.objects.get(email=email)
    assert user.email_verified is False
    return user


def verify(client: Client, user: User) -> None:
    """Follow the emailed verification link (page #11)."""
    token = make_verification_token(user)

    response = client.get(VERIFY_URL, {"token": token})

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email_verified is True


def login(client: Client, email: str):
    """Submit page #7 with the shared password."""
    return client.post(LOGIN_URL, {"email": email, "password": PASSWORD})


def assert_no_candidate_identity(html: str, candidate_user: User) -> None:
    """REQ-FR-029/054: an employer surface carries the alias and nothing else.

    The internal user id and the profile id are included because the requirement
    names the internal UUID, not only the name and the address. A page that
    exposes an id is one join away from exposing its owner.
    """
    secrets = (
        CANDIDATE_FIRST,
        CANDIDATE_LAST,
        CANDIDATE_EMAIL,
        str(candidate_user.pk),
    )
    for secret in secrets:
        assert secret not in html


def test_phase_one_journey(role_groups, monkeypatch):
    """Register, verify, onboard, create/activate a job, apply, shortlist, notify.

    One test rather than a chain of fixtures: the point is that the sequence
    works against a real database with the pages' own side effects, and a
    fixture that pre-creates the job would skip the create and activate steps
    that make the public job board reachable.
    """
    verification_ids: list[str] = []
    notification_ids: list[str] = []
    monkeypatch.setattr(
        send_verification_email,
        "delay",
        lambda user_id: verification_ids.append(user_id),
    )
    monkeypatch.setattr(
        send_notification_email,
        "delay",
        lambda notification_id: notification_ids.append(notification_id),
    )

    # ------------------------------------------------------------- employer
    employer_client = Client()
    employer = register(
        employer_client,
        role="employer_hr",
        first_name=EMPLOYER_FIRST,
        last_name=EMPLOYER_LAST,
        email=EMPLOYER_EMAIL,
    )

    # The verification step is load-bearing: before it, sign-in is refused with
    # the documented sentence rather than a generic credential error.
    refused = login(employer_client, EMPLOYER_EMAIL)
    assert refused.status_code == 200
    assert "Confirm your email address before signing in." in refused.content.decode()

    verify(employer_client, employer)
    assert login(employer_client, EMPLOYER_EMAIL).status_code == 302

    response = employer_client.post(
        "/employer/onboarding/",
        {
            "company_name": "Acme Ltd",
            "industry": "Software",
            "company_size": "40",
            "show_company_name": "on",
        },
    )

    assert response.status_code == 302
    assert response.url == "/employer/company/"
    profile = EmployerProfile.objects.get(user=employer)
    assert profile.company_name == "Acme Ltd"

    response = employer_client.post(
        "/employer/jobs/new/",
        {
            "title": JOB_TITLE,
            "description": JOB_DESCRIPTION,
            "location": "Dhaka",
            "remote_allowed": "on",
            "experience_level": "senior",
        },
    )

    assert response.status_code == 302
    job = Job.objects.get()
    assert job.employer == profile
    assert job.status == Job.Status.DRAFT
    assert response.url == f"/employer/jobs/{job.pk}/edit/"

    response = employer_client.post(f"/employer/jobs/{job.pk}/activate/")

    assert response.status_code == 302
    job.refresh_from_db()
    assert job.status == Job.Status.ACTIVE

    # ------------------------------------------------------------ candidate
    candidate_client = Client()
    candidate_user = register(
        candidate_client,
        role="candidate",
        first_name=CANDIDATE_FIRST,
        last_name=CANDIDATE_LAST,
        email=CANDIDATE_EMAIL,
    )
    verify(candidate_client, candidate_user)

    response = login(candidate_client, CANDIDATE_EMAIL)

    assert response.status_code == 302
    assert response.url == "/candidate/profile/"

    # Login lands on the profile page, which sends a candidate without a profile
    # to onboarding (page #14).
    response = candidate_client.get("/candidate/profile/")
    assert response.status_code == 302
    assert response.url == "/candidate/onboarding/"

    response = candidate_client.post(
        "/candidate/onboarding/",
        {
            "title": "Backend developer",
            "bio": "Six years of Python services.",
            "location": "Dhaka",
            "remote_ok": "on",
        },
    )

    assert response.status_code == 302
    assert response.url == "/candidate/profile/"
    candidate_profile = CandidateProfile.objects.get(user=candidate_user)
    assert candidate_profile.title == "Backend developer"

    # ---------------------------------------------------------------- apply
    job_url = f"/jobs/{job.pk}/"
    content = candidate_client.get(job_url).content.decode()
    assert JOB_TITLE in content
    assert f'action="{job_url}apply/"' in content

    response = candidate_client.post(f"{job_url}apply/")

    assert response.status_code == 302
    assert response.url == job_url
    application = Application.objects.get(job=job, candidate=candidate_profile)
    assert application.status == Application.Status.APPLIED

    content = candidate_client.get(job_url).content.decode()
    assert "Application sent." in content
    assert f'action="{job_url}apply/"' not in content

    # ----------------------------------------------- the alias, not the person
    inbox_url = f"/employer/jobs/{job.pk}/applications/"
    response = employer_client.get(inbox_url)

    assert response.status_code == 200
    content = response.content.decode()
    alias = alias_for(profile, candidate_profile)
    assert alias in content
    assert CANDIDATE_FIRST not in content
    assert CANDIDATE_LAST not in content
    assert CANDIDATE_EMAIL not in content
    assert str(candidate_user.pk) not in content

    # A candidate cannot perform the employer's decision, even with the id.
    review_url = f"/employer/applications/{application.pk}/"
    assert candidate_client.get(review_url).status_code == 403
    assert candidate_client.post(f"{review_url}shortlist/").status_code == 403
    application.refresh_from_db()
    assert application.status == Application.Status.APPLIED

    # ----------------------------------------------------------- shortlist
    response = employer_client.post(f"{review_url}shortlist/")

    assert response.status_code == 302
    assert response.url == review_url
    application.refresh_from_db()
    assert application.status == Application.Status.SHORTLISTED
    assert application.decided_by == employer
    assert application.shortlisted_at is not None

    entry = AuditLogEntry.objects.get(action="application.shortlisted")
    assert entry.resource_id == application.pk
    details = str(entry.details)
    for secret in (CANDIDATE_FIRST, CANDIDATE_LAST, CANDIDATE_EMAIL, alias):
        assert secret not in details

    # -------------------------------------------------- candidate sees status
    application_url = f"/candidate/applications/{application.pk}/"
    content = candidate_client.get(application_url).content.decode()
    assert "Shortlisted" in content

    content = candidate_client.get("/candidate/applications/").content.decode()
    assert JOB_TITLE in content
    assert "Shortlisted" in content

    # -------------------------------------------------------- notifications
    employer_notifications = list(
        Notification.objects.filter(recipient=employer).order_by("created_at")
    )
    candidate_notifications = list(
        Notification.objects.filter(recipient=candidate_user).order_by("created_at")
    )

    assert len(employer_notifications) == 1
    assert len(candidate_notifications) == 2
    assert [row.title for row in candidate_notifications] == [
        "Application received",
        "Your application was shortlisted",
    ]
    assert [row.title for row in employer_notifications] == ["New application"]

    # REQ-FR-054: the employer's copy names the alias, never the person.
    employer_message = employer_notifications[0].message
    assert alias in employer_message
    assert CANDIDATE_FIRST not in employer_message
    assert CANDIDATE_LAST not in employer_message
    assert CANDIDATE_EMAIL not in employer_message

    content = candidate_client.get("/notifications/").content.decode()
    assert "Application received" in content
    assert "Your application was shortlisted" in content
    assert application_url in content

    content = employer_client.get("/notifications/").content.decode()
    assert "New application" in content
    assert alias in content
    assert_no_candidate_identity(content, candidate_user)

    # The email half is queued on commit: two verification mails and three
    # notification mails (one application pair plus the candidate's decision).
    assert len(verification_ids) == 2
    assert set(verification_ids) == {str(employer.pk), str(candidate_user.pk)}
    assert len(notification_ids) == 3
    assert set(notification_ids) == {
        str(row.pk) for row in employer_notifications + candidate_notifications
    }

    # The journey created exactly the rows it says it did, in the right role.
    assert employer.groups.filter(name="employer_hr").exists()
    assert candidate_user.groups.filter(name="candidate").exists()
