"""Login service tests: lockout, verification and counter reset (REQ-FR-002/003).

These test `accounts.services.authenticate_with_lockout` only. The API and the
page tests sit on top of it; if the rules were duplicated there, these tests
would still pass and the two surfaces could disagree.

**The clock is frozen, never slept.** `User.is_locked()` compares `locked_until`
against `timezone.now()`, so patching `django.utils.timezone.now` moves the model
and the service together. A test that slept fifteen minutes would not run in CI,
and a test that compared against a real clock would be flaky at the boundary.

The lock is set by the **fifth** consecutive failure (see the service docstring),
so the sixth attempt is refused rather than counted.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.utils import timezone

from accounts.models import User
from accounts.services import (
    INVALID_CREDENTIALS_DETAIL,
    LOGIN_LOCKOUT_AUDIT_ACTION,
    MAX_FAILED_LOGIN_ATTEMPTS,
    AccountLocked,
    EmailNotVerified,
    InvalidCredentials,
    authenticate_with_lockout,
)
from core.models import AuditLogEntry

pytestmark = pytest.mark.django_db

PASSWORD = "Wanderlust7Quartz-Meadow"
NEW_PASSWORD = "Cobalt8Juniper-Harbour"


@pytest.fixture
def clock(monkeypatch):
    """A frozen, movable clock shared by the model and the service."""
    state = {"now": timezone.now()}
    monkeypatch.setattr(timezone, "now", lambda: state["now"])
    return state


@pytest.fixture
def user(make_user) -> User:
    return make_user(
        "candidate",
        email="ada@example.com",
        password=PASSWORD,
        email_verified=True,
        first_name="Ada",
        last_name="Lovelace",
    )


def fail_login(email: str) -> None:
    with pytest.raises(InvalidCredentials):
        authenticate_with_lockout(email, "not-the-password")


class TestSuccess:
    def test_valid_credentials_return_the_user(self, user):
        assert authenticate_with_lockout("ada@example.com", PASSWORD).pk == user.pk

    def test_the_address_is_matched_case_insensitively(self, user):
        assert authenticate_with_lockout("ADA@Example.COM", PASSWORD).pk == user.pk

    def test_success_stamps_last_login_and_resets_the_counter(self, user, clock):
        user.failed_login_attempts = 3
        user.save(update_fields=["failed_login_attempts"])

        authenticated = authenticate_with_lockout("ada@example.com", PASSWORD)

        user.refresh_from_db()
        assert authenticated.pk == user.pk
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        assert user.last_login == clock["now"]

    def test_success_clears_an_expired_lock(self, user, clock):
        fail_login_before_lock(user)
        with pytest.raises(AccountLocked):
            fail_login("ada@example.com")

        clock["now"] += timedelta(minutes=15, seconds=1)

        assert authenticate_with_lockout("ada@example.com", PASSWORD).pk == user.pk
        user.refresh_from_db()
        assert user.failed_login_attempts == 0
        assert user.locked_until is None


def fail_login_before_lock(user: User) -> None:
    """Four failures: one short of the threshold, so no lock yet."""
    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS - 1):
        fail_login(user.email)
    user.refresh_from_db()
    assert user.failed_login_attempts == MAX_FAILED_LOGIN_ATTEMPTS - 1
    assert not user.is_locked()


class TestFailure:
    def test_a_wrong_password_is_rejected_and_counted(self, user):
        with pytest.raises(InvalidCredentials):
            authenticate_with_lockout("ada@example.com", "wrong")

        user.refresh_from_db()
        assert user.failed_login_attempts == 1
        assert not user.is_locked()

    def test_an_unknown_address_is_the_same_error_as_a_wrong_password(self, user):
        with pytest.raises(InvalidCredentials) as wrong:
            authenticate_with_lockout("ada@example.com", "wrong")

        with pytest.raises(InvalidCredentials) as unknown:
            authenticate_with_lockout("nobody@example.com", "wrong")

        # The anti-enumeration contract: a caller cannot tell the two apart from
        # the exception type or its text.
        assert str(wrong.value) == str(unknown.value) == INVALID_CREDENTIALS_DETAIL

    def test_an_inactive_account_is_a_credential_failure(self, user):
        user.is_active = False
        user.save(update_fields=["is_active"])

        with pytest.raises(InvalidCredentials):
            authenticate_with_lockout("ada@example.com", PASSWORD)

        user.refresh_from_db()
        # A correct password on a deactivated account must not lock it: the
        # account is already unusable, and a lock would be a second signal.
        assert user.failed_login_attempts == 0

    def test_an_empty_address_is_refused_without_a_query(self):
        with pytest.raises(InvalidCredentials):
            authenticate_with_lockout("   ", PASSWORD)


class TestVerification:
    def test_an_unverified_account_cannot_sign_in(self, user):
        user.email_verified = False
        user.save(update_fields=["email_verified"])

        with pytest.raises(EmailNotVerified):
            authenticate_with_lockout("ada@example.com", PASSWORD)

        user.refresh_from_db()
        # The password was right; that is not a failed attempt.
        assert user.failed_login_attempts == 0
        assert user.last_login is None

    def test_an_unverified_account_with_a_wrong_password_is_only_that(self, user):
        user.email_verified = False
        user.save(update_fields=["email_verified"])

        # "Verify your email" is only shown to someone who proved they own the
        # account. Otherwise it would answer "does this address exist?".
        with pytest.raises(InvalidCredentials):
            authenticate_with_lockout("ada@example.com", "wrong")


class TestLockout:
    def test_the_fifth_failure_locks_for_fifteen_minutes(self, user, clock):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS - 1):
            fail_login(user.email)

        with pytest.raises(AccountLocked) as locked:
            fail_login(user.email)

        user.refresh_from_db()
        assert user.locked_until == clock["now"] + timedelta(minutes=15)
        assert locked.value.retry_after == 15 * 60

    def test_the_sixth_attempt_is_refused_even_with_the_right_password(
        self, user, clock
    ):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
            with pytest.raises((InvalidCredentials, AccountLocked)):
                authenticate_with_lockout("ada@example.com", "wrong")

        with pytest.raises(AccountLocked) as locked:
            authenticate_with_lockout("ada@example.com", PASSWORD)

        assert 0 < locked.value.retry_after <= 15 * 60
        user.refresh_from_db()
        assert user.failed_login_attempts == MAX_FAILED_LOGIN_ATTEMPTS
        assert user.is_locked()

    def test_a_locked_account_does_not_keep_counting_attempts(self, user, clock):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
            with pytest.raises((InvalidCredentials, AccountLocked)):
                authenticate_with_lockout("ada@example.com", "wrong")
        user.refresh_from_db()
        counted_at_lock = user.failed_login_attempts

        with pytest.raises(AccountLocked):
            authenticate_with_lockout("ada@example.com", "wrong")

        user.refresh_from_db()
        assert user.failed_login_attempts == counted_at_lock

    def test_the_lock_expires_on_its_own(self, user, clock):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
            with pytest.raises((InvalidCredentials, AccountLocked)):
                authenticate_with_lockout("ada@example.com", "wrong")
        user.refresh_from_db()
        assert user.is_locked()

        clock["now"] += timedelta(minutes=15) + timedelta(seconds=1)

        user.refresh_from_db()
        assert not user.is_locked()
        assert authenticate_with_lockout("ada@example.com", PASSWORD).pk == user.pk

    def test_after_expiry_a_wrong_password_starts_the_count_again(self, user, clock):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
            with pytest.raises((InvalidCredentials, AccountLocked)):
                authenticate_with_lockout("ada@example.com", "wrong")

        clock["now"] += timedelta(minutes=15, seconds=1)

        # The counter must be cleared with the lock; otherwise this single
        # failure would immediately re-lock the account.
        with pytest.raises(InvalidCredentials):
            authenticate_with_lockout("ada@example.com", "wrong")

        user.refresh_from_db()
        assert user.failed_login_attempts == 1
        assert not user.is_locked()

    def test_a_success_before_the_threshold_resets_the_counter(self, user):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS - 2):
            fail_login(user.email)

        authenticate_with_lockout("ada@example.com", PASSWORD)

        user.refresh_from_db()
        assert user.failed_login_attempts == 0


class TestLockoutAudit:
    def test_a_lock_writes_one_audit_entry_without_personal_data(self, user):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS - 1):
            fail_login(user.email)
        assert not AuditLogEntry.objects.exists()

        with pytest.raises(AccountLocked):
            fail_login(user.email)

        entry = AuditLogEntry.objects.get()
        assert entry.action == LOGIN_LOCKOUT_AUDIT_ACTION
        assert entry.result == "locked"
        assert entry.actor_id == user.pk
        assert entry.resource_id == user.pk
        assert entry.details == {
            "reason": "failed_login_threshold",
            "failed_attempts": MAX_FAILED_LOGIN_ATTEMPTS,
        }

        # AGENTS.md: the audit table must never hold PII. The email and the name
        # are the fields this entry is most likely to pick up by accident.
        serialised = json.dumps(entry.details)
        assert "ada@example.com" not in serialised
        assert "Ada" not in serialised
        assert PASSWORD not in serialised

    def test_a_success_writes_no_lockout_audit_entry(self, user):
        authenticate_with_lockout("ada@example.com", PASSWORD)
        assert not AuditLogEntry.objects.exists()
