"""Tests for the rationale-path bias audit and the audit-trail payload it builds.

No Django, no database. That is the point: the audit trail's *shape* is provable
before Phase 1 exists, and Complete Doc C.8.1 rules that no ``RunPython`` may call
an external service -- so this suite deliberately asserts on the payload a caller
would persist rather than touching a model.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai.bias_audit import (
    ACTION_REVIEWED,
    ACTION_SCREENED,
    AUDIT_RESOURCE_TYPE,
    RESULT_FLAG,
    RESULT_PASS,
    audit_payload,
    audit_rationale,
    review_payload,
)

SET_DIR = Path(__file__).resolve().parents[2] / "tests" / "bias" / "v1.0.1"

CLEAN_RATIONALE = (
    "Strong match. The resume evidences Django and PostgreSQL in production, "
    "which covers 2 of the 3 required skills. Missing: Kubernetes. "
    "Evidence: 'built a Django REST API serving 120 req/s'."
)
FLAGGED_RATIONALE = (
    "Good cultural fit for the team. The candidate is young and dynamic, "
    "though the resume does not evidence Kubernetes."
)

RESOURCE_ID = "6f1c2b4e-0000-4000-8000-000000000001"


@pytest.fixture(scope="module")
def clean_audit():
    return audit_rationale(CLEAN_RATIONALE, set_dir=SET_DIR)


@pytest.fixture(scope="module")
def flagged_audit():
    return audit_rationale(FLAGGED_RATIONALE, set_dir=SET_DIR)


# ------------------------------------------------------------- the verdict

def test_clean_rationale_passes(clean_audit):
    assert not clean_audit.flagged
    assert clean_audit.outcome == RESULT_PASS


def test_flagged_rationale_flags(flagged_audit):
    assert flagged_audit.flagged
    assert flagged_audit.outcome == RESULT_FLAG


def test_a_flag_is_not_a_veto(flagged_audit):
    """The pass never blocks the employer.

    ``design.md`` 7.7 holds a flagged candidate out of *bulk* shortlist until a human
    reviews. It never prevents an individual decision -- ``REQ-FR-052`` is explicit
    that overrides are not blocked. A bias audit that vetoes a recruiter is an
    unappealable automated rejection, which is the failure this product exists to
    avoid, and it would be introduced by a well-meaning "let's just block on flag".
    """
    assert flagged_audit.blocks_bulk_shortlist is True
    # and the payload exposes it as a queue constraint, not a decision
    payload = audit_payload(flagged_audit, resource_id=RESOURCE_ID)
    assert payload["details"]["blocks_bulk_shortlist"] is True
    assert payload["result"] == RESULT_FLAG  # an observation, not an action taken


# --------------------------------------------------- the "what was checked"

def test_checked_lists_every_rule_not_only_the_firing_ones(clean_audit, flagged_audit):
    """A silent rule must still be reported as having run.

    Otherwise "checked and found nothing" and "never checked" look identical, and
    the second is indistinguishable from a clean result -- which is exactly the
    failure mode ``load_terms`` refuses to allow by returning an empty list.
    """
    for audit in (clean_audit, flagged_audit):
        assert audit.checked, "a clean scan must still report what it checked"
        assert "graduation_year" in audit.checked
        assert "explicit_age_years" in audit.checked


def test_a_missing_rule_set_fails_loudly_rather_than_passing(tmp_path):
    """An audit that silently finds nothing would write a ``pass`` row to a
    retained audit trail. That is worse than an exception."""
    with pytest.raises(FileNotFoundError):
        audit_rationale(CLEAN_RATIONALE, set_dir=tmp_path)


# ------------------------------------------------------- the audit payload

def test_payload_maps_to_real_columns(clean_audit):
    """Every key must correspond to a column in Arch Doc 5.1.

    Asserted against the DDL's own column names, so a schema rename breaks this
    test rather than producing a payload the ORM rejects at runtime.
    """
    payload = audit_payload(clean_audit, resource_id=RESOURCE_ID)
    repo = Path(__file__).resolve().parents[2]
    arch = (repo / "FAIRFOLD_Project_Architecture_and_Requirements.md").read_text(encoding="utf-8")
    ddl = arch[arch.index("CREATE TABLE audit_log_entries"):]
    ddl = ddl[: ddl.index(");")]

    for column in ("action", "resource_type", "resource_id", "details", "result"):
        assert re_search(column, ddl), f"no column {column!r} in the DDL"
        assert column in payload, f"payload has no {column!r}"


def re_search(name: str, haystack: str) -> bool:
    import re

    return re.search(rf"^\s+{name}\s+\w", haystack, re.M) is not None


def test_resource_type_selects_the_long_retention_class(clean_audit):
    """``ai_decision`` is what keeps the row for 2y/5y instead of rotating at 90d.

    If this ever becomes ``access``, the evidence that a decision was not biased is
    destroyed after 90 days, and nothing else in the system would notice.
    """
    payload = audit_payload(clean_audit, resource_id=RESOURCE_ID)
    assert payload["resource_type"] == AUDIT_RESOURCE_TYPE == "ai_decision"


def test_actor_is_null_for_an_automatic_audit(clean_audit):
    """A null actor records that the audit was automatic, not that it was skipped.

    The bias audit runs in a Celery task with no session user. Writing a fabricated
    actor, or omitting the field, would both misrepresent how the row came to exist.
    """
    payload = audit_payload(clean_audit, resource_id=RESOURCE_ID)
    assert payload["actor_id"] is None
    assert "actor_id" in payload


def test_details_carry_everything_needed_to_replay_the_flag(flagged_audit):
    """The entry must let a later reader re-derive the verdict.

    That means the rule set version, the parameterisation in force, what fired, and
    a hash of the text. Without the version, a flag cannot be explained a year later
    once the terms have changed.
    """
    details = audit_payload(flagged_audit, resource_id=RESOURCE_ID)["details"]
    for key in ("pass_version", "rationale_hash", "checked", "highlights",
                "explanation", "reference_year", "graduation_window_years"):
        assert key in details, f"details missing {key!r}"
    assert details["pass_version"] == "1.0.1"
    assert details["highlights"], "a flag must quote what fired"
    assert details["reference_year"] >= 2026


def test_details_contain_no_pii_and_no_raw_rationale(clean_audit):
    """``details`` is JSONB on a retained table. It carries a HASH, not the text.

    ``REQ-COM-008`` requires the audit trail to hold no raw PII, and the rationale
    belongs to the application record, not duplicated into the log.
    """
    payload = audit_payload(clean_audit, resource_id=RESOURCE_ID)
    serialised = json.dumps(payload["details"])
    assert "120 req/s" not in serialised, "raw rationale text leaked into the audit row"
    assert len(payload["details"]["rationale_hash"]) == 64


def test_payload_is_json_serialisable(clean_audit, flagged_audit):
    """It goes into a JSONB column. A non-serialisable value fails at write time,
    in production, after the flag has already been shown to a recruiter."""
    for audit in (clean_audit, flagged_audit):
        json.dumps(audit_payload(audit, resource_id=RESOURCE_ID))


# --------------------------------------------------------- the review step

def test_review_payload_names_a_real_person(flagged_audit):
    payload = review_payload(
        flagged_audit, resource_id=RESOURCE_ID, actor_id="9a8b7c6d-0000-4000-8000-000000000002",
        note="Reviewed the phrase; the CV genuinely lists a society role.",
    )
    assert payload["actor_id"] is not None
    assert payload["action"] == ACTION_REVIEWED
    assert payload["details"]["note"].startswith("Reviewed the phrase")
    assert payload["details"]["reviewed_outcome"] == RESULT_FLAG


def test_review_allows_an_empty_note(flagged_audit):
    """An employer may agree with a flag and just be acknowledging it. Forcing a
    written reason here would recreate the override-reason rule (REQ-FR-052) on an
    action that needs no justification."""
    payload = review_payload(flagged_audit, resource_id=RESOURCE_ID, actor_id="x")
    assert payload["details"]["note"] == ""


def test_screening_and_review_use_different_actions(clean_audit, flagged_audit):
    """Otherwise an audit trail cannot distinguish 'the system flagged this' from
    'a person looked at it', which is the entire point of the review step."""
    screening = audit_payload(clean_audit, resource_id=RESOURCE_ID)
    review = review_payload(flagged_audit, resource_id=RESOURCE_ID, actor_id="x")
    assert screening["action"] != review["action"]
    assert screening["action"] == ACTION_SCREENED


def test_the_same_rationale_always_hashes_the_same(clean_audit):
    """Deterministic, or the same text produces two different audit rows."""
    again = audit_rationale(CLEAN_RATIONALE, set_dir=SET_DIR)
    assert again.rationale_hash == clean_audit.rationale_hash