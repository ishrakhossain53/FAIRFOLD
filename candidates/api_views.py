"""API views for the candidate profile (REQ-FR-009, Complete Doc §C.12).

One view, two methods, no id in the path. The target is always
`request.user`, which is the ownership rule rather than a separate check that a
future edit could remove: candidate B cannot address candidate A's row because
there is nowhere in the request to put A's identifier.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCandidate
from candidates.models import CandidateProfile
from candidates.serializers import (
    CandidateProfileSerializer,
    CandidateProfileUpdateSerializer,
)

# One sentence for both "you have not onboarded yet" and "the row is gone".
# A 404 here does not enumerate anything: the only row it could describe is the
# caller's own, and a distinguishable 403/404 would tell an employer whether a
# given account has a profile.
NO_PROFILE_DETAIL = "No candidate profile yet. Complete onboarding first."


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
