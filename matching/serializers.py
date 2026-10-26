"""API serializers for applications (REQ-FR-022, Complete Doc §C.12).

The create response is a whitelist. An `Application` carries the candidate FK,
the match score, the screening state and the decision fields; none of them belong
in the body returned to the candidate who just applied. `job_id` is included
because the caller addressed the job by id and a client should not have to
remember it.

The application detail/list serializers (batches 1.38/1.40) are separate: an
employer-facing body must show the per-employer alias (REQ-FR-054), while the
candidate-facing body may show the job and status. One serializer for both would
be the place that leak happens.
"""

from __future__ import annotations

from rest_framework import serializers

from matching.models import Application


class ApplicationCreatedSerializer(serializers.ModelSerializer):
    """The `201` body of `POST /api/v1/jobs/{id}/apply/`."""

    # Declared because `job_id` is the FK's attname, not a model field that
    # `ModelSerializer` would discover on its own.
    job_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Application
        fields = ("id", "job_id", "status", "created_at")
        read_only_fields = fields
