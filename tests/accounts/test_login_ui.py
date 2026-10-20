"""Template login, logout and access-denied tests (REQ-FR-002/003, D-1, page #7).

The credential and lockout rules are tested once, in `test_login_service.py`.
These assert the page layer:

* page #7 renders a real form (email, password, "Forgot password?") and works
  without JavaScript;
* a wrong password, an unknown address and a deactivated account show the same
  sentence, and an unverified address is explained only to someone who got the
  password right;
* a locked account shows the countdown and no session;
* `next` is honoured only when it points at this host, so the login form is not
  an open redirect;
* logout is POST-only and flushes the session;
* the 403 handler renders the documented error page.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory

import config.urls
from accounts.models import User
from accounts.services import INVALID_CREDENTIALS_DETAIL, MAX_FAILED_LOGIN_ATTEMPTS
from core.views import error_403

pytestmark = pytest.mark.django_db

LOGIN_URL = "/login/"
LOGOUT_URL = "/logout/"

PASSWORD = "Wanderlust7Quartz-Meadow"


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def user(make_user) -> User:
    return make_user(
        "candidate",
        email="ada@example.com",
        password=PASSWORD,
        email_verified=True,
    )


def post_login(client: Client, password: str = PASSWORD, next_url: str = ""):
    return client.post(
        LOGIN_URL,
        {"email": "ada@example.com", "password": password, "next": next_url},
    )


class TestLoginPage:
    def test_get_renders_the_form_from_page_7(self, client):
        response = client.get(LOGIN_URL)
        body = response.content.decode()

        assert response.status_code == 200
        assert "<h1" in body and "Log in" in body
        assert 'name="email"' in body
        assert 'name="password"' in body
        assert 'autocomplete="current-password"' in body
        assert "/forgot-password/" in body
        assert "/register/" in body

    def test_valid_credentials_start_a_session_and_land_on_the_role_page(
        self, client, user
    ):
        response = post_login(client)

        assert response.status_code == 302
        # Page #16 is the candidate landing page; it forwards a candidate with
        # no profile to onboarding (#14). The dashboard is a later batch.
        assert response.url == "/candidate/profile/"
        assert client.session["_auth_user_id"] == str(user.pk)

    def test_an_authenticated_user_visiting_login_is_redirected(self, client, user):
        client.force_login(user)

        response = client.get(LOGIN_URL)

        assert response.status_code == 302
        assert response.url == "/candidate/profile/"

    def test_a_wrong_password_re_renders_with_a_generic_error(self, client, user):
        response = post_login(client, password="wrong")
        body = response.content.decode()

        assert response.status_code == 200
        assert INVALID_CREDENTIALS_DETAIL in body
        assert "_auth_user_id" not in client.session

    def test_an_unknown_address_shows_the_same_sentence(self, client, user):
        wrong = post_login(client, password="wrong")
        unknown = client.post(
            LOGIN_URL, {"email": "nobody@example.com", "password": "wrong"}
        )

        # Same sentence, same status. The page must not answer "does this
        # address have an account?".
        assert unknown.status_code == wrong.status_code == 200
        assert INVALID_CREDENTIALS_DETAIL in unknown.content.decode()
        assert INVALID_CREDENTIALS_DETAIL in wrong.content.decode()

    def test_a_deactivated_account_shows_the_generic_error(self, client, user):
        user.is_active = False
        user.save(update_fields=["is_active"])

        response = post_login(client)

        assert INVALID_CREDENTIALS_DETAIL in response.content.decode()
        assert "_auth_user_id" not in client.session

    def test_an_unverified_account_is_told_to_confirm(self, client, user):
        user.email_verified = False
        user.save(update_fields=["email_verified"])

        response = post_login(client)
        body = response.content.decode()

        assert response.status_code == 200
        assert "Confirm your email address" in body
        assert "_auth_user_id" not in client.session


class TestLockoutPage:
    def test_the_lockout_state_shows_a_countdown(self, client, user):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS - 1):
            post_login(client, password="wrong")

        response = post_login(client, password="wrong")

        body = response.content.decode()
        assert "Too many failed sign-in attempts" in body
        assert "Try again in" in body
        assert 'role="alert"' in body
        assert "_auth_user_id" not in client.session

    def test_a_locked_account_is_refused_with_the_right_password(self, client, user):
        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
            post_login(client, password="wrong")

        response = post_login(client)

        assert "Try again in" in response.content.decode()
        assert "_auth_user_id" not in client.session


class TestNextHandling:
    def test_a_local_next_is_honoured(self, client, user):
        response = post_login(client, next_url="/health/")

        assert response.status_code == 302
        assert response.url == "/health/"

    @pytest.mark.parametrize(
        "unsafe",
        [
            "https://evil.example/steal",
            "//evil.example/steal",
            "http://evil.example",
            "javascript:alert(1)",
            "/\\evil.example",
        ],
    )
    def test_an_offsite_next_falls_back_to_the_role_page(self, client, user, unsafe):
        response = post_login(client, next_url=unsafe)

        assert response.status_code == 302
        assert response.url == "/candidate/profile/"

    def test_next_is_carried_through_the_form(self, client):
        response = client.get(LOGIN_URL + "?next=/health/")

        assert 'name="next" value="/health/"' in response.content.decode()

    def test_login_url_setting_points_at_this_route(self):
        assert settings.LOGIN_URL == "/login/"


class TestLogout:
    def test_logout_flushes_the_session(self, client, user):
        client.force_login(user)

        response = client.post(LOGOUT_URL)

        assert response.status_code == 302
        assert response.url == settings.LOGOUT_REDIRECT_URL
        assert "_auth_user_id" not in client.session

    def test_logout_is_post_only(self, client, user):
        client.force_login(user)

        assert client.get(LOGOUT_URL).status_code == 405
        # A GET must not have signed the user out.
        assert client.session["_auth_user_id"] == str(user.pk)


class TestAccessDenied:
    def test_the_403_handler_renders_the_documented_page(self):
        request = RequestFactory().get("/candidate/dashboard/")
        request.user = AnonymousUser()

        response = error_403(request)

        assert response.status_code == 403
        assert "don't have access" in response.content.decode()

    def test_the_project_wires_that_handler(self):
        assert config.urls.handler403 == "core.views.error_403"
