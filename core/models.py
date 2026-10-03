"""Cross-cutting models owned by no single feature.

Two models live here, for two different reasons:

- **`AuditLogEntry`** is a compliance entity that the entity list assigned to no
  app. It is written by `ai.bias_audit.audit_rationale` and read by the admin
  compliance queue, so putting it in `ai/` would make the audit trail depend on
  the AI feature existing, and putting it in `admin/` would make it depend on the
  admin UI. `core/` is the only home with no such dependency. Recorded in
  Complete Doc §4.2.
- **`Skill`** is the skill taxonomy that Stage-1 matching filters on and that the
  bias audit's categories are drawn from. `core/fixtures/skills.json` loads into
  it, and a fixture with no model is a `loaddata` error.

Neither is written "just in case". Each exists because something already
references it: `AUTH_USER_MODEL`, an import in `ai/bias_audit.py`, and a
committed fixture respectively.

The other 22 tables in Arch Doc §5.1 are **not** here. They are written one app
at a time against the DDL, each with its own migration, so that a mismatch
between the DDL and a model is caught by `makemigrations --check` while the diff
is small enough to read.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class AuditLogEntry(models.Model):
    """One recorded action.

    **Append-only.** There is no update path, and rows are never deleted — not by
    a user, and not by the GDPR erasure workflow. `REQ-FR-041` hard-deletes the
    candidate's personal data while the audit trail survives, because an erasure
    that also erases the record of what was erased is indistinguishable from one
    that never happened. `actor_id` is `SET NULL` for the same reason: deleting
    the actor must not cascade into deleting the evidence.

    `details` holds the bias-pass result for a rationale audit — the terms that
    fired, the category, the fixture version and the rationale hash. It must
    never hold the rationale text itself or any candidate PII: this table is the
    one place a compliance export would not expect to find them.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # SET NULL, not CASCADE. See the class docstring.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
    )

    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=50, null=True, blank=True)
    resource_id = models.UUIDField(null=True, blank=True)

    # A dict, not free text: this column is queried (`ai_decision` per
    # application, for the override-rate analytics in REQ-FR-035).
    details = models.JSONField(default=dict, blank=True)

    # `GenericIPAddressField` rather than a string, so an IPv6 address is not
    # truncated at 45 characters.
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, null=True, blank=True)
    result = models.CharField(max_length=20, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_log_entries"
        verbose_name = "audit log entry"
        verbose_name_plural = "audit log entries"
        ordering = ["-created_at"]
        indexes = [
            # Matches idx_audit_resource in the DDL. The compliance queue filters
            # by resource far more often than by action.
            models.Index(
                fields=["resource_type", "resource_id"], name="idx_audit_resource"
            ),
            models.Index(fields=["action", "created_at"], name="idx_audit_action"),
        ]

    def __str__(self) -> str:
        # Deliberately not `self.actor` — that field is SET NULL and rendering it
        # forces a query per row in an admin list of hundreds of entries.
        return f"{self.action} @ {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def resource_label(self) -> str:
        """Human-readable resource reference, or an em dash when unset.

        Used by the admin compliance queue, where an entry with a null
        `resource_id` is normal (a login, a failed auth attempt) and rendering
        "None" there reads as an error.
        """
        if not self.resource_type:
            return "—"
        if not self.resource_id:
            return self.resource_type
        return f"{self.resource_type}:{self.resource_id}"


class Skill(models.Model):
    """A canonical skill in the taxonomy.

    Stage-1 matching filters on this table (Complete Doc §C.5) and the bias
    audit's categories come from `category`. `aliases` is what lets a resume
    saying "JS" or "Node.js" resolve to one skill instead of three, which is the
    difference between a candidate being ranked and being silently dropped.

    `canonical_name` is UNIQUE and `aliases` is a JSON list rather than a
    separate table. A separate table would be the right call if alias matching
    needed to be case-insensitive, locale-aware or scored — none of which is
    specified yet, and all of which are cheap to add later.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    canonical_name = models.CharField(max_length=100, unique=True)
    aliases = models.JSONField(default=list, blank=True)
    category = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "skills"
        verbose_name = "skill"
        verbose_name_plural = "skills"
        ordering = ["canonical_name"]
        indexes = [models.Index(fields=["category"], name="idx_skills_category")]

    def __str__(self) -> str:
        return self.canonical_name

    def matches(self, candidate_name: str) -> bool:
        """True when `candidate_name` is this skill's name or one of its aliases.

        Case-insensitive and whitespace-trimmed, because the input is free text
        lifted from a resume. Not accent-folded: the alias list is short enough
        to extend explicitly, and implicit normalisation hides a mismatch that
        someone should see.
        """
        needle = " ".join(candidate_name.split()).lower()
        if not needle:
            return False
        if needle == self.canonical_name.lower():
            return True
        return any(needle == str(alias).lower() for alias in self.aliases or [])
