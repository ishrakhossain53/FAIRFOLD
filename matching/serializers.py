"""API serializers for applications (REQ-FR-022, Complete Doc §C.12).

The create response is a whitelist. An `Application` carries the candidate FK,
the match score, the screening state and the decision fields; none of them belong
in the body returned to the candidate who just applied. `job_id` is included
because the caller addressed the job by id and a client should not have to
remember it.

The application detail/list serializers are split by audience: batch 1.38 added
the candidate-facing pair below, which shows the job and the status; batch 1.40's
employer-facing body must show the per-employer alias instead (REQ-FR-054). One
serializer for both would be the place that leak happens.
"""

from __future__ import annotations

from rest_framework import serializers

from employers.serializers import public_employer_name
from matching.models import Application, Job


class ApplicationCreatedSerializer(serializers.ModelSerializer):
    """The `201` body of `POST /api/v1/jobs/{id}/apply/`."""

    # Declared because `job_id` is the FK's attname, not a model field that
    # `ModelSerializer` would discover on its own.
    job_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Application
        fields = ("id", "job_id", "status", "created_at")
        read_only_fields = fields


class ApplicationJobSerializer(serializers.ModelSerializer):
    """The job summary an application row carries (REQ-FR-023, batch 1.38).

    A candidate's tracker names the job and, when the employer has opted in, the
    company (design.md S06). The employer identity goes through the same
    `public_employer_name()` whitelist as the public job board: REQ-FR-042 says
    the name is withheld until the employer reveals it, and a second
    implementation here would be a second place that rule can drift.

    `job.description` and the four Markdown columns are absent on purpose. The
    tracker row needs a title, a place and a level; the full posting already has
    a public page, and a list response that carried every description would be
    the largest payload in the candidate API for no display.
    """

    employer_name = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = (
            "id",
            "title",
            "location",
            "remote_allowed",
            "experience_level",
            "employer_name",
        )
        read_only_fields = fields

    def get_employer_name(self, job: Job) -> str | None:
        return public_employer_name(job.employer)


class CandidateApplicationSerializer(serializers.ModelSerializer):
    """One application, as its owner may see it (REQ-FR-023, batch 1.38).

    Complete Doc §C.12 declares the two candidate reads but names no fields. This
    is the row the tracker (page #28) and the detail page (#29) need, and nothing
    else:

    * `status` is the pipeline state the requirement is about. `status_display`
      is the model's own label, so the API and the pages cannot disagree about
      what `not_matched` reads as.
    * `match_score` and `screened_at` are present and null until Phase 2 produces
      a score (REQ-FR-024). Declaring them now keeps the contract stable; the
      alternative is a candidate client that breaks when screening ships.
    * `match_rationale` is deliberately absent. `ai.citation.load_rationale()` is
      the only reader of that JSON text and the rationale payload is batch
      2.21-2.25's contract; returning the raw TEXT column here would publish a
      shape this batch would have to invent.
    * The candidate is never a field. The route is owner-scoped, so the caller
      already knows which application it is, and an alias or a profile id in a
      candidate body is one more place identity can leak from.
    """

    job = ApplicationJobSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Application
        fields = (
            "id",
            "job",
            "status",
            "status_display",
            "match_score",
            "screening_status",
            "created_at",
            "screened_at",
        )
        read_only_fields = fields
