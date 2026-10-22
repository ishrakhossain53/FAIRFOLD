"""Employer onboarding and company-profile UI tests (REQ-FR-045, page #33).

These sit on top of the API tests (`test_employer_profile_api.py`). They assert
what the server-rendered pages add:

* anonymous users are sent to login with a `next` back to the page; an
  authenticated candidate, interviewer or admin gets 403, not a profile created
  for them;
* onboarding creates the four §5.1 columns and validation errors are rendered
  against the field, with the profile unchanged;
* the company page shows the stored values, the public-name disclosure state and
  an edit form;
* an edit writes exactly the declared columns and a failed edit re-renders with
  the error and the stored value intact;
* the employer's own text is escaped -- a company name containing a `<script>`
  tag is displayed, never executed;
* the page works without JavaScript; the form is a plain POST.

CSRF is enforced by Django on the session-authenticated POSTs. The default test
client turns that check off, so one test uses `enforce_csrf_checks=True`.
"""

from __future__ import annotations

import re

import pytest
from django.test import Client

from employers.models import EmployerProfile

pytestmark = pytest.mark.django_db

ONBOARDING_URL = "/employer/onboarding/"
COMPANY_URL = "/employer/company/"
EDIT_URL = "/employer/company/edit/"

PASSWORD = "Wanderlust7Quartz-Meadow"


@pytest.fixture
def employer(make_user):
    return make_user(
        "employer_hr",
        email="hr@example.com",
        password=PASSWORD,
        email_verified=True,
    )


@pytest.fixture
def profile(employer):
    return EmployerProfile.objects.create(
        user=employer,
        company_name="Acme Ltd",
        industry="Software",
        company_size=40,
        show_company_name=False,
    )


@pytest.fixture
def signed_in(employer):
    client = Client()
    client.force_login(employer)
    return client


def payload(**overrides) -> dict:
    body = {
        "company_name": "Acme Ltd",
        "industry": "Software",
        "company_size": "40",
        "show_company_name": "on",
    }
    body.update(overrides)
    return body


def unique_ids(html: str) -> list[str]:
    return re.findall(r'\bid="([^"]+)"', html)


def normalized(html: str) -> str:
    """Collapse HTML whitespace so a sentence split across source lines matches."""
    return re.sub(r"\s+", " ", html)


def assert_unique_ids(html: str) -> None:
    found = unique_ids(html)
    duplicates = sorted({value for value in found if found.count(value) > 1})
    assert duplicates == []


class TestAccess:
    def test_anonymous_is_sent_to_login_with_a_next(self):
        response = Client().get(ONBOARDING_URL)

        assert response.status_code == 302
        assert response.url == "/login/?next=/employer/onboarding/"

    def test_anonymous_post_is_sent_to_login(self):
        response = Client().post(ONBOARDING_URL, payload())

        assert response.status_code == 302
        assert response.url == "/login/?next=/employer/onboarding/"

    @pytest.mark.parametrize("role", ["candidate", "interviewer"])
    def test_a_non_employer_role_is_forbidden(self, make_user, role):
        user = make_user(role)
        client = Client()
        client.force_login(user)

        for response in (
            client.get(ONBOARDING_URL),
            client.get(COMPANY_URL),
            client.post(EDIT_URL, payload()),
        ):
            assert response.status_code == 403

        assert not EmployerProfile.objects.filter(user=user).exists()

    def test_a_platform_admin_without_the_employer_group_is_forbidden(self, make_user):
        admin = make_user(is_staff=True, is_superuser=True)
        client = Client()
        client.force_login(admin)

        assert client.get(ONBOARDING_URL).status_code == 403
        assert client.get(COMPANY_URL).status_code == 403
        assert client.post(EDIT_URL, payload()).status_code == 403
        assert not EmployerProfile.objects.filter(user=admin).exists()

    def test_an_employer_manager_can_use_the_portal(self, make_user):
        manager = make_user("employer_manager")
        client = Client()
        client.force_login(manager)

        response = client.get(ONBOARDING_URL)

        assert response.status_code == 200

    def test_a_deactivated_employer_is_sent_to_login(self, make_user):
        employer = make_user("employer_hr", is_active=False)
        client = Client()
        client.force_login(employer)

        response = client.get(ONBOARDING_URL)

        # Django's ModelBackend refuses an inactive account when it rebuilds
        # `request.user` from the session, so the page sees an anonymous request.
        assert response.status_code == 302
        assert response.url == "/login/?next=/employer/onboarding/"
        assert not EmployerProfile.objects.filter(user=employer).exists()


class TestOnboardingPage:
    def test_renders_the_documented_fields_with_labels(self, signed_in):
        response = signed_in.get(ONBOARDING_URL)
        body = response.content.decode()

        assert response.status_code == 200
        assert body.count("<h1") == 1
        assert "Set up your company" in body
        assert f'action="{ONBOARDING_URL}"' in body
        assert 'method="post"' in body
        assert 'name="company_name"' in body
        assert 'name="industry"' in body
        assert 'name="company_size"' in body
        assert 'name="show_company_name"' in body
        assert "Company name" in body
        assert "Industry" in body
        assert "Company size" in body
        assert "Show my company name on public job listings" in body
        assert "csrfmiddlewaretoken" in body
        assert_unique_ids(body)

    def test_company_size_is_a_number_input(self, signed_in):
        body = signed_in.get(ONBOARDING_URL).content.decode()

        assert re.search(r'<input[^>]*type="number"[^>]*name="company_size"', body)

    def test_the_toggle_is_off_by_default(self, signed_in):
        body = signed_in.get(ONBOARDING_URL).content.decode()

        assert not re.search(r'name="show_company_name"[^>]*checked', body)

    def test_the_toggle_is_explained_in_plain_language(self, signed_in):
        body = signed_in.get(ONBOARDING_URL).content.decode()

        assert "job seekers see the role but not your company name" in body
        assert "never affects how candidates are ranked" in body

    def test_the_page_offers_an_equal_weight_skip(self, signed_in):
        body = signed_in.get(ONBOARDING_URL).content.decode()

        assert "Skip for now" in body
        assert 'href="/"' in body

    def test_the_page_says_the_profile_is_not_public_until_saved(self, signed_in):
        body = normalized(signed_in.get(ONBOARDING_URL).content.decode())

        assert "not visible on the public job board" in body

    def test_an_employer_with_a_profile_is_sent_to_the_company_page(
        self, signed_in, profile
    ):
        response = signed_in.get(ONBOARDING_URL)

        assert response.status_code == 302
        assert response.url == COMPANY_URL

    def test_a_valid_post_creates_the_profile_and_redirects(self, signed_in, employer):
        response = signed_in.post(ONBOARDING_URL, payload(), follow=True)

        assert response.status_code == 200
        assert response.redirect_chain[-1][0] == COMPANY_URL
        profile = EmployerProfile.objects.get(user=employer)
        assert profile.company_name == "Acme Ltd"
        assert profile.industry == "Software"
        assert profile.company_size == 40
        assert profile.show_company_name is True
        assert "Your company profile is saved." in response.content.decode()

    def test_an_unchecked_toggle_stores_false(self, signed_in, employer):
        body = payload()
        body.pop("show_company_name")

        response = signed_in.post(ONBOARDING_URL, body)

        assert response.status_code == 302
        assert EmployerProfile.objects.get(user=employer).show_company_name is False

    def test_a_missing_company_name_shows_a_field_error_and_creates_nothing(
        self, signed_in, employer
    ):
        body = payload()
        body.pop("company_name")

        response = signed_in.post(ONBOARDING_URL, body)
        page = response.content.decode()

        assert response.status_code == 200
        assert "There is a problem with your company profile" in page
        assert 'href="#id_company_name"' in page
        assert not EmployerProfile.objects.filter(user=employer).exists()

    def test_an_industry_over_100_characters_shows_a_field_error(
        self, signed_in, employer
    ):
        response = signed_in.post(ONBOARDING_URL, payload(industry="x" * 101))
        page = response.content.decode()

        assert response.status_code == 200
        assert "at most 100" in page
        assert not EmployerProfile.objects.filter(user=employer).exists()

    def test_a_stale_post_updates_the_existing_profile(
        self, signed_in, employer, profile
    ):
        response = signed_in.post(ONBOARDING_URL, payload(company_name="Acme Global"))

        assert response.status_code == 302
        profile.refresh_from_db()
        assert profile.company_name == "Acme Global"

    def test_a_session_post_without_a_csrf_token_is_rejected(self, employer):
        client = Client(enforce_csrf_checks=True)
        client.force_login(employer)

        response = client.post(ONBOARDING_URL, payload())

        assert response.status_code == 403
        assert not EmployerProfile.objects.filter(user=employer).exists()


class TestCompanyPage:
    def test_an_employer_without_a_profile_is_sent_to_onboarding(self, signed_in):
        response = signed_in.get(COMPANY_URL)

        assert response.status_code == 302
        assert response.url == ONBOARDING_URL

    def test_renders_the_stored_values_and_the_disclosure_state(
        self, signed_in, profile
    ):
        response = signed_in.get(COMPANY_URL)
        body = response.content.decode()

        assert response.status_code == 200
        assert body.count("<h1") == 1
        assert "Your company profile" in body
        assert "Acme Ltd" in body
        assert "Software" in body
        assert "40" in body
        assert "Public company name" in body
        assert "Off." in body
        assert (
            "Public job listings show the role but not your company name."
            in normalized(body)
        )
        assert f'action="{EDIT_URL}"' in body
        assert_unique_ids(body)

    def test_the_disclosure_state_is_on_after_opt_in(self, signed_in, profile):
        profile.show_company_name = True
        profile.save(update_fields=["show_company_name"])

        body = signed_in.get(COMPANY_URL).content.decode()

        assert "On." in body
        assert "Your company name appears on public job listings." in normalized(body)

    def test_the_employers_text_is_escaped(self, signed_in, employer):
        EmployerProfile.objects.create(
            user=employer,
            company_name="<script>alert(1)</script>",
        )

        body = signed_in.get(COMPANY_URL).content.decode()

        assert "<script>alert(1)</script>" not in body
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body

    def test_a_valid_edit_updates_the_declared_fields(self, signed_in, profile):
        response = signed_in.post(
            EDIT_URL,
            payload(
                company_name="Acme Global",
                industry="Healthcare",
                company_size="250",
            ),
            follow=True,
        )

        assert response.status_code == 200
        assert response.redirect_chain[-1][0] == COMPANY_URL
        profile.refresh_from_db()
        assert profile.company_name == "Acme Global"
        assert profile.industry == "Healthcare"
        assert profile.company_size == 250
        assert profile.show_company_name is True
        assert "Your company profile is updated." in response.content.decode()

    def test_an_invalid_edit_keeps_the_stored_value_and_shows_the_error(
        self, signed_in, profile
    ):
        response = signed_in.post(
            EDIT_URL, payload(company_name="", industry="Healthcare")
        )
        page = response.content.decode()

        assert response.status_code == 200
        assert "There is a problem with your company profile" in page
        assert 'href="#id_company_name"' in page
        profile.refresh_from_db()
        assert profile.company_name == "Acme Ltd"
        assert profile.industry == "Software"

    def test_an_edit_cannot_write_billing_or_owner_columns(self, signed_in, profile):
        owner = profile.user
        body = payload()
        body.update(
            {
                "billing_plan": "enterprise",
                "billing_cycle": "yearly",
                "stripe_customer_id": "cus_attacker",
                "user": "00000000-0000-0000-0000-000000000000",
            }
        )

        response = signed_in.post(EDIT_URL, body)

        assert response.status_code == 302
        profile.refresh_from_db()
        assert profile.billing_plan == "free"
        assert profile.billing_cycle == "monthly"
        assert profile.stripe_customer_id == ""
        assert profile.user == owner

    def test_an_employer_without_a_profile_cannot_post_an_edit(
        self, signed_in, employer
    ):
        response = signed_in.post(EDIT_URL, payload())

        assert response.status_code == 302
        assert response.url == ONBOARDING_URL
        assert not EmployerProfile.objects.filter(user=employer).exists()

    def test_a_session_edit_without_a_csrf_token_is_rejected(self, employer, profile):
        client = Client(enforce_csrf_checks=True)
        client.force_login(employer)

        response = client.post(EDIT_URL, payload(company_name="Nope"))

        assert response.status_code == 403
        profile.refresh_from_db()
        assert profile.company_name == "Acme Ltd"
