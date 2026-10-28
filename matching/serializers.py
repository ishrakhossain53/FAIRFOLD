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

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from candidates.services import candidate_for_employer
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


# ---------------------------------------------------------------------------
# Employer application inbox (REQ-FR-029, REQ-FR-054, batch 1.40)
# ---------------------------------------------------------------------------


class EmployerApplicationFilterSerializer(serializers.Serializer):
    """The query parameters of `GET /api/v1/jobs/{id}/applications/`.

    Complete Doc §C.12 declares exactly `?status=`, and names `not_matched` as
    the value that shows the applications the hard filter excluded. That is the
    whole filter in Phase 1: ranking and the score range arrive with 2.19/2.20,
    and a parameter this batch accepted but ignored would show a caller a list
    that does not match the URL.

    **Validation, not silent coercion.** An unknown status is a 400 for the same
    reason `JobPublicFilterSerializer` refuses an unknown experience level: a
    filter that quietly does nothing is worse than an error. A blank value means
    "no filter", because a page's "All" control submits an empty string.
    """

    status = serializers.ChoiceField(
        choices=Application.Status.choices,
        required=False,
        allow_blank=True,
    )


class EmployerApplicationListSerializer(serializers.ModelSerializer):
    """One application in an employer's inbox (REQ-FR-029, batch 1.40).

    **Identity is the per-employer alias, never the candidate.** The nested
    `candidate` object is `candidates.services.candidate_for_employer()`, the
    whitelist batch 1.35 built for exactly this surface: alias, title, location,
    remote preference and skill names. There is no name, photo, contact detail,
    internal candidate UUID or `visibility_tier` in it, and this serializer does
    not fall back to the model row for any of them. The employer's own job is the
    only thing that grants access to the row, so the alias is stable across every
    job that employer posts (REQ-FR-054).

    **`match_score` and `screening_status` are declared and empty in Phase 1.**
    Ranking is 2.19/2.20 and the score column is written by screening; declaring
    them now keeps the contract stable instead of breaking every client when
    Phase 2 lands -- the same reasoning batch 1.38 used for the candidate tracker.

    **Absent on purpose.**

    * `not_matched_reason` and `filter_rules_version`: Gap G3 requires them on the
      employer's list, but the `not_matched` surface is batch 2.18 and its copy
      has not been designed yet. The row is still returned here, so a filtered
      candidate is never hidden.
    * `match_rationale`: `ai.citation.load_rationale()` is the only reader and the
      payload is 2.21-2.25's contract (page #41, batch 2.29).
    * `decision_override*` and `decided_by`: REQ-FR-052's decision path, batch 1.41.
    * `assessment_gate_status`: REQ-FR-051's gate panel, a later batch.

    `job` is absent: the route addresses one job, so the key would repeat what the
    caller already sent.
    """

    candidate = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Application
        fields = (
            "id",
            "candidate",
            "status",
            "status_display",
            "match_score",
            "screening_status",
            "created_at",
        )
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_candidate(self, application: Application) -> dict[str, object]:
        """The employer-facing whitelist, with the page's prefetched alias.

        The view may pass `context["aliases"]` -- one query for the whole page.
        A candidate with no alias yet (first visit to this inbox) falls through
        to `alias_for()`, which creates it once under concurrency (REQ-FR-054).

        `@extend_schema_field(OpenApiTypes.OBJECT)` is the honest schema: the
        shape is defined by `candidate_for_employer()`, and declaring a second
        copy of the five fields here would be a place for the two to drift.
        """
        employer = self.context["employer"]
        aliases = self.context.get("aliases") or {}
        return candidate_for_employer(
            employer,
            application.candidate,
            alias=aliases.get(application.candidate_id),
        )


class ApplicationDecisionSerializer(serializers.Serializer):
    """The body of `POST /api/v1/applications/{id}/shortlist|reject/` (batch 1.41).

    **`reason` is accepted now and mandatory for overrides in Phase 2.**
    Complete Doc §C.12 writes both actions as `{reason?}`. REQ-FR-052 makes the
    reason required only when the decision goes *against* the employer's ranking
    cut-off, which does not exist until batch 2.19 ranks applications, so in
    Phase 1 an empty body is a complete request.

    **Nothing is written to a column by this batch.** There is no
    "decision reason" column in Arch Doc §5.1; `decision_override_reason` is
    specifically the reason for an override, and the database refuses a non-empty
    one while `decision_override` is `False` (`chk_override_has_reason`). Storing
    a Phase-1 reason there would either raise or claim an override that never
    happened. The override path that persists it is Phase 2.

    **No `status` field.** The action decides the target status; a body that could
    name one would be the bare `PATCH applications/{id}/` that Complete Doc §C.12
    rules out. Undeclared keys are ignored by DRF, exactly as on the job
    endpoints -- asserted by a test rather than assumed.
    """

    reason = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=True
    )
