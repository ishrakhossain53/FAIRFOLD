"""Email delivery for notifications (REQ-FR-022, REQ-FR-023, batch 1.43).

Celery tasks. Registered by `config.celery` autodiscovery, which imports this
module at worker startup.

A task must be **safe to run twice**. Celery retries on worker death without
knowing whether the first attempt finished, so anything that writes a row also
needs an idempotency key or a natural unique constraint. This task only sends, so
a second copy is a duplicate email and nothing worse -- the same trade the
verification email makes. Nothing here mutates the notification: a delivery
failure is not a read, and the row must stay unread until the recipient opens it.
"""

from __future__ import annotations

import logging
from email.utils import formataddr

from celery import shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail

from notifications.models import Notification

logger = logging.getLogger(__name__)


def notification_link(path: str) -> str:
    """Turn a stored notification path into an absolute URL.

    `notifications.url` holds a path (the DDL's VARCHAR(500) is the link target,
    not a per-environment origin). The origin is `settings.SITE_URL` because a
    Celery worker has no request to build one from and the host differs per
    environment -- the same reasoning as the verification and reset links.

    An absolute URL is passed through unchanged: a future caller may store one,
    and prefixing it would produce `http://localhost:8000/https://...`.
    """
    if not path:
        return ""
    if path.startswith(("http://", "https://")):
        return path
    return f"{settings.SITE_URL.rstrip('/')}/{path.lstrip('/')}"


@shared_task(ignore_result=True)
def send_notification_email(notification_id: str) -> None:
    """Email the notification named by `notification_id` to its recipient.

    The argument is the id, not the user object, the address or the message: the
    broker payload is JSON in Redis and must not carry an email address or
    candidate data, and the worker has to re-read the row so a retry after an edit
    sends what the database actually holds.

    A missing row (deleted recipient, rolled-back transaction, already-purged
    notification) is a silent no-op: no retry can bring it back, and an exception
    would put the id in the worker's error log for no benefit.

    An inactive account is skipped for the same reason the verification task skips
    it: the account cannot be used, so the email would only be a message to an
    address the product has stopped serving.

    The subject is `notification.title` and the body is `notification.message`
    plus the absolute link. No recipient data is interpolated into either: the
    recipient is who the message is addressed to, not something it describes.
    """
    try:
        notification = Notification.objects.select_related("recipient").get(
            pk=notification_id
        )
    except (Notification.DoesNotExist, ValidationError, TypeError, ValueError):
        return

    user = notification.recipient
    if not user.is_active:
        return

    body = notification.message
    link = notification_link(notification.url)
    if link:
        body = f"{body}\n\n{link}\n"

    send_mail(
        subject=notification.title,
        message=body,
        from_email=formataddr(
            (settings.DEFAULT_FROM_EMAIL_NAME, settings.DEFAULT_FROM_EMAIL)
        ),
        recipient_list=[user.email],
        fail_silently=False,
    )
