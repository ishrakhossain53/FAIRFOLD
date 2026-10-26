"""Application rules shared by the API and the job-board page (REQ-FR-022).

The rule is one sentence -- "an authenticated candidate may apply once to an
active job" -- but it has two surfaces: `POST /api/v1/jobs/{id}/apply/` (batch
1.36) and the Apply button on page #5 (batch 1.37). Writing the status check and
the duplicate translation twice would let the two disagree about whether a
paused job is appliable or about which request wins a race.

So the rules live here, HTTP-free:

* the functions take model instances, never a request;
* an inactive job raises `JobNotOpen`, a duplicate raises `DuplicateApplication`;
* each surface maps those to its own status code and sentence.

**No job row lock.** Applying is the hot path (the load test in Complete Doc
§C.13 runs 1000 concurrent applications), and `select_for_update()` on the job
would serialise every applicant to one job. A `close/` that commits between the
status check and the insert can therefore admit one application to a job that
has just closed; that is a reviewable row, not a lost decision, and it is the
cheaper failure. The uniqueness rule is still enforced by the database.
"""

from __future__ import annotations

from django.db import IntegrityError, transaction

from matching.models import Application, Job

#: Shown verbatim by both surfaces. A 409 without a reason reads as a bug.
JOB_NOT_OPEN = "This job is not accepting applications."
ALREADY_APPLIED = "You have already applied to this job."


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
    """
    if job.status != Job.Status.ACTIVE:
        raise JobNotOpen(JOB_NOT_OPEN)

    try:
        with transaction.atomic():
            return Application.objects.create(
                job=job,
                candidate=candidate,
                status=Application.Status.APPLIED,
            )
    except IntegrityError as exc:
        raise DuplicateApplication(ALREADY_APPLIED) from exc
