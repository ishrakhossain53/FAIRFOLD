"""The evidence-cited rationale contract (Arch Doc §7.5, REQ-FR-030, batch 2.28).

No Django and no database: the citation check is the highest-risk logic in the
product (RSK-002), and `ai/citation.py` is deliberately dependency-free so this
suite can run anywhere.

The adversarial cases are the point of the file. A validator that accepts a
paraphrase, a stitched-together quote or a stop word as "evidence" is worse than no
validator: it certifies the product's differentiating claim while the claim is
false.
"""

from __future__ import annotations

import json

import pytest

from ai.citation import (
    MIN_EVIDENCE_CHARS,
    CitationError,
    load_rationale,
    parse_rationale,
)

SOURCE = (
    "Backend developer with six years of experience.\n"
    "Built a Django REST API serving 120 req/s at scale.\n"
    "Led a migration from MySQL to PostgreSQL with zero downtime.\n"
    "Mentored two junior engineers on testing."
)

GOOD_CLAIM = {
    "claim": "Runs Django in production",
    "evidence": "Built a Django REST API serving 120 req/s at scale.",
    "skills": ["Django"],
}
SECOND_CLAIM = {
    "claim": "Has migrated a relational database",
    "evidence": "Led a migration from MySQL to PostgreSQL with zero downtime.",
    "skills": ["PostgreSQL", "MySQL"],
}


def payload(**overrides):
    """A valid payload, with one field replaced per test."""
    base = {
        "summary": "Strong backend match; both required skills are evidenced.",
        "claims": [dict(GOOD_CLAIM), dict(SECOND_CLAIM)],
        "missing_skills": [
            {"skill": "Kubernetes", "reason": "not mentioned in the resume"}
        ],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------- accepted


def test_a_supported_rationale_is_accepted():
    rationale = parse_rationale(payload(), source_text=SOURCE)

    assert len(rationale.claims) == 2
    assert rationale.claims[0].evidence == GOOD_CLAIM["evidence"]
    assert rationale.claims[0].skills == ("Django",)
    assert rationale.missing_skills[0].skill == "Kubernetes"


def test_evidence_may_be_json_text_rather_than_a_mapping():
    """The provider returns JSON; the caller should not have to parse it first."""
    rationale = parse_rationale(json.dumps(payload()), source_text=SOURCE)
    assert len(rationale.claims) == 2


def test_text_that_is_not_json_is_refused():
    with pytest.raises(CitationError) as error:
        parse_rationale("{not json", source_text=SOURCE)

    assert "not valid JSON" in str(error.value)


def test_evidence_differing_only_in_case_and_whitespace_is_accepted():
    """Re-wrapping and casing change between storage and reading; wording does not."""
    claim = {
        "claim": "Runs Django in production",
        "evidence": "built a django rest api serving\n120 req/s at scale.",
        "skills": ["Django"],
    }
    rationale = parse_rationale(payload(claims=[claim]), source_text=SOURCE)
    assert rationale.claims[0].evidence.startswith("built a django")


def test_a_whole_word_skill_inside_a_longer_word_is_not_a_contradiction():
    """ "Rust" is missing from a resume that says "trusted", and listing it as
    missing is correct. A naive substring check would reject the honest answer."""
    source = SOURCE + "\nTrusted with production database access."
    rationale = parse_rationale(payload(), source_text=source)
    assert rationale.missing_skills[0].skill == "Kubernetes"


def test_missing_skills_may_be_empty():
    rationale = parse_rationale(payload(missing_skills=[]), source_text=SOURCE)
    assert rationale.missing_skills == ()


# ---------------------------------------------- invented evidence is refused


def test_evidence_that_does_not_occur_in_the_text_is_rejected():
    """The core of batch 2.28: a plausible sentence nobody wrote."""
    claim = {
        "claim": "Deployed Kubernetes in production",
        "evidence": "Deployed Kubernetes clusters across three regions.",
        "skills": ["Kubernetes"],
    }
    with pytest.raises(CitationError) as error:
        parse_rationale(payload(claims=[claim]), source_text=SOURCE)

    assert "does not occur" in str(error.value)
    assert "Kubernetes" not in str(
        error.value
    ), "the error must not quote invented text"


def test_a_paraphrase_of_real_text_is_rejected():
    """ "120 req/s" -> "120 requests per second" is a fair summary and not a quote."""
    claim = {
        "claim": "Runs Django in production",
        "evidence": "Built a Django REST API handling 120 requests per second.",
        "skills": ["Django"],
    }
    with pytest.raises(CitationError):
        parse_rationale(payload(claims=[claim]), source_text=SOURCE)


def test_a_quote_stitched_from_two_places_is_rejected():
    claim = {
        "claim": "Runs Django and has migrated databases",
        "evidence": "Built a Django REST API with zero downtime.",
        "skills": ["Django", "PostgreSQL"],
    }
    with pytest.raises(CitationError):
        parse_rationale(payload(claims=[claim]), source_text=SOURCE)


def test_a_stop_word_is_not_evidence():
    """Without a floor, "the" is a substring of every resume and passes."""
    claim = {
        "claim": "Runs Django in production",
        "evidence": "the",
        "skills": ["Django"],
    }
    with pytest.raises(CitationError) as error:
        parse_rationale(payload(claims=[claim]), source_text=SOURCE)

    assert str(MIN_EVIDENCE_CHARS) in str(error.value)
    assert "shorter" in str(error.value)


def test_a_typographic_apostrophe_is_not_a_straight_one():
    """Verbatim means verbatim: a curly quote is a different character."""
    source = "Candidate\u2019s work on payments is evidenced by the ledger redesign."
    claim = {
        "claim": "Worked on payments",
        "evidence": "Candidate's work on payments is evidenced",
        "skills": ["Payments"],
    }
    with pytest.raises(CitationError):
        parse_rationale(payload(claims=[claim]), source_text=source)


def test_missing_skill_that_the_resume_evidences_is_rejected():
    """A fabricated gap is as damaging as a fabricated match: it hides real skill."""
    with pytest.raises(CitationError) as error:
        parse_rationale(
            payload(missing_skills=[{"skill": "Django", "reason": "not mentioned"}]),
            source_text=SOURCE,
        )

    assert "contains it" in str(error.value)


def test_a_skill_name_with_punctuation_is_matched_whole():
    source = SOURCE + "\nSome C++ and .NET exposure on internal tools."
    with pytest.raises(CitationError):
        parse_rationale(
            payload(missing_skills=[{"skill": "C++"}, {"skill": ".NET"}]),
            source_text=source,
        )


def test_an_empty_source_text_is_refused():
    """With nothing to check against, every citation is unverifiable, and
    accepting it would be the product asserting what it cannot evidence."""
    with pytest.raises(CitationError) as error:
        parse_rationale(payload(), source_text="   \n ")

    assert "sanitised resume text" in str(error.value)


# ------------------------------------------------------- structural failures


@pytest.mark.parametrize(
    "broken",
    [
        payload(claims=[]),
        payload(claims="a claim"),
        payload(summary=""),
        payload(extra_field="unexpected"),
        {"summary": "no claims key", "missing_skills": []},
        ["not", "a", "mapping"],
        payload(summary=42),
        payload(claims=[["not", "a", "mapping"]]),
        payload(claims=[dict(GOOD_CLAIM, skills=[""])]),
        payload(claims=[dict(GOOD_CLAIM, claim="")]),
        payload(claims=[dict(GOOD_CLAIM, evidence="")]),
        payload(claims=[dict(GOOD_CLAIM, evidence=42)]),
        payload(claims=[{"claim": "No evidence key", "skills": ["Django"]}]),
        payload(missing_skills="Kubernetes"),
        payload(missing_skills=[["not", "a", "mapping"]]),
        payload(missing_skills=[{"skill": ""}]),
        payload(missing_skills=[{"reason": "no skill key"}]),
        payload(missing_skills=[{"skill": "Kubernetes", "reason": 7}]),
        payload(missing_skills=[dict({"skill": "Kubernetes"}, note="extra")]),
    ],
)
def test_a_malformed_payload_is_rejected(broken):
    with pytest.raises(CitationError):
        parse_rationale(broken, source_text=SOURCE)


def test_a_claim_without_skills_is_rejected():
    with pytest.raises(CitationError):
        parse_rationale(
            payload(
                claims=[
                    {
                        "claim": "Something",
                        "evidence": GOOD_CLAIM["evidence"],
                        "skills": [],
                    }
                ]
            ),
            source_text=SOURCE,
        )


def test_an_unknown_claim_key_is_rejected():
    claim = dict(GOOD_CLAIM, confidence=0.92)
    with pytest.raises(CitationError) as error:
        parse_rationale(payload(claims=[claim]), source_text=SOURCE)

    assert "unknown keys" in str(error.value)


def test_every_problem_is_reported_at_once():
    """One re-prompt, not one per defect."""
    bad_claims = [
        dict(GOOD_CLAIM, evidence="Invented sentence about Kubernetes."),
        dict(SECOND_CLAIM, evidence="Another invented sentence entirely."),
    ]
    with pytest.raises(CitationError) as error:
        parse_rationale(payload(claims=bad_claims), source_text=SOURCE)

    assert len(error.value.problems) == 2


# ------------------------------------------------------------- read side


def test_a_stored_payload_round_trips():
    stored = parse_rationale(payload(), source_text=SOURCE).to_json()

    assert load_rationale(stored).to_dict() == payload()


@pytest.mark.parametrize("stored", ["", "not json", json.dumps({"summary": "x"})])
def test_a_stored_payload_that_is_not_a_rationale_is_refused(stored):
    with pytest.raises(CitationError):
        load_rationale(stored)


def test_the_text_rendering_names_claims_evidence_and_missing_skills():
    """This is what the bias pass scans and what the rationale hash covers, so it
    must contain the substance rather than a pointer to it."""
    rationale = parse_rationale(payload(), source_text=SOURCE)
    rendered = rationale.to_text()

    assert rationale.summary in rendered
    assert GOOD_CLAIM["claim"] in rendered
    assert GOOD_CLAIM["evidence"] in rendered
    assert "Kubernetes" in rendered
