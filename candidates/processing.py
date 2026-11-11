"""The resume processing state machine (REQ-FR-012, D-6(a), batch 2.1).

``candidate_resumes.status`` is the whole pipeline — upload, virus scan and the
Phase 2 extraction/embedding stages — and this module is the **one place** that
says which status may follow which. The table is data, not a chain of ``if``s,
so a status added to the model without a transition here is a visible gap rather
than a silently reachable state.

The legal transitions, from the DDL comment on ``candidate_resumes`` (§5.1) and
the upload/scan flow built in batches 1.18-1.20:

    pending   -> uploaded | scanning | rejected
    uploaded  -> scanning | rejected        (defined by the DDL; no row rests here)
    scanning  -> clean | rejected
    clean     -> processing
    processing-> extracted | failed
    extracted -> embedded | failed
    embedded  -> (terminal)
    rejected  -> (terminal)
    failed    -> processing                 (retry)

Two rules shape the table:

* **A hard failure only ever moves forward into `failed` or `rejected`.** There
  is no path back to `clean`/`uploaded` from an error: re-processing starts from
  `failed -> processing`, so the "this was broken" fact is never silently
  overwritten by a retry.
* **`failed` and `rejected` require a reason.** ``status_reason`` is the only
  place the row explains itself, and a failure without one is indistinguishable
  from a healthy row to the candidate.
"""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from candidates.models import CandidateResume

Status = CandidateResume.Status


def resume_status(member: Any) -> str:
    """The stored string of a `CandidateResume.Status` member (or a plain string).

    Django's choices metaclass is untyped, so mypy reads a `TextChoices` attribute
    as its `(value, label)` tuple although it is a `str` subclass at runtime.
    Converting in one place keeps the table honestly typed as `dict[str, ...]`
    without ``type: ignore`` noise — the same reason `matching.services` has
    `application_status`.
    """
    return str(member)


#: ``current -> {next, ...}``. Every value is one of the nine `Status` choices,
#: and every status appears as a key, so the exhaustive test in
#: `tests/candidates/test_resume_processing.py` cannot miss an unlisted state.
PROCESSING_TRANSITIONS: dict[str, frozenset[str]] = {
    resume_status(Status.PENDING): frozenset(
        {
            resume_status(Status.UPLOADED),
            resume_status(Status.SCANNING),
            resume_status(Status.REJECTED),
        }
    ),
    resume_status(Status.UPLOADED): frozenset(
        {resume_status(Status.SCANNING), resume_status(Status.REJECTED)}
    ),
    resume_status(Status.SCANNING): frozenset(
        {resume_status(Status.CLEAN), resume_status(Status.REJECTED)}
    ),
    resume_status(Status.CLEAN): frozenset({resume_status(Status.PROCESSING)}),
    resume_status(Status.PROCESSING): frozenset(
        {resume_status(Status.EXTRACTED), resume_status(Status.FAILED)}
    ),
    resume_status(Status.EXTRACTED): frozenset(
        {resume_status(Status.EMBEDDED), resume_status(Status.FAILED)}
    ),
    resume_status(Status.EMBEDDED): frozenset(),
    resume_status(Status.REJECTED): frozenset(),
    resume_status(Status.FAILED): frozenset({resume_status(Status.PROCESSING)}),
}

#: Statuses that must carry a non-empty `status_reason`.
REASON_REQUIRED = frozenset(
    {resume_status(Status.REJECTED), resume_status(Status.FAILED)}
)

#: Statuses that record a successful extraction + embedding, and so stamp
#: `processed_at` (the DDL defines it as "last successful extraction + embedding").
PROCESSED_STATUSES = frozenset(
    {resume_status(Status.EXTRACTED), resume_status(Status.EMBEDDED)}
)


class InvalidTransition(ValueError):
    """`from_status -> to_status` is not in :data:`PROCESSING_TRANSITIONS`."""


def can_transition(current: str, target: str) -> bool:
    """True when `current -> target` is a legal move."""
    return target in PROCESSING_TRANSITIONS.get(current, frozenset())


def next_statuses(status: str) -> frozenset[str]:
    """The legal successors of `status`, or the empty set for a terminal one."""
    return PROCESSING_TRANSITIONS.get(status, frozenset())


def transition(
    resume: CandidateResume,
    target: Any,
    *,
    reason: str = "",
) -> CandidateResume:
    """Move `resume` to `target`, enforcing the transition table.

    `target` is a `CandidateResume.Status` member or its stored string. Returns
    `resume`. Raises :class:`InvalidTransition` for an illegal move and
    :class:`ValueError` for an unknown target or a missing reason. A transition
    to the state the row already holds is a no-op: it returns without writing,
    so a duplicated delivery (Celery, a double-click) cannot clear the reason a
    failed row recorded.

    On success it also clears `status_reason` (a healthy row has nothing to say)
    and stamps `processed_at` when the target is a successful pipeline stage.
    """
    target = resume_status(target)

    if target not in PROCESSING_TRANSITIONS:
        raise ValueError(f"unknown resume status {target!r}")

    if resume.status == target:
        return resume

    if not can_transition(resume.status, target):
        raise InvalidTransition(
            f"Cannot move a resume from {resume.status!r} to {target!r}."
        )

    if target in REASON_REQUIRED and not reason.strip():
        raise ValueError(f"a transition to {target!r} requires a reason")

    resume.status = target
    resume.status_reason = reason
    update_fields = ["status", "status_reason"]
    if target in PROCESSED_STATUSES:
        resume.processed_at = timezone.now()
        update_fields.append("processed_at")
    resume.save(update_fields=update_fields)
    return resume
