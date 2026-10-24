"""AI matching engine, pgvector storage and ranking.

`Job` (Arch Doc §5.1 `jobs`, batch 1.26) and `Application` (§5.1
`applications`, batch 1.34) live here because Complete Doc §C.4 assigns both to
`matching/models.py`, and because the ranking service that reads them is in this
app. `ai/` still holds no models of its own and `AuditLogEntry` lives in `core/`
(Complete Doc §4.2).

Two deliberate departures from the DDL, both narrow:

* **`jobs.description_embedding VECTOR(384)` is absent.** Batch 2.12 owns the
  pgvector columns *and* the extension migration. Adding the column first would
  make every test run depend on an extension the test database has not created,
  which is the same deferral `candidates.models.CandidateResume` documents.
* **Nullable text columns are `blank=True` without `null=True`** (`location`,
  `screening_error`, `not_matched_reason`, ...). The DDL permits either; the
  repository precedent (`CandidateProfile.title`) is that an empty string is the
  single spelling of "not provided". `screening_error` is rendered in the UI, and
  a null there would surface as "None". `cost_estimate` stays nullable because
  zero is a real cost and "no estimate yet" is not zero.

**The AI pipeline never writes `status`.** `ai.screening.screen_application()`
sets `match_score`, `match_rationale`, `ai_model_used`, `screening_status` and
`screened_at`, and nothing else. Auto-shortlist and auto-reject are forbidden
(`REQ-FR-052`), and the cleanest place to enforce that is the set of columns the
writer is allowed to touch.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Job(models.Model):
    """A job posting (Arch Doc §5.1 `jobs`, batch 1.26).

    **`status` is a posting state, not a screening state.** `draft`, `active`,
    `paused` and `closed` are the four values in the DDL; the transitions between
    them (batches 1.27-1.29) are not modelled here, because a job that has never
    been published must still be storable.

    **`screening_config` and its version travel together.** `REQ-FR-029` requires
    the rule-set version that produced a `not_matched` result to be recorded on
    the application, so `screening_config_version` is bumped whenever the rules
    change and copied onto every application scored under it. A rule set without
    a version cannot be replayed, and a replayable rule set is the whole point of
    recording the exclusion reason.
    """

    class Status(models.TextChoices):
        """The four values in the DDL comment, in one place."""

        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CLOSED = "closed", "Closed"

    class ExperienceLevel(models.TextChoices):
        """The DDL comment calls these `entry, intermediate, senior, lead`."""

        ENTRY = "entry", "Entry"
        INTERMEDIATE = "intermediate", "Intermediate"
        SENIOR = "senior", "Senior"
        LEAD = "lead", "Lead"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    employer = models.ForeignKey(
        "employers.EmployerProfile",
        on_delete=models.CASCADE,
        related_name="jobs",
    )

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    responsibilities = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    nice_to_have = models.TextField(blank=True)

    location = models.CharField(max_length=200, blank=True)
    remote_allowed = models.BooleanField(default=False)
    experience_level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    # Questions asked at apply time (REQ-FR-028's screening answers). A list, not
    # a model, because the answer shape is per-job and edited as one blob.
    screening_questions = models.JSONField(default=list, blank=True)

    # Gap G3. `{"filters": {...}}`; the version is stamped onto each application.
    screening_config = models.JSONField(default=dict, blank=True)
    screening_config_version = models.PositiveIntegerField(default=1)

    # Which model produced the scores on this job's applications. Nullable in the
    # DDL and blank here, because a job is created before anything is screened.
    ai_model_used = models.CharField(max_length=100, blank=True)

    # Nullable: no estimate has been made yet (batch 2.31 owns the estimator).
    cost_estimate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jobs"
        verbose_name = "job"
        verbose_name_plural = "jobs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        # The title only. `employer.company_name` is encrypted and, for a job the
        # employer has not opted to show, not public (REQ-FR-042); an admin list
        # that rendered it would leak it into every page and log line.
        return self.title


class Application(models.Model):
    """One candidate's application to one job (Arch Doc §5.1, batch 1.34).

    **`not_matched` is a filter outcome, not a rejection.** Gap G3: the stage-1
    hard filter may only produce `not_matched`, with the firing rule in
    `not_matched_reason` and the rule-set version in `filter_rules_version`. The
    candidate stays reviewable and the employer can pull them back into
    `screened`. Only a person may write `rejected`.

    **`decision_override` is recorded, never prevented.** `REQ-FR-052`: a decision
    against the ranking needs a written reason, and the DDL enforces that in the
    database (`chk_override_has_reason`) as well as in the service. The check is
    repeated here as a model constraint so a test that bypasses the service still
    cannot store an unexplained override.

    **`assessment_gate_status` blocks shortlisting in the backend.** `REQ-FR-051`
    is explicit that the gate is not a UI affordance; `can_shortlist()` is the
    single predicate any shortlist path must consult. It is deliberately not
    consulted by the screening writer, which must never shortlist at all.
    """

    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        SCREENED = "screened", "Screened"
        NOT_MATCHED = "not_matched", "Not matched"
        SHORTLISTED = "shortlisted", "Shortlisted"
        INTERVIEW = "interview", "Interview"
        OFFERED = "offered", "Offered"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"

    class ScreeningStatus(models.TextChoices):
        """D-6(b): the per-application state of a "Screen All" run."""

        NOT_SCREENED = "not_screened", "Not screened"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class AssessmentGateStatus(models.TextChoices):
        """REQ-FR-051. `not_required` is the default because no assessment is
        required until an employer says so."""

        NOT_REQUIRED = "not_required", "Not required"
        PENDING = "pending", "Pending"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(
        "candidates.CandidateProfile",
        on_delete=models.CASCADE,
        related_name="applications",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPLIED,
    )

    # AI scoring (REQ-FR-030). `match_rationale` holds the validated payload as
    # JSON text; `ai.citation.load_rationale()` is the only reader. The DDL has
    # one TEXT column and the page needs claim-level structure, so the choice is
    # between serialising here or adding a second column that would duplicate the
    # same data. Arch Doc §7.5 records the decision.
    match_score = models.IntegerField(null=True, blank=True)
    match_rationale = models.TextField(blank=True)
    ai_model_used = models.CharField(max_length=100, blank=True)

    screening_status = models.CharField(
        max_length=20,
        choices=ScreeningStatus.choices,
        default=ScreeningStatus.NOT_SCREENED,
    )
    screening_attempts = models.PositiveIntegerField(default=0)
    screening_started_at = models.DateTimeField(null=True, blank=True)
    screening_error = models.TextField(blank=True)  # PII-free
    screened_at = models.DateTimeField(null=True, blank=True)
    shortlisted_at = models.DateTimeField(null=True, blank=True)

    # Gap G3: what the hard filter excluded, and under which rule set.
    not_matched_reason = models.TextField(blank=True)
    filter_rules_version = models.PositiveIntegerField(null=True, blank=True)

    # Gap G1: the employer-required assessment gate (REQ-FR-051).
    assessment_gate_status = models.CharField(
        max_length=20,
        choices=AssessmentGateStatus.choices,
        default=AssessmentGateStatus.NOT_REQUIRED,
    )

    # Gap G2: a decision against the ranking is recorded, not prevented.
    decision_override = models.BooleanField(default=False)
    decision_override_reason = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_applications",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "applications"
        verbose_name = "application"
        verbose_name_plural = "applications"
        ordering = ["-created_at"]
        unique_together = [("job", "candidate")]
        constraints = [
            # The DDL's `chk_override_has_reason`, repeated at the model level.
            # `decision_override_reason` is never null, so "has a reason" is
            # "is not empty after trimming".
            models.CheckConstraint(
                condition=models.Q(decision_override=False)
                | ~models.Q(decision_override_reason=""),
                name="chk_override_has_reason",
            ),
            # The DDL's `ck_screening_status`. A typo in a Celery task would
            # otherwise be indistinguishable from a real state.
            models.CheckConstraint(
                condition=models.Q(
                    screening_status__in=[
                        "not_screened",
                        "queued",
                        "running",
                        "completed",
                        "failed",
                    ]
                ),
                name="ck_screening_status",
            ),
        ]

    def __str__(self) -> str:
        # Never the candidate. This model is rendered in employer-facing admin
        # pages, where a name is hidden until shortlist (REQ-FR-029).
        return f"Application {self.pk} ({self.status})"

    def can_shortlist(self) -> bool:
        """REQ-FR-051. Shortlist is refused while the gate is open or failed.

        `not_matched` is deliberately *not* consulted: a filter outcome stays
        reviewable and pullable back into `screened` (Gap G3), so it must not
        become a second, hidden gate.
        """
        return self.assessment_gate_status in (
            self.AssessmentGateStatus.NOT_REQUIRED,
            self.AssessmentGateStatus.PASSED,
        )
