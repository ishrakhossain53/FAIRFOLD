"""API tests for registration and email verification (REQ-FR-001, D-3).

These tests sit on top of the service tests (`test_registration.py`,
`test_email_verification.py`) and assert only what the HTTP layer adds:

* the endpoints are anonymous -- the global `DEFAULT_PERMISSION_CLASSES` is
  `IsAuthenticated`, so a view that forgets `permission_classes = []` 401s every
  signup;
* a duplicate address is indistinguishable from a new one, in status *and* body,
  because the public form must not become an account-enumeration oracle;
* a weak password comes back keyed to `password`, not as a 500;
* expired and tampered links are different 400s, because page #11 has different
  copy for each;
* the resend endpoint answers identically for a known address, an unknown one, a
  verified account and a request inside the cooldown;
* the throttle scope actually throttles;
* drf-spectacular still generates a document and lists the three operations.

Celery is deliberately not eager in CI, so the tasks are captured by patching
`.delay`. `transaction.on_commit` is captured with pytest-django's
`django_capture_on_commit_callbacks`; the default `django_db` wrapper never
commits, and without the fixture every dispatch assertion would be vacuous.
"""

from __future__ import annotations

import json
import time
from unittest import mock

import pytest
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from accounts.api_views import (
    RegisterView,
    ResendVerificationEmailView,
    VerifyEmailView,
)
from accounts.models import User
from accounts.services import REGISTRATION_AUDIT_ACTION, make_verification_token
from accounts.tasks import send_verification_email
from core.models import AuditLogEntry

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/v1/auth/register/"
VERIFY_URL = "/api/v1/auth/verify-email/"
RESEND_URL = "/api/v1/auth/verify-email/resend/"

# Long, not numeric, not in Django's common-password list and not similar to the
# names below. Same constant as test_registration.py on purpose: a different
# password here would let one file's password policy drift from the other's.
STRONG_PASSWORD = "Wanderlust7Quartz-Meadow"


@pytest.fixture(autouse=True)
def _clean_cache():
    """Clear throttle counters and resend cooldowns between tests.

    Both live in Redis, which is not rolled back with the database. Without this
    a throttle test leaves a counter that makes the next test 429, and a signup
    leaves a cooldown that makes a resend test look broken.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def dispatched(monkeypatch):
    """Record verification-email dispatches instead of using the broker."""
    calls: list[str] = []

    def _delay(user_id: str) -> None:
        calls.append(user_id)

    monkeypatch.setattr(send_verification_email, "delay", _delay)
    return calls


def payload(**overrides) -> dict:
    body = {
        "email": "ada@example.com",
        "password": STRONG_PASSWORD,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "role": "candidate",
    }
    body.update(overrides)
    return body


def _resolve(schema: dict, node: dict) -> dict:
    """Follow a component `$ref`, if the node is one."""
    ref = node.get("$ref")
    if not ref:
        return node
    return schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]


class TestAnonymousAccess:
    def test_all_three_views_opt_out_of_the_authenticated_default(self):
        # The single most likely way to break signup: the project default is
        # IsAuthenticated, and an empty `permission_classes` is easy to forget.
        for view in (RegisterView, VerifyEmailView, ResendVerificationEmailView):
            assert view.permission_classes == []
            assert view.authentication_classes == []

    def test_register_succeeds_without_credentials(self, api, role_groups):
        response = api.post(REGISTER_URL, payload(), format="json")

        assert response.status_code == 201

    def test_the_api_index_lists_the_auth_prefix(self, api):
        response = api.get("/api/v1/")

        assert response.status_code == 200
        assert response.json()["domains"]["auth"] == "/api/v1/auth/"


class TestRegisterSuccess:
    def test_creates_an_unverified_candidate(self, api, role_groups):
        response = api.post(REGISTER_URL, payload(), format="json")

        assert response.status_code == 201
        user = User.objects.get(email="ada@example.com")
        assert user.email_verified is False
        assert user.is_candidate is True
        assert user.check_password(STRONG_PASSWORD) is True

    def test_employer_signup_gets_the_base_employer_role(self, api, role_groups):
        response = api.post(REGISTER_URL, payload(role="employer_hr"), format="json")

        assert response.status_code == 201
        assert User.objects.get(email="ada@example.com").is_employer is True

    def test_the_body_reports_what_was_stored_and_not_the_account_id(
        self, api, role_groups
    ):
        response = api.post(
            REGISTER_URL, payload(email="Ada@Example.COM"), format="json"
        )

        body = response.json()
        assert body["email"] == "ada@example.com"
        assert body["email_verified"] is False
        assert "detail" in body
        user = User.objects.get(email="ada@example.com")
        assert str(user.pk) not in response.content.decode()
        assert STRONG_PASSWORD not in response.content.decode()

    def test_writes_one_audit_entry_with_the_role_only(self, api, role_groups):
        api.post(REGISTER_URL, payload(), format="json")

        entry = AuditLogEntry.objects.get(action=REGISTRATION_AUDIT_ACTION)
        assert entry.details == {"role": "candidate"}
        serialised = json.dumps(entry.details)
        assert "ada@example.com" not in serialised
        assert "Lovelace" not in serialised

    def test_queues_one_verification_email_by_user_id(
        self, api, role_groups, dispatched, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            api.post(REGISTER_URL, payload(), format="json")

        user = User.objects.get(email="ada@example.com")
        assert dispatched == [str(user.pk)]
        # The payload crossing the broker must carry no address.
        assert "@" not in dispatched[0]


class TestRegisterValidation:
    @pytest.mark.parametrize(
        "field", ["email", "password", "first_name", "last_name", "role"]
    )
    def test_a_missing_field_is_a_400_keyed_to_that_field(
        self, api, role_groups, field
    ):
        body = payload()
        body.pop(field)

        response = api.post(REGISTER_URL, body, format="json")

        assert response.status_code == 400
        assert field in response.json()
        assert User.objects.count() == 0

    def test_a_malformed_address_is_a_400_keyed_to_email(self, api, role_groups):
        response = api.post(
            REGISTER_URL, payload(email="not-an-address"), format="json"
        )

        assert response.status_code == 400
        assert "email" in response.json()

    def test_a_weak_password_is_a_400_keyed_to_password(self, api, role_groups):
        response = api.post(REGISTER_URL, payload(password="password"), format="json")

        assert response.status_code == 400
        assert "password" in response.json()
        assert User.objects.count() == 0

    def test_the_password_is_not_trimmed(self, api, role_groups):
        response = api.post(
            REGISTER_URL, payload(password=f" {STRONG_PASSWORD} "), format="json"
        )

        assert response.status_code == 201
        user = User.objects.get(email="ada@example.com")
        assert user.check_password(f" {STRONG_PASSWORD} ") is True

    @pytest.mark.parametrize("role", ["employer_manager", "interviewer", "admin"])
    def test_a_role_the_signup_form_may_not_grant_is_a_400(
        self, api, role_groups, role
    ):
        response = api.post(REGISTER_URL, payload(role=role), format="json")

        assert response.status_code == 400
        assert "role" in response.json()
        assert User.objects.count() == 0

    def test_a_whitespace_only_name_is_a_400(self, api, role_groups):
        response = api.post(REGISTER_URL, payload(first_name="   "), format="json")

        assert response.status_code == 400
        assert "first_name" in response.json()


class TestRegisterDuplicate:
    def test_a_duplicate_address_returns_the_identical_success_body(
        self, api, role_groups
    ):
        first = api.post(REGISTER_URL, payload(), format="json")
        second = api.post(REGISTER_URL, payload(), format="json")

        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json() == second.json()
        assert User.objects.filter(email="ada@example.com").count() == 1

    def test_a_duplicate_does_not_touch_the_existing_account(self, api, role_groups):
        api.post(REGISTER_URL, payload(), format="json")

        api.post(
            REGISTER_URL,
            payload(
                password="Meadow8Quartz-Wanderlust",
                first_name="Someone",
                last_name="Else",
            ),
            format="json",
        )

        user = User.objects.get(email="ada@example.com")
        assert user.check_password(STRONG_PASSWORD) is True
        assert user.first_name == "Ada"
        assert user.last_name == "Lovelace"

    def test_a_duplicate_queues_no_second_email(
        self, api, role_groups, dispatched, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            api.post(REGISTER_URL, payload(), format="json")
            api.post(REGISTER_URL, payload(), format="json")

        assert len(dispatched) == 1


class TestVerifyEmail:
    def test_a_valid_token_verifies_the_account(self, api, make_user):
        user = make_user()
        token = make_verification_token(user)

        response = api.post(VERIFY_URL, {"token": token}, format="json")

        assert response.status_code == 200
        assert "detail" in response.json()
        assert User.objects.get(pk=user.pk).email_verified is True

    def test_a_second_use_reports_success(self, api, make_user):
        user = make_user()
        token = make_verification_token(user)

        api.post(VERIFY_URL, {"token": token}, format="json")
        second = api.post(VERIFY_URL, {"token": token}, format="json")

        # Design.md page #11's success state, not an error page.
        assert second.status_code == 200

    def test_an_expired_token_is_the_expired_state(self, api, make_user):
        user = make_user()
        lifetime = settings.EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS
        with mock.patch.object(
            signing.TimestampSigner,
            "timestamp",
            return_value=signing.b62_encode(int(time.time()) - lifetime - 60),
        ):
            token = make_verification_token(user)

        response = api.post(VERIFY_URL, {"token": token}, format="json")

        assert response.status_code == 400
        assert response.json()["code"] == "token_expired"
        assert token not in response.content.decode()
        assert User.objects.get(pk=user.pk).email_verified is False

    def test_a_tampered_token_is_invalid(self, api, make_user):
        user = make_user()
        token = make_verification_token(user)
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

        response = api.post(VERIFY_URL, {"token": tampered}, format="json")

        assert response.status_code == 400
        assert response.json()["code"] == "invalid_token"
        assert User.objects.get(pk=user.pk).email_verified is False

    def test_a_token_for_a_deleted_account_is_invalid(self, api, make_user):
        user = make_user()
        token = make_verification_token(user)
        user.delete()

        response = api.post(VERIFY_URL, {"token": token}, format="json")

        assert response.status_code == 400
        assert response.json()["code"] == "invalid_token"

    def test_a_missing_token_is_a_400_keyed_to_the_field(self, api):
        response = api.post(VERIFY_URL, {}, format="json")

        assert response.status_code == 400
        assert "token" in response.json()


class TestResend:
    def test_a_known_address_queues_one_email(
        self, api, make_user, dispatched, django_capture_on_commit_callbacks
    ):
        user = make_user()

        with django_capture_on_commit_callbacks(execute=True):
            response = api.post(RESEND_URL, {"email": user.email}, format="json")

        assert response.status_code == 202
        assert dispatched == [str(user.pk)]

    def test_an_unknown_address_returns_the_same_body(
        self, api, make_user, dispatched, django_capture_on_commit_callbacks
    ):
        known = make_user()
        with django_capture_on_commit_callbacks(execute=True):
            known_response = api.post(RESEND_URL, {"email": known.email}, format="json")
            unknown_response = api.post(
                RESEND_URL, {"email": "nobody@example.com"}, format="json"
            )

        assert known_response.status_code == unknown_response.status_code == 202
        assert known_response.json() == unknown_response.json()
        assert len(dispatched) == 1

    def test_a_request_inside_the_cooldown_sends_nothing_extra(
        self, api, make_user, dispatched, django_capture_on_commit_callbacks
    ):
        user = make_user()
        with django_capture_on_commit_callbacks(execute=True):
            api.post(RESEND_URL, {"email": user.email}, format="json")
            second = api.post(RESEND_URL, {"email": user.email}, format="json")

        assert second.status_code == 202
        assert len(dispatched) == 1

    def test_a_verified_account_is_answered_but_not_emailed(
        self, api, make_user, dispatched, django_capture_on_commit_callbacks
    ):
        user = make_user(email_verified=True)

        with django_capture_on_commit_callbacks(execute=True):
            response = api.post(RESEND_URL, {"email": user.email}, format="json")

        assert response.status_code == 202
        assert dispatched == []

    def test_the_address_is_matched_after_normalisation(self, api, make_user):
        user = make_user(email="ada@example.com")

        # A different case must still find the row the signup created.
        response = api.post(RESEND_URL, {"email": "Ada@Example.COM"}, format="json")

        assert response.status_code == 202
        assert User.objects.get(pk=user.pk).email == "ada@example.com"

    def test_a_missing_address_is_a_400(self, api):
        response = api.post(RESEND_URL, {}, format="json")

        assert response.status_code == 400
        assert "email" in response.json()


class TestThrottling:
    @pytest.fixture
    def low_rates(self, monkeypatch):
        """Two requests per hour for both scopes.

        Patching the class attribute is what DRF's own tests do: `api_settings`
        caches `DEFAULT_THROTTLE_RATES`, so `override_settings` alone would not
        reach an already-imported throttle class.
        """
        monkeypatch.setattr(
            SimpleRateThrottle,
            "THROTTLE_RATES",
            {"register": "2/hour", "verify_email": "2/hour"},
        )

    def test_register_is_throttled(self, api, role_groups, low_rates):
        statuses = [
            api.post(
                REGISTER_URL, payload(email=f"user{i}@example.com"), format="json"
            ).status_code
            for i in range(3)
        ]

        assert statuses == [201, 201, 429]

    def test_verify_email_is_throttled(self, api, low_rates):
        statuses = [
            api.post(VERIFY_URL, {"token": "not-a-token"}, format="json").status_code
            for _ in range(3)
        ]

        assert statuses == [400, 400, 429]

    def test_the_throttled_response_uses_the_shared_error_shape(self, api, low_rates):
        for _ in range(2):
            api.post(VERIFY_URL, {"token": "not-a-token"}, format="json")

        response = api.post(VERIFY_URL, {"token": "not-a-token"}, format="json")

        assert response.status_code == 429
        assert "detail" in response.json()


class TestSchema:
    """The Done-when for this batch: `/api/schema/` still generates.

    `config/urls.py` mounts the schema view only when `DEBUG` is on, and the test
    settings keep `DEBUG=False` on purpose. So the check calls the generator
    directly -- the same call `SpectacularAPIView` makes -- instead of taking the
    URL out of the settings that production shares.
    """

    def test_the_document_generates_and_lists_the_auth_paths(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)

        for path in (REGISTER_URL, VERIFY_URL, RESEND_URL):
            assert path in schema["paths"], path
            assert "post" in schema["paths"][path]

    def test_the_register_body_documents_every_accepted_field(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)
        operation = schema["paths"][REGISTER_URL]["post"]
        body = _resolve(
            schema,
            operation["requestBody"]["content"]["application/json"]["schema"],
        )

        assert set(body["properties"]) == {
            "email",
            "first_name",
            "last_name",
            "password",
            "role",
        }
        assert body["properties"]["password"].get("writeOnly") is True

    def test_the_register_role_enum_is_the_self_assignable_set(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)
        operation = schema["paths"][REGISTER_URL]["post"]
        body = _resolve(
            schema,
            operation["requestBody"]["content"]["application/json"]["schema"],
        )
        role = _resolve(schema, body["properties"]["role"])

        assert role["enum"] == ["candidate", "employer_hr"]

    def test_the_verify_endpoint_documents_both_outcomes(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)
        responses = schema["paths"][VERIFY_URL]["post"]["responses"]

        assert "200" in responses
        assert "400" in responses
