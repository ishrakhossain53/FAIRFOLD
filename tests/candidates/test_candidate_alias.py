"""Per-employer candidate aliases (REQ-FR-054, D-4, batch 1.35).

The alias is the only identity an employer may see before shortlist
(REQ-FR-029), so these tests pin the properties the requirement names:

* stable for one employer across calls and across that employer's jobs;
* different for two employers, so the two lists cannot be joined;
* random, non-sequential and never derived from PII or the candidate UUID;
* created once under a concurrent first use, and retried on a collision;
* removed by the two cascades the DDL declares.

The whitelist helper is tested by exact keys, not by "the name is absent": a new
`CandidateProfile` column must not become employer-visible by default.
"""

from __future__ import annotations

import re

import pytest
from django.db import IntegrityError, transaction

import candidates.services as alias_service
from candidates.models import CandidateAlias, CandidateProfile
from candidates.services import (
    ALIAS_ALPHABET,
    ALIAS_LENGTH,
    ALIAS_PREFIX,
    AliasGenerationError,
    alias_for,
    candidate_for_employer,
)
from employers.models import EmployerProfile
from matching.models import Job

pytestmark = pytest.mark.django_db

ALIAS_RE = re.compile(
    rf"^{re.escape(ALIAS_PREFIX)}[{re.escape(ALIAS_ALPHABET)}]{{{ALIAS_LENGTH}}}$"
)


@pytest.fixture
def employer(make_user):
    return EmployerProfile.objects.create(
        user=make_user("employer_hr"),
        company_name="Acme Ltd",
    )


@pytest.fixture
def other_employer(make_user):
    return EmployerProfile.objects.create(
        user=make_user("employer_hr"),
        company_name="Beta Ltd",
    )


@pytest.fixture
def candidate(make_user):
    return CandidateProfile.objects.create(
        user=make_user(
            "candidate",
            email="distinctive-candidate@example.com",
            first_name="Zubaida",
            last_name="Rahman",
        ),
        title="Backend developer",
        location="Dhaka",
        skills=["Python"],
    )


@pytest.fixture
def other_candidate(make_user):
    return CandidateProfile.objects.create(user=make_user("candidate"))


# ------------------------------------------------------------ stability


def test_one_employer_gets_one_stable_alias(employer, candidate):
    first = alias_for(employer, candidate)
    second = alias_for(employer, candidate)

    assert first == second
    assert (
        CandidateAlias.objects.filter(employer=employer, candidate=candidate).count()
        == 1
    )


def test_the_alias_is_the_same_across_the_employers_jobs(employer, candidate):
    """REQ-FR-054: the label belongs to the pair, not to an application."""
    Job.objects.create(employer=employer, title="Backend Engineer")
    Job.objects.create(employer=employer, title="Data Engineer")

    assert alias_for(employer, candidate) == alias_for(employer, candidate)


def test_two_employers_get_different_aliases_for_the_same_candidate(
    employer, other_employer, candidate
):
    """Different organisations cannot link their lists through the label."""
    first = alias_for(employer, candidate)
    second = alias_for(other_employer, candidate)

    assert first != second
    assert CandidateAlias.objects.filter(candidate=candidate).count() == 2


# ------------------------------------------------------ randomness and PII


def test_aliases_are_random_labels_not_sequence_numbers(employer, make_user):
    aliases = []
    for _ in range(20):
        profile = CandidateProfile.objects.create(user=make_user("candidate"))
        aliases.append(alias_for(employer, profile))

    assert all(ALIAS_RE.match(alias) for alias in aliases)
    assert len(set(aliases)) == len(aliases)


def test_the_alias_is_not_derived_from_candidate_identity(employer, candidate):
    alias = alias_for(employer, candidate).upper()
    user = candidate.user

    fragments = {
        str(candidate.pk),
        str(user.pk),
        user.email.split("@")[0],
        user.first_name,
        user.last_name,
    }
    for fragment in fragments:
        # Empty names would make `in` trivially true; the fixture sets both.
        assert fragment
        assert fragment.upper() not in alias


def test_the_employer_summary_is_a_whitelist(employer, candidate):
    payload = candidate_for_employer(employer, candidate)

    assert payload == {
        "alias": alias_for(employer, candidate),
        "title": "Backend developer",
        "location": "Dhaka",
        "remote_ok": True,
        "skills": ["Python"],
    }
    # REQ-FR-053: paid discovery controls are not screening inputs and must not
    # appear on this surface, even though they are columns on the profile.
    assert "visibility_tier" not in payload
    assert "is_promoted" not in payload


def test_the_employer_summary_contains_no_name_email_or_internal_id(
    employer, candidate
):
    rendered = repr(candidate_for_employer(employer, candidate))
    user = candidate.user

    assert str(candidate.pk) not in rendered
    assert str(user.pk) not in rendered
    assert user.email not in rendered
    assert user.first_name not in rendered
    assert user.last_name not in rendered


# ---------------------------------------------------------- collision/race


def test_a_collision_retries_with_a_fresh_alias(
    employer, candidate, other_candidate, monkeypatch
):
    CandidateAlias.objects.create(
        employer=employer,
        candidate=other_candidate,
        alias="C-AAAAAA",
    )
    labels = iter(["C-AAAAAA", "C-BBBBBB"])
    monkeypatch.setattr(alias_service, "_new_alias", lambda: next(labels))

    assert alias_for(employer, candidate) == "C-BBBBBB"
    assert CandidateAlias.objects.filter(employer=employer).count() == 2


def test_an_existing_pair_never_generates_a_second_alias(
    employer, candidate, monkeypatch
):
    CandidateAlias.objects.create(
        employer=employer,
        candidate=candidate,
        alias="C-7H2X9",
    )
    monkeypatch.setattr(
        alias_service,
        "_new_alias",
        lambda: pytest.fail("an existing alias must not be regenerated"),
    )

    assert alias_for(employer, candidate) == "C-7H2X9"


def test_a_concurrent_first_use_returns_the_winners_alias(
    employer, candidate, monkeypatch
):
    """Simulate the losing side of the `UNIQUE(employer, candidate)` race.

    The winner's row exists before the call, but the first lookup is made to miss
    -- which is what the loser sees. Its insert then fails, and the retry must
    read the committed row instead of generating a second label.
    """
    CandidateAlias.objects.create(
        employer=employer,
        candidate=candidate,
        alias="C-RACE22",
    )
    real_lookup = alias_service._stored_alias
    calls = {"count": 0}

    def miss_once(employer_arg, candidate_arg):
        calls["count"] += 1
        if calls["count"] == 1:
            return None
        return real_lookup(employer_arg, candidate_arg)

    monkeypatch.setattr(alias_service, "_stored_alias", miss_once)

    assert alias_for(employer, candidate) == "C-RACE22"
    assert CandidateAlias.objects.count() == 1


def test_exhausted_collisions_raise_instead_of_duplicating(
    employer, candidate, other_candidate, monkeypatch
):
    CandidateAlias.objects.create(
        employer=employer,
        candidate=other_candidate,
        alias="C-AAAAAA",
    )
    monkeypatch.setattr(alias_service, "_new_alias", lambda: "C-AAAAAA")

    with pytest.raises(AliasGenerationError):
        alias_for(employer, candidate)

    assert CandidateAlias.objects.filter(employer=employer).count() == 1


# ------------------------------------------------------ database constraints


def test_the_database_refuses_a_second_row_for_the_same_pair(
    employer, candidate, other_candidate
):
    CandidateAlias.objects.create(
        employer=employer,
        candidate=candidate,
        alias="C-AAAAAA",
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CandidateAlias.objects.create(
                employer=employer,
                candidate=candidate,
                alias="C-BBBBBB",
            )


def test_the_database_refuses_one_alias_for_two_candidates(
    employer, candidate, other_candidate
):
    CandidateAlias.objects.create(
        employer=employer,
        candidate=candidate,
        alias="C-AAAAAA",
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CandidateAlias.objects.create(
                employer=employer,
                candidate=other_candidate,
                alias="C-AAAAAA",
            )


def test_two_employers_may_hold_the_same_label_independently(
    employer, other_employer, candidate, other_candidate
):
    """The DDL's uniqueness is per employer; a global constraint would invent one."""
    CandidateAlias.objects.create(
        employer=employer,
        candidate=candidate,
        alias="C-SAME22",
    )
    CandidateAlias.objects.create(
        employer=other_employer,
        candidate=other_candidate,
        alias="C-SAME22",
    )

    assert CandidateAlias.objects.count() == 2


# ---------------------------------------------------------------- cascades


def test_deleting_the_candidate_removes_the_alias(employer, candidate):
    alias_for(employer, candidate)

    candidate.delete()

    assert not CandidateAlias.objects.filter(candidate_id=candidate.pk).exists()


def test_deleting_the_employer_removes_the_alias(employer, candidate):
    alias_for(employer, candidate)

    employer.delete()

    assert not CandidateAlias.objects.filter(employer_id=employer.pk).exists()
