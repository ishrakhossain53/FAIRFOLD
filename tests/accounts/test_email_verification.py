"""Tests for email verification (REQ-FR-001, decision D-3).

The properties pinned here are the ones a later refactor would quietly lose:

* the token is signed and expiring, and is **not** the user id, so knowing an id
  does not let anyone verify an account;
* verification flips `email_verified` exactly once — a reused link is refused,
  not re-applied;
* expired, tampered and unknown-account tokens fail with a domain error and
  leave the account unverified;
* the Celery task takes an id, not an address, and a redundant run sends nothing;
* resending is throttled per user through the cache, and the signup email starts
  that cooldown.

`mailoutbox` is pytest-django's fixture, not `mail.outbox` directly: it clears
the outbox between tests, so a count assertion cannot pass on a previous test's
message.
"""

from __future__ import annotations

import re
import time
import uuid
from unittest import mock
from urllib.parse import unquote

import pytest
from django.conf import settings
from django.core import signing
from django.core.cache import cache

from accounts.models import User
from accounts.services import (
    EmailAlreadyVerified,
    InvalidVerificationToken,
    VerificationTokenExpired,
    make_verification_token,
    queue_verification_email,
    resend_throttle_cache_key,
    resend_verification_email,
    verify_email,
)
from accounts.tasks import send_verification_email

pytestmark = pytest.mark.django_db


@pytest.fixture
def dispatched(monkeypatch):
    """Record task ids instead of putting them on the real broker.

    Celery is deliberately not eager in CI (config/settings/ci.py). A test that
    actually called `.delay()` would enqueue a message, send no email in-process,
    and prove only that Redis accepts messages.
    """
    calls: list[str] = []

    def _delay(user_id: str) -> None:
        calls.append(user_id)

    monkeypatch.setattr(send_verification_email, "delay", _delay)
    return calls


class TestVerificationToken:
    def test_token_is_signed_and_not_the_user_id(self, make_user):
        user = make_user()

        token = make_verification_token(user)

        assert token != str(user.pk)
        # A UUID contains hyphens, which are outside the base64 alphabet the
        # signed value uses. The literal id cannot be read out of the token.
        assert str(user.pk) not in token

    def test_valid_token_verifies_the_account(self, make_user):
        user = make_user()
        token = make_verification_token(user)

        verified = verify_email(token)

        assert verified.pk == user.pk
        assert User.objects.get(pk=user.pk).email_verified is True

    def test_second_use_of_the_same_token_is_refused(self, make_user):
        user = make_user()
        token = make_verification_token(user)
        verify_email(token)

        with pytest.raises(EmailAlreadyVerified):
            verify_email(token)

        assert User.objects.get(pk=user.pk).email_verified is True

    def test_a_fresh_token_for_a_verified_account_is_refused(self, make_user):
        # The link was reissued (or a different link arrived) after the first
        # verification. Re-applying is a no-op, and the caller is told so it can
        # render the success state instead of an error.
        user = make_user(email_verified=True)

        with pytest.raises(EmailAlreadyVerified):
            verify_email(make_verification_token(user))

    def test_expired_token_is_refused(self, make_user):
        user = make_user()
        lifetime = settings.EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS

        # Sign as if the token had been issued just outside its lifetime. Only
        # the signing clock is patched; `unsign` runs against the real one.
        with mock.patch.object(
            signing.TimestampSigner,
            "timestamp",
            return_value=signing.b62_encode(int(time.time()) - lifetime - 60),
        ):
            token = make_verification_token(user)

        with pytest.raises(VerificationTokenExpired):
            verify_email(token)

        assert User.objects.get(pk=user.pk).email_verified is False

    def test_tampered_token_is_refused(self, make_user):
        user = make_user()
        token = make_verification_token(user)
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

        with pytest.raises(InvalidVerificationToken):
            verify_email(tampered)

        assert User.objects.get(pk=user.pk).email_verified is False

    def test_a_bare_user_id_is_not_a_token(self, make_user):
        # The property the "do not make the token a user id" rule exists for.
        user = make_user()

        with pytest.raises(InvalidVerificationToken):
            verify_email(str(user.pk))

        assert User.objects.get(pk=user.pk).email_verified is False

    @pytest.mark.parametrize("token", ["", "   ", "not-a-token"])
    def test_malformed_tokens_are_refused(self, make_user, token):
        user = make_user()

        with pytest.raises(InvalidVerificationToken):
            verify_email(token)

        assert User.objects.get(pk=user.pk).email_verified is False

    def test_a_token_for_a_deleted_account_is_refused(self, make_user):
        user = make_user()
        token = make_verification_token(user)
        user.delete()

        with pytest.raises(InvalidVerificationToken):
            verify_email(token)


class TestVerificationEmailTask:
    def test_sends_one_email_to_the_account(self, make_user, mailoutbox):
        user = make_user()

        send_verification_email(str(user.pk))

        assert len(mailoutbox) == 1
        message = mailoutbox[0]
        assert message.to == [user.email]
        assert "verify" in message.subject.lower()
        assert settings.DEFAULT_FROM_EMAIL in message.from_email

    def test_the_link_verifies_the_account(self, make_user, mailoutbox):
        user = make_user()

        send_verification_email(str(user.pk))

        match = re.search(r"[?&]token=([^\s]+)", mailoutbox[0].body)
        assert match, "the email body must contain a tokenised link"
        assert verify_email(unquote(match.group(1))).pk == user.pk

    def test_a_verified_account_gets_no_email(self, make_user, mailoutbox):
        user = make_user(email_verified=True)

        send_verification_email(str(user.pk))

        assert mailoutbox == []

    def test_an_inactive_account_gets_no_email(self, make_user, mailoutbox):
        user = make_user(is_active=False)

        send_verification_email(str(user.pk))

        assert mailoutbox == []

    @pytest.mark.parametrize("user_id", ["not-a-uuid", None])
    def test_a_malformed_id_is_a_no_op(self, user_id, mailoutbox):
        send_verification_email(user_id)

        assert mailoutbox == []

    def test_a_deleted_account_is_a_no_op(self, mailoutbox):
        send_verification_email(str(uuid.uuid4()))

        assert mailoutbox == []


# `transaction=True`: `resend_verification_email` dispatches through
# `transaction.on_commit`, and the default TestCase-style wrapping would never
# commit, so the callback would wait for a commit that does not happen.
@pytest.mark.django_db(transaction=True)
class TestResend:
    def test_first_resend_queues_the_task(self, make_user, dispatched):
        user = make_user()

        assert resend_verification_email(user) is True

        assert dispatched == [str(user.pk)]

    def test_second_resend_inside_the_cooldown_is_throttled(
        self, make_user, dispatched
    ):
        user = make_user()
        assert resend_verification_email(user) is True

        assert resend_verification_email(user) is False

        assert dispatched == [str(user.pk)]

    def test_after_the_cooldown_expires_a_new_email_is_queued(
        self, make_user, dispatched
    ):
        user = make_user()
        assert resend_verification_email(user) is True

        # The key expiring is what Redis does after the timeout; deleting it is
        # the same state without sleeping for 45 seconds.
        cache.delete(resend_throttle_cache_key(user))

        assert resend_verification_email(user) is True
        assert len(dispatched) == 2

    def test_the_cooldown_is_per_user(self, make_user, dispatched):
        first = make_user()
        second = make_user()

        assert resend_verification_email(first) is True
        assert resend_verification_email(second) is True
        assert resend_verification_email(first) is False

        assert dispatched == [str(first.pk), str(second.pk)]

    def test_a_verified_account_is_not_emailed(self, make_user, dispatched):
        user = make_user(email_verified=True)

        assert resend_verification_email(user) is False

        assert dispatched == []

    def test_the_signup_email_starts_the_cooldown(self, make_user, dispatched):
        user = make_user()

        queue_verification_email(user)

        assert dispatched == [str(user.pk)]
        assert resend_verification_email(user) is False

    def test_resend_reaches_the_outbox(self, make_user, mailoutbox, monkeypatch):
        user = make_user()
        monkeypatch.setattr(
            send_verification_email,
            "delay",
            lambda user_id: send_verification_email(user_id),
        )

        assert resend_verification_email(user) is True

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]

    def test_dispatch_waits_for_the_commit(self, make_user, dispatched):
        user = make_user()

        with mock.patch("accounts.services.transaction.on_commit") as on_commit:
            queue_verification_email(user)

        assert dispatched == []
        on_commit.assert_called_once()
        on_commit.call_args.args[0]()
        assert dispatched == [str(user.pk)]
