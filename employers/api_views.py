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

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsEmployer
from employers.models import EmployerProfile
from employers.serializers import (
    EmployerProfileSerializer,
    EmployerProfileUpdateSerializer,
)

# One sentence for both "you have not onboarded yet" and "the row is gone".
# A 404 here does not enumerate anything: the only row it could describe is the
# caller's own, and a distinguishable 403/404 would tell an account whether a
# given user has a profile.
NO_PROFILE_DETAIL = "No employer profile yet. Complete onboarding first."

# REQ-FR-045 says the profile is created during onboarding *with a company
# name*. A PATCH that would create a row without one is a 400 rather than an
# empty profile the public job board could later render as a nameless employer.
COMPANY_NAME_REQUIRED = {
    "company_name": ["A company name is required to create an employer profile."]
}


def _profile_for(user) -> EmployerProfile:
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
        return Response(EmployerProfileSerializer(_profile_for(request.user)).data)

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
