"""Job lifecycle operations shared by the API and the employer portal (Arch Doc §4.3).

The state machine has to behave the same whether it is driven by
`POST /api/v1/jobs/{id}/activate/` or by the pause button on page #37. Writing it
twice would let the two surfaces disagree about an idempotent no-op, about which
transition is a conflict, or about what the audit entry says -- and the audit
entry is the only record of who published a job.

So the rules live here, HTTP-free:

* the functions take ids and an `EmployerProfile`, never a request;
* an id that is not this employer's job raises `Job.DoesNotExist`, and each
  surface maps that to its own 404 (DRF's for the API, Django's for the portal);
* outcomes are string constants, not HTTP status codes.

Everything that writes also locks the row (`select_for_update`) inside a single
transaction, so two racing requests cannot both audit one transition, and a
rolled-back write cannot leave an entry claiming it happened.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from core.models import AuditLogEntry
from matching.models import Job


#: The job moved to the target status and one audit entry was written.
def job_status(member: Any) -> str:
    """The stored string of a `Job.Status` member.

    Django's choices metaclass is untyped, so mypy reads a `TextChoices` attribute
    as its `(value, label)` tuple although it is a `str` subclass at runtime.
    Converting in one place keeps the callers honestly typed as `str` without
    scattering `type: ignore` comments over every view.
    """
    return str(member.value)


#: The job moved to the target status and one audit entry was written.
CHANGED = "changed"
#: The job already held the target status; nothing was written (Arch Doc §4.3 rule 2).
NOOP = "noop"
#: The transition is not in the §4.3 matrix; nothing was written.
CONFLICT = "conflict"
#: The draft row was removed and one audit entry was written.
DELETED = "deleted"


def record_job_audit(
    *,
    actor,
    action: str,
    job: Job,
    details: dict,
) -> AuditLogEntry:
    """Append one job entry to the audit trail.

    Kept as a function so every job action goes through the same field set. The
    callers pass `{"title": ...}` on creation/deletion, `{"changed": [...]}` on
    an edit and `{"from", "to"}` on a transition: employer content and field
    names, never candidate data and never a rationale.
    """
    return AuditLogEntry.objects.create(
        actor=actor,
        action=action,
        resource_type="job",
        resource_id=job.pk,
        details=details,
        result="success",
    )


def change_job_status(
    *,
    job_id,
    employer,
    to_status: str,
    allowed_from: tuple[str, ...],
    audit_action: str,
    actor,
) -> tuple[str, Job]:
    """Apply one Arch Doc §4.3 transition under a row lock.

    Returns `(outcome, job)`, where `outcome` is `CHANGED`, `NOOP` or `CONFLICT`.
    A conflict returns the unchanged job so the caller can render it; the
    sentence explaining the conflict belongs to the caller, because the API
    returns it in a JSON body and the portal shows it as a message.
    """
    with transaction.atomic():
        job = Job.objects.select_for_update().get(pk=job_id, employer=employer)

        if job.status == to_status:
            return NOOP, job

        if job.status not in allowed_from:
            return CONFLICT, job

        previous = job.status
        job.status = to_status
        job.save(update_fields=["status", "updated_at"])
        record_job_audit(
            actor=actor,
            action=audit_action,
            job=job,
            details={"from": previous, "to": job.status},
        )

    return CHANGED, job


def delete_draft_job(*, job_id, employer, actor) -> tuple[str, Job]:
    """Delete a draft and audit it (Arch Doc §4.3 rule 4).

    Only a draft is deletable: every §5.1 reference to `jobs` cascades, so
    deleting a published job would destroy its applications and interviews.
    Returns `(DELETED | CONFLICT, job)`; the instance keeps its pk after deletion
    so the caller can still put the id in a message.
    """
    with transaction.atomic():
        job = Job.objects.select_for_update().get(pk=job_id, employer=employer)
        if job.status != Job.Status.DRAFT:
            return CONFLICT, job

        # The entry outlives the row: `resource_id` is a plain UUID, not a
        # reference, so the trail still says a job existed and who removed it.
        record_job_audit(
            actor=actor,
            action="job.deleted",
            job=job,
            details={"title": job.title},
        )
        job.delete()

    return DELETED, job
