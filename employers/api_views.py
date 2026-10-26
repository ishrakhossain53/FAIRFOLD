"""API views for the employer company profile (REQ-FR-045, Complete Doc §C.12).

One view, two methods, no id in the path. The target is always
`request.user`, which is the ownership rule rather than a separate check that a
future edit could remove: employer B cannot address employer A's row because
there is nowhere in the request to put A's identifier.

`permission_classes` is explicit. The project default is `IsAuthenticated`, but
this resource is for the employer side only (`employer_hr` or
`employer_manager`). A candidate, interviewer or platform admin gets 403, not a
profile created for them.

The candidate/employer mutual-exclusion rule from REQ-FR-045 is enforced by
`accounts.services.assign_role` when a role is granted (batch 1.2), not by a
`role` column on this model. `IsEmployer` is therefore the correct gate here: it
reads the seeded group and a candidate account never reaches the view. A
manually corrupted account holding both groups would still pass `IsEmployer`;
that is the data-drift case `assign_role` exists to prevent, and the profile
endpoint is not a second place to repair roles.
"""

from __future__ import annotations

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCandidate, IsEmployer
from candidates.models import CandidateProfile
from core.pagination import PublicJobPagination
from employers.models import EmployerProfile
from employers.serializers import (
    EmployerProfileSerializer,
    EmployerProfileUpdateSerializer,
    JobCreateSerializer,
    JobPublicDetailSerializer,
    JobPublicFilterSerializer,
    JobPublicListSerializer,
    JobSerializer,
    JobUpdateSerializer,
)
from employers.services import (
    CONFLICT,
    change_job_status,
    delete_draft_job,
    job_status,
    public_job_queryset,
    record_job_audit,
)
from matching.models import Job
from matching.serializers import ApplicationCreatedSerializer
from matching.services import (
    ALREADY_APPLIED,
    JOB_NOT_OPEN,
    DuplicateApplication,
    JobNotOpen,
    apply_to_job,
)

# One sentence for both "you have not onboarded yet" and "the row is gone".
# A 404 here does not enumerate anything: the only row it could describe is the
# caller's own, and a distinguishable 403/404 would tell an account whether a
# given user has a profile.
NO_PROFILE_DETAIL = "No employer profile yet. Complete onboarding first."

# The candidate side of the same state conflict. A role grant without onboarding
# is a 409, not a 400: the request is well formed, the account is incomplete.
NO_CANDIDATE_PROFILE_DETAIL = "Complete your candidate profile before applying."

# A draft is not public (REQ-FR-025), so it answers exactly like an id that does
# not exist. Paused and closed jobs are named in JOB_NOT_OPEN because they were
# public; hiding that fact would make a just-closed job look deleted.
JOB_NOT_FOUND_DETAIL = "No such job."

# REQ-FR-045 says the profile is created during onboarding *with a company
# name*. A PATCH that would create a row without one is a 400 rather than an
# empty profile the public job board could later render as a nameless employer.
COMPANY_NAME_REQUIRED = {
    "company_name": ["A company name is required to create an employer profile."]
}

# The two draft-only rules from Arch Doc §4.3. One sentence each, because the
# client shows it verbatim and a 409 without a reason reads as a bug.
EDIT_DRAFT_ONLY = "Only a draft job can be edited."
DELETE_DRAFT_ONLY = "Only a draft job can be deleted."


def employer_profile_for(user) -> EmployerProfile:
    """Return the caller's profile or raise the API's 404."""
    profile = EmployerProfile.objects.filter(user=user).first()
    if profile is None:
        raise NotFound(NO_PROFILE_DETAIL)
    return profile


class EmployerMeView(APIView):
    """`GET`/`PATCH /api/v1/employers/me/` -- the caller's own company profile.

    `authentication_classes` is left at the project default. The browser uses
    session auth for the HTMX pages, and external clients use the JWT pair; both
    must work here. SessionAuthentication keeps enforcing CSRF on PATCH.
    """

    permission_classes = [IsEmployer]

    @extend_schema(
        responses={200: EmployerProfileSerializer},
        summary="Get the current employer's company profile",
        description=(
            "Employer group only. Returns the caller's company name, industry, "
            "company size and public-name disclosure preference. 404 until the "
            "employer has completed onboarding."
        ),
    )
    def get(self, request) -> Response:
        return Response(
            EmployerProfileSerializer(employer_profile_for(request.user)).data
        )

    @extend_schema(
        request=EmployerProfileUpdateSerializer,
        responses={200: EmployerProfileSerializer},
        summary="Update the current employer's company profile",
        description=(
            "Employer group only. Create-or-update: a non-empty PATCH carrying "
            "company_name creates the profile when the caller has none, which is "
            "the only documented way an API client can complete REQ-FR-045 (there "
            "is no POST). Only company_name, industry, company_size and "
            "show_company_name are writable; undeclared keys are ignored. An "
            "empty PATCH on an absent profile is 404."
        ),
    )
    def patch(self, request) -> Response:
        serializer = EmployerProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        profile = EmployerProfile.objects.filter(user=request.user).first()

        if profile is None:
            # A PATCH with no fields is not an onboarding action. Refusing it
            # keeps an accidental empty request from creating a row.
            if not data:
                raise NotFound(NO_PROFILE_DETAIL)
            if not (data.get("company_name") or "").strip():
                return Response(
                    COMPANY_NAME_REQUIRED, status=status.HTTP_400_BAD_REQUEST
                )
            # `get_or_create` rather than `create`: two concurrent first PATCHes
            # from the same employer must not turn the unique user constraint
            # into a 500. The loser gets the row the winner created.
            profile, _created = EmployerProfile.objects.get_or_create(user=request.user)

        # Named columns only. `save(update_fields=...)` means a future field added
        # to the serializer cannot silently write a column this endpoint does not
        # own. There is no `updated_at` column in §5.1, so only the sent fields
        # move.
        if data:
            for field, value in data.items():
                setattr(profile, field, value)
            profile.save(update_fields=list(data.keys()))

        return Response(EmployerProfileSerializer(profile).data)


class JobCreateView(APIView):
    """`POST /api/v1/jobs/` -- create a **draft** job (REQ-FR-025, batch 1.27).

    The caller must hold an employer role *and* have completed onboarding. A job
    belongs to `EmployerProfile`, and an employer without one has nothing to
    attach it to; `404` with the onboarding message is the same answer the
    profile endpoint gives, so a client handles one case rather than two.

    **Draft, always.** `status` is written here, not read from the body. REQ-FR-027
    makes activation a separate, audited action (batch 1.29); a create call that
    could publish would be a bypass of that.

    **One audit entry per creation.** The `AuditLogEntry` docstring in
    `core/models.py` and Complete Doc §C.4 name `"job.created"` as an example
    action, and a job is employer-visible state that later screens against
    candidate data. The entry carries the title and status -- employer content,
    never candidate PII -- and an id, so the trail says what was created, by whom,
    and when.

    `GET` on this path is deliberately absent: the jobs list is a separate batch,
    and a 405 is honest about that.
    """

    permission_classes = [IsEmployer]

    @extend_schema(
        request=JobCreateSerializer,
        responses={201: JobSerializer},
        summary="Create a draft job",
        description=(
            "Employer group only, and only after onboarding. Creates a draft; "
            "activation is POST /api/v1/jobs/{id}/activate/. Writable: title, "
            "description, responsibilities, requirements, nice_to_have, location, "
            "remote_allowed, experience_level. `status` and `employer` are not "
            "writable."
        ),
    )
    def post(self, request) -> Response:
        profile = employer_profile_for(request.user)

        serializer = JobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            job = serializer.save(employer=profile, status=Job.Status.DRAFT)
            record_job_audit(
                actor=request.user,
                action="job.created",
                job=job,
                details={"title": job.title, "status": job.status},
            )

        return Response(JobSerializer(job).data, status=status.HTTP_201_CREATED)


class JobPublicListView(APIView):
    """`GET /api/v1/jobs/public/` -- the public job board (REQ-FR-042, batch 1.31).

    **Anonymous on purpose.** `permission_classes` is `[AllowAny]` because the
    project default is `IsAuthenticated`, and an explicit override is the only
    documented way to open a route. Signed-in callers use the same endpoint: the
    board is not personalised, and no viewer identity is a ranking input
    (REQ-FR-053).

    **Only `active` jobs.** Drafts are unpublished text, `paused` has stopped
    accepting applications and `closed` is retired. Complete Doc §C.12 returns
    those as a 404 on the detail route and they are absent from this list.

    **Filters, newest first, paginated** (batch 1.32). `q`, `location`, `remote`
    and `experience_level` are validated by `JobPublicFilterSerializer` and
    applied by `public_job_queryset()`, the same function page #4 uses. An
    unknown level or a non-boolean `remote` is a 400 rather than an ignored
    parameter. `PublicJobPagination` caps `page_size` at §C.12's 50.

    The response never carries the employer row, only `employer_name` through
    `public_employer_name()`; the whitelist is in `JobPublicListSerializer`.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[JobPublicFilterSerializer],
        responses={200: JobPublicListSerializer(many=True)},
        summary="List active jobs on the public board",
        description=(
            "Public. Active jobs only, newest first, paginated (page_size up to "
            "50). Filters: q (title, description, skill name), location, remote, "
            "experience_level; they combine. The employer name is `null` unless "
            "that employer opted into candidate-facing disclosure (REQ-FR-042)."
        ),
    )
    def get(self, request) -> Response:
        filters = JobPublicFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)

        queryset = public_job_queryset(filters.validated_data)

        paginator = PublicJobPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = JobPublicListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class JobPublicDetailView(APIView):
    """`GET /api/v1/jobs/public/{id}/` -- public job detail (REQ-FR-042).

    **404 for every non-active status**, not 403 (Complete Doc §C.12). A 403
    would confirm that the id exists, turning the route into an enumeration
    oracle for drafts. The 404 body comes from `core.exceptions`, so it names
    neither the job nor its employer.

    The row is fetched with `select_related("employer")` for the same reason as
    the list: the serializer reads the employer's disclosure flag and name.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: JobPublicDetailSerializer},
        summary="Open an active job on the public board",
        description=(
            "Public. 404 unless the job is `active`, and 404 for an unknown "
            "id. The employer name is `null` unless that employer opted into "
            "candidate-facing disclosure (REQ-FR-042)."
        ),
    )
    def get(self, request, job_id) -> Response:
        # The same queryset as the list: active-only, employer joined and skills
        # prefetched in one query. A detail page with a hidden employer name must
        # not pay a different query shape than the card that led here.
        job = get_object_or_404(public_job_queryset({}), pk=job_id)
        return Response(JobPublicDetailSerializer(job).data)


def owned_job(profile: EmployerProfile, job_id) -> Job:
    """The caller's job, or the API's 404.

    Filtering by `employer` rather than fetching by id and comparing afterwards is
    the ownership rule: another employer's id is indistinguishable from an id that
    does not exist, so the response cannot be used to enumerate jobs.
    """
    return get_object_or_404(Job, pk=job_id, employer=profile)


def owned_job_for_update(profile: EmployerProfile, job_id) -> Job:
    """`owned_job` with a row lock. Call only inside `transaction.atomic()`.

    Two state changes racing on one job would otherwise both read `draft` and
    both write an audit entry; the lock makes the second request see the first
    request's status and take the no-op branch in `_JobStateView`.
    """
    return get_object_or_404(
        Job.objects.select_for_update(), pk=job_id, employer=profile
    )


class JobDetailView(APIView):
    """`GET`, `PATCH` and `DELETE` on `/api/v1/jobs/{id}/` (REQ-FR-026, batch 1.28).

    **`GET` is the read side of the edit form.** Complete Doc §C.12 declares it,
    and a client that can `PATCH` a resource but not read it would have to keep
    its own copy of every field it wants to edit.

    **`PATCH` is draft-only** (Arch Doc §4.3, rule 3). Editing a live job changes
    the text candidates applied to without a revision trail, so an active, paused
    or closed job answers `409` with the sentence in `EDIT_DRAFT_ONLY`; the way to
    change a published job is to close it and post a new one. `status` and
    `employer` are not in the serializer, so neither can be written here.

    **`DELETE` is draft-only and hard** (rule 4). Every §5.1 reference to `jobs`
    cascades, so deleting a published job would destroy its applications and
    interviews. A draft has none by construction.

    Both writes record one entry inside the same transaction as the change, so a
    rolled-back write leaves no audit entry claiming it happened.
    """

    permission_classes = [IsEmployer]

    @extend_schema(responses={200: JobSerializer}, summary="Get a job")
    def get(self, request, job_id) -> Response:
        profile = employer_profile_for(request.user)
        return Response(JobSerializer(owned_job(profile, job_id)).data)

    @extend_schema(
        request=JobUpdateSerializer,
        responses={200: JobSerializer},
        summary="Update a draft job",
        description=(
            "Employer group only, owner only. Draft status only: any other "
            "status is 409. Writable: title, description, responsibilities, "
            "requirements, nice_to_have, location, remote_allowed, "
            "experience_level. `status` and `employer` are not writable."
        ),
    )
    def patch(self, request, job_id) -> Response:
        profile = employer_profile_for(request.user)

        with transaction.atomic():
            job = owned_job_for_update(profile, job_id)
            if job.status != Job.Status.DRAFT:
                return Response(
                    {"detail": EDIT_DRAFT_ONLY}, status=status.HTTP_409_CONFLICT
                )

            serializer = JobUpdateSerializer(job, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            # Field *names*, never values: `job.updated` must not become a second
            # copy of employer-entered text in an append-only table. A PATCH that
            # changes nothing (an auto-save firing on an untouched form) is a
            # no-op and does not add an entry.
            changed = sorted(
                field
                for field, value in serializer.validated_data.items()
                if getattr(job, field) != value
            )
            if changed:
                serializer.save()
                record_job_audit(
                    actor=request.user,
                    action="job.updated",
                    job=job,
                    details={"changed": changed},
                )

        return Response(JobSerializer(job).data)

    @extend_schema(
        responses={204: None},
        summary="Delete a draft job",
        description="Employer group only, owner only. Draft status only: any other status is 409.",
    )
    def delete(self, request, job_id) -> Response:
        profile = employer_profile_for(request.user)

        try:
            outcome, _ = delete_draft_job(
                job_id=job_id, employer=profile, actor=request.user
            )
        except Job.DoesNotExist as exc:
            raise Http404 from exc

        if outcome == CONFLICT:
            return Response(
                {"detail": DELETE_DRAFT_ONLY}, status=status.HTTP_409_CONFLICT
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class _JobStateView(APIView):
    """Shared implementation of the three Arch Doc §4.3 state actions.

    The subclasses below differ only in data, so the transition check, the lock,
    the no-op rule and the audit entry are written once. `status` is the only
    field written: the action endpoints cannot be used to smuggle a content edit
    past the draft-only rule on `PATCH`.
    """

    permission_classes = [IsEmployer]

    #: The status this action writes.
    to_status: str = ""
    #: Statuses this action may leave. Anything else is a 409.
    allowed_from: tuple[str, ...] = ()
    #: Audit action recorded on an effective change.
    audit_action: str = ""
    #: Sentence returned when the transition is not in the §4.3 matrix.
    conflict_detail: str = ""

    def post(self, request, job_id) -> Response:
        profile = employer_profile_for(request.user)

        try:
            # One implementation of the §4.3 matrix, shared with the employer
            # portal (`employers.services`). The service locks the row, applies
            # the no-op rule and writes the audit entry.
            outcome, job = change_job_status(
                job_id=job_id,
                employer=profile,
                to_status=self.to_status,
                allowed_from=self.allowed_from,
                audit_action=self.audit_action,
                actor=request.user,
            )
        except Job.DoesNotExist as exc:
            raise Http404 from exc

        if outcome == CONFLICT:
            return Response(
                {"detail": self.conflict_detail},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(JobSerializer(job).data)


@extend_schema(
    request=None,
    responses={200: JobSerializer},
    summary="Activate a draft or paused job",
    description=(
        "REQ-FR-027. draft|paused -> active; activating an active job is a no-op. "
        "A closed job cannot be reactivated (409)."
    ),
)
class JobActivateView(_JobStateView):
    """`POST /api/v1/jobs/{id}/activate/` -- publish, or resume a paused job.

    Resume reuses this endpoint rather than adding a fourth URL: the action is
    "make this job live again", and the §4.3 matrix allows it from `draft` and
    `paused`. A closed job is terminal -- employers who want to rehire post a new
    job, which keeps the old job's applications attached to the terms candidates
    actually applied to.
    """

    to_status = job_status(Job.Status.ACTIVE)
    allowed_from = (job_status(Job.Status.DRAFT), job_status(Job.Status.PAUSED))
    audit_action = "job.activated"
    conflict_detail = "A closed job cannot be reactivated. Create a new job instead."


@extend_schema(
    request=None,
    responses={200: JobSerializer},
    summary="Pause an active job",
    description="active -> paused; pausing a paused job is a no-op. Any other status is 409.",
)
class JobPauseView(_JobStateView):
    """`POST /api/v1/jobs/{id}/pause/` -- stop accepting applications.

    The row, its applications and its audit trail are untouched (rule 5); only
    visibility and the ability to apply stop. A draft was never published, so
    there is nothing to pause and the answer is 409.
    """

    to_status = job_status(Job.Status.PAUSED)
    allowed_from = (job_status(Job.Status.ACTIVE),)
    audit_action = "job.paused"
    conflict_detail = "Only an active job can be paused."


@extend_schema(
    request=None,
    responses={200: JobSerializer},
    summary="Close a job",
    description=(
        "active|paused -> closed; closing a closed job is a no-op. A draft is "
        "deleted rather than closed (409)."
    ),
)
class JobCloseView(_JobStateView):
    """`POST /api/v1/jobs/{id}/close/` -- retire the posting for good.

    Closing is the documented way to take a published job down (rule 3): the row
    and its applications stay for the audit trail and for analytics. Drafts are
    deleted instead, because they have no history to keep.
    """

    to_status = job_status(Job.Status.CLOSED)
    allowed_from = (job_status(Job.Status.ACTIVE), job_status(Job.Status.PAUSED))
    audit_action = "job.closed"
    conflict_detail = "Only an active or paused job can be closed."


@extend_schema(
    request=None,
    responses={201: ApplicationCreatedSerializer},
    summary="Apply to an active job",
    description=(
        "Candidate group only. Creates one `applied` application for the "
        "caller's candidate profile. 404 for an unknown or draft job; 409 for a "
        "paused/closed job, a duplicate application, or a caller with no "
        "candidate profile. The request has no body and the response carries no "
        "candidate identity."
    ),
)
class JobApplyView(APIView):
    """`POST /api/v1/jobs/{id}/apply/` -- REQ-FR-022 (batch 1.36).

    **The applicant is `request.user`, structurally.** There is no candidate id
    in the path or the body, so a caller cannot apply on another candidate's
    behalf; an undeclared `candidate` key is ignored by DRF. This is the same
    ownership rule as `/api/v1/employers/me/`, expressed by the absence of a
    parameter rather than by a comparison a later edit could drop.

    **A draft is a 404, not a 409.** A draft was never public (REQ-FR-025), so a
    distinguishable answer would confirm that an employer is preparing a posting.
    Paused and closed jobs were public; their 409 says why they cannot be applied
    to instead of pretending they vanished.

    **No resume is required.** REQ-FR-022 names an authenticated candidate and an
    active job, and §5.1 `applications` has no resume foreign key. Page #30's
    resume picker is a later UI decision, not a precondition this batch may
    invent.

    **Notifications are not sent here.** REQ-FR-022 says the candidate and the
    employer are notified; batch 1.43 owns the notification model and delivery,
    and the call site is left out rather than faked.
    """

    permission_classes = [IsCandidate]

    def post(self, request, job_id) -> Response:
        job = get_object_or_404(Job, pk=job_id)
        if job.status == Job.Status.DRAFT:
            raise NotFound(JOB_NOT_FOUND_DETAIL)

        profile = CandidateProfile.objects.filter(user=request.user).first()
        if profile is None:
            return Response(
                {"detail": NO_CANDIDATE_PROFILE_DETAIL},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            application = apply_to_job(candidate=profile, job=job)
        except JobNotOpen:
            return Response(
                {"detail": JOB_NOT_OPEN},
                status=status.HTTP_409_CONFLICT,
            )
        except DuplicateApplication:
            return Response(
                {"detail": ALREADY_APPLIED},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            ApplicationCreatedSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )
