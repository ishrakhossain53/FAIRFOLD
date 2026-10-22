"""Employer company-profile API tests (REQ-FR-045, REQ-FR-042, batch 1.24).

What these tests pin down beyond the happy path:

* the target is the caller -- there is no id in the path or the body, so a
  second employer's PATCH cannot reach the first employer's row;
* the endpoint is employer-only. A candidate, interviewer or platform admin
  gets 403, not an automatically created profile;
* the body is a whitelist. `user`, `id`, billing columns and `created_at` change
  nothing;
* GET is a read. It returns 404 before onboarding rather than creating a row;
* PATCH is the documented create-or-update operation. §C.12 lists no POST, so
  the first PATCH carrying `company_name` creates the profile;
* `show_company_name` is false until the employer opts in (REQ-FR-042) and is
  never accepted from an undeclared column.

`force_authenticate` is not used. The 401 and role cases run through the real JWT
path the frontend uses; a forced request would skip the authenticator's 401.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from employers.models import EmployerProfile

pytestmark = pytest.mark.django_db

URL = "/api/v1/employers/me/"

EXPECTED_KEYS = {
    "company_name",
    "industry",
    "company_size",
    "show_company_name",
}


def api_client(user) -> APIClient:
    """A real JWT client for `user`; no forced authentication."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


def profile_payload(**overrides) -> dict:
    payload = {
        "company_name": "Acme Ltd",
        "industry": "Software",
        "company_size": 40,
        "show_company_name": False,
    }
    payload.update(overrides)
    return payload


class TestRead:
    def test_anonymous_is_401(self):
        response = APIClient().get(URL)

        assert response.status_code == 401

    def test_get_without_a_profile_is_404_and_does_not_create_one(self, make_user):
        employer = make_user("employer_hr")

        response = api_client(employer).get(URL)

        assert response.status_code == 404
        assert not EmployerProfile.objects.filter(user=employer).exists()
        assert "onboarding" in response.data["detail"].lower()

    def test_get_returns_the_callers_profile(self, make_user):
        employer = make_user("employer_hr")
        EmployerProfile.objects.create(
            user=employer,
            company_name="Acme Ltd",
            industry="Software",
            company_size=40,
            show_company_name=True,
        )

        response = api_client(employer).get(URL)

        assert response.status_code == 200
        assert set(response.data) == EXPECTED_KEYS
        assert response.data["company_name"] == "Acme Ltd"
        assert response.data["industry"] == "Software"
        assert response.data["company_size"] == 40
        assert response.data["show_company_name"] is True

    def test_the_body_does_not_expose_the_owner_or_billing_columns(self, make_user):
        employer = make_user("employer_hr")
        EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")

        body = api_client(employer).get(URL).data

        for forbidden in (
            "id",
            "user",
            "email",
            "billing_plan",
            "billing_cycle",
            "stripe_customer_id",
            "created_at",
        ):
            assert forbidden not in body


class TestCreateAndUpdate:
    def test_the_first_patch_with_a_company_name_creates_the_profile(self, make_user):
        employer = make_user("employer_hr")

        response = api_client(employer).patch(URL, profile_payload(), format="json")

        assert response.status_code == 200
        assert set(response.data) == EXPECTED_KEYS
        profile = EmployerProfile.objects.get(user=employer)
        assert profile.company_name == "Acme Ltd"
        assert profile.industry == "Software"
        assert profile.company_size == 40
        assert profile.show_company_name is False

    def test_a_minimal_create_needs_only_a_company_name(self, make_user):
        employer = make_user("employer_hr")

        response = api_client(employer).patch(
            URL, {"company_name": "Acme Ltd"}, format="json"
        )

        assert response.status_code == 200
        profile = EmployerProfile.objects.get(user=employer)
        assert profile.company_name == "Acme Ltd"
        assert profile.industry == ""
        assert profile.company_size is None
        assert profile.show_company_name is False

    @pytest.mark.parametrize(
        "body",
        [
            {"industry": "Software"},
            {"company_name": ""},
            {"company_name": "   "},
            {"company_size": 40},
        ],
    )
    def test_a_create_without_a_company_name_is_400_and_creates_nothing(
        self, make_user, body
    ):
        employer = make_user("employer_hr")

        response = api_client(employer).patch(URL, body, format="json")

        assert response.status_code == 400
        assert "company_name" in response.data
        assert not EmployerProfile.objects.filter(user=employer).exists()

    def test_an_empty_patch_without_a_profile_is_404_and_creates_nothing(
        self, make_user
    ):
        employer = make_user("employer_hr")

        response = api_client(employer).patch(URL, {}, format="json")

        assert response.status_code == 404
        assert not EmployerProfile.objects.filter(user=employer).exists()

    def test_an_empty_patch_on_an_existing_profile_is_a_no_op(self, make_user):
        employer = make_user("employer_hr")
        EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")

        response = api_client(employer).patch(URL, {}, format="json")

        assert response.status_code == 200
        assert response.data["company_name"] == "Acme Ltd"
        assert EmployerProfile.objects.get(user=employer).company_name == "Acme Ltd"

    def test_patch_updates_only_the_fields_that_were_sent(self, make_user):
        employer = make_user("employer_hr")
        EmployerProfile.objects.create(
            user=employer,
            company_name="Acme Ltd",
            industry="Software",
            company_size=40,
            show_company_name=False,
        )

        response = api_client(employer).patch(
            URL, {"industry": "Healthcare"}, format="json"
        )

        assert response.status_code == 200
        profile = EmployerProfile.objects.get(user=employer)
        assert profile.company_name == "Acme Ltd"
        assert profile.industry == "Healthcare"
        assert profile.company_size == 40
        assert profile.show_company_name is False

    def test_a_patch_can_turn_the_public_name_on(self, make_user):
        employer = make_user("employer_hr")
        EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")

        response = api_client(employer).patch(
            URL, {"show_company_name": True}, format="json"
        )

        assert response.status_code == 200
        assert response.data["show_company_name"] is True
        assert EmployerProfile.objects.get(user=employer).show_company_name is True

    def test_company_size_accepts_null(self, make_user):
        employer = make_user("employer_hr")
        EmployerProfile.objects.create(
            user=employer, company_name="Acme Ltd", company_size=40
        )

        response = api_client(employer).patch(
            URL, {"company_size": None}, format="json"
        )

        assert response.status_code == 200
        assert EmployerProfile.objects.get(user=employer).company_size is None

    def test_put_is_not_documented_and_is_rejected(self, make_user):
        employer = make_user("employer_hr")
        EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")

        response = api_client(employer).put(URL, profile_payload(), format="json")

        assert response.status_code == 405


class TestValidation:
    def test_industry_over_100_characters_is_a_field_error(self, make_user):
        employer = make_user("employer_hr")

        response = api_client(employer).patch(
            URL, {"company_name": "Acme Ltd", "industry": "x" * 101}, format="json"
        )

        assert response.status_code == 400
        assert "industry" in response.data
        assert not EmployerProfile.objects.filter(user=employer).exists()

    def test_company_size_must_be_an_integer(self, make_user):
        employer = make_user("employer_hr")

        response = api_client(employer).patch(
            URL,
            {"company_name": "Acme Ltd", "company_size": "not-a-number"},
            format="json",
        )

        assert response.status_code == 400
        assert "company_size" in response.data

    def test_show_company_name_must_be_boolean(self, make_user):
        employer = make_user("employer_hr")

        response = api_client(employer).patch(
            URL,
            {"company_name": "Acme Ltd", "show_company_name": "sometimes"},
            format="json",
        )

        assert response.status_code == 400
        assert "show_company_name" in response.data

    def test_null_company_name_is_not_accepted(self, make_user):
        employer = make_user("employer_hr")

        response = api_client(employer).patch(
            URL, {"company_name": None}, format="json"
        )

        assert response.status_code == 400
        assert "company_name" in response.data


class TestWhitelist:
    def test_unknown_and_read_only_keys_change_nothing(self, make_user):
        employer = make_user("employer_hr")
        other = make_user("employer_hr")
        profile = EmployerProfile.objects.create(
            user=employer,
            company_name="Original",
            industry="Software",
            company_size=40,
        )

        response = api_client(employer).patch(
            URL,
            {
                "company_name": "Updated",
                "user": str(other.pk),
                "id": str(uuid.uuid4()),
                "billing_plan": "enterprise",
                "billing_cycle": "yearly",
                "stripe_customer_id": "cus_attacker",
                "created_at": "2000-01-01T00:00:00Z",
                "email": "attacker@example.com",
            },
            format="json",
        )

        assert response.status_code == 200
        profile.refresh_from_db()
        assert profile.company_name == "Updated"
        assert profile.user == employer
        assert profile.billing_plan == "free"
        assert profile.billing_cycle == "monthly"
        assert profile.stripe_customer_id == ""


class TestOwnership:
    def test_two_employers_read_and_write_only_their_own_rows(self, make_user):
        first = make_user("employer_hr")
        second = make_user("employer_hr")

        first_client = api_client(first)
        second_client = api_client(second)

        assert (
            first_client.patch(
                URL, {"company_name": "First Ltd"}, format="json"
            ).status_code
            == 200
        )
        assert (
            second_client.patch(
                URL, {"company_name": "Second Ltd"}, format="json"
            ).status_code
            == 200
        )

        assert EmployerProfile.objects.get(user=first).company_name == "First Ltd"
        assert EmployerProfile.objects.get(user=second).company_name == "Second Ltd"
        assert first_client.get(URL).data["company_name"] == "First Ltd"
        assert second_client.get(URL).data["company_name"] == "Second Ltd"

    def test_a_patch_cannot_address_another_employer(self, make_user):
        first = make_user("employer_hr")
        second = make_user("employer_hr")
        EmployerProfile.objects.create(user=first, company_name="First Ltd")

        # The path has no id and the body's `user` is not declared, so this is
        # only ever an update of `second`.
        response = api_client(second).patch(
            URL,
            {"company_name": "Second Ltd", "user": str(first.pk)},
            format="json",
        )

        assert response.status_code == 200
        assert EmployerProfile.objects.get(user=first).company_name == "First Ltd"
        assert EmployerProfile.objects.get(user=second).company_name == "Second Ltd"


class TestRoleGate:
    def test_a_candidate_cannot_read_or_write(self, make_user):
        candidate = make_user("candidate")
        client = api_client(candidate)

        assert client.get(URL).status_code == 403
        assert (
            client.patch(URL, {"company_name": "Nope"}, format="json").status_code
            == 403
        )
        assert not EmployerProfile.objects.filter(user=candidate).exists()

    def test_an_interviewer_cannot_read_or_write(self, make_user):
        interviewer = make_user("interviewer")
        client = api_client(interviewer)

        assert client.get(URL).status_code == 403
        assert (
            client.patch(URL, {"company_name": "Nope"}, format="json").status_code
            == 403
        )
        assert not EmployerProfile.objects.filter(user=interviewer).exists()

    def test_an_admin_without_an_employer_group_cannot_read_or_write(self, make_user):
        admin = make_user(is_staff=True, is_superuser=True)
        client = api_client(admin)

        assert client.get(URL).status_code == 403
        assert (
            client.patch(URL, {"company_name": "Nope"}, format="json").status_code
            == 403
        )
        assert not EmployerProfile.objects.filter(user=admin).exists()

    def test_an_employer_manager_is_an_employer(self, make_user):
        manager = make_user("employer_manager")
        client = api_client(manager)

        response = client.patch(URL, {"company_name": "Managed Ltd"}, format="json")

        assert response.status_code == 200
        assert EmployerProfile.objects.get(user=manager).company_name == "Managed Ltd"

    def test_anonymous_cannot_write(self):
        response = APIClient().patch(URL, {"company_name": "Nope"}, format="json")

        assert response.status_code == 401
