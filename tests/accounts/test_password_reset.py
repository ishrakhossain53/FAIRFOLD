"""Password reset and change tests (REQ-FR-004).

Service tests cover the token lifecycle: a valid token works once, expiry and
reuse are refused, the new password runs through the validators, a reset clears
lockout state and revokes refresh tokens. API tests cover non-enumeration, the
error shapes and the authenticated change route.

The one-hour lifetime is `settings.PASSWORD_RESET_TIMEOUT`, read by Django's
`default_token_generator`. Expiry is proved with `override_settings` rather than
by waiting an hour.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.services import (
    InvalidPasswordResetToken,
    WrongPassword,
    change_password,
    make_password_reset_token,
    request_password_reset,
    reset_password,
)
from accounts.tasks import send_password_reset_email

pytestmark = pytest.mark.django_db

RESET_URL = "/api/v1/auth/password/reset/"
RESET_CONFIRM_URL = "/api/v1/auth/password/reset/confirm/"
CHANGE_URL = "/api/v1/auth/password/change/"

PASSWORD = "Wanderlust7Quartz-Meadow"
NEW_PASSWORD = "Cobalt8Juniper-Harbour"
OTHER_PASSWORD = "Saffron9Orchard-Lantern"


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def user(make_user) -> User:
    return make_user(
        "candidate",
        email="ada@example.com",
        password=PASSWORD,
        email_verified=True,
    )


def uid_for(user: User) -> str:
    return urlsafe_base64_encode(str(user.pk).encode())


def token_for(user: User) -> str:
    return make_password_reset_token(user)


class TestRequestService:
    def test_a_known_active_address_returns_the_account(self, user):
        assert request_password_reset("ADA@Example.com").pk == user.pk

    def test_an_unknown_address_returns_none(self, user):
        assert request_password_reset("nobody@example.com") is None

    def test_a_deactivated_account_returns_none(self, user):
        user.is_active = False
        user.save(update_fields=["is_active"])
        assert request_password_reset("ada@example.com") is None

    def test_a_malformed_address_returns_none(self):
        assert request_password_reset("not-an-email") is None
        assert request_password_reset("") is None


class TestResetService:
    def test_a_valid_token_sets_the_new_password(self, user):
        reset_password(uid_for(user), token_for(user), NEW_PASSWORD)

        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)
        assert not user.check_password(PASSWORD)

    def test_a_reset_clears_the_lockout_state(self, user):
        user.failed_login_attempts = 5
        user.save(update_fields=["failed_login_attempts"])

        reset_password(uid_for(user), token_for(user), NEW_PASSWORD)

        user.refresh_from_db()
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    def test_a_token_cannot_be_reused(self, user):
        uid, token = uid_for(user), token_for(user)
        reset_password(uid, token, NEW_PASSWORD)

        with pytest.raises(InvalidPasswordResetToken):
            reset_password(uid, token, OTHER_PASSWORD)

        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)

    @override_settings(PASSWORD_RESET_TIMEOUT=-1)
    def test_an_expired_token_is_refused(self, user):
        with pytest.raises(InvalidPasswordResetToken):
            reset_password(uid_for(user), token_for(user), NEW_PASSWORD)

        user.refresh_from_db()
        assert user.check_password(PASSWORD)

    def test_a_tampered_token_is_refused(self, user):
        with pytest.raises(InvalidPasswordResetToken):
            reset_password(uid_for(user), token_for(user) + "x", NEW_PASSWORD)

    def test_an_unknown_uid_is_refused(self, user):
        with pytest.raises(InvalidPasswordResetToken):
            reset_password(
                urlsafe_base64_encode(b"not-a-uuid"), token_for(user), NEW_PASSWORD
            )

    def test_a_weak_password_is_refused_and_nothing_changes(self, user):
        with pytest.raises(ValidationError):
            reset_password(uid_for(user), token_for(user), "short")

        user.refresh_from_db()
        assert user.check_password(PASSWORD)

    def test_a_reset_revokes_outstanding_refresh_tokens(self, user):
        RefreshToken.for_user(user)
        assert OutstandingToken.objects.filter(user=user).count() == 1

        reset_password(uid_for(user), token_for(user), NEW_PASSWORD)

        assert BlacklistedToken.objects.count() == 1


class TestResetEmailTask:
    def test_the_task_sends_a_working_link(self, user, mailoutbox):
        send_password_reset_email(str(user.pk))

        assert len(mailoutbox) == 1
        body = mailoutbox[0].body
        assert "expires in one hour" in body

        link = next(word for word in body.split() if "reset-password" in word)
        query = parse_qs(urlparse(link).query)
        reset_password(query["uid"][0], query["token"][0], NEW_PASSWORD)

        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)

    def test_the_task_is_a_no_op_for_an_unknown_id(self, mailoutbox):
        send_password_reset_email("00000000-0000-0000-0000-000000000000")
        assert mailoutbox == []

    def test_the_task_is_a_no_op_for_a_deactivated_account(self, user, mailoutbox):
        user.is_active = False
        user.save(update_fields=["is_active"])

        send_password_reset_email(str(user.pk))

        assert mailoutbox == []


class TestChangePassword:
    def test_the_current_password_is_required(self, user):
        with pytest.raises(WrongPassword):
            change_password(user, "wrong", NEW_PASSWORD)

        user.refresh_from_db()
        assert user.check_password(PASSWORD)

    def test_a_valid_change_updates_the_hash(self, user):
        change_password(user, PASSWORD, NEW_PASSWORD)

        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)

    def test_the_new_password_runs_through_the_validators(self, user):
        with pytest.raises(ValidationError):
            change_password(user, PASSWORD, "short")


class TestResetApi:
    @pytest.fixture
    def dispatched(self, monkeypatch):
        calls: list[str] = []
        monkeypatch.setattr(
            send_password_reset_email, "delay", lambda user_id: calls.append(user_id)
        )
        return calls

    def test_a_known_address_returns_202_and_is_indistinguishable(
        self, api, user, dispatched, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            known = api.post(RESET_URL, {"email": "ada@example.com"}, format="json")

        with django_capture_on_commit_callbacks(execute=True):
            unknown = api.post(
                RESET_URL, {"email": "nobody@example.com"}, format="json"
            )

        assert known.status_code == unknown.status_code == 202
        assert known.json() == unknown.json()
        # Only the known address queued a mail, and the caller cannot see that.
        assert dispatched == [str(user.pk)]

    def test_a_malformed_address_is_a_400_keyed_to_the_field(self, api):
        response = api.post(RESET_URL, {"email": "not-an-email"}, format="json")

        assert response.status_code == 400
        assert "email" in response.json()

    def test_a_valid_token_confirms_the_reset(self, api, user):
        response = api.post(
            RESET_CONFIRM_URL,
            {
                "uid": uid_for(user),
                "token": token_for(user),
                "new_password": NEW_PASSWORD,
            },
            format="json",
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)

    def test_a_reused_token_is_a_400_invalid_token(self, api, user):
        body = {
            "uid": uid_for(user),
            "token": token_for(user),
            "new_password": NEW_PASSWORD,
        }
        first = api.post(RESET_CONFIRM_URL, body, format="json")

        second = api.post(
            RESET_CONFIRM_URL,
            {**body, "new_password": OTHER_PASSWORD},
            format="json",
        )

        assert first.status_code == 200
        assert second.status_code == 400
        assert second.json()["code"] == "invalid_token"

    @override_settings(PASSWORD_RESET_TIMEOUT=-1)
    def test_an_expired_token_is_a_400_invalid_token(self, api, user):
        response = api.post(
            RESET_CONFIRM_URL,
            {
                "uid": uid_for(user),
                "token": token_for(user),
                "new_password": NEW_PASSWORD,
            },
            format="json",
        )

        assert response.status_code == 400
        assert response.json()["code"] == "invalid_token"

    def test_a_weak_password_is_a_400_keyed_to_new_password(self, api, user):
        response = api.post(
            RESET_CONFIRM_URL,
            {
                "uid": uid_for(user),
                "token": token_for(user),
                "new_password": "short",
            },
            format="json",
        )

        assert response.status_code == 400
        assert "new_password" in response.json()

    def test_the_confirm_endpoint_is_anonymous(self, api, user):
        # The global default is IsAuthenticated. A reset is performed by someone
        # who cannot log in, so a missing opt-out would 401 every real reset.
        response = api.post(
            RESET_CONFIRM_URL,
            {"uid": "x", "token": "y", "new_password": NEW_PASSWORD},
            format="json",
        )
        assert response.status_code == 400


class TestChangeApi:
    def test_anonymous_callers_are_refused(self, api, user):
        assert (
            api.post(
                CHANGE_URL,
                {
                    "current_password": PASSWORD,
                    "new_password": NEW_PASSWORD,
                },
                format="json",
            ).status_code
            == 401
        )

    def test_the_wrong_current_password_is_a_400_on_that_field(self, api, user):
        api.force_authenticate(user=user)

        response = api.post(
            CHANGE_URL,
            {"current_password": "wrong", "new_password": NEW_PASSWORD},
            format="json",
        )

        assert response.status_code == 400
        assert "current_password" in response.json()

    def test_a_valid_change_updates_the_password(self, api, user):
        api.force_authenticate(user=user)

        response = api.post(
            CHANGE_URL,
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            format="json",
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)

    def test_a_weak_new_password_is_a_400(self, api, user):
        api.force_authenticate(user=user)

        response = api.post(
            CHANGE_URL,
            {"current_password": PASSWORD, "new_password": "short"},
            format="json",
        )

        assert response.status_code == 400
        assert "new_password" in response.json()
