"""API views for the candidate profile (REQ-FR-009, Complete Doc §C.12).

One view, two methods, no id in the path. The target is always
`request.user`, which is the ownership rule rather than a separate check that a
future edit could remove: candidate B cannot address candidate A's row because
there is nowhere in the request to put A's identifier.
"""

from __future__ import annotations

from celery.exceptions import CeleryError
from django.conf import settings
from drf_spectacular.utils import extend_schema
from kombu.exceptions import OperationalError
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCandidate
from candidates.models import CandidateProfile, CandidateResume
from candidates.serializers import (
    CandidateProfileSerializer,
    CandidateProfileUpdateSerializer,
    ResumeStatusSerializer,
    ResumeSummarySerializer,
    ResumeUploadRequestSerializer,
    ResumeUploadResponseSerializer,
)
from candidates.services import delete_resume
from candidates.tasks import scan_resume
from candidates.uploads import (
    ResumeUploadUnavailable,
    UploadMissing,
    UploadProblem,
    build_resume_key,
    inspect_upload,
    mark_rejected,
    presign_resume_put,
)
from core.pagination import StandardPagination
from matching.models import Application
from matching.serializers import CandidateApplicationSerializer

# One sentence for both "you have not onboarded yet" and "the row is gone".
# A 404 here does not enumerate anything: the only row it could describe is the
# caller's own, and a distinguishable 403/404 would tell an employer whether a
# given account has a profile.
NO_PROFILE_DETAIL = "No candidate profile yet. Complete onboarding first."

# One sentence for both "no such row" and "not yours". A distinguishable answer
# would let one candidate probe another candidate's application ids.
NO_APPLICATION_DETAIL = "Application not found."

# One sentence for both "no such row" and "not yours". A distinguishable answer
# would let one candidate probe another candidate's resume ids.
NO_RESUME_DETAIL = "Resume not found."


def _profile_for(user) -> CandidateProfile:
    """Return the caller's profile or raise the API's 404."""
    profile = CandidateProfile.objects.filter(user=user).first()
    if profile is None:
        raise NotFound(NO_PROFILE_DETAIL)
    return profile


class CandidateMeView(APIView):
    """`GET`/`PATCH /api/v1/candidates/me/` -- the caller's own profile.

    `permission_classes` is set explicitly. The project default is
    `IsAuthenticated`, but this resource is for the `candidate` group only: an
    authenticated employer or platform admin must get 403, not a profile created
    for them. `IsCandidate` is the same permission class the rest of the role
    surface uses (D-2), so the answer comes from the seeded group and not from a
    new role column.

    `authentication_classes` is left at the project default. The browser uses
    session auth for the HTMX pages, and external clients use the JWT pair; both
    must work here. SessionAuthentication keeps enforcing CSRF on PATCH.
    """

    permission_classes = [IsCandidate]

    @extend_schema(
        responses={200: CandidateProfileSerializer},
        summary="Get the current candidate's profile",
        description=(
            "Candidate group only. Returns the caller's title, bio, location and "
            "remote preference. 404 until the candidate has completed onboarding."
        ),
    )
    def get(self, request) -> Response:
        return Response(CandidateProfileSerializer(_profile_for(request.user)).data)

    @extend_schema(
        request=CandidateProfileUpdateSerializer,
        responses={200: CandidateProfileSerializer},
        summary="Update the current candidate's profile",
        description=(
            "Candidate group only. Create-or-update: a non-empty PATCH creates "
            "the profile when the caller has none, which is the only documented "
            "way an API client can complete REQ-FR-009 (there is no POST). Only "
            "title, bio, location and remote_ok are writable; undeclared keys "
            "are ignored. An empty PATCH on an absent profile is 404."
        ),
    )
    def patch(self, request) -> Response:
        serializer = CandidateProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = CandidateProfile.objects.filter(user=request.user).first()
        if profile is None:
            # A PATCH with no fields is not an onboarding action. Refusing it
            # keeps an accidental empty request from creating a row; a PATCH
            # that carries at least one profile field is the documented way to
            # create the profile (there is no POST in §C.12).
            if not serializer.validated_data:
                raise NotFound(NO_PROFILE_DETAIL)
            # `get_or_create` rather than `create`: two concurrent first PATCHes
            # from the same candidate must not turn the unique user constraint
            # into a 500. The loser gets the row the winner created.
            profile, _created = CandidateProfile.objects.get_or_create(
                user=request.user
            )

        # Named columns only. `save(update_fields=...)` means a future field added
        # to the serializer cannot silently write a column this endpoint does not
        # own, and it keeps `updated_at` moving without a full-row write.
        if serializer.validated_data:
            for field, value in serializer.validated_data.items():
                setattr(profile, field, value)
            profile.save(
                update_fields=[*serializer.validated_data.keys(), "updated_at"]
            )

        return Response(CandidateProfileSerializer(profile).data)


class CandidateResumeListView(APIView):
    """`GET`/`POST /api/v1/candidates/resumes/` -- the caller's own resumes.

    Two verbs, one path. Complete Doc §C.12 declares `GET` (list) and `POST`
    (upload), and both are owner-scoped for the same structural reason: the
    candidate comes from `request.user`, never from the body or the path, so
    there is nowhere in a list request to name someone else's profile.

    **`GET` returns metadata only.** See `ResumeSummarySerializer`: no storage
    key, no URL, no extracted text. A resume that was never completed is still
    listed -- `pending` is a real state the owner must be able to see and retry
    (batch 1.20 leaves the row `pending` when the bytes have not landed), and
    hiding it would make a failed upload vanish silently.

    **A candidate with no profile gets 404, not an empty list.** The same
    `_profile_for` answer as `/me/`: a profile is the onboarding step that
    precedes any resume (REQ-FR-009), so "no profile yet" and "no resumes yet"
    are different facts and the client is told which one it hit.

    **`POST` issues a presigned upload URL.** REQ-FR-010: the browser uploads
    directly to object storage and Django stores only the key. This view
    therefore validates the *declaration*, writes the `pending` row, and signs a
    PUT; it never sees the file.

    **Order matters.** Validate, then create the row, then sign. If signing
    fails the row is deleted: no URL was issued, so no bytes can arrive, and a
    `pending` row would be an upload the candidate cannot finish or retry.

    **The caller cannot choose the key or the owner.** There is no id in the
    path, no `candidate` field in the body and no `file_key` field: the profile
    comes from `request.user` and the key from `build_resume_key`. Unknown keys
    in the body are ignored by the serializer, as on the profile endpoint.

    `permission_classes` is explicit. The project default is `IsAuthenticated`,
    but only the `candidate` group owns resumes; an employer gets 403, not a row.
    """

    permission_classes = [IsCandidate]

    @extend_schema(
        responses={200: ResumeSummarySerializer(many=True)},
        summary="List the current candidate's resumes",
        description=(
            "Candidate group only. Newest first, paginated (page_size up to 100). "
            "Returns metadata and scan status only: never the storage key, a "
            "download URL or resume text. 404 until the candidate has a profile."
        ),
    )
    def get(self, request) -> Response:
        profile = _profile_for(request.user)
        queryset = CandidateResume.objects.filter(candidate=profile)

        # `StandardPagination` is applied by DRF's generic views, not by an
        # APIView, so it is driven by hand here. The class is the project one
        # rather than a local page size: it carries the 100-row ceiling that
        # keeps a caller from asking for everything at once.
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ResumeSummarySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=ResumeUploadRequestSerializer,
        responses={201: ResumeUploadResponseSerializer},
        summary="Start a resume upload (presigned PUT)",
        description=(
            "Candidate group only. Validates the declared content type against "
            "RESUME_ALLOWED_MIME_TYPES and the size against MAX_UPLOAD_SIZE_BYTES, "
            "creates a pending resume with a server-generated key, and returns a "
            "short-lived presigned PUT URL. The file itself never touches Django."
        ),
    )
    def post(self, request) -> Response:
        serializer = ResumeUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        profile = _profile_for(request.user)
        content_type = data["content_type"]
        expires_in = settings.RESUME_PRESIGN_EXPIRES_SECONDS

        resume = CandidateResume.objects.create(
            candidate=profile,
            file_key=build_resume_key(profile.id, content_type),
            original_filename=data["original_filename"],
            file_size=data["file_size"],
            mime_type=content_type,
            status=CandidateResume.Status.PENDING,
        )

        try:
            url = presign_resume_put(
                key=resume.file_key,
                content_type=content_type,
                expires_in=expires_in,
            )
        except ResumeUploadUnavailable:
            resume.delete()
            return Response(
                {"detail": "Object storage is unavailable; no upload URL was issued."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        body = {
            "id": resume.id,
            "status": resume.status,
            "upload": {
                "url": url,
                "method": "PUT",
                "headers": {"Content-Type": content_type},
                "expires_in": expires_in,
            },
        }
        return Response(
            ResumeUploadResponseSerializer(body).data,
            status=status.HTTP_201_CREATED,
        )


class CandidateResumeCompleteView(APIView):
    """`POST /api/v1/candidates/resumes/{id}/complete/` -- finish an upload.

    The presigned PUT only proves the browser *can* write. This endpoint is the
    point at which the server looks at what actually arrived: the object's real
    size, and its type as reported by libmagic (REQ-SEC-012), not the type the
    browser declared when the URL was signed. A file that fails either check is
    `rejected` with a reason and its bytes are discarded; it never reaches the
    scanner, because there is nothing to learn from scanning a file we will not
    keep.

    A file that passes is moved to `scanning` and the Celery task is queued. The
    response is `202`, not `200`: the scan is asynchronous and the resume is not
    `clean` yet. If the broker is unavailable the row goes back to `pending`, so
    the client can retry rather than being stuck in `scanning` forever.

    **Idempotent for settled states.** Re-posting after `scanning`, `clean` or
    `rejected` returns the current row and queues nothing, so a retried request
    cannot overwrite a malware verdict or start a second scan. The Phase 2
    states (`processing`/`extracted`/`embedded`/`failed`) answer `409`: they are
    not upload states, and re-running the upload checks on them would be wrong.

    Ownership is part of the lookup (`candidate__user=request.user`), so another
    candidate's id is indistinguishable from one that does not exist.
    """

    permission_classes = [IsCandidate]

    @extend_schema(
        request=None,
        responses={200: ResumeStatusSerializer, 202: ResumeStatusSerializer},
        summary="Finish a resume upload (size/MIME check, then scan)",
        description=(
            "Candidate group only. Verifies the stored object's size and "
            "libmagic-detected type, rejects a file that fails either check, and "
            "otherwise queues the ClamAV scan and returns 202 with status "
            "'scanning'. Re-posting a settled resume returns its current state."
        ),
    )
    def post(self, request, pk) -> Response:
        resume = CandidateResume.objects.filter(
            pk=pk, candidate__user=request.user
        ).first()
        if resume is None:
            raise NotFound(NO_RESUME_DETAIL)

        # Already settled or in flight: report, do not rescan.
        if resume.status in {
            CandidateResume.Status.SCANNING,
            CandidateResume.Status.CLEAN,
            CandidateResume.Status.REJECTED,
        }:
            return Response(ResumeStatusSerializer(resume).data)

        # Phase 2 owns these states. Refusing is clearer than pretending this
        # endpoint can restart extraction by re-checking the upload.
        if resume.status != CandidateResume.Status.PENDING:
            return Response(
                {
                    "detail": "This resume has already been processed.",
                    "status": resume.status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            _size, sniffed = inspect_upload(
                resume.file_key,
                max_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
            )
        except UploadMissing:
            # The PUT has not landed yet. Keep the row pending so the client can
            # retry completion after the upload finishes.
            return Response(
                {
                    "detail": (
                        "No uploaded file found for this resume. Upload it and "
                        "try again."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        except UploadProblem as exc:
            mark_rejected(resume, str(exc))
            return Response(ResumeStatusSerializer(resume).data)
        except ResumeUploadUnavailable:
            return Response(
                {"detail": "Object storage is unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        allowed = settings.RESUME_ALLOWED_MIME_TYPES
        if sniffed not in allowed:
            mark_rejected(resume, f"file type {sniffed!r} is not allowed")
            return Response(ResumeStatusSerializer(resume).data)
        if sniffed != resume.mime_type:
            # The declared type was signed into the URL, so a mismatch means the
            # client PUT something other than what it asked to upload.
            mark_rejected(
                resume,
                f"declared {resume.mime_type!r} but the file is {sniffed!r}",
            )
            return Response(ResumeStatusSerializer(resume).data)

        resume.status = CandidateResume.Status.SCANNING
        resume.status_reason = ""
        resume.save(update_fields=["status", "status_reason"])

        try:
            scan_resume.delay(str(resume.id))
        except (CeleryError, OperationalError):
            # No worker accepted the task. Revert so completion can be retried;
            # `scanning` with no task would never settle.
            resume.status = CandidateResume.Status.PENDING
            resume.save(update_fields=["status"])
            return Response(
                {"detail": "The scan could not be queued. Try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            ResumeStatusSerializer(resume).data,
            status=status.HTTP_202_ACCEPTED,
        )


class CandidateResumeDetailView(APIView):
    """`GET`/`DELETE /api/v1/candidates/resumes/{id}/` -- one of the caller's rows.

    Same body as a list entry on `GET`, so a client that has an id from the list
    does not need a second shape. `file_key` is not in it (see
    `ResumeSummarySerializer`): the detail view is where a storage key would be
    most tempting to add, and it is still not part of the contract.

    **Ownership is in the lookup, not in a branch.** `candidate__user` is part of
    the filter, so another candidate's id and an id that exists nowhere produce
    the same 404. A distinguishable 403/404 would let one candidate enumerate
    another's resume ids.

    **`DELETE` is a hard delete**, decided for batch 1.21: the row goes and the
    stored bytes go. §5.1 has no FK pointing at `candidate_resumes`, and
    REQ-FR-041's model for erasure is "delete the personal data, keep the audit
    trail", so a soft-delete column would add a predicate to every future resume
    query without a requirement behind it. An `AuditLogEntry` records that the
    deletion happened, without the filename or the key.

    Any status may be deleted, including `scanning`: the queued task re-reads
    the row (batch 1.20) and returns quietly when it is gone, so a deletion
    cannot leave a scan that resurrects a row. Deleting is idempotent at the
    HTTP level in the usual sense -- the second request is a 404, not a 500.
    """

    permission_classes = [IsCandidate]

    @extend_schema(
        responses={200: ResumeSummarySerializer},
        summary="Get one of the current candidate's resumes",
        description=(
            "Candidate group only, owner-only. Metadata and scan status for one "
            "resume; 404 for an id the caller does not own. No storage key, no "
            "download URL."
        ),
    )
    def get(self, request, pk) -> Response:
        resume = CandidateResume.objects.filter(
            pk=pk, candidate__user=request.user
        ).first()
        if resume is None:
            raise NotFound(NO_RESUME_DETAIL)

        return Response(ResumeSummarySerializer(resume).data)

    @extend_schema(
        responses={204: None},
        summary="Delete one of the current candidate's resumes",
        description=(
            "Candidate group only, owner-only. Removes the row and the stored "
            "object; writes an audit entry that carries no filename or key. 404 "
            "for an id the caller does not own."
        ),
    )
    def delete(self, request, pk) -> Response:
        resume = CandidateResume.objects.filter(
            pk=pk, candidate__user=request.user
        ).first()
        if resume is None:
            raise NotFound(NO_RESUME_DETAIL)

        # Row, audit entry and bytes are handled by one shared operation, because
        # the Resume manager's Delete button (batch 1.22) has the same rule.
        delete_resume(resume, actor=request.user)

        return Response(status=status.HTTP_204_NO_CONTENT)


class CandidateApplicationListView(APIView):
    """`GET /api/v1/candidates/applications/` -- REQ-FR-023 (batch 1.38).

    **Owner-only, structurally.** The candidate comes from `request.user`; there
    is no candidate id in the path or in a query parameter, so a caller cannot
    ask for another candidate's history. The list is a whitelist through
    `CandidateApplicationSerializer`, not the model row.

    **A candidate with no profile gets 404, not an empty list.** The same answer
    as `/me/` and `/resumes/`: onboarding (REQ-FR-009) is the step that precedes
    an application, so "no profile yet" and "no applications yet" are different
    facts and the client is told which one it hit.

    **The ordering is total.** `-created_at` is "newest first" (design.md S06);
    `-id` breaks a tie deterministically so a page boundary cannot repeat or skip
    a row when two applications share a timestamp.

    **No job-status filter.** An application to a job that has since been paused
    or closed is still part of the candidate's history. Hiding it would make an
    application vanish without the requirement saying so.
    """

    permission_classes = [IsCandidate]

    @extend_schema(
        responses={200: CandidateApplicationSerializer(many=True)},
        summary="List the current candidate's applications",
        description=(
            "Candidate group only. Newest first, paginated (page_size up to 100). "
            "Each row carries the job, the pipeline status and the match score "
            "fields; the score is null until Phase 2 screening. 404 until the "
            "candidate has a profile."
        ),
    )
    def get(self, request) -> Response:
        profile = _profile_for(request.user)
        queryset = (
            Application.objects.filter(candidate=profile)
            # One join for the employer name: `public_employer_name()` reads the
            # disclosure flag, and without the join each row would query again.
            .select_related("job__employer").order_by("-created_at", "-id")
        )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = CandidateApplicationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class CandidateApplicationDetailView(APIView):
    """`GET /api/v1/candidates/applications/{id}/` -- REQ-FR-023 (batch 1.38).

    Same body as a list entry, so a client that already has an id from the list
    needs no second parser. Complete Doc §C.12 also promises the AI rationale on
    this route; batch 1.38's scope stops at the status and the empty score
    fields, and the rationale payload belongs to Phase 2 (2.21-2.25).

    **Ownership is part of the lookup.** `candidate__user` is in the filter, so
    another candidate's id, an id that exists nowhere and a caller without a
    profile all produce the same 404. A distinguishable 403/404 would let one
    candidate enumerate another's application ids, and would confirm to an
    employer that a given application exists.

    Read-only by construction: there is no `PUT`, `PATCH` or `DELETE` on this
    view. Status changes are audited actions (batch 1.41), not a field write.
    """

    permission_classes = [IsCandidate]

    @extend_schema(
        responses={200: CandidateApplicationSerializer},
        summary="Get one of the current candidate's applications",
        description=(
            "Candidate group only, owner-only. One application with its job, "
            "pipeline status and match score fields; 404 for an id the caller "
            "does not own. No candidate identity in the body."
        ),
    )
    def get(self, request, pk) -> Response:
        application = (
            Application.objects.filter(pk=pk, candidate__user=request.user)
            .select_related("job__employer")
            .first()
        )
        if application is None:
            raise NotFound(NO_APPLICATION_DETAIL)

        return Response(CandidateApplicationSerializer(application).data)
