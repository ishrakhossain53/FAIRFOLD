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

`CandidateProfile` is batch 1.14. `resume_embedding VECTOR(384)` is deliberately
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
