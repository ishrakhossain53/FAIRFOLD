"""Email and in-app notifications (REQ-FR-022, REQ-FR-023, batch 1.43).

One table and one model. `notifications` in Arch Doc §5.1 is **per recipient**:
one row per user a message reaches, never one row per event. That is why a job
offer that notifies the candidate and the employer writes two rows, and why the
`announcements` table (REQ-FR-050) exists separately -- a broadcast cannot be
stored here, only its deliveries.

The model is the record; `notifications.services.notify()` is the only writer and
`notifications.tasks.send_notification_email` is the email half. The scaffold's
"models are declared empty on purpose" note no longer applies to this app: one
table is now specified in enough detail (`Arch Doc §5.1`, `Complete Doc` §C.4 model
sketch) to build it against a running database.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """One message for one recipient (Arch Doc §5.1 `notifications`).

    **`notification_type` is the documented vocabulary.** The five values are the
    ones `Complete Doc` §C.4 lists for this model; the DDL leaves the column
    unconstrained (`VARCHAR(30)`), so the choices live here rather than as a
    database check. Batch 1.43's three messages all use `application_update`:
    a new application and a status change are both updates about an application,
    and the documented list has no separate "application received" value. A
    notification centre's type filter (design.md W19, batch 1.44) therefore sees
    them as one category, which is what its "Applications" tab means.

    **No PII by construction.** `title` and `message` are copy built by the
    caller. An employer-facing message names the candidate by their per-employer
    alias (REQ-FR-054), never by name, email or internal UUID; the recipient's own
    identity lives in `recipient`, which is where it belongs.

    **`read` is a column, not a derived value.** design.md W19's unread filter and
    the header badge both need it, and a `read_at` timestamp would answer a
    question (when) that no page asks. Marking read is batch 1.44.
    """

    class Type(models.TextChoices):
        """The five values in `Complete Doc` §C.4."""

        APPLICATION_UPDATE = "application_update", "Application Update"
        INTERVIEW_SCHEDULED = "interview_scheduled", "Interview Scheduled"
        AI_SCORE_READY = "ai_score_ready", "AI Score Ready"
        OFFER = "offer", "Offer"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=Type.choices)
    read = models.BooleanField(default=False)

    # A path, e.g. `/candidate/applications/<id>/`. The origin comes from
    # `settings.SITE_URL` at send time, so one row is not tied to one host.
    url = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        # design.md W19 renders the list newest first; the default ordering also
        # makes the email task's row stable if a recipient has several.
        ordering = ["-created_at"]

    def __str__(self) -> str:
        # Never the recipient's email: this string reaches admin pages and logs.
        return f"{self.get_notification_type_display()}: {self.title}"
