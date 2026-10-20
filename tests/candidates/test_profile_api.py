"""Candidate profile API tests (REQ-FR-009, batch 1.15, Complete Doc §C.12).

What these tests pin down beyond the happy path:

* the target is the caller -- there is no id in the path or the body, so a
  second candidate's PATCH cannot reach the first candidate's row;
* the endpoint is candidate-only. An authenticated employer or platform admin
  gets 403, not an automatically created profile;
* the body is a whitelist. `user`, `skills`, `visibility_tier`, `is_promoted`,
  `match_scores` and an `id` in a PATCH change nothing;
* GET is a read. It returns 404 before onboarding rather than creating a row;
* PATCH is the documented create-or-update operation. §C.12 lists no POST, so
  the first PATCH by a candidate with no profile creates it.

`force_authenticate` is not used. The 401 and role cases run through the real JWT
path the frontend uses; a forced request would skip the authenticator's 401.
"""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from candidates.models import CandidateProfile

pytestmark = pytest.mark.django_db

URL = "/api/v1/candidates/me/"

EXPECTED_KEYS = {
    "title",
    "bio",
    "location",
    "remote_ok",
}


def api_client(user) -> APIClient:
    """A real JWT client for `user`; no forced authentication."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


def profile_payload(**overrides) -> dict:
    payload = {
        "title": "Backend developer",
        "bio": "Django and PostgreSQL.",
        "location": "Dhaka",
        "remote_ok": False,
    }
    payload.update(overrides)
    return payload


class TestRead:
    def test_anonymous_is_401(self):
        response = APIClient().get(URL)

        assert response.status_code == 401

    def test_get_without_a_profile_is_404_and_does_not_create_one(self, make_user):
        candidate = make_user("candidate")

        response = api_client(candidate).get(URL)

        assert response.status_code == 404
        assert not CandidateProfile.objects.filter(user=candidate).exists()

    def test_get_returns_the_callers_profile(self, make_user):
        candidate = make_user("candidate")
        CandidateProfile.objects.create(
            user=candidate,
            title="Backend developer",
            bio="Django and PostgreSQL.",
            location="Dhaka",
            remote_ok=False,
        )

        response = api_client(candidate).get(URL)

        assert response.status_code == 200
        assert set(response.data) == EXPECTED_KEYS
        assert response.data["title"] == "Backend developer"
        assert response.data["bio"] == "Django and PostgreSQL."
        assert response.data["location"] == "Dhaka"
        assert response.data["remote_ok"] is False

    def test_the_body_does_not_expose_the_user_or_discovery_columns(self, make_user):
        candidate = make_user("candidate")
        CandidateProfile.objects.create(user=candidate, title="Backend developer")

        body = api_client(candidate).get(URL).data

        for forbidden in (
            "user",
            "email",
            "skills",
            "journey_timeline",
            "match_scores",
            "visibility_tier",
            "is_promoted",
        ):
            assert forbidden not in body


class TestCreateAndUpdate:
    def test_the_first_patch_creates_the_profile_for_the_caller(self, make_user):
        candidate = make_user("candidate")

        response = api_client(candidate).patch(URL, profile_payload(), format="json")

        assert response.status_code == 200
        assert set(response.data) == EXPECTED_KEYS
        profile = CandidateProfile.objects.get(user=candidate)
        assert profile.title == "Backend developer"
        assert profile.bio == "Django and PostgreSQL."
        assert profile.location == "Dhaka"
        assert profile.remote_ok is False

    def test_a_non_empty_patch_creates_with_defaults_for_unsent_fields(self, make_user):
        candidate = make_user("candidate")

        response = api_client(candidate).patch(
            URL, {"title": "Only a title"}, format="json"
        )

        assert response.status_code == 200
        profile = CandidateProfile.objects.get(user=candidate)
        assert profile.title == "Only a title"
        assert profile.bio == ""
        assert profile.location == ""
        assert profile.remote_ok is True

    def test_an_empty_patch_without_a_profile_is_404_and_creates_nothing(
        self, make_user
    ):
        candidate = make_user("candidate")

        response = api_client(candidate).patch(URL, {}, format="json")

        assert response.status_code == 404
        assert not CandidateProfile.objects.filter(user=candidate).exists()

    def test_an_empty_patch_on_an_existing_profile_is_a_no_op(self, make_user):
        candidate = make_user("candidate")
        CandidateProfile.objects.create(user=candidate, title="Existing")

        response = api_client(candidate).patch(URL, {}, format="json")

        assert response.status_code == 200
        assert response.data["title"] == "Existing"
        assert CandidateProfile.objects.get(user=candidate).title == "Existing"

    def test_patch_updates_only_the_fields_that_were_sent(self, make_user):
        candidate = make_user("candidate")
        CandidateProfile.objects.create(
            user=candidate,
            title="Old title",
            bio="Old bio",
            location="Old location",
            remote_ok=False,
        )

        response = api_client(candidate).patch(
            URL, {"title": "New title"}, format="json"
        )

        assert response.status_code == 200
        profile = CandidateProfile.objects.get(user=candidate)
        assert profile.title == "New title"
        assert profile.bio == "Old bio"
        assert profile.location == "Old location"
        assert profile.remote_ok is False

    def test_patch_can_store_false_for_remote_ok(self, make_user):
        candidate = make_user("candidate")
        CandidateProfile.objects.create(user=candidate, remote_ok=True)

        response = api_client(candidate).patch(URL, {"remote_ok": False}, format="json")

        assert response.status_code == 200
        assert CandidateProfile.objects.get(user=candidate).remote_ok is False

    def test_blank_strings_are_allowed_because_the_model_uses_empty_not_null(
        self, make_user
    ):
        candidate = make_user("candidate")

        response = api_client(candidate).patch(
            URL, {"title": "", "bio": "", "location": ""}, format="json"
        )

        assert response.status_code == 200
        profile = CandidateProfile.objects.get(user=candidate)
        assert profile.title == ""
        assert profile.bio == ""
        assert profile.location == ""

    def test_the_header_boundary_is_200_characters(self, make_user):
        candidate = make_user("candidate")

        response = api_client(candidate).patch(URL, {"title": "x" * 200}, format="json")

        assert response.status_code == 200
        assert CandidateProfile.objects.get(user=candidate).title == "x" * 200

    def test_put_is_not_documented_and_is_rejected(self, make_user):
        candidate = make_user("candidate")
        CandidateProfile.objects.create(user=candidate)

        response = api_client(candidate).put(URL, profile_payload(), format="json")

        assert response.status_code == 405


class TestValidation:
    def test_a_title_over_200_characters_is_a_field_error(self, make_user):
        candidate = make_user("candidate")

        response = api_client(candidate).patch(URL, {"title": "x" * 201}, format="json")

        assert response.status_code == 400
        assert "title" in response.data
        assert not CandidateProfile.objects.filter(user=candidate).exists()

    def test_null_is_not_a_valid_title(self, make_user):
        candidate = make_user("candidate")

        response = api_client(candidate).patch(URL, {"title": None}, format="json")

        assert response.status_code == 400
        assert "title" in response.data

    def test_remote_ok_must_be_boolean(self, make_user):
        candidate = make_user("candidate")

        response = api_client(candidate).patch(
            URL, {"remote_ok": "not-a-boolean"}, format="json"
        )

        assert response.status_code == 400
        assert "remote_ok" in response.data


class TestWhitelist:
    def test_unknown_and_read_only_keys_change_nothing(self, make_user):
        candidate = make_user("candidate")
        other = make_user("candidate")
        profile = CandidateProfile.objects.create(
            user=candidate,
            title="Original",
            visibility_tier=CandidateProfile.VisibilityTier.STANDARD,
        )

        response = api_client(candidate).patch(
            URL,
            {
                "title": "Updated",
                "user": str(other.pk),
                "id": str(uuid.uuid4()),
                "skills": [{"name": "Python"}],
                "journey_timeline": [{"event": "joined"}],
                "match_scores": {"job": 99},
                "visibility_tier": CandidateProfile.VisibilityTier.VERIFIED,
                "is_promoted": True,
                "email": "attacker@example.com",
            },
            format="json",
        )

        assert response.status_code == 200
        profile.refresh_from_db()
        assert profile.title == "Updated"
        assert profile.user == candidate
        assert profile.skills == []
        assert profile.journey_timeline == []
        assert profile.match_scores == {}
        assert profile.visibility_tier == CandidateProfile.VisibilityTier.STANDARD
        assert profile.is_promoted is False


class TestOwnership:
    def test_two_candidates_read_and_write_only_their_own_rows(self, make_user):
        first = make_user("candidate")
        second = make_user("candidate")

        first_client = api_client(first)
        second_client = api_client(second)

        assert (
            first_client.patch(URL, {"title": "First"}, format="json").status_code
            == 200
        )
        assert (
            second_client.patch(URL, {"title": "Second"}, format="json").status_code
            == 200
        )

        assert CandidateProfile.objects.get(user=first).title == "First"
        assert CandidateProfile.objects.get(user=second).title == "Second"
        assert first_client.get(URL).data["title"] == "First"
        assert second_client.get(URL).data["title"] == "Second"

    def test_a_patch_cannot_address_another_candidate(self, make_user):
        first = make_user("candidate")
        second = make_user("candidate")
        CandidateProfile.objects.create(user=first, title="First")

        # The path has no id and the body's `user` is not declared, so this is
        # only ever an update of `second`.
        response = api_client(second).patch(
            URL, {"title": "Second", "user": str(first.pk)}, format="json"
        )

        assert response.status_code == 200
        assert CandidateProfile.objects.get(user=first).title == "First"
        assert CandidateProfile.objects.get(user=second).title == "Second"


class TestRoleGate:
    def test_an_employer_cannot_read_or_write(self, make_user):
        employer = make_user("employer_hr")
        client = api_client(employer)

        assert client.get(URL).status_code == 403
        assert client.patch(URL, {"title": "Nope"}, format="json").status_code == 403
        assert not CandidateProfile.objects.filter(user=employer).exists()

    def test_an_admin_without_the_candidate_group_cannot_read_or_write(self, make_user):
        admin = make_user(is_staff=True, is_superuser=True)
        client = api_client(admin)

        assert client.get(URL).status_code == 403
        assert client.patch(URL, {"title": "Nope"}, format="json").status_code == 403
        assert not CandidateProfile.objects.filter(user=admin).exists()

    def test_an_interviewer_cannot_read_or_write(self, make_user):
        interviewer = make_user("interviewer")
        client = api_client(interviewer)

        assert client.get(URL).status_code == 403
        assert client.patch(URL, {"title": "Nope"}, format="json").status_code == 403

    def test_anonymous_cannot_write(self):
        response = APIClient().patch(URL, {"title": "Nope"}, format="json")

        assert response.status_code == 401
