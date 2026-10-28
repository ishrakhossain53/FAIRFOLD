"""API serializers for the employer company profile and job postings.

Complete Doc §C.12 lists exactly two operations on the company-profile resource:

    GET    /api/v1/employers/me/    # Get employer profile
    PATCH  /api/v1/employers/me/    # Update employer profile

There is no `POST` and no id in the path. The target is always `request.user`,
so the ownership rule is structural: a caller cannot name another employer's
row.

**Why PATCH creates the row when it is missing.** The endpoint list has no
creation verb, yet REQ-FR-045 requires a registered employer to end up with a
profile during onboarding. A non-empty PATCH carrying `company_name` is that
creation path. An empty PATCH is not an onboarding action and stays a 404.

**The response is a whitelist.** It names the columns this resource owns:
`company_name`, `industry`, `company_size` (REQ-FR-045) and
`show_company_name` (REQ-FR-042). The row `id`, the owner, `created_at` and the
Phase-5 billing columns are deliberately absent. Billing is stored from the
DDL but has no documented behaviour yet, and the row id is not needed on a
`/me/` route.

**Encryption.** The DDL marks `company_name` ENCRYPTED. Decision D-5 is still
open, so the column remains plain text, following `User.first_name` and
`CandidateProfile.location`. The serializer does not pretend otherwise.
"""

from __future__ import annotations

from rest_framework import serializers

from employers.models import EmployerProfile
from matching.models import Job


class EmployerProfileSerializer(serializers.ModelSerializer):
    """The `GET`/`PATCH /api/v1/employers/me/` response body.

    Exactly the four documented onboarding columns. The owner, timestamps and
    billing columns stay out: the route is `/me/`, so the caller already knows
    which profile it is, and billing is Phase 5 with no API contract in §C.12.
    """

    class Meta:
        model = EmployerProfile
        fields = (
            "company_name",
            "industry",
            "company_size",
            "show_company_name",
        )
        read_only_fields = fields


class EmployerProfileUpdateSerializer(serializers.Serializer):
    """The `PATCH /api/v1/employers/me/` body.

    All four fields are optional because the verb is PATCH. Only these keys are
    declared; DRF ignores undeclared keys, which is the whitelist: a body
    carrying `user`, `billing_plan`, `billing_cycle`, `stripe_customer_id` or
    `created_at` succeeds while changing none of them.

    `company_name` has no `max_length` because the DDL declares TEXT. The
    Complete Doc's abridged model sketch says 300, but Arch Doc §5.1 is
    canonical and sets no width. `company_size` has no minimum because the DDL
    has no CHECK and the model docstring deliberately does not narrow it to a
    positive-only value.

    Creation requires a non-blank `company_name`; that rule lives in the view,
    because the serializer does not know whether the caller has a profile yet.
    """

    company_name = serializers.CharField(required=False, allow_blank=True)
    industry = serializers.CharField(
        max_length=EmployerProfile._meta.get_field("industry").max_length,
        required=False,
        allow_blank=True,
    )
    company_size = serializers.IntegerField(required=False, allow_null=True)
    show_company_name = serializers.BooleanField(required=False)


# ---------------------------------------------------------------------------
# Jobs (REQ-FR-025, Complete Doc §C.12 `POST /api/v1/jobs/`, batch 1.27)
# ---------------------------------------------------------------------------


class JobCreateSerializer(serializers.ModelSerializer):
    """The `POST /api/v1/jobs/` body.

    **A creation endpoint produces a draft or nothing.** `status` is not a field
    here: publishing is `POST /api/v1/jobs/{id}/activate/` (REQ-FR-027, batch
    1.29), and a create body that could set `status="active"` would be a second,
    unaudited activation path. The view writes `draft` explicitly.

    **`employer` is not a field either.** It comes from the caller's profile, so
    one employer cannot post a job under another's name. This is the same
    structural ownership rule as `EmployerProfileSerializer`: there is nowhere in
    the request to put a different owner.

    **Not writable yet, and why.** `screening_questions` is filled by the AI
    suggestion step in REQ-FR-025 (Phase 2) and its element shape is not
    specified in any document, so accepting a list here would invent a contract.
    `screening_config` is the Gap-G3 rule set with its own version bump; writing
    it through creation would bypass the versioning that makes a `not_matched`
    result replayable. `cost_estimate`, `ai_model_used` and the embedding are
    produced by later batches. All keep their model defaults.

    `description` is optional because the DDL allows a job with no description
    and page #36 auto-saves a draft while the employer is still typing.
    """

    class Meta:
        model = Job
        fields = (
            "title",
            "description",
            "responsibilities",
            "requirements",
            "nice_to_have",
            "location",
            "remote_allowed",
            "experience_level",
        )


class JobSerializer(serializers.ModelSerializer):
    """The `POST /api/v1/jobs/` response body.

    The `id` is included because the client needs it for `PATCH` and
    `activate/`; the owner is not, because the caller is the owner. Timestamps
    let the jobs list (page #35) show "last activity" without a second request.
    """

    class Meta:
        model = Job
        fields = (
            "id",
            "title",
            "description",
            "responsibilities",
            "requirements",
            "nice_to_have",
            "location",
            "remote_allowed",
            "experience_level",
            "status",
            "screening_questions",
            "screening_config_version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class JobUpdateSerializer(JobCreateSerializer):
    """The `PATCH /api/v1/jobs/{id}/` body (REQ-FR-026, batch 1.28).

    The writable set is the creation set, deliberately: a field an employer can
    type into a draft is a field they can correct in it, and a field the create
    path refuses (`status`, `employer`, `screening_config`) is not writable here
    either. The view applies it with `partial=True`, so page #36's auto-save can
    send one changed field at a time.

    **`status` still cannot be written.** The Arch Doc §4.3 lifecycle table is
    enforced by the action endpoints; a `PATCH` that could set `active` would be
    an unaudited publishing path, and one that could set `closed` would skip the
    retention rule.
    """


# ---------------------------------------------------------------------------
# Public job board (REQ-FR-042, Complete Doc §C.12 `GET /api/v1/jobs/public/`,
# batch 1.31)
# ---------------------------------------------------------------------------


def public_employer_name(employer: EmployerProfile) -> str | None:
    """The only employer identity a public job response may carry.

    REQ-FR-042: the name is withheld until the employer opts in, and the
    response then carries `null` rather than omitting the key (Complete Doc
    §C.12). An opted-in employer with an empty `company_name` also yields
    `null`, because there is no name to show and `""` would render as a blank
    company line in the UI.

    Nothing else about the employer is returned. `industry` and `company_size`
    are not covered by the requirement and, together with a job title, would
    identify a small company as effectively as its name.
    """
    if not employer.show_company_name:
        return None
    return employer.company_name or None


class JobPublicListSerializer(serializers.ModelSerializer):
    """One card on the public job board (REQ-FR-042, batch 1.31).

    **A whitelist, not a `ModelSerializer` default.** The full `Job` row also
    holds `screening_config`, `screening_questions`, `ai_model_used` and
    `cost_estimate`; none of those is candidate- or guest-facing, and a default
    field set would ship them silently. The list also omits the four long-text
    columns, because a page of twenty cards does not need every description.

    `employer` is not a field at all. The only employer value is
    `employer_name`, and it goes through `public_employer_name()`.

    **`skills` is names only.** Batch 1.32 added the join table so REQ-FR-042
    can search skills and so the card can render the chips design.md S04 draws.
    The ids, the `required` flag and the taxonomy row stay server-side: the
    public board needs a list of strings, not a second resource.
    """

    employer_name = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = (
            "id",
            "title",
            "location",
            "remote_allowed",
            "experience_level",
            "employer_name",
            "skills",
            "created_at",
        )
        read_only_fields = fields

    def get_employer_name(self, job: Job) -> str | None:
        return public_employer_name(job.employer)

    def get_skills(self, job: Job) -> list[str]:
        # Sorted in Python so the card is deterministic whatever order the join
        # rows come back in; the view prefetches `job_skills__skill`, so this is
        # not a query per job.
        return sorted(
            job_skill.skill.canonical_name for job_skill in job.job_skills.all()
        )


class JobPublicDetailSerializer(JobPublicListSerializer):
    """The public job detail body (REQ-FR-042, batch 1.31).

    The card fields plus the four Markdown source fields and `updated_at`.
    `status` is deliberately absent: the route only answers for `active` jobs,
    so the field would be a constant. The serializer is read-only by
    construction; there is no public write path.
    """

    class Meta:
        model = Job
        # Repeated rather than concatenated from the parent's `Meta.fields`:
        # mypy infers a fixed-length tuple for the parent and rejects a longer
        # assignment to the inherited attribute.
        fields = (
            "id",
            "title",
            "location",
            "remote_allowed",
            "experience_level",
            "employer_name",
            "skills",
            "created_at",
            "description",
            "responsibilities",
            "requirements",
            "nice_to_have",
            "updated_at",
        )
        read_only_fields = fields


class JobPublicFilterSerializer(serializers.Serializer):
    """The query parameters of `GET /api/v1/jobs/public/` (REQ-FR-042).

    Complete Doc §C.12 declares exactly `q`, `location`, `remote`,
    `experience_level`, `page` and `page_size`; `page`/`page_size` belong to the
    paginator, so only the four filters are declared here.

    **Validation rather than silent coercion.** An unknown `experience_level` or
    a `remote` that is not a boolean is a 400, not an ignored parameter: a
    filter that silently does nothing shows the caller a board that does not
    match the URL, which is worse than an error. `q` and `location` are trimmed
    by DRF's `CharField`, and an empty string means "no filter".

    `remote` is a tri-state: absent means "either", `true` means remote jobs
    only and `false` means on-site/hybrid only. A two-valued checkbox in the UI
    sends `true` when ticked and omits the key otherwise.
    """

    q = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    # `default=None` is load-bearing. DRF's HTML-input handling substitutes its
    # `default_empty_html` (False) for an absent BooleanField, which would turn
    # "no remote filter" into "on-site only" for every request without the key.
    remote = serializers.BooleanField(required=False, allow_null=True, default=None)
    experience_level = serializers.ChoiceField(
        choices=Job.ExperienceLevel.choices,
        required=False,
        # The page's "Any" radio submits an empty value; that means "no filter",
        # exactly as a blank `q` or `location` does.
        allow_blank=True,
    )
