"""Notification rows and their email (REQ-FR-022, REQ-FR-023, batch 1.43).

Arch Doc §5.1:

    CREATE TABLE notifications (
        id UUID PRIMARY KEY, recipient_id UUID REFERENCES users(id) ON DELETE CASCADE,
        title VARCHAR(200), message TEXT, notification_type VARCHAR(30),
        read BOOLEAN DEFAULT FALSE, url VARCHAR(500), created_at TIMESTAMPTZ
    );

What these tests pin down:

* **the vocabulary is the documented five values**, so a sixth cannot appear by
  typo and batch 1.44's type filter has a closed set to render;
* **the row is per recipient** and disappears with the account (the DDL's
  `ON DELETE CASCADE`), because a notification addressed to a deleted user is
  personal data with nobody to serve;
* **the email is queued after the commit and carries an id, not an address** --
  the broker payload is JSON in Redis;
* **the email body is the stored copy plus an absolute link**, built from
  `settings.SITE_URL` because a worker has no request;
* **a missing row or an inactive account is a silent no-op**, never a retry loop.

The apply/decision wiring is `tests/notifications/test_notification_wiring.py`;
it needs real commits, and this file deliberately does not.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.conf import settings
from django.core import mail
from django.utils import timezone

from candidates.models import CandidateProfile
from employers.models import EmployerProfile
from notifications.models import Notification
from notifications.services import notify
from notifications.tasks import notification_link, send_notification_email

pytestmark = pytest.mark.django_db

# Written out rather than derived: the five values are `Complete Doc` §C.4's, and
# a value added to the model without a decision must fail here.
EXPECTED_TYPES = {
    "application_update",
    "interview_scheduled",
    "ai_score_ready",
    "offer",
    "system",
}


@pytest.fixture
def recipient(make_user):
    return make_user("candidate")


@pytest.fixture
def notification(recipient):
    return Notification.objects.create(
        recipient=recipient,
        title="Application received",
        message="We received your application for Backend Engineer.",
        notification_type=Notification.Type.APPLICATION_UPDATE,
        url="/candidate/applications/abc/",
    )


@pytest.fixture
def dispatched(monkeypatch):
    """Record the ids `notify()` asks Celery to deliver."""
    sent: list[str] = []

    def _delay(notification_id):
        sent.append(notification_id)

    monkeypatch.setattr(send_notification_email, "delay", _delay)
    return sent


# ------------------------------------------------------------------- model


def test_the_vocabulary_is_the_documented_five():
    assert set(Notification.Type.values) == EXPECTED_TYPES


def test_defaults_are_unread_and_timestamped(recipient):
    row = Notification.objects.create(
        recipient=recipient,
        title="System",
        message="Maintenance tonight.",
        notification_type=Notification.Type.SYSTEM,
    )

    assert row.read is False
    assert row.url == ""
    assert row.created_at is not None


def test_the_list_is_newest_first(recipient):
    older = Notification.objects.create(
        recipient=recipient,
        title="Older",
        message="…",
        notification_type=Notification.Type.SYSTEM,
    )
    newer = Notification.objects.create(
        recipient=recipient,
        title="Newer",
        message="…",
        notification_type=Notification.Type.SYSTEM,
    )
    Notification.objects.filter(pk=older.pk).update(
        created_at=timezone.now() - timedelta(days=1)
    )

    assert list(Notification.objects.all()) == [newer, older]


def test_deleting_the_account_removes_its_notifications(recipient):
    Notification.objects.create(
        recipient=recipient,
        title="System",
        message="…",
        notification_type=Notification.Type.SYSTEM,
    )

    recipient.delete()

    assert not Notification.objects.exists()


def test_the_representation_is_the_type_and_title(recipient):
    row = Notification.objects.create(
        recipient=recipient,
        title="Application received",
        message="…",
        notification_type=Notification.Type.APPLICATION_UPDATE,
    )

    assert str(row) == "Application Update: Application received"
    # The one place an address lives is `recipient`; the label must not repeat it.
    assert recipient.email not in str(row)


# ----------------------------------------------------------------- service


def test_notify_writes_the_row(recipient):
    row = notify(
        recipient,
        Notification.Type.INTERVIEW_SCHEDULED,
        title="Interview scheduled",
        message="Acme Ltd proposed Tuesday.",
        url="/candidate/applications/abc/",
    )

    stored = Notification.objects.get(pk=row.pk)
    assert stored.recipient == recipient
    assert stored.title == "Interview scheduled"
    assert stored.message == "Acme Ltd proposed Tuesday."
    assert stored.notification_type == Notification.Type.INTERVIEW_SCHEDULED
    assert stored.url == "/candidate/applications/abc/"
    assert stored.read is False


def test_notify_queues_one_email_with_only_the_id(
    recipient, dispatched, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        row = notify(
            recipient,
            Notification.Type.SYSTEM,
            title="Maintenance",
            message="Tonight, 22:00-23:00.",
        )

    assert dispatched == [str(row.pk)]
    # A broker dump must not contain an address or the message.
    assert "@" not in dispatched[0]
    assert "Tonight" not in dispatched[0]


def test_the_email_waits_for_the_commit(
    recipient, dispatched, django_capture_on_commit_callbacks
):
    """The dispatch is attached to the commit, not run immediately."""
    with django_capture_on_commit_callbacks() as callbacks:
        notify(
            recipient,
            Notification.Type.SYSTEM,
            title="Maintenance",
            message="…",
        )

    assert dispatched == []
    assert len(callbacks) == 1
    # The row exists before the commit; only the email is deferred.
    assert Notification.objects.count() == 1


# -------------------------------------------------------------------- task


def test_the_task_emails_the_recipient(notification):
    send_notification_email(str(notification.pk))

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [notification.recipient.email]
    assert message.subject == "Application received"
    assert "We received your application for Backend Engineer." in message.body
    assert f"{settings.SITE_URL}/candidate/applications/abc/" in message.body


def test_a_notification_without_a_link_has_no_url_line(recipient):
    row = Notification.objects.create(
        recipient=recipient,
        title="System",
        message="Maintenance tonight.",
        notification_type=Notification.Type.SYSTEM,
    )

    send_notification_email(str(row.pk))

    assert settings.SITE_URL not in mail.outbox[0].body


def test_an_absolute_url_is_not_prefixed(recipient):
    row = Notification.objects.create(
        recipient=recipient,
        title="System",
        message="Read the note.",
        notification_type=Notification.Type.SYSTEM,
        url="https://example.com/notes/1",
    )

    send_notification_email(str(row.pk))

    assert "https://example.com/notes/1" in mail.outbox[0].body
    assert f"{settings.SITE_URL}https" not in mail.outbox[0].body


def test_a_deleted_row_is_a_silent_no_op(notification):
    notification_id = str(notification.pk)
    notification.delete()

    send_notification_email(notification_id)

    assert mail.outbox == []


@pytest.mark.parametrize("bad_id", ["not-a-uuid", "", None])
def test_a_malformed_id_is_a_silent_no_op(bad_id):
    send_notification_email(bad_id)

    assert mail.outbox == []


def test_an_inactive_account_is_not_emailed(notification):
    notification.recipient.is_active = False
    notification.recipient.save(update_fields=["is_active"])

    send_notification_email(str(notification.pk))

    assert mail.outbox == []


def test_the_task_can_run_twice(notification):
    """A retry sends a duplicate; it never mutates the row."""
    send_notification_email(str(notification.pk))
    send_notification_email(str(notification.pk))

    assert len(mail.outbox) == 2
    notification.refresh_from_db()
    assert notification.read is False


# --------------------------------------------------------------- the link


@pytest.mark.parametrize(
    "path,expected",
    [
        ("", ""),
        (
            "/candidate/applications/1/",
            f"{settings.SITE_URL}/candidate/applications/1/",
        ),
        ("candidate/applications/1/", f"{settings.SITE_URL}/candidate/applications/1/"),
        ("https://example.com/x", "https://example.com/x"),
        ("http://example.com/x", "http://example.com/x"),
    ],
)
def test_the_link_is_absolute(path, expected):
    assert notification_link(path) == expected


def test_the_link_does_not_double_the_slash(settings):
    settings.SITE_URL = "https://fairfold.example/"

    assert notification_link("/candidate/applications/1/") == (
        "https://fairfold.example/candidate/applications/1/"
    )


# ------------------------------------------------------------- no PII box


def test_an_employer_notification_names_no_candidate(make_user):
    """The copy is the caller's, but this test pins the shape the wiring uses."""
    employer = EmployerProfile.objects.create(
        user=make_user("employer_hr"), company_name="Acme Ltd"
    )
    candidate_user = make_user(
        "candidate",
        email="distinctive-candidate@example.com",
        first_name="Zubaida",
        last_name="Rahman",
    )
    candidate = CandidateProfile.objects.create(user=candidate_user)

    row = notify(
        employer.user,
        Notification.Type.APPLICATION_UPDATE,
        title="New application",
        message="C-ABC123 applied for Backend Engineer.",
        url="/employer/applications/1/",
    )

    rendered = f"{row.title} {row.message} {row.url}"
    assert "Zubaida" not in rendered
    assert "Rahman" not in rendered
    assert candidate_user.email not in rendered
    assert str(candidate.pk) not in rendered
