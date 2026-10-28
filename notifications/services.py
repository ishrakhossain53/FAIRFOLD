"""The one write path for a notification (REQ-FR-022, REQ-FR-023, batch 1.43).

`notify()` is called from `matching.services` -- once when an application is
created, once when a human decision changes its status -- so the API and the
template pages both produce the same record and the same email. Writing the row
and queueing the email at the call site would be two places to forget one half,
and the two surfaces would drift exactly like the apply rule did before batch
1.36 moved it into a service.

**The email is queued after the commit, and the payload is an id.** Both points
are load-bearing:

* a notification row created inside a transaction is invisible to a worker until
  that transaction commits, so dispatching the task inside it can hand the worker
  an id it cannot find and silently drop the only email;
* the argument is the notification id, not the address or the message, because
  Celery serialises JSON into Redis and a broker dump must not contain an email
  address or candidate data (AGENTS.md privacy invariants).

A notification that is queued but never sent (worker down) is visible in the
recipient's list, which is the honest failure: the in-app record is the source of
truth and the email is its mirror.
"""

from __future__ import annotations

from django.db import transaction

from notifications.models import Notification
from notifications.tasks import send_notification_email


def notification_type(member) -> str:
    """The stored string of a `Notification.Type` member.

    Same reason as `employers.services.job_status` and
    `matching.services.application_status`: Django's choices metaclass is
    untyped, so mypy reads a `TextChoices` attribute as its `(value, label)`
    tuple although it is a `str` subclass at runtime. Converting in one place
    keeps `notify()`'s parameter honestly typed as `str` without a
    `type: ignore` at every call site.
    """
    return str(member.value)


def notify(
    recipient,
    notification_type: str,
    *,
    title: str,
    message: str,
    url: str = "",
) -> Notification:
    """Create one notification for `recipient` and queue its email.

    **Keyword-only copy.** `title` and `message` are required keywords so a caller
    cannot swap them, and `url` is optional because not every message has a page
    (a system notice may not).

    **`notification_type` is the model's vocabulary, not free text.** Passing
    `Notification.Type.SYSTEM` rather than `"system"` keeps the five documented
    values in one place; the column has no database check (the DDL does not
    declare one), so the choices on the model are the only guard.

    **The caller owns the copy and its privacy.** This function cannot tell an
    employer-facing message from a candidate-facing one: it writes what it is
    given. `matching.services` is where the alias is chosen for the employer
    (REQ-FR-054) and where the candidate's own status is named.
    """
    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        url=url,
    )

    notification_id = str(notification.pk)
    transaction.on_commit(lambda: send_notification_email.delay(notification_id))
    return notification
