"""Current-user endpoint tests (`GET`/`PUT /api/v1/auth/me/`, batch 1.12).

The endpoint has no requirement id of its own: Complete Doc §C.12 lists the two
operations, and prd.md §10.3 groups them with the auth routes. What these tests
pin down is the contract the batch fixed:

* the caller sees their own row and only their own row;
* the body is the four documented fields -- no lockout, MFA, staff or group
  data -- and roles are names, not ids;
* anonymous requests are 401, not 403 and not a redirect;
* PUT replaces the two names and cannot write email or any other column.

`force_authenticate` is deliberately not used. The 401 case and the "own row"
case are only meaningful through the real JWT path the frontend uses; a forced
request never exercises the authenticator's 401.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User

pytestmark = pytest.mark.django_db

ME_URL = "/api/v1/auth/me/"

# Deliberately longer than the 12-character minimum and unlike the email, so the
# value is not rejected by the similarity validator if a test ever changes it.
PASSWORD = "Wanderlust7Quartz-Meadow"

# The fields the contract allows. Kept as a set so an extra key fails the test
# instead of being ignored, which is how "never expose lockout state" regresses.
DOCUMENTED_FIELDS = {"email", "first_name", "last_name", "roles"}


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def candidate(make_user) -> User:
    return make_user(
        "candidate",
        email="ada@example.com",
        password=PASSWORD,
        email_verified=True,
        first_name="Ada",
        last_name="Lovelace",
    )


def authenticate(api: APIClient, user: User) -> APIClient:
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return api


class TestGet:
    def test_returns_the_callers_own_account(self, api, candidate):
        response = authenticate(api, candidate).get(ME_URL)

        assert response.status_code == 200
        assert response.data == {
            "email": "ada@example.com",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "roles": ["candidate"],
        }

    def test_returns_exactly_the_documented_fields(self, api, candidate):
        response = authenticate(api, candidate).get(ME_URL)

        assert set(response.data) == DOCUMENTED_FIELDS

    def test_roles_are_documented_names_in_a_stable_order(self, api, make_user):
        user = make_user(
            "interviewer",
            "employer_hr",
            email="grace@example.com",
            password=PASSWORD,
            email_verified=True,
            first_name="Grace",
            last_name="Hopper",
        )

        response = authenticate(api, user).get(ME_URL)

        # Fixture order (not Group.pk order) so the list does not shuffle
        # between requests or between databases.
        assert response.data["roles"] == ["employer_hr", "interviewer"]
        assert all(isinstance(role, str) for role in response.data["roles"])

    def test_lockout_mfa_staff_and_group_data_are_absent(self, api, candidate):
        candidate.mfa_enabled = True
        candidate.failed_login_attempts = 3
        candidate.locked_until = timezone.now() + timedelta(minutes=10)
        candidate.is_staff = True
        candidate.save(
            update_fields=[
                "mfa_enabled",
                "failed_login_attempts",
                "locked_until",
                "is_staff",
            ]
        )
        # A group that is not one of the documented roles must not leak either:
        # role names are a whitelist, not "whatever groups the user holds".
        internal = Group.objects.create(name="internal_ops")
        candidate.groups.add(internal)

        response = authenticate(api, candidate).get(ME_URL)

        assert response.status_code == 200
        assert set(response.data) == DOCUMENTED_FIELDS
        assert response.data["roles"] == ["candidate"]
        for forbidden in (
            "groups",
            "id",
            "locked_until",
            "failed_login_attempts",
            "mfa_enabled",
            "is_staff",
            "is_superuser",
            "password",
        ):
            assert forbidden not in response.data

    def test_another_users_row_is_unreachable(self, api, candidate, make_user):
        other = make_user(
            "candidate",
            email="katherine@example.com",
            password=PASSWORD,
            email_verified=True,
            first_name="Katherine",
            last_name="Johnson",
        )

        response = authenticate(api, candidate).get(ME_URL)

        assert response.data["email"] == "ada@example.com"
        assert response.data["email"] != other.email
        assert response.data["first_name"] == "Ada"
        assert response.data["first_name"] != other.first_name

    def test_a_query_parameter_cannot_select_another_user(
        self, api, candidate, make_user
    ):
        other = make_user(
            "candidate",
            email="katherine@example.com",
            password=PASSWORD,
            email_verified=True,
            first_name="Katherine",
            last_name="Johnson",
        )

        response = authenticate(api, candidate).get(f"{ME_URL}?user_id={other.pk}")

        assert response.status_code == 200
        assert response.data["email"] == "ada@example.com"

    def test_anonymous_get_is_401(self, api):
        response = api.get(ME_URL)

        assert response.status_code == 401


class TestPut:
    def test_replaces_both_names(self, api, candidate):
        response = authenticate(api, candidate).put(
            ME_URL,
            {"first_name": "Augusta", "last_name": "King"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["first_name"] == "Augusta"
        assert response.data["last_name"] == "King"
        candidate.refresh_from_db()
        assert candidate.first_name == "Augusta"
        assert candidate.last_name == "King"
        # Email is still returned but was not part of the write.
        assert response.data["email"] == "ada@example.com"

    def test_a_missing_name_is_400(self, api, candidate):
        response = authenticate(api, candidate).put(
            ME_URL,
            {"first_name": "Augusta"},
            format="json",
        )

        assert response.status_code == 400
        assert "last_name" in response.data
        candidate.refresh_from_db()
        assert candidate.first_name == "Ada"
        assert candidate.last_name == "Lovelace"

    def test_an_empty_body_is_400(self, api, candidate):
        response = authenticate(api, candidate).put(ME_URL, {}, format="json")

        assert response.status_code == 400
        assert {"first_name", "last_name"} <= set(response.data)

    def test_a_blank_name_is_400(self, api, candidate):
        response = authenticate(api, candidate).put(
            ME_URL,
            {"first_name": "   ", "last_name": "King"},
            format="json",
        )

        assert response.status_code == 400
        assert "first_name" in response.data
        candidate.refresh_from_db()
        assert candidate.first_name == "Ada"

    def test_email_and_privileged_fields_are_ignored(self, api, candidate):
        original_roles = set(candidate.groups.values_list("name", flat=True))
        other_group = Group.objects.create(name="internal_ops")

        response = authenticate(api, candidate).put(
            ME_URL,
            {
                "first_name": "Augusta",
                "last_name": "King",
                "email": "attacker@example.com",
                "is_staff": True,
                "is_superuser": True,
                "mfa_enabled": True,
                "locked_until": "2099-01-01T00:00:00Z",
                "failed_login_attempts": 99,
                "email_verified": False,
                "groups": [other_group.pk],
                "roles": ["employer_manager"],
            },
            format="json",
        )

        assert response.status_code == 200
        assert set(response.data) == DOCUMENTED_FIELDS

        candidate.refresh_from_db()
        assert candidate.first_name == "Augusta"
        assert candidate.last_name == "King"
        assert candidate.email == "ada@example.com"
        assert candidate.is_staff is False
        assert candidate.is_superuser is False
        assert candidate.mfa_enabled is False
        assert candidate.locked_until is None
        assert candidate.failed_login_attempts == 0
        assert candidate.email_verified is True
        assert set(candidate.groups.values_list("name", flat=True)) == original_roles
        assert response.data["roles"] == ["candidate"]

    def test_only_the_callers_row_changes(self, api, candidate, make_user):
        other = make_user(
            "candidate",
            email="katherine@example.com",
            password=PASSWORD,
            email_verified=True,
            first_name="Katherine",
            last_name="Johnson",
        )

        authenticate(api, candidate).put(
            ME_URL,
            {"first_name": "Augusta", "last_name": "King"},
            format="json",
        )

        other.refresh_from_db()
        assert other.first_name == "Katherine"
        assert other.last_name == "Johnson"

    def test_anonymous_put_is_401_and_writes_nothing(self, api, candidate):
        response = api.put(
            ME_URL,
            {"first_name": "Augusta", "last_name": "King"},
            format="json",
        )

        assert response.status_code == 401
        candidate.refresh_from_db()
        assert candidate.first_name == "Ada"

    def test_patch_is_not_allowed(self, api, candidate):
        """§C.12 lists GET and PUT, not PATCH. A silent PATCH would be a second
        update contract (partial) with no schema entry."""
        response = authenticate(api, candidate).patch(
            ME_URL,
            {"first_name": "Augusta"},
            format="json",
        )

        assert response.status_code == 405
        candidate.refresh_from_db()
        assert candidate.first_name == "Ada"


class TestSchema:
    def test_both_operations_are_in_the_openapi_document(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)

        assert ME_URL in schema["paths"], ME_URL
        assert {"get", "put"} <= set(schema["paths"][ME_URL])
