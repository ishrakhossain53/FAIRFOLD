"""JWT login, refresh, logout and revocation API tests (REQ-FR-002/007/008, D-7).

The credential rules themselves are tested in `test_login_service.py`. These
tests assert what the HTTP layer adds:

* login returns the token pair and no account data;
* a wrong password, an unknown address and a deactivated account are one 401;
* an unverified address is a 403 only after the correct password, and a locked
  one is a 423 with `retry_after` and no token;
* the access token really is 15 minutes and the refresh token 7 days (D-7);
* refresh rotates and blacklists the previous refresh token;
* logout blacklists, and the next refresh with that token is 401;
* the login endpoint carries the `login` throttle scope and actually throttles.
"""

from __future__ import annotations

import re
from datetime import timedelta

import pytest
from django.conf import settings
from django.core.cache import cache
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.tokens import AccessToken

from accounts.api_views import LoginView
from accounts.models import User
from accounts.services import (
    INVALID_CREDENTIALS_DETAIL,
    LOGIN_LOCKOUT_AUDIT_ACTION,
    MAX_FAILED_LOGIN_ATTEMPTS,
)
from core.models import AuditLogEntry

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/refresh/"
LOGOUT_URL = "/api/v1/auth/logout/"

PASSWORD = "Wanderlust7Quartz-Meadow"


@pytest.fixture(autouse=True)
def _clean_cache():
    """The throttle counters live in Redis and are not rolled back with the DB."""
    cache.clear()
    yield
    cache.clear()


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


def login(api: APIClient, password: str = PASSWORD) -> dict:
    return api.post(
        LOGIN_URL, {"email": "ada@example.com", "password": password}, format="json"
    )


class TestLogin:
    def test_valid_credentials_return_a_token_pair(self, api, user):
        response = login(api)

        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"access", "refresh"}
        # No email, no name, no id: the token pair is the whole answer.
        assert "ada@example.com" not in response.content.decode()

    def test_login_stamps_last_login(self, api, user):
        login(api)
        user.refresh_from_db()
        assert user.last_login is not None

    def test_a_wrong_password_is_a_generic_401(self, api, user):
        response = login(api, password="wrong")

        assert response.status_code == 401
        assert response.json()["detail"] == INVALID_CREDENTIALS_DETAIL
        assert response.json()["code"] == "invalid_credentials"

    def test_an_unknown_address_is_indistinguishable_from_a_wrong_password(
        self, api, user
    ):
        wrong = login(api, password="wrong")
        unknown = api.post(
            LOGIN_URL,
            {"email": "nobody@example.com", "password": "wrong"},
            format="json",
        )

        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json()["detail"] == unknown.json()["detail"]
        assert wrong.json()["code"] == unknown.json()["code"]

    def test_a_deactivated_account_is_the_same_401(self, api, user):
        user.is_active = False
        user.save(update_fields=["is_active"])

        response = login(api)

        assert response.status_code == 401
        assert response.json()["code"] == "invalid_credentials"

    def test_an_unverified_address_is_a_403_after_the_right_password(self, api, user):
        user.email_verified = False
        user.save(update_fields=["email_verified"])

        response = login(api)

        assert response.status_code == 403
        assert response.json()["code"] == "email_not_verified"
        assert "access" not in response.json()

    def test_an_unverified_address_with_a_wrong_password_stays_401(self, api, user):
        user.email_verified = False
        user.save(update_fields=["email_verified"])

        response = login(api, password="wrong")

        assert response.status_code == 401

    def test_the_fifth_failure_locks_and_returns_423(self, api, user):
        statuses = [login(api, password="wrong").status_code for _ in range(5)]

        assert statuses == [401, 401, 401, 401, 423]

        locked = login(api, password="wrong").json()
        assert locked["code"] == "account_locked"
        assert 0 < locked["retry_after"] <= 15 * 60

        # Even the correct password is refused while the lock holds.
        assert login(api).status_code == 423

        user.refresh_from_db()
        assert user.is_locked()
        assert (
            AuditLogEntry.objects.filter(action=LOGIN_LOCKOUT_AUDIT_ACTION).count() == 1
        )

    def test_the_lockout_body_uses_the_mm_ss_countdown(self, api, user):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
            login(api, password="wrong")

        detail = login(api, password="wrong").json()["detail"]

        # design.md S01: "Too many attempts. Try again in 14:32." The minutes
        # start at 15 on a fresh lock and count down, so the shape is what is
        # asserted here.
        assert re.search(r"Try again in \d{1,2}:\d{2}\.", detail), detail


class TestTokenLifetimes:
    def test_d7_settings_are_the_documented_ones(self):
        assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] == timedelta(minutes=15)
        assert settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] == timedelta(days=7)
        assert settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"] is True
        assert settings.SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] is True
        assert "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS

    def test_the_access_token_lives_fifteen_minutes(self, api, user):
        access = login(api).json()["access"]

        payload = AccessToken(access).payload

        assert payload["exp"] - payload["iat"] == 15 * 60


class TestRefresh:
    def test_refresh_rotates_the_pair(self, api, user):
        original = login(api).json()

        response = api.post(
            REFRESH_URL, {"refresh": original["refresh"]}, format="json"
        )

        assert response.status_code == 200
        rotated = response.json()
        assert rotated["access"] != original["access"]
        assert rotated["refresh"] != original["refresh"]

    def test_rotation_blacklists_the_previous_refresh_token(self, api, user):
        original = login(api).json()

        api.post(REFRESH_URL, {"refresh": original["refresh"]}, format="json")

        replay = api.post(REFRESH_URL, {"refresh": original["refresh"]}, format="json")

        assert replay.status_code == 401

    def test_a_malformed_refresh_token_is_401(self, api):
        response = api.post(REFRESH_URL, {"refresh": "not-a-token"}, format="json")
        assert response.status_code == 401

    def test_refresh_requires_the_field(self, api):
        assert api.post(REFRESH_URL, {}, format="json").status_code == 400


class TestLogout:
    def test_logout_blacklists_the_refresh_token(self, api, user):
        tokens = login(api).json()

        response = api.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json")

        assert response.status_code == 204
        assert (
            api.post(
                REFRESH_URL, {"refresh": tokens["refresh"]}, format="json"
            ).status_code
            == 401
        )

    def test_a_second_logout_with_the_same_token_is_401(self, api, user):
        tokens = login(api).json()
        api.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json")

        second = api.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json")

        assert second.status_code in (400, 401)

    def test_logout_with_a_malformed_token_is_401(self, api):
        assert (
            api.post(LOGOUT_URL, {"refresh": "garbage"}, format="json").status_code
            == 401
        )

    def test_logout_needs_no_access_token(self, api, user):
        # The refresh token in the body is the credential; requiring a bearer
        # header as well would mean an expired access token cannot log out.
        tokens = login(api).json()
        api.credentials()

        assert (
            api.post(
                LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json"
            ).status_code
            == 204
        )


class TestThrottle:
    def test_the_login_view_uses_the_login_scope(self):
        assert LoginView.throttle_scope == "login"

    @pytest.fixture
    def low_rates(self, monkeypatch):
        monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {"login": "2/minute"})

    def test_login_is_throttled(self, api, user, low_rates):
        statuses = [login(api, password="wrong").status_code for _ in range(3)]

        assert statuses == [401, 401, 429]


class TestSchema:
    def test_the_three_operations_are_in_the_openapi_document(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)

        for path in (LOGIN_URL, REFRESH_URL, LOGOUT_URL):
            assert path in schema["paths"], path
