"""Score one application: validate, audit, persist, record.

This is the seam batches 2.26-2.28 describe, and it is deliberately the *only*
writer of the AI scoring columns on an application:

1. **Validate** the rationale against the sanitised resume text (`ai.citation`,
   Arch Doc §7.5). Invented evidence raises before anything is written.
2. **Audit** the rationale's text with the versioned bias pass (`ai.bias_audit`).
   The verdict is advisory: it is stored on the audit trail and returned, never
   acted on here.
3. **Persist** `match_score`, `match_rationale`, `ai_model_used`, `screened_at`
   and `screening_status` -- and nothing else. `status`, `shortlisted_at` and
   `decided_by` are not in the `update_fields` list, so auto-shortlist and
   auto-reject are impossible from this path rather than merely discouraged
   (`REQ-FR-052`).
4. **Record** exactly one `audit_log_entries` row per scoring action, carrying the
   model and the rationale hash and never the rationale text (`REQ-FR-030`,
   Arch Doc §7.3 "Audit log completeness").

Where the bias status lives
---------------------------

Not on `applications`. Arch Doc §5.1 has no bias column, and adding one would be a
second source of truth for something the append-only trail already records. The
employer-facing status is the newest `bias_audit` row for the application;
`bias_status_for()` is the only reader, and `design.md` 7.7's "Mark as reviewed"
appends a `bias_audit_reviewed` row through `ai.bias_audit.review_payload()`.

Why the transaction covers both writes
--------------------------------------

An application whose `match_score` is written but whose audit row is not is a
scoring action with no evidence that it happened -- the exact failure `REQ-COM-008`
exists to prevent. One `transaction.atomic()` makes those two writes one unit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ai.bias_audit import (
    ACTION_REVIEWED,
    ACTION_SCREENED,
    AUDIT_RESOURCE_TYPE,
    RESULT_FLAG,
    BiasAudit,
    audit_payload,
    audit_rationale,
    record,
)
from ai.citation import Rationale, parse_rationale

MIN_SCORE = 0
MAX_SCORE = 100

#: The exact columns this module may write. Exposed so the advisory boundary is
#: asserted rather than described: `status` is absent on purpose.
SCORING_FIELDS = (
    "match_score",
    "match_rationale",
    "ai_model_used",
    "screened_at",
    "screening_status",
)


@dataclass(frozen=True)
class ScreeningOutcome:
    """What one scoring action produced."""

    rationale: Rationale
    audit: BiasAudit
    audit_entry: object
    score: int


@dataclass(frozen=True)
class BiasStatus:
    """The employer-facing audit status for one application (design.md 7.7).

    `entry` is deliberately `Any`: `ai/` has no Django import at module scope, so
    this module cannot name `core.models.AuditLogEntry` without breaking the rule
    that the AI layer loads without a database.
    """

    outcome: str | None
    reviewed: bool
    entry: Any | None = None

    @property
    def flagged(self) -> bool:
        return self.outcome == RESULT_FLAG

    @property
    def audited(self) -> bool:
        return self.outcome is not None


def _validate_score(score: int) -> int:
    """A score is an integer 0-100. `True` is not 1, and `"80"` is not a score."""
    if isinstance(score, bool) or not isinstance(score, int):
        raise ValueError("match score must be an integer between 0 and 100")
    if not MIN_SCORE <= score <= MAX_SCORE:
        raise ValueError(
            f"match score must be between {MIN_SCORE} and {MAX_SCORE}, got {score}"
        )
    return score


def screen_application(
    application: Any,
    *,
    score: int,
    payload: Mapping[str, Any] | str,
    source_text: str,
    model_used: str,
    actor: Any | None = None,
    set_dir: Any | None = None,
) -> ScreeningOutcome:
    """Validate, audit and store one rationale for `application`.

    Args:
        application: the `matching.Application` being scored. Saved in place.
        score: `match_score`, an integer 0-100 from the ranking/scoring step.
        payload: the generated rationale, as a mapping or JSON text.
        source_text: the **sanitised** resume text the rationale cites.
        model_used: provider model identifier, e.g. `"deepseek/deepseek-chat"`.
        actor: the user who triggered the run, or `None` for an automatic task.
            A null actor records "this was automatic", which is not the same as
            "nobody did this".
        set_dir: bias set version, for reproducible audits in tests.

    Raises:
        ValueError: score out of range or not an integer, or a blank model name.
        ai.citation.CitationError: the rationale is malformed or cites text the
            resume does not contain. Nothing is written when this raises.

    Returns:
        What was stored, including the audit verdict. The verdict is advisory;
        callers must not branch on it in a way that blocks a human decision.
    """
    from django.db import transaction
    from django.utils import timezone

    from matching.models import Application

    score = _validate_score(score)

    if not isinstance(model_used, str) or not model_used.strip():
        raise ValueError("ai_model_used is required: the audit row must name the model")
    model_used = model_used.strip()

    # Order matters. Validation runs before the audit so a fabricated rationale
    # never reaches the keyword pass, and both run before the transaction so a
    # rejected rationale leaves no partial write behind.
    rationale = parse_rationale(payload, source_text=source_text)
    audit = audit_rationale(rationale.to_text(), set_dir=set_dir)

    entry_payload = audit_payload(
        audit,
        resource_id=str(application.pk),
        actor_id=getattr(actor, "pk", None),
        action=ACTION_SCREENED,
        model=model_used,
    )

    with transaction.atomic():
        application.match_score = score
        application.match_rationale = rationale.to_json()
        application.ai_model_used = model_used
        application.screened_at = timezone.now()
        application.screening_status = Application.ScreeningStatus.COMPLETED
        application.save(update_fields=list(SCORING_FIELDS))

        entry = record(entry_payload)

    return ScreeningOutcome(
        rationale=rationale,
        audit=audit,
        audit_entry=entry,
        score=score,
    )


def bias_status_for(application: Any) -> BiasStatus:
    """Read the newest bias verdict for `application` from the audit trail.

    `reviewed` is scoped to the newest scoring row rather than "any review ever":
    after a re-screen, a review of the previous rationale says nothing about the
    new one, and carrying it forward would show a green tick over unreviewed text.
    """
    from core.models import AuditLogEntry

    entries = AuditLogEntry.objects.filter(
        resource_type=AUDIT_RESOURCE_TYPE,
        resource_id=application.pk,
    )
    latest = (
        entries.filter(action=ACTION_SCREENED).order_by("-created_at", "-id").first()
    )
    if latest is None:
        return BiasStatus(outcome=None, reviewed=False, entry=None)

    reviewed = entries.filter(
        action=ACTION_REVIEWED,
        created_at__gte=latest.created_at,
    ).exists()
    return BiasStatus(outcome=latest.result, reviewed=reviewed, entry=latest)
