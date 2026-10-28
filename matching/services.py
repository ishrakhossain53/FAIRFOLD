"""Application rules shared by the API and the job-board page (REQ-FR-022).

The rule is one sentence -- "an authenticated candidate may apply once to an
active job" -- but it has two surfaces: `POST /api/v1/jobs/{id}/apply/` (batch
1.36) and the Apply button on page #5 (batch 1.37). Writing the status check and
the duplicate translation twice would let the two disagree about whether a
paused job is appliable or about which request wins a race.

Batch 1.41 adds the other half: **the human decision** (`shortlist` / `reject`,
REQ-FR-052, REQ-FR-023). Its transition table is `DECISION_ACTIONS` below, and it
stays here for the same reason -- the API's two action endpoints and the Phase 1
review UI (batch 1.42) must not be able to disagree about which transitions are
legal, or about what the audit entry says.

Batch 1.43 adds the two notifications the requirements name: the candidate and the
employer are told when an application arrives (REQ-FR-022), and the candidate is
told when a decision changes the status (REQ-FR-023). They are written here, not
in the API views, because the apply and decision actions have two surfaces each
(page and API) and a notification is one per event, not one per surface.

So the rules live here, HTTP-free:

* the functions take model instances or ids, never a request;
* an inactive job raises `JobNotOpen`, a duplicate raises `DuplicateApplication`;
* a decision returns an outcome constant, and the caller maps it to a status code;
* each surface maps those to its own status code and sentence.

**No job row lock.** Applying is the hot path (the load test in Complete Doc
§C.13 runs 1000 concurrent applications), and `select_for_update()` on the job
would serialise every applicant to one job. A `close/` that commits between the
status check and the insert can therefore admit one application to a job that
has just closed; that is a reviewable row, not a lost decision, and it is the
cheaper failure. The uniqueness rule is still enforced by the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from candidates.services import alias_for
from core.models import AuditLogEntry
from matching.models import Application, Job
from notifications.models import Notification
from notifications.services import notification_type, notify

#: Shown verbatim by both surfaces. A 409 without a reason reads as a bug.
JOB_NOT_OPEN = "This job is not accepting applications."
ALREADY_APPLIED = "You have already applied to this job."

#: `AuditLogEntry.resource_type` for a decision on an application. REQ-FR-052
#: gives overrides their own class (`ai_decision`) in Phase 2; a Phase-1 decision
#: has no ranking to be measured against, so it is an application action.
APPLICATION_AUDIT_RESOURCE_TYPE = "application"


class JobNotOpen(Exception):
    """The job is not `active`, so Arch Doc §4.3 rule 5 forbids applying."""


class DuplicateApplication(Exception):
    """This candidate already has a row for this job (`UNIQUE(job, candidate)`)."""


def apply_to_job(*, candidate, job: Job) -> Application:
    """Create one `applied` application, or raise the documented refusal.

    `status` is written explicitly rather than left to the model default: REQ-FR-022
    names `applied` as the outcome, and an explicit write keeps that requirement
    visible at the call site.

    The `IntegrityError` is caught **outside** `atomic()`: after the constraint
    fires, the transaction is aborted until the savepoint is rolled back, so the
    translation has to happen after the block exits. The only other constraint on
    this insert is `ck_screening_status`, whose default is valid, so an
    `IntegrityError` here is the duplicate pair.

    **Applying notifies both parties** (REQ-FR-022, batch 1.43): one notification
    for the candidate and one for the employer, in the same transaction as the
    row. The employer's copy names the candidate by their per-employer alias
    (REQ-FR-054), never by name or email.
    """
    if job.status != Job.Status.ACTIVE:
        raise JobNotOpen(JOB_NOT_OPEN)

    try:
        with transaction.atomic():
            application = Application.objects.create(
                job=job,
                candidate=candidate,
                status=Application.Status.APPLIED,
            )
            _notify_application_created(application, job=job, candidate=candidate)
            return application
    except IntegrityError as exc:
        raise DuplicateApplication(ALREADY_APPLIED) from exc


def _notify_application_created(
    application: Application,
    *,
    job: Job,
    candidate,
) -> None:
    """Tell the candidate and the employer that an application exists.

    REQ-FR-022: "candidate notified; And employer notified". Both rows are written
    in the applying transaction, so a rolled-back application leaves no
    notification claiming it happened -- `notify()` queues the email on commit.

    **The employer's message names the candidate by alias.** REQ-FR-054 makes the
    per-employer alias the only identity an employer sees; the name, the email and
    the internal UUID never reach `title` or `message`. The alias row is created
    here on first contact rather than at first page view, because the message
    cannot be written without one -- and `alias_for()` is the single write path
    that guarantees one label per pair.

    **Both links are pages that exist.** The candidate's is page #29 (built in
    1.39); the employer's is page #41 (built in 1.25). An email that links to a
    page nobody built is worse than one with no link.
    """
    notify(
        candidate.user,
        notification_type(Notification.Type.APPLICATION_UPDATE),
        title="Application received",
        message=(
            f"We received your application for {job.title}. "
            "Track its status in your dashboard."
        ),
        url=f"/candidate/applications/{application.pk}/",
    )
    notify(
        job.employer.user,
        notification_type(Notification.Type.APPLICATION_UPDATE),
        title="New application",
        message=f"{alias_for(job.employer, candidate)} applied for {job.title}.",
        url=f"/employer/applications/{application.pk}/",
    )


# ---------------------------------------------------------------------------
# Decision actions (REQ-FR-052, REQ-FR-023, batch 1.41)
# ---------------------------------------------------------------------------


def application_status(member: Any) -> str:
    """The stored string of an `Application.Status` member.

    Same reason as `employers.services.job_status`: Django's choices metaclass is
    untyped, so mypy reads a `TextChoices` attribute as its `(value, label)` tuple
    although it is a `str` subclass at runtime. Converting in one place keeps the
    table honestly typed as `tuple[str, ...]` without `type: ignore` noise.
    """
    return str(member.value)


#: `prd.md` §11.3 and `design.md` §7.4: `applied -> screened -> shortlisted ->
#: interview -> offered -> hired`, with `rejected` reachable from any stage.
#:
#: `applied` is a shortlist source as well as `screened` because the step that
#: produces `screened` is REQ-FR-028's screening run, which is Phase 2. In Phase 1
#: an application rests at `applied`, so refusing to shortlist it would make the
#: action unusable until screening ships -- and `screened` is not a *decision*
#: state, it is "the AI has looked at it".
SHORTLIST_SOURCES = (
    application_status(Application.Status.APPLIED),
    application_status(Application.Status.SCREENED),
)

#: `not_matched` is a filter outcome, not a pipeline stage (Gap G3), and rejecting
#: from it is a person's action. `hired` is terminal: it is an outcome, not a
#: stage a rejection can follow.
REJECT_SOURCES = (
    application_status(Application.Status.APPLIED),
    application_status(Application.Status.SCREENED),
    application_status(Application.Status.NOT_MATCHED),
    application_status(Application.Status.SHORTLISTED),
    application_status(Application.Status.INTERVIEW),
    application_status(Application.Status.OFFERED),
)


@dataclass(frozen=True)
class DecisionAction:
    """One row of the application decision table.

    The table exists so the transition rules are data, not a chain of `if`s: the
    tests iterate it, the API reads it, and a status added to the model without a
    decision here is a visible gap rather than a silently reachable state.
    """

    to_status: str
    allowed_from: tuple[str, ...]
    audit_action: str
    conflict_detail: str


#: The single transition table for a human decision. The two action endpoints are
#: the only way into it: `ai.screening` may not touch `status`, and the Phase 2
#: `review/` pull-back (batch 2.18) is the only other documented writer.
DECISION_ACTIONS: dict[str, DecisionAction] = {
    "shortlist": DecisionAction(
        to_status=application_status(Application.Status.SHORTLISTED),
        allowed_from=SHORTLIST_SOURCES,
        audit_action="application.shortlisted",
        conflict_detail="Only an applied or screened application can be shortlisted.",
    ),
    "reject": DecisionAction(
        to_status=application_status(Application.Status.REJECTED),
        allowed_from=REJECT_SOURCES,
        audit_action="application.rejected",
        conflict_detail="A hired application cannot be rejected.",
    ),
}

#: REQ-FR-029 / Gap G3: a filtered candidate is pulled back into review first,
#: which is `review/` in batch 2.18. Shortlisting straight from `not_matched`
#: would make the recorded exclusion reason meaningless.
NOT_MATCHED_SHORTLIST_DETAIL = (
    "This application was excluded by the job's filter. It must be reviewed "
    "before it can be shortlisted."
)

#: REQ-FR-051, worded as design.md W27 / page #41 states it. The gate is checked
#: here, in the service, so the rule holds for any caller and not only the page.
SHORTLIST_GATE_DETAIL = (
    "Shortlisting is blocked until the required assessment is passed."
)

#: The row moved to the action's target status and one audit entry was written.
DECISION_CHANGED = "changed"
#: The row already held the target status; nothing was written (Arch Doc §4.3 rule 2).
DECISION_NOOP = "noop"
#: The row cannot take this action from its current status; nothing was written.
DECISION_CONFLICT = "conflict"
#: REQ-FR-051: the assessment gate is `pending` or `failed`; nothing was written.
DECISION_GATE_BLOCKED = "gate_blocked"


def decide_application(
    *,
    application_id,
    employer,
    action: str,
    actor,
) -> tuple[str, Application]:
    """Apply one human decision to one of `employer`'s applications.

    Returns `(outcome, application)` where `outcome` is `DECISION_CHANGED`,
    `DECISION_NOOP`, `DECISION_CONFLICT` or `DECISION_GATE_BLOCKED`. The sentence
    explaining a refusal belongs to the caller, because the API renders it as
    JSON and a page would render it as a message.

    **Ownership is in the lookup.** `job__employer` is part of the filter, so an
    application belonging to another employer raises `Application.DoesNotExist`
    -- the same answer as an id that exists nowhere.

    **A repeated action is a no-op.** Shortlisting a shortlisted application, or
    rejecting a rejected one, returns the row and writes no second audit entry.
    This is Arch Doc §4.3 rule 2 applied to the application lifecycle, and it is
    what makes a double-clicked button or a retried request harmless.

    **Two writes, one transaction.** The status change, `decided_by` (and
    `shortlisted_at` on a shortlist) and the audit entry commit together, so a
    rolled-back decision cannot leave an entry claiming it happened.

    **The audit entry carries statuses, not people.** `{"from", "to"}` only: no
    candidate name, alias, email or rationale text (`REQ-FR-052`,
    `AuditLogEntry` is append-only and PII-free). The actor is `actor_id`, which
    is the column designed for it.

    **No ranking yet, so no override.** `decision_override` stays `False`: it
    means "went against the employer's cut-off", and there is no cut-off until
    batch 2.19 ranks applications. Writing it here would inflate REQ-FR-035's
    override rate with decisions that were never compared to anything.

    **A change notifies the candidate** (REQ-FR-023, batch 1.43). A no-op and a
    refusal return before the write, so they notify nobody: there is nothing to
    tell the candidate about.
    """
    spec = DECISION_ACTIONS[action]

    with transaction.atomic():
        application = (
            Application.objects
            # `of=("self",)` locks the application row only: the joined job and
            # candidate are read for the notification copy, and locking them
            # would serialise unrelated writes for the length of this decision.
            .select_for_update(of=("self",))
            # Read in the same query: the notification needs the job title and
            # the candidate's user, and a lazy load per decision is a query
            # nobody would notice until a bulk action ran one per row.
            .select_related("job", "candidate__user").get(
                pk=application_id, job__employer=employer
            )
        )

        if application.status == spec.to_status:
            return DECISION_NOOP, application

        if action == "shortlist" and application.status == application_status(
            Application.Status.NOT_MATCHED
        ):
            return DECISION_CONFLICT, application

        if application.status not in spec.allowed_from:
            return DECISION_CONFLICT, application

        # REQ-FR-051: the gate is a backend rule, not a disabled button. `reject`
        # deliberately does not consult it -- declining a candidate who never sat
        # the assessment must stay possible.
        if action == "shortlist" and not application.can_shortlist():
            return DECISION_GATE_BLOCKED, application

        previous = application.status
        application.status = spec.to_status
        application.decided_by = actor
        update_fields = ["status", "decided_by"]
        if action == "shortlist":
            application.shortlisted_at = timezone.now()
            update_fields.append("shortlisted_at")
        application.save(update_fields=update_fields)

        AuditLogEntry.objects.create(
            actor=actor,
            action=spec.audit_action,
            resource_type=APPLICATION_AUDIT_RESOURCE_TYPE,
            resource_id=application.pk,
            details={"from": previous, "to": spec.to_status},
            result="success",
        )

        # REQ-FR-023: a status change notifies the candidate. Written after the
        # audit entry so the entry exists even if the copy below ever raised, and
        # inside the transaction so a rollback removes both. A no-op or a refused
        # decision returns above and notifies nobody: there was no change to tell
        # them about.
        notify(
            application.candidate.user,
            notification_type(Notification.Type.APPLICATION_UPDATE),
            title=f"Your application was {application.get_status_display().lower()}",
            message=(
                f"Your application for {application.job.title} is now "
                f"{application.get_status_display().lower()}."
            ),
            url=f"/candidate/applications/{application.pk}/",
        )

    return DECISION_CHANGED, application
