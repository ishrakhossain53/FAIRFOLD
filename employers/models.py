"""Employer dashboard, job postings, shortlisting and team management.

One table so far: `EmployerProfile` (REQ-FR-045, Arch Doc §5.1). The DDL is the
specification; models are added app by app against it, one migration at a time.

This module deliberately does **not** pre-declare the remaining employer-side
tables (jobs, applications, assessments, interviews). Transcribing the whole DDL
in one pass would produce fields whose types, indexes and constraints were never
checked against a running database, and `makemigrations --check` in CI would then
pass on migrations that encode a guess.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class EmployerProfile(models.Model):
    """An employer's company profile (REQ-FR-045, Arch Doc §5.1).

    **One profile per user.** The DDL leaves `user_id` nullable, but §5.2 draws
    `users (1) ──(1)──> employer_profiles` and REQ-FR-045 creates the profile
    during onboarding. A profile with no owner is a row nobody can reach, so the
    foreign key is non-null and unique — the same reading as
    `candidates.models.CandidateProfile`.

    **`company_name` is not encrypted yet.** The DDL marks it `ENCRYPTED`, and
    decision D-5 (encrypt from creation vs defer to Phase 4) is still open. This
    follows the precedent set by `accounts.models.User.first_name`/`last_name`
    and `CandidateProfile.location`: plain text until the `key_version` rotation
    design in Complete Doc §C.8.2 exists, because an `Encrypted*` field without
    it creates rows the rotation procedure cannot read. Switching the column is a
    migration, not a rewrite.

    **`show_company_name` is off by default (REQ-FR-042).** The public job board
    may show a company name only after the employer opts in, because "who is
    hiring" is itself information. Flipping it is an employer choice; nothing in
    ranking reads it (REQ-FR-053).

    **Billing columns are stored, not acted on.** `billing_plan`,
    `billing_cycle` and `stripe_customer_id` come from the DDL with no CHECK
    constraints and no documented value list, so they are plain columns with the
    DDL's defaults and no `choices`. Payments are Phase 5; the DDL's comment
    notes the current provider is bKash/SSLCommerz, whose id column does not
    exist in §5.1 and is therefore not invented here.

    **Roles are not a field.** `employer_hr` and `employer_manager` are Django
    groups (D-2), checked with `has_perm`. A `role` column would be a second
    source of truth for REQ-FR-047's last-admin rule.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employer_profile",
    )

    # DDL: TEXT ENCRYPTED. Plain until D-5 is accepted — see the class docstring.
    # The DDL puts no NOT NULL on it, and an empty string is the "not provided"
    # value, matching the candidate profile's text columns.
    company_name = models.TextField(blank=True)

    industry = models.CharField(max_length=100, blank=True)

    # INTEGER in the DDL with no CHECK: a nullable column is the only way to say
    # "not provided", and narrowing it to a positive-only field would be a rule
    # the specification does not state.
    company_size = models.IntegerField(null=True, blank=True)

    # REQ-FR-042: opt-in disclosure of the company name on candidate-facing
    # surfaces. Off by default in the DDL and here.
    show_company_name = models.BooleanField(default=False)

    billing_plan = models.CharField(max_length=20, default="free")
    billing_cycle = models.CharField(max_length=10, default="monthly")

    # DDL: TEXT ENCRYPTED, Phase 5. Same D-5 deferral as `company_name`.
    stripe_customer_id = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "employer_profiles"
        verbose_name = "employer profile"
        verbose_name_plural = "employer profiles"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        # The primary key, not the company name. The DDL encrypts that column,
        # so it is treated as sensitive here: an admin list or a log line that
        # renders it would put the value everywhere the model is printed.
        return f"Employer profile {self.pk}"
