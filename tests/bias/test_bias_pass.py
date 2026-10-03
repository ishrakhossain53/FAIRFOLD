"""CI-gated tests for the deterministic bias pass against the versioned set.

Spec: ``FAIRFOLD_Project_Architecture_and_Requirements.md`` §7.4.

These assertions gate on the *deterministic keyword pass only*. The LLM bias
pass is advisory and is deliberately not asserted here: an advisory signal is
allowed to be wrong, and gating CI on it makes the suite flaky and invites
disabling it.

Read the results honestly. A pass that scores 100% recall on a set whose terms
were authored alongside it has demonstrated very little -- that is why the
false-positive assertions and the flag-rate band carry the weight here, and why
the negatives are 18 of the 76 cases.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai.bias_pass import ScanContext, load_rules, load_terms, normalise, scan

REPO_ROOT = Path(__file__).resolve().parents[2]
SET_DIR = REPO_ROOT / "tests" / "bias" / "v1.0.1"

MANIFEST = json.loads((SET_DIR / "manifest.json").read_text(encoding="utf-8"))
TERMS_DOC = json.loads((SET_DIR / "keyword_terms.json").read_text(encoding="utf-8"))

# Categories 1-8 and 11-12 are the proxy surface the pass exists to catch.
# Categories 9, 10 and 13 are must-not-flag and exist to stop the pass being
# trivially good.
FLAG_RATE_CATEGORIES = {
    "gendered_club_role",
    "institution_gender_signal",
    "age_reference",
    "nationality_origin_proxy",
    "family_status",
    "disability_health",
    "photo_appearance",
    "uncited_vague_rationale",
    "numeric_age",
    "graduation_year_proximity",
}


def _load_cases(filename: str) -> list[dict]:
    lines = (SET_DIR / filename).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


ALL_CASES = (
    _load_cases("proxy_cases.jsonl")
    + _load_cases("negative_cases.jsonl")
    + _load_cases("rationale_cases.jsonl")
)

MUST_FLAG = [c for c in ALL_CASES if c["must_flag"]]
MUST_NOT_FLAG = [c for c in ALL_CASES if not c["must_flag"]]


@pytest.fixture(scope="module")
def terms():
    return load_terms(SET_DIR)


@pytest.fixture(scope="module")
def rules():
    """The numeric rule layer, added in v1.0.1 to close LIM-001 and LIM-002."""
    return load_rules(SET_DIR)


@pytest.fixture(scope="module")
def context():
    return ScanContext()


@pytest.fixture(scope="module")
def results(terms, rules, context):
    return {case["id"]: scan(case["text"], terms, rules, context) for case in ALL_CASES}


# ------------------------------------------------------------------ the pass


def test_recall_is_total(results):
    """Every must-flag case is flagged.

    A proxy phrase that gets through is a silent ranking error. There is no
    acceptable miss rate for a phrase already known to be bad.
    """
    missed = [case["id"] for case in MUST_FLAG if not results[case["id"]].flagged]
    assert not missed, f"must-flag cases not flagged: {missed}"


def test_matched_by_expected_term_not_incidentally(results):
    """A case is flagged via its own declared term, not by an unrelated hit.

    Without this, a pass that flagged every line would satisfy recall while
    proving nothing -- and the expected_terms field would be decorative.
    """
    wrong = []
    for case in MUST_FLAG:
        if not case["expected_terms"]:
            continue
        found = set(results[case["id"]].phrases)
        declared = {normalise(t) for t in case["expected_terms"]}
        if not declared & {normalise(f) for f in found}:
            wrong.append(
                f"{case['id']}: expected one of {case['expected_terms']}, got {results[case['id']].phrases}"
            )
    assert not wrong, "; ".join(wrong)


def test_no_false_positives(results):
    """No must-not-flag case is flagged.

    Every false positive is an employer shown a rationale the product calls
    biased when it is not, and it trains recruiters to ignore the badge.
    """
    flagged = [case["id"] for case in MUST_NOT_FLAG if results[case["id"]].flagged]
    assert not flagged, f"false positives on must-not-flag cases: {flagged}"


def test_flag_rate_is_inside_the_band(results):
    """Overall flag rate stays in the band fixed by §7.4.5.

    The band is what catches both failure directions: a pass that flags
    everything fails the false-positive test above, but the band is what stops
    it being "fixed" by deleting the negatives. Under the floor means the term
    list is too thin; over the ceiling means it is flagging noise.

    Measured across ALL cases. Over the proxy categories alone it would be
    1.0 by construction, since 100% recall there is a separate requirement --
    the two numbers cannot both be asserted on the same denominator.
    """
    flagged = sum(1 for case in ALL_CASES if results[case["id"]].flagged)
    rate = flagged / len(ALL_CASES)
    low, high = MANIFEST["pass_criteria"]["flag_rate_band_categories_1_to_8"]
    assert low <= rate <= high, (
        f"overall flag rate {rate:.3f} outside [{low}, {high}] "
        f"({flagged}/{len(ALL_CASES)})"
    )


def test_every_category_1_to_8_case_carries_at_least_one_match(results):
    """Sanity floor independent of the band: the proxy categories all fire."""
    silent = [
        case["id"]
        for case in ALL_CASES
        if case["category"] in FLAG_RATE_CATEGORIES and not results[case["id"]].flagged
    ]
    assert not silent, f"silent proxy cases: {silent}"


# ------------------------------------------------------------- the term list


def test_no_bare_vague_adjectives_in_the_list(terms):
    """GAP-001 holds: the named vague/age-coded adjectives are not terms.

    This asserts the rule GAP-001 actually states -- no single-word *vague or
    age-coded adjective* -- and not the broader rule "no single-word terms".
    Those are different claims, and an earlier draft of this test asserted the
    broader one, which wrongly failed on ``married``, ``presentable`` and
    ``all-girls``. Those are specific marital-status and appearance tokens, not
    ordinary professional adjectives, so they belong.

    Enforced as a test rather than left to review, because the temptation to add
    ``energetic`` arrives every time someone reads a missed case.
    """
    banned = {
        "energetic",
        "articulate",
        "mature",
        "ambitious",
        "young",
        "dynamic",
        "passive",
        "confident",
        "enthusiastic",
        "driven",
        "outgoing",
    }
    present = sorted({t.phrase.lower() for t in terms} & banned)
    assert not present, (
        f"bare vague adjectives in the term list: {present}. See GAP-001 in "
        f"keyword_terms.json -- these flag ordinary professional text."
    )


def test_single_word_terms_are_narrow_tokens_not_adjectives(terms):
    """Whatever single-word terms exist must be specific tokens.

    A single-word term matches inside longer words, so it earns its place only
    by naming something concrete. This keeps the set from drifting toward
    one-word adjectives over time without pretending they are all banned.
    """
    single = sorted(t.phrase for t in terms if " " not in t.phrase)
    assert len(single) <= 8, (
        f"single-word terms have grown to {single}. Each one matches inside "
        f"longer words, so every addition needs a negative case proving it does "
        f"not fire on ordinary text."
    )


def test_deliberately_excluded_terms_are_absent(terms):
    """The six exclusions are absent, each naming a case that enforces it."""
    present = {normalise(t.phrase) for t in terms}
    still_here = [
        entry["term"]
        for entry in TERMS_DOC["deliberately_excluded"]
        if normalise(entry["term"]) in present
    ]
    assert not still_here, f"excluded terms reintroduced: {still_here}"


def test_excluded_terms_are_all_enforced_by_a_negative_case():
    """Every exclusion names a real negative case, so none can be deleted alone."""
    negative_ids = {case["id"] for case in MUST_NOT_FLAG}
    dangling = [
        entry["term"]
        for entry in TERMS_DOC["deliberately_excluded"]
        if entry["caught_by"] not in negative_ids
    ]
    assert not dangling, f"exclusions with no enforcing case: {dangling}"


def test_manifest_results_are_current(results):
    """The manifest's measured figures must still match a live run.

    This test replaced an earlier guard that asserted ``measured is False`` --
    written to make an overclaim impossible to commit silently. It earned its
    keep: when the pass was implemented the guard failed by design, forcing the
    flip to be a deliberate replacement rather than a quiet deletion. The
    manifest's numbers are therefore never older than the last run.

    Read ``measured.caveat`` before quoting anything here. Recall of 1.0 on a
    set whose terms were authored alongside it is close to tautological; the
    figures that carry real information are the zero false positives and the
    flag rate being inside the band.
    """
    measured = MANIFEST["measured"]
    assert measured is not False, "manifest reverted to unmeasured"
    flagged = sum(1 for case in ALL_CASES if results[case["id"]].flagged)
    assert (
        measured["flagged"] == flagged
    ), f"manifest says {measured['flagged']} flagged, live run says {flagged}"
    assert measured["cases"] == len(ALL_CASES)
    assert measured["caveat"], "a measured result must carry its caveat"
    assert measured["false_positives"] == sum(
        1 for case in MUST_NOT_FLAG if results[case["id"]].flagged
    )


def test_manifest_cases_match_the_files():
    assert MANIFEST["case_count"] == len(ALL_CASES)
    assert MANIFEST["must_flag_count"] == len(MUST_FLAG)
    assert MANIFEST["must_not_flag_count"] == len(MUST_NOT_FLAG)


def test_missing_term_list_fails_loudly():
    """A pass with no terms must RAISE, not return an empty list.

    This is the worst failure mode the pass has: with no terms it flags nothing,
    every case looks clean, and the output is indistinguishable from a pass
    finding no bias. It looks exactly like success.

    Added after negative-testing the implementation -- swapping this raise for
    ``return []`` passed the whole suite, because every other test supplies an
    explicit set directory and never exercises the missing-file branch.
    """
    with pytest.raises(FileNotFoundError):
        load_terms(Path("/nonexistent-set-directory"))


def test_no_versioned_set_fails_loudly(monkeypatch):
    """Same reasoning for the default path when no versioned set exists."""
    import ai.bias_pass as bias_pass

    monkeypatch.setattr(bias_pass, "SET_ROOT", Path("/nonexistent-set-root"))
    with pytest.raises(FileNotFoundError):
        bias_pass.load_terms()


def test_empty_case_set_does_not_produce_a_clean_result(terms):
    """Guards the degenerate input the branch above protects against.

    Scanning nothing yields nothing flagged. Any caller that treats "no cases"
    as "no bias found" is wrong, so this documents the value rather than
    asserting behaviour -- the assertion is the raise above.
    """
    assert scan("", terms).phrases == []
    assert not scan("", terms).flagged


# ------------------------------------------------------------ normalisation


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("President, University Women’s Society", True),  # U+2019
        ("President, University Womenʼs Society", True),  # U+02BC
        ("President, University Women's Society", True),  # ASCII
        ("PRESIDENT, UNIVERSITY WOMEN'S SOCIETY", True),  # case
    ],
)
def test_apostrophe_and_case_variants_all_match(terms, raw, expected):
    """A candidate cannot be cleared by their word processor's apostrophe.

    If any of these variants failed to match, the pass would report clean on
    exactly the phrasing it was written to catch, and the failure would look
    like a pass result.
    """
    assert scan(raw, terms).flagged is expected


# ------------------------------------------------- the numeric rules (v1.0.1)


def test_every_rule_reports_as_checked_even_when_silent(results):
    """The panel shows what was CHECKED, so an unfired rule must still appear.

    Without this, a reader cannot distinguish "rule ran and found nothing" from
    "rule did not run" -- and the second is indistinguishable from a pass.
    """
    silent = results["NEG-001"]
    assert silent.rules_checked, "a clean scan must still report the rules it ran"
    assert "graduation_year" in silent.rules_checked
    assert "explicit_age_years" in silent.rules_checked


def test_stated_age_is_caught_in_every_common_form(terms, rules, context):
    """LIM-001. An age can be written at least four ways and all are proxies."""
    for text in (
        "24 years old",
        "Age: 31",
        "Aged 22",
        "DOB: 12/03/1998",
        "Born on 1999-06-14",
        "Date of birth 4 July 1995",
    ):
        assert scan(text, terms, rules, context).flagged, f"not caught: {text!r}"


def test_graduation_recency_is_parameterised_not_hardcoded(terms, rules):
    """LIM-002. The window is a parameter, so 'recent' cannot silently mean 2026.

    A rule hard-coding the current year would need editing every January, and
    one omission would make last year's cohort stop flagging with nothing in
    the changelog. So the year travels in ScanContext and is asserted here.
    """
    text = "Graduated in 2020."
    assert not scan(text, terms, rules, ScanContext(reference_year=2026)).flagged
    assert scan(
        text, terms, rules, ScanContext(reference_year=2026, graduation_window_years=10)
    ).flagged


def test_graduation_year_needs_an_education_keyword(terms, rules, context):
    """A bare four-digit year is a phone number or a budget, not a signal.

    Without the keyword requirement this rule would fire on every CV, and a
    pass that flags everything reports clean by flagging everything.
    """
    assert not scan(
        "Budget approved: 2026 for the platform team.", terms, rules, context
    ).flagged
    assert not scan(
        "Call +880 1711 2026 for the recruiter.", terms, rules, context
    ).flagged
    assert scan("Graduated in 2026.", terms, rules, context).flagged


def test_a_year_outside_the_window_never_flags(terms, rules, context):
    """NUMF-009. Every resume has a graduation year, so an unbounded rule is useless."""
    assert not scan(
        "Graduated in 1994 from a public university.", terms, rules, context
    ).flagged


def test_ordinary_numbers_are_not_ages(terms, rules, context):
    """The 10 numeric near-misses, as a single assertion over the worst shapes.

    These are the cases a loosened rule would break first: a bare two-digit
    number after 'team of', three-digit throughput, and durations.
    """
    for text in (
        "Managed a team of 12 junior engineers over three quarters.",
        "Sustained 120 req/s at p95 180 ms across six replicas.",
        "Ran a 1,000-concurrent applicant load test; 99.9 percent success.",
        "Owned the on-call rotation for 18 months; cut P1 incidents by 40 percent.",
    ):
        assert not scan(
            text, terms, rules, context
        ).flagged, f"false positive: {text!r}"


def test_rule_matches_carry_their_captured_value(terms, rules, context):
    """The audit trail must quote what fired, not just which rule.

    A flag reading 'graduation_year' with no year attached is not evidence, and
    evidence is the whole product claim.
    """
    result = scan("Graduated in 2026.", terms, rules, context)
    assert "2026" in " ".join(result.highlights)
