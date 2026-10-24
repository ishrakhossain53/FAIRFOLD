"""Scoring one application: persistence, audit entry, and the advisory boundary.

Batches 2.26-2.28 (REQ-FR-030, Arch Doc §7.3/§7.5). The properties asserted here
are the ones a reviewer cannot see by reading the happy path:

* exactly one audit row per scoring action, naming the model and hashing the
  rationale -- and holding neither the rationale text nor any candidate data;
* a flagged rationale is stored and changes no decision field, because the pass is
  advisory (REQ-FR-052, design.md 7.7);
* a rejected rationale writes nothing at all, including when the bias pass itself
  fails after validation.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from accounts.models import User
from ai.bias_audit import record, review_payload
from ai.citation import CitationError, load_rationale
from ai.screening import SCORING_FIELDS, bias_status_for, screen_application
from candidates.models import CandidateProfile
from core.models import AuditLogEntry
from employers.models import EmployerProfile
from matching.models import Application, Job

pytestmark = pytest.mark.django_db

MODEL = "deepseek/deepseek-chat"
MODEL_AFTER_RESCREEN = "deepseek/deepseek-chat-v2"

SOURCE = (
    "Backend developer with six years of experience.\n"
    "Built a Django REST API serving 120 req/s at scale.\n"
    "Led a migration from MySQL to PostgreSQL with zero downtime."
)

CANDIDATE_EMAIL = "candidate-9f2a@example.com"


def payload(**overrides):
    base = {
        "summary": "Strong backend match; both required skills are evidenced.",
        "claims": [
            {
                "claim": "Runs Django in production",
                "evidence": "Built a Django REST API serving 120 req/s at scale.",
                "skills": ["Django"],
            },
            {
                "claim": "Has migrated a relational database",
                "evidence": "Led a migration from MySQL to PostgreSQL with zero downtime.",
                "skills": ["PostgreSQL", "MySQL"],
            },
        ],
        "missing_skills": [
            {"skill": "Kubernetes", "reason": "not mentioned in the resume"}
        ],
    }
    base.update(overrides)
    return base


@pytest.fixture
def employer_profile():
    user = User.objects.create_user("hr@example.com", "not-used-in-these-tests")
    return EmployerProfile.objects.create(user=user, company_name="Acme Ltd")


@pytest.fixture
def candidate_profile():
    user = User.objects.create_user(CANDIDATE_EMAIL, "not-used-in-these-tests")
    return CandidateProfile.objects.create(user=user, title="Backend developer")


@pytest.fixture
def job(employer_profile):
    return Job.objects.create(employer=employer_profile, title="Backend Engineer")


@pytest.fixture
def application(job, candidate_profile):
    return Application.objects.create(job=job, candidate=candidate_profile)


def screen(application, *, rationale=None, score=91, model=MODEL, **kwargs):
    return screen_application(
        application,
        score=score,
        payload=rationale or payload(),
        source_text=SOURCE,
        model_used=model,
        **kwargs,
    )


# --------------------------------------------------------------- persistence


def test_scoring_persists_the_ddl_columns_and_completes_the_run(application):
    outcome = screen(application)
    application.refresh_from_db()

    assert application.match_score == 91
    assert application.ai_model_used == MODEL
    assert application.screening_status == Application.ScreeningStatus.COMPLETED
    assert application.screened_at is not None
    assert outcome.score == 91
    assert outcome.rationale.claims[0].evidence.startswith("Built a Django")


def test_the_stored_rationale_round_trips(application):
    screen(application)
    application.refresh_from_db()

    assert load_rationale(application.match_rationale).to_dict() == payload()


def test_the_audit_hash_covers_the_text_the_reader_sees(application):
    """`rationale_hash` must be recomputable from the stored record, or it is a
    number nobody can check."""
    screen(application)
    application.refresh_from_db()

    entry = AuditLogEntry.objects.get()
    stored_text = load_rationale(application.match_rationale).to_text()

    assert (
        entry.details["rationale_hash"]
        == hashlib.sha256(stored_text.encode("utf-8")).hexdigest()
    )


# ------------------------------------------------------------ the audit row


def test_one_scoring_action_writes_exactly_one_entry(application):
    screen(application)

    entries = AuditLogEntry.objects.all()
    assert entries.count() == 1

    entry = entries.get()
    assert entry.action == "bias_audit"
    assert entry.resource_type == "ai_decision"
    assert entry.resource_id == application.pk
    assert entry.result == "pass"
    assert entry.actor_id is None, "an automatic run has no actor, and that is a fact"


def test_the_entry_names_the_model_and_not_the_rationale(application):
    screen(application)
    entry = AuditLogEntry.objects.get()

    assert entry.details["ai_model_used"] == MODEL
    assert len(entry.details["rationale_hash"]) == 64
    assert all(
        "rationale" not in key or key == "rationale_hash" for key in entry.details
    ), "the only rationale key may be the hash"


def test_the_entry_holds_no_rationale_text_and_no_candidate_data(application):
    """REQ-COM-008 and the `AuditLogEntry` docstring: the retained table is the one
    place a compliance export would not expect to find candidate data."""
    screen(application)
    serialised = json.dumps(AuditLogEntry.objects.get().details)

    for fragment in (
        "Built a Django REST API",
        "Led a migration from MySQL",
        "Strong backend match",
        CANDIDATE_EMAIL,
        "Backend developer",
    ):
        assert fragment not in serialised


def test_the_actor_is_recorded_when_a_person_triggers_the_run(
    application, employer_profile
):
    screen(application, actor=employer_profile.user)

    assert AuditLogEntry.objects.get().actor_id == employer_profile.user.pk


# --------------------------------------------------------------- advisory


def test_a_flagged_rationale_is_stored_and_decides_nothing(application):
    """design.md 7.7 + REQ-FR-052: a flag holds a candidate out of *bulk* shortlist
    until reviewed. It never shortlists, rejects or blocks a person."""
    flagged = payload(summary="Good cultural fit; the candidate is young and dynamic.")
    outcome = screen(application, rationale=flagged)
    application.refresh_from_db()

    assert outcome.audit.flagged is True
    assert AuditLogEntry.objects.get().result == "flag"
    assert AuditLogEntry.objects.get().details["blocks_bulk_shortlist"] is True

    assert application.status == Application.Status.APPLIED
    assert application.shortlisted_at is None
    assert application.decided_by is None
    assert application.decision_override is False
    assert application.match_score == 91, "a flag does not discard the score"
    assert load_rationale(application.match_rationale).claims


def test_the_writer_cannot_touch_a_decision_field():
    """The advisory boundary is a property of the write set, not a convention."""
    forbidden = {
        "status",
        "shortlisted_at",
        "decided_by",
        "decision_override",
        "decision_override_reason",
        "assessment_gate_status",
    }
    assert forbidden.isdisjoint(SCORING_FIELDS)


def test_the_status_reader_reports_an_unaudited_application(application):
    status = bias_status_for(application)

    assert status.audited is False
    assert status.outcome is None
    assert status.reviewed is False
    assert status.flagged is False


def test_the_status_reader_returns_the_newest_verdict(application):
    screen(application, score=64)
    screen(application, score=88, model=MODEL_AFTER_RESCREEN)

    status = bias_status_for(application)
    assert status.outcome == "pass"
    assert status.entry.details["ai_model_used"] == MODEL_AFTER_RESCREEN
    assert AuditLogEntry.objects.count() == 2, "a re-screen is a second action"


def test_a_review_is_read_back_and_does_not_survive_a_rescreen(application):
    """A review of the old text says nothing about new text."""
    outcome = screen(application)
    reviewer = User.objects.create_user(
        "reviewer@example.com", "not-used-in-these-tests"
    )

    record(
        review_payload(
            outcome.audit,
            resource_id=str(application.pk),
            actor_id=reviewer.pk,
            note="Checked the phrase in context",
        )
    )
    assert bias_status_for(application).reviewed is True

    screen(application, rationale=payload(), model=MODEL_AFTER_RESCREEN)
    assert bias_status_for(application).reviewed is False


# ----------------------------------------------------------- refusal paths


def test_invented_evidence_writes_nothing(application):
    invented = payload(
        claims=[
            {
                "claim": "Deployed Kubernetes in production",
                "evidence": "Deployed Kubernetes clusters across three regions.",
                "skills": ["Kubernetes"],
            }
        ]
    )

    with pytest.raises(CitationError):
        screen(application, rationale=invented)

    application.refresh_from_db()
    assert application.match_score is None
    assert application.match_rationale == ""
    assert application.ai_model_used == ""
    assert application.screened_at is None
    assert application.screening_status == Application.ScreeningStatus.NOT_SCREENED
    assert AuditLogEntry.objects.count() == 0


@pytest.mark.parametrize("score", [-1, 101, True, "80", 80.5, None])
def test_an_invalid_score_is_refused_before_anything_is_written(application, score):
    with pytest.raises(ValueError):
        screen(application, score=score)

    application.refresh_from_db()
    assert application.match_score is None
    assert AuditLogEntry.objects.count() == 0


def test_a_blank_model_name_is_refused(application):
    """REQ-FR-030 requires the audit row to name the model. A blank name would
    make the entry unreplayable, so it fails before the write."""
    with pytest.raises(ValueError):
        screen(application, model="   ")

    assert AuditLogEntry.objects.count() == 0


def test_a_failing_bias_pass_rolls_back_the_application_write(application, tmp_path):
    """Validation and audit run before the transaction; if the audit cannot load
    its rule set it must not leave a score with no trail behind it."""
    with pytest.raises(FileNotFoundError):
        screen(application, set_dir=tmp_path)

    application.refresh_from_db()
    assert application.match_score is None
    assert application.screening_status == Application.ScreeningStatus.NOT_SCREENED
    assert AuditLogEntry.objects.count() == 0
