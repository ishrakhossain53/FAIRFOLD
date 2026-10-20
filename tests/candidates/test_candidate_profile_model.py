"""Model tests for `CandidateProfile` (REQ-FR-009, batch 1.14).

The DDL is the specification, so these tests assert the parts that are easy to
get wrong when transcribing it: the one-to-one owner, the defaults of the JSON
columns, the cascade direction, and the width of `title`. They do not snapshot
the whole field list -- `makemigrations --check` already proves the model and the
migration agree, and a field-list assertion would turn every future column into
a test edit without testing anything.
"""

from __future__ import annotations

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from accounts.models import User
from candidates.models import CandidateProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def candidate():
    return User.objects.create_user("candidate@example.com", "not-used-in-these-tests")


@pytest.fixture
def profile(candidate):
    return CandidateProfile.objects.create(
        user=candidate,
        title="Senior Software Engineer",
        bio="Backend engineer.",
        location="Dhaka",
        remote_ok=False,
    )


def test_a_profile_belongs_to_one_user_and_is_reachable_from_them(profile, candidate):
    assert profile.user == candidate
    assert candidate.candidate_profile == profile


def test_a_user_cannot_have_two_profiles(candidate):
    CandidateProfile.objects.create(user=candidate)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CandidateProfile.objects.create(user=candidate)


def test_a_profile_cannot_exist_without_a_user():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CandidateProfile.objects.create()


def test_defaults_match_the_ddl(candidate):
    profile = CandidateProfile.objects.create(user=candidate)

    assert profile.title == ""
    assert profile.bio == ""
    assert profile.location == ""
    assert profile.remote_ok is True
    assert profile.skills == []
    assert profile.journey_timeline == []
    assert profile.match_scores == {}
    assert profile.visibility_tier == CandidateProfile.VisibilityTier.STANDARD
    assert profile.is_promoted is False


def test_json_defaults_are_per_row_not_shared(candidate):
    first = CandidateProfile.objects.create(user=candidate)
    second = CandidateProfile.objects.create(
        user=User.objects.create_user("other@example.com", "not-used")
    )

    first.skills.append({"name": "Python", "level": "expert"})
    first.match_scores["job-id"] = 87
    first.save()

    first.refresh_from_db()
    second.refresh_from_db()

    assert first.skills == [{"name": "Python", "level": "expert"}]
    assert first.match_scores == {"job-id": 87}
    assert second.skills == []
    assert second.match_scores == {}


def test_deleting_the_user_deletes_the_profile(profile, candidate):
    profile_id = profile.pk

    candidate.delete()

    assert not CandidateProfile.objects.filter(pk=profile_id).exists()


def test_deleting_the_profile_keeps_the_user(profile, candidate):
    candidate_id = candidate.pk

    profile.delete()

    assert User.objects.filter(pk=candidate_id).exists()


def test_title_accepts_the_ddl_width_and_rejects_one_more_character(profile):
    profile.title = "x" * 200
    profile.full_clean()

    profile.title = "x" * 201
    with pytest.raises(ValidationError):
        profile.full_clean()


def test_visibility_tier_has_the_three_documented_values():
    assert [value for value, _ in CandidateProfile.VisibilityTier.choices] == [
        "standard",
        "promoted",
        "verified",
    ]


def test_str_never_renders_the_candidate_email(candidate):
    profile = CandidateProfile.objects.create(user=candidate)

    assert profile.title == ""
    assert str(profile) == f"Candidate profile {profile.pk}"
    assert candidate.email not in str(profile)

    profile.title = "Staff Engineer"
    assert str(profile) == "Staff Engineer"


def test_roles_are_not_a_column_on_the_profile(profile):
    """D-2: roles are groups. A `role` column here would be a second source of truth."""
    field_names = {field.name for field in CandidateProfile._meta.get_fields()}

    assert "role" not in field_names
    assert "user" in field_names


def test_the_owner_key_is_a_uuid_and_the_table_matches_the_ddl(profile):
    assert isinstance(profile.user_id, uuid.UUID)
    assert CandidateProfile._meta.db_table == "candidate_profiles"
