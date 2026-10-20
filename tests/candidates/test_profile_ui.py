"""Candidate onboarding and profile UI tests (REQ-FR-009, pages #14/#16).

These sit on top of the API tests (`test_profile_api.py`). They assert what the
server-rendered pages add:

* anonymous users are sent to login with a `next` back to the page; an
  authenticated employer, interviewer or admin gets 403, not a profile created
  for them;
* onboarding creates the four REQ-FR-009 columns and validation errors are
  rendered against the field, with the profile unchanged;
* the profile page shows the stored values, a progressbar with its percentage as
  text, and one inline form per section;
* an inline edit writes exactly one column, an unknown section is a 400, and a
  failed edit re-renders with the section open and the stored value intact;
* the candidate's own text is escaped -- a bio containing a `<script>` tag is
  displayed, never executed;
* the page works without JavaScript; `<details>` is the edit disclosure.

CSRF is enforced by Django on the session-authenticated POSTs. The default test
client turns that check off, so one test uses `enforce_csrf_checks=True`.
"""

from __future__ import annotations

import re

import pytest
from django.test import Client

from candidates.models import CandidateProfile

pytestmark = pytest.mark.django_db

ONBOARDING_URL = "/candidate/onboarding/"
PROFILE_URL = "/candidate/profile/"
EDIT_URL = "/candidate/profile/edit/"

PASSWORD = "Wanderlust7Quartz-Meadow"


@pytest.fixture
def candidate(make_user):
    return make_user(
        "candidate",
        email="ada@example.com",
        password=PASSWORD,
        email_verified=True,
    )


@pytest.fixture
def profile(candidate):
    return CandidateProfile.objects.create(
        user=candidate,
        title="Backend developer",
        bio="Django and PostgreSQL.",
        location="Dhaka",
        remote_ok=False,
    )


@pytest.fixture
def signed_in(candidate):
    client = Client()
    client.force_login(candidate)
    return client


def payload(**overrides) -> dict:
    body = {
        "title": "Backend developer",
        "bio": "Django and PostgreSQL.",
        "location": "Dhaka",
        "remote_ok": "on",
    }
    body.update(overrides)
    return body


def unique_ids(html: str) -> list[str]:
    return re.findall(r'\bid="([^"]+)"', html)


def assert_unique_ids(html: str) -> None:
    found = unique_ids(html)
    duplicates = sorted({value for value in found if found.count(value) > 1})
    assert duplicates == []


class TestAccess:
    def test_anonymous_is_sent_to_login_with_a_next(self):
        response = Client().get(ONBOARDING_URL)

        assert response.status_code == 302
        assert response.url == "/login/?next=/candidate/onboarding/"

    def test_anonymous_post_is_sent_to_login(self):
        response = Client().post(EDIT_URL, {"section": "title", "title": "Nope"})

        assert response.status_code == 302
        assert response.url.startswith("/login/?next=")

    @pytest.mark.parametrize(
        "role",
        ["employer_hr", "interviewer"],
    )
    def test_a_non_candidate_role_is_forbidden(self, make_user, role):
        user = make_user(role)
        client = Client()
        client.force_login(user)

        for response in (
            client.get(ONBOARDING_URL),
            client.get(PROFILE_URL),
            client.post(EDIT_URL, {"section": "title", "title": "Nope"}),
        ):
            assert response.status_code == 403

        assert not CandidateProfile.objects.filter(user=user).exists()

    def test_a_platform_admin_without_the_candidate_group_is_forbidden(self, make_user):
        admin = make_user(is_staff=True, is_superuser=True)
        client = Client()
        client.force_login(admin)

        assert client.get(ONBOARDING_URL).status_code == 403
        assert client.get(PROFILE_URL).status_code == 403
        assert (
            client.post(EDIT_URL, {"section": "title", "title": "Nope"}).status_code
            == 403
        )
        assert not CandidateProfile.objects.filter(user=admin).exists()

    def test_a_deactivated_candidate_is_sent_to_login(self, make_user):
        candidate = make_user("candidate", is_active=False)
        client = Client()
        client.force_login(candidate)

        response = client.get(ONBOARDING_URL)

        # Django's ModelBackend refuses an inactive account when it rebuilds
        # `request.user` from the session, so the page sees an anonymous request.
        assert response.status_code == 302
        assert response.url == "/login/?next=/candidate/onboarding/"
        assert not CandidateProfile.objects.filter(user=candidate).exists()


class TestOnboardingPage:
    def test_renders_the_four_fields_with_labels(self, signed_in):
        response = signed_in.get(ONBOARDING_URL)
        body = response.content.decode()

        assert response.status_code == 200
        assert body.count("<h1") == 1
        assert "Complete your profile" in body
        assert f'action="{ONBOARDING_URL}"' in body
        assert 'method="post"' in body
        assert 'name="title"' in body
        assert 'name="bio"' in body
        assert 'name="location"' in body
        assert 'name="remote_ok"' in body
        assert "Headline" in body
        assert "About" in body
        assert "Open to remote work" in body
        assert "csrfmiddlewaretoken" in body
        assert_unique_ids(body)

    def test_remote_work_is_checked_by_default(self, signed_in):
        body = signed_in.get(ONBOARDING_URL).content.decode()

        assert re.search(r'name="remote_ok"[^>]*checked', body)

    def test_a_candidate_with_a_profile_is_sent_to_the_profile(
        self, signed_in, profile
    ):
        response = signed_in.get(ONBOARDING_URL)

        assert response.status_code == 302
        assert response.url == PROFILE_URL

    def test_a_valid_post_creates_the_profile_and_redirects(self, signed_in, candidate):
        response = signed_in.post(ONBOARDING_URL, payload(), follow=True)

        assert response.status_code == 200
        assert response.redirect_chain[-1][0] == PROFILE_URL
        profile = CandidateProfile.objects.get(user=candidate)
        assert profile.title == "Backend developer"
        assert profile.bio == "Django and PostgreSQL."
        assert profile.location == "Dhaka"
        assert profile.remote_ok is True
        assert "Your profile is saved." in response.content.decode()

    def test_an_unchecked_remote_box_stores_false(self, signed_in, candidate):
        body = payload()
        body.pop("remote_ok")

        response = signed_in.post(ONBOARDING_URL, body)

        assert response.status_code == 302
        assert CandidateProfile.objects.get(user=candidate).remote_ok is False

    def test_a_title_over_200_characters_shows_a_field_error_and_creates_nothing(
        self, signed_in, candidate
    ):
        response = signed_in.post(ONBOARDING_URL, payload(title="x" * 201))
        body = response.content.decode()

        assert response.status_code == 200
        assert "There is a problem with your profile" in body
        assert "at most 200" in body
        assert 'href="#id_title"' in body
        assert not CandidateProfile.objects.filter(user=candidate).exists()

    def test_a_stale_post_updates_the_existing_profile(
        self, signed_in, candidate, profile
    ):
        response = signed_in.post(ONBOARDING_URL, payload(title="Staff engineer"))

        assert response.status_code == 302
        profile.refresh_from_db()
        assert profile.title == "Staff engineer"


class TestProfilePage:
    def test_a_candidate_without_a_profile_is_sent_to_onboarding(self, signed_in):
        response = signed_in.get(PROFILE_URL)

        assert response.status_code == 302
        assert response.url == ONBOARDING_URL

    def test_renders_the_stored_values_and_the_edit_controls(self, signed_in, profile):
        response = signed_in.get(PROFILE_URL)
        body = response.content.decode()

        assert response.status_code == 200
        assert body.count("<h1") == 1
        assert "Profile" in body
        assert "Backend developer" in body
        assert "Django and PostgreSQL." in body
        assert "Dhaka" in body
        assert "Edit headline" in body
        assert "Edit bio" in body
        assert "Edit location" in body
        assert "Edit remote preference" in body
        assert_unique_ids(body)

    def test_the_completeness_bar_has_the_percentage_as_text(self, signed_in, profile):
        body = signed_in.get(PROFILE_URL).content.decode()

        assert 'role="progressbar"' in body
        assert 'aria-valuenow="100"' in body
        assert "Profile completeness" in body
        assert "100%" in body

    def test_an_empty_profile_reports_the_starting_completeness(
        self, signed_in, candidate
    ):
        CandidateProfile.objects.create(user=candidate)

        body = signed_in.get(PROFILE_URL).content.decode()

        assert 'aria-valuenow="25"' in body
        assert "25%" in body
        assert "Not provided" in body

    def test_the_candidates_text_is_escaped(self, signed_in, candidate):
        CandidateProfile.objects.create(
            user=candidate,
            bio="<script>alert(1)</script>",
        )

        body = signed_in.get(PROFILE_URL).content.decode()

        assert "<script>alert(1)</script>" not in body
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body


class TestInlineEdit:
    def test_updates_exactly_one_section(self, signed_in, profile):
        response = signed_in.post(
            EDIT_URL,
            {"section": "title", "title": "Staff engineer"},
            follow=True,
        )

        assert response.status_code == 200
        profile.refresh_from_db()
        assert profile.title == "Staff engineer"
        assert profile.bio == "Django and PostgreSQL."
        assert profile.location == "Dhaka"
        assert profile.remote_ok is False
        assert "Headline updated." in response.content.decode()

    def test_can_turn_remote_work_off(self, signed_in, candidate):
        CandidateProfile.objects.create(user=candidate, remote_ok=True)

        response = signed_in.post(EDIT_URL, {"section": "remote_ok"})

        assert response.status_code == 302
        assert CandidateProfile.objects.get(user=candidate).remote_ok is False

    def test_an_invalid_title_keeps_the_stored_value_and_opens_the_section(
        self, signed_in, profile
    ):
        response = signed_in.post(EDIT_URL, {"section": "title", "title": "x" * 201})
        body = response.content.decode()

        assert response.status_code == 200
        assert "at most 200" in body
        assert re.search(r'<details id="title-edit"[\s\S]{0,200}?\bopen\b', body)
        profile.refresh_from_db()
        assert profile.title == "Backend developer"

    def test_an_unknown_section_is_a_400(self, signed_in, profile):
        response = signed_in.post(EDIT_URL, {"section": "skills", "skills": "Python"})

        assert response.status_code == 400
        profile.refresh_from_db()
        assert profile.title == "Backend developer"

    def test_a_missing_section_is_a_400(self, signed_in, profile):
        response = signed_in.post(EDIT_URL, {"title": "Nope"})

        assert response.status_code == 400

    def test_a_candidate_without_a_profile_is_sent_to_onboarding(self, signed_in):
        response = signed_in.post(EDIT_URL, {"section": "title", "title": "Nope"})

        assert response.status_code == 302
        assert response.url == ONBOARDING_URL

    def test_one_candidate_cannot_edit_another_candidates_profile(
        self, make_user, profile
    ):
        other = make_user("candidate", email="other@example.com")
        other_client = Client()
        other_client.force_login(other)

        response = other_client.post(
            EDIT_URL, {"section": "title", "title": "Hijacked"}
        )

        assert response.status_code == 302
        assert response.url == ONBOARDING_URL
        profile.refresh_from_db()
        assert profile.title == "Backend developer"
        assert not CandidateProfile.objects.filter(user=other).exists()

    def test_a_session_post_without_a_csrf_token_is_rejected(self, candidate, profile):
        client = Client(enforce_csrf_checks=True)
        client.force_login(candidate)

        response = client.post(EDIT_URL, {"section": "title", "title": "Nope"})

        assert response.status_code == 403
