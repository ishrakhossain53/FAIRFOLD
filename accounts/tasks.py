"""User model, authentication, MFA, RBAC and profiles.

Celery tasks. Registered by `config.celery` autodiscovery, which imports this
module at worker startup.

A task must be **safe to run twice**. Celery retries on worker death without
knowing whether the first attempt finished, so anything that writes a row also
needs an idempotency key or a natural unique constraint. The verification email
satisfies that by being a read-only send: two copies of the same link are
harmless, and `verify_email` flips the flag only once.
"""

from __future__ import annotations

import logging
from email.utils import formataddr
from urllib.parse import quote

from celery import shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode

from accounts.models import User
from accounts.services import make_password_reset_token, make_verification_token

logger = logging.getLogger(__name__)


def verification_link(token: str) -> str:
    """Absolute URL the recipient clicks.

    The token is URL-quoted: it contains `:` and base64 characters, and an
    unquoted `+` in a query string is decoded as a space, which would turn a
    valid link into an invalid signature.

    The base URL is a setting because the template route lands in batch 1.6 and
    because the task has no request to build an absolute URI from.
    """
    base = settings.EMAIL_VERIFICATION_URL
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}token={quote(token, safe='')}"


@shared_task(ignore_result=True)
def send_verification_email(user_id: str) -> None:
    """Email a fresh verification link to the account named by `user_id`.

    The argument is the id, not the user object or the address: Celery
    serialises the payload to JSON into Redis, and a broker dump must not
    contain an email address (AGENTS.md privacy invariants). It also keeps the
    task callable after a retry, when the object in the caller's memory is stale.

    A missing, malformed or no-longer-eligible account is a silent no-op rather
    than a retry: none of those can be fixed by running the task again, and an
    exception would put the id in the worker's error log for no benefit.

    The token is created here, at send time, so the link's lifetime is not spent
    waiting behind other queued tasks.
    """
    try:
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValidationError, TypeError, ValueError):
        return

    if user.email_verified or not user.is_active:
        return

    link = verification_link(make_verification_token(user))
    if settings.DEBUG:
        # The console email backend prints the whole message, but it prints to
        # whichever process sends it -- often a Celery worker in a container, not
        # the terminal running the web server. One explicit line makes the link
        # findable in either log stream. DEBUG-gated: a token must never reach a
        # production log.
        logger.info("Development verification link: %s", link)

    send_mail(
        subject="Verify your FairFold email",
        message=(
            "Confirm your email address to finish setting up your FairFold "
            "account:\n\n"
            f"{link}\n\n"
            "If you did not create an account, you can ignore this email."
        ),
        from_email=formataddr(
            (settings.DEFAULT_FROM_EMAIL_NAME, settings.DEFAULT_FROM_EMAIL)
        ),
        recipient_list=[user.email],
        fail_silently=False,
    )


def password_reset_link(uidb64: str, token: str) -> str:
    """Absolute URL for design.md page #10.

    Both values are URL-quoted: the token contains `:` and base64 characters,
    and an unquoted `+` in a query string decodes as a space, turning a valid
    token into an invalid signature.
    """
    base = settings.PASSWORD_RESET_URL
    separator = "&" if "?" in base else "?"
    return (
        f"{base}{separator}uid={quote(uidb64, safe='')}"
        f"&token={quote(token, safe='')}"
    )


@shared_task(ignore_result=True)
def send_password_reset_email(user_id: str) -> None:
    """Email a one-hour reset link to the account named by `user_id`.

    The argument is the id for the same reasons as the verification task: a
    broker dump must not contain an address, and the worker must re-read the
    row rather than trust a serialised object.

    A missing or deactivated account is a silent no-op. The request endpoint
    answers identically for an unknown address, so a retry here could not make
    the address exist, and an exception would put the id in the worker log for
    no benefit.

    The task is safe to run twice: two copies of the link are harmless, and the
    first successful reset invalidates every outstanding copy.
    """
    try:
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValidationError, TypeError, ValueError):
        return

    if not user.is_active:
        return

    uidb64 = urlsafe_base64_encode(str(user.pk).encode())
    link = password_reset_link(uidb64, make_password_reset_token(user))

    send_mail(
        subject="Reset your FairFold password",
        message=(
            "We received a request to reset your FairFold password. The link "
            "below works once and expires in one hour:\n\n"
            f"{link}\n\n"
            "If you did not request this, you can ignore this email; your "
            "password has not changed."
        ),
        from_email=formataddr(
            (settings.DEFAULT_FROM_EMAIL_NAME, settings.DEFAULT_FROM_EMAIL)
        ),
        recipient_list=[user.email],
        fail_silently=False,
    )
