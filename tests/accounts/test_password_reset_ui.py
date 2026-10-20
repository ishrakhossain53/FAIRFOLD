"""Password reset page tests (REQ-FR-004, design.md pages #9 and #10, X02).

The flow is three pages: request, "if that email exists", and the new-password
form with its expired state. These assert the parts the service tests cannot:
the generic sentence is the same for a known and an unknown address, the token
travels in hidden fields and never in the action URL, an expired or reused link
renders one state, and the page is not cached.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.utils.http import urlsafe_base64_encode

from accounts.models import User
from accounts.services import make_password_reset_token
from accounts.tasks import send_password_reset_email

pytestmark = pytest.mark.django_db

FORGOT_URL = "/forgot-password/"
RESET_URL = "/reset-password/"

PASSWORD = "Wanderlust7Quartz-Meadow"
NEW_PASSWORD = "Cobalt8Juniper-Harbour"


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


def uid_for(user: User) -> str:
    return urlsafe_base64_encode(str(user.pk).encode())


def reset_get(client: Client, user: User, token: str | None = None):
    return client.get(
        RESET_URL,
        {
            "uid": uid_for(user),
            "token": token if token is not None else make_password_reset_token(user),
        },
    )


class TestForgotPasswordPage:
    def test_get_renders_page_9(self, client):
        response = client.get(FORGOT_URL)
        body = response.content.decode()

        assert response.status_code == 200
        assert "Reset your password" in body
        assert 'name="email"' in body
        assert "Send reset link" in body

    def test_a_known_address_gets_the_generic_sentence(
        self, client, user, monkeypatch, django_capture_on_commit_callbacks
    ):
        calls: list[str] = []
        monkeypatch.setattr(
            send_password_reset_email, "delay", lambda user_id: calls.append(user_id)
        )

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(FORGOT_URL, {"email": "ada@example.com"})

        assert response.status_code == 200
        assert (
            "If that email exists, we&#x27;ve sent a link." in response.content.decode()
            or ("If that email exists, we've sent a link." in response.content.decode())
        )
        assert calls == [str(user.pk)]

    def test_an_unknown_address_gets_the_same_page(
        self, client, user, monkeypatch, django_capture_on_commit_callbacks
    ):
        calls: list[str] = []
        monkeypatch.setattr(
            send_password_reset_email, "delay", lambda user_id: calls.append(user_id)
        )

        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(FORGOT_URL, {"email": "nobody@example.com"})

        assert response.status_code == 200
        assert "If that email exists" in response.content.decode()
        # No mail queued, and the page does not say so.
        assert calls == []

    def test_a_malformed_address_re_renders_the_form(self, client):
        response = client.post(FORGOT_URL, {"email": "not-an-email"})
        body = response.content.decode()

        assert response.status_code == 200
        assert "There is a problem with your details" in body
        assert "If that email exists" not in body


class TestResetPasswordPage:
    def test_get_renders_page_10_with_the_token_in_a_hidden_field(self, client, user):
        token = make_password_reset_token(user)

        response = reset_get(client, user, token)
        body = response.content.decode()

        assert response.status_code == 200
        assert "Choose a new password" in body
        assert 'name="uid"' in body
        assert 'name="token"' in body
        assert token in body
        # The token is not in the form action: it would land in the access log
        # a second time.
        assert f'action="{RESET_URL}?' not in body

    def test_a_valid_post_changes_the_password(self, client, user):
        token = make_password_reset_token(user)

        response = client.post(
            RESET_URL,
            {
                "uid": uid_for(user),
                "token": token,
                "new_password": NEW_PASSWORD,
                "confirm_password": NEW_PASSWORD,
            },
        )

        assert response.status_code == 200
        assert "Password changed" in response.content.decode()
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)

    def test_a_reused_link_shows_the_expired_state(self, client, user):
        token = make_password_reset_token(user)
        body = {
            "uid": uid_for(user),
            "token": token,
            "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD,
        }
        first = client.post(RESET_URL, body)

        second = client.post(
            RESET_URL,
            {
                **body,
                "new_password": "Saffron9Orchard-Lantern",
                "confirm_password": "Saffron9Orchard-Lantern",
            },
        )

        assert first.status_code == 200
        assert second.status_code == 400
        assert "This link has expired" in second.content.decode()

    def test_a_bad_token_shows_the_expired_state_on_get(self, client, user):
        response = reset_get(client, user, "not-a-token")

        assert response.status_code == 400
        assert "This link has expired" in response.content.decode()
        assert "Request new link" in response.content.decode()

    def test_an_unknown_uid_shows_the_expired_state(self, client, user):
        response = client.get(
            RESET_URL,
            {
                "uid": urlsafe_base64_encode(b"not-a-uuid"),
                "token": "anything",
            },
        )

        assert response.status_code == 400
        assert "This link has expired" in response.content.decode()

    def test_a_mismatch_is_a_field_error(self, client, user):
        response = client.post(
            RESET_URL,
            {
                "uid": uid_for(user),
                "token": make_password_reset_token(user),
                "new_password": NEW_PASSWORD,
                "confirm_password": "Something9Else-Entirely",
            },
        )

        body = response.content.decode()
        assert response.status_code == 200
        assert "The two passwords do not match." in body
        user.refresh_from_db()
        assert user.check_password(PASSWORD)

    def test_a_weak_password_is_a_field_error(self, client, user):
        response = client.post(
            RESET_URL,
            {
                "uid": uid_for(user),
                "token": make_password_reset_token(user),
                "new_password": "short",
                "confirm_password": "short",
            },
        )

        body = response.content.decode()
        assert response.status_code == 200
        assert "There is a problem with your details" in body
        user.refresh_from_db()
        assert user.check_password(PASSWORD)

    def test_the_page_is_never_cached_and_never_leaks_a_referrer(self, client, user):
        response = reset_get(client, user)

        assert response["Cache-Control"].startswith("no-store")
        assert response["Referrer-Policy"] == "no-referrer"
