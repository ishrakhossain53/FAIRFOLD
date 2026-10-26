"""Candidate dashboard, resume upload, journey mapping and profile.

Models are added here one table at a time, against Arch Doc §5.1. `ai/` is the
exception: it has no models of its own, and `AuditLogEntry` lives in `core/`
(Complete Doc §4.2).

This scaffold deliberately does **not** pre-declare the 24 tables from
Arch Doc §5.1. Writing them from the DDL in one pass would produce models
whose field types, indexes and constraints were never checked against a running
database, and `makemigrations --check` in CI would then pass on migrations that
encode a guess. The DDL remains the specification; models are added app by app
against it, one migration at a time.

`CandidateProfile` is batch 1.14, `CandidateResume` is batch 1.18 and
`CandidateAlias` is batch 1.35. `resume_embedding VECTOR(384)` is deliberately
absent: `docs/ROADMAP.md` batch 2.12 owns the pgvector columns and the extension
migration, and adding the column before that migration would make every test run
depend on the extension being present in a database that has not created it yet.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class CandidateProfile(models.Model):
    """A candidate's professional profile (REQ-FR-009, Arch Doc §5.1).

    **One profile per user.** The DDL leaves `user_id` nullable, but §5.2 draws
    `users (1) ──(1)──> candidate_profiles` and REQ-FR-009 creates the profile
    for a registered candidate. A profile with no owner is a row nobody can
    reach, so the foreign key is non-null and unique.

    **`location` is not encrypted yet.** The DDL marks it `ENCRYPTED`, and
    decision D-5 (encrypt from creation vs defer to Phase 4) is still open. This
    follows the precedent set by `accounts.models.User.first_name`/`last_name`:
    plain text until the `key_version` rotation design in Complete Doc §C.8.2
    exists, because an `Encrypted*` field without it creates rows the rotation
    procedure cannot read. Switching the column is a migration, not a rewrite.

    **`visibility_tier` and `is_promoted` are discovery controls, never ranking
    inputs.** REQ-FR-053 and RSK-016: they may affect where a candidate appears
    on the public board or in employer search, but `rank_applications()` takes
    no tier argument and neither column may enter `match_score`. They live on
    this table only, not on applications.

    **`skills` is a denormalised search copy.** `prd.md:756` and D-6(e) name the
    `candidate_skills` table (REQ-FR-014) as the source of truth once it lands;
    this JSONB column exists so a profile can be searched before that table is
    populated. Do not write to it as if it were authoritative.
    """

    class VisibilityTier(models.TextChoices):
        """The three values in the DDL comment, in one place."""

        STANDARD = "standard", "Standard"
        PROMOTED = "promoted", "Promoted"
        VERIFIED = "verified", "Verified"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="candidate_profile",
    )

    # REQ-FR-009's four onboarding fields. The DDL puts no NOT NULL on title,
    # bio or location, so an empty string is the "not provided" value -- a
    # nullable text column has two spellings of the same state.
    title = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    location = models.TextField(blank=True)
    remote_ok = models.BooleanField(default=True)

    skills = models.JSONField(default=list, blank=True)
    journey_timeline = models.JSONField(default=list, blank=True)

    # `{job_id: score}` cache from the DDL. It is a read cache for the candidate
    # dashboard, recomputed from screened applications; it is not the ranking
    # input and must not be treated as one.
    match_scores = models.JSONField(default=dict, blank=True)

    # Paid discovery only (REQ-FR-053, D3). See the class docstring.
    visibility_tier = models.CharField(
        max_length=20,
        choices=VisibilityTier.choices,
        default=VisibilityTier.STANDARD,
    )
    is_promoted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "candidate_profiles"
        verbose_name = "candidate profile"
        verbose_name_plural = "candidate profiles"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        # The title, not the user. `User.__str__` is the email, and an admin
        # list of profiles that renders it would put PII in every page and log
        # line that touches this model.
        return self.title or f"Candidate profile {self.pk}"


class CandidateAlias(models.Model):
    """One candidate's stable alias for one employer (REQ-FR-054, D-4, batch 1.35).

    **Why this exists before the employer inbox.** REQ-FR-029 already forbids a
    name, photo or contact detail in the employer's application list, and the
    first such list is Phase 1 (batches 1.40/1.42). Building the alias afterwards
    would mean shipping a list that shows the internal candidate UUID and then
    retrofitting it -- exactly the interim identity leak D-4 rejects.

    **The pair is the identity, not the alias alone.** `UNIQUE(employer,
    candidate)` is what makes the alias stable across every job the employer
    posts; `UNIQUE(employer, alias)` keeps two candidates from sharing a label in
    one inbox. The alias is generated by `candidates.services.alias_for()`, never
    here, because "random and non-sequential" is a rule about generation and a
    model default cannot express it. The service also retries a collision, which
    a `default=` callable could not do against the second unique constraint.

    **The column is `employer_org_id`, as §5.1 spells it.** `Job` uses
    `employer_id`, so this is not a project-wide convention; `db_column` keeps the
    DDL and a database dump diffable without renaming the relation. No explicit
    `idx_aliases_employer` is declared: Django already indexes every foreign key,
    and a second index on the same column would be dead weight in every write.

    **Deletion follows the candidate.** Both foreign keys cascade, so GDPR erasure
    of a candidate removes the mapping (REQ-FR-054) and deleting an employer does
    not leave an orphan alias pointing at nothing.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    employer = models.ForeignKey(
        "employers.EmployerProfile",
        on_delete=models.CASCADE,
        related_name="candidate_aliases",
        db_column="employer_org_id",
    )
    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name="employer_aliases",
    )

    # e.g. "C-7H2X9". Not unique globally: two employers may coincidentally
    # generate the same label, and that is not a link between them.
    alias = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_aliases"
        verbose_name = "candidate alias"
        verbose_name_plural = "candidate aliases"
        # The DDL's two UNIQUE constraints, in the same order.
        unique_together = [("employer", "candidate"), ("employer", "alias")]

    def __str__(self) -> str:
        # The alias is safe by construction (no PII). The candidate and employer
        # are not rendered: an admin list would otherwise put a name next to a
        # label whose whole purpose is to replace it.
        return self.alias


class CandidateResume(models.Model):
    """An uploaded resume (REQ-FR-010/012, REQ-SEC-012, Arch Doc §5.1).

    **The row exists before the bytes do.** Requesting a presigned URL (batch
    1.19) creates a `pending` row that carries the server-generated key; only
    the completion step (batch 1.20) may move it to `uploaded`. Without that
    split, a URL a client requested and never used would leave a row
    indistinguishable from a real upload, and a scan would later report a
    missing object as if the candidate had uploaded it.

    **`file_key` is the only file reference.** REQ-FR-010: the browser uploads
    directly to object storage and Django stores only the key. The key is built
    server-side from a UUID, so it cannot be guessed from, or used to discover,
    `original_filename`. Never write the original name into it.

    **`original_filename` is not encrypted yet.** The DDL marks it `ENCRYPTED`;
    D-5 is still open, so this follows the `CandidateProfile.location`
    precedent: plain text until the Complete Doc §C.8.2 `key_version` rotation
    procedure exists. It is never rendered to an employer before shortlist
    (REQ-FR-029, 054) and never logged.

    **`status` is the whole pipeline, including the scan gate.** D-6(a) gave
    this table a status column, and REQ-SEC-012/gap P added the scan stage.
    `pending -> uploaded -> scanning -> clean` is the Phase 1 path; `rejected`
    is terminal and must carry a `status_reason`. `processing -> extracted ->
    embedded` belongs to Phase 2 (batches 2.10-2.12), and `failed` is their
    error state. The database CHECK constraint mirrors the DDL, so an unknown
    value fails in PostgreSQL rather than only in a form.

    **`status_reason` never holds PII or resume text.** It is a machine code or
    a short operator sentence such as "clamav unavailable", which is what
    `AuditLogEntry` may safely quote.
    """

    class Status(models.TextChoices):
        """The nine states in `ck_resume_status`, in pipeline order."""

        PENDING = "pending", "Pending upload"
        UPLOADED = "uploaded", "Uploaded"
        SCANNING = "scanning", "Scanning"
        CLEAN = "clean", "Clean"
        REJECTED = "rejected", "Rejected"
        PROCESSING = "processing", "Processing"
        EXTRACTED = "extracted", "Extracted"
        EMBEDDED = "embedded", "Embedded"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Non-null: the DDL leaves this nullable, but a resume with no candidate is
    # a row nobody can reach, and §5.2 draws the relation 1 -> N. Same reasoning
    # as `CandidateProfile.user`.
    candidate = models.ForeignKey(
        CandidateProfile,
        on_delete=models.CASCADE,
        related_name="resumes",
    )

    file_key = models.CharField(max_length=500)
    original_filename = models.TextField(blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    extracted_text = models.TextField(blank=True)
    raw_text_hash = models.CharField(max_length=64, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    status_reason = models.TextField(blank=True)

    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "candidate_resumes"
        verbose_name = "candidate resume"
        verbose_name_plural = "candidate resumes"
        ordering = ["-created_at"]
        constraints = [
            # Name matches the DDL so a database dump and §5.1 are diffable.
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "pending",
                        "uploaded",
                        "scanning",
                        "clean",
                        "rejected",
                        "processing",
                        "extracted",
                        "embedded",
                        "failed",
                    ]
                ),
                name="ck_resume_status",
            )
        ]

    def __str__(self) -> str:
        # Neither the key nor the original name: the first is storage detail,
        # the second is PII. An admin list that renders either would leak it.
        return f"Resume {self.pk}"
