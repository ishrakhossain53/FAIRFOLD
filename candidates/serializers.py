"""API serializers for the candidate profile (REQ-FR-009, batch 1.15).

Complete Doc §C.12 lists exactly two operations on this resource:

    GET    /api/v1/candidates/me/    # Get candidate profile
    PATCH  /api/v1/candidates/me/    # Update candidate profile
                                      # (title, bio, location, remote_ok)

There is no `POST` and no id in the path. The target is always
`request.user`, so the ownership rule is structural: a caller cannot name
another candidate's row.

**Why PATCH creates the row when it is missing.** The endpoint list has no
creation verb, yet REQ-FR-009 requires a registered candidate to end up with a
profile. A profile can only be created through the onboarding UI (batch 1.16)
or through a PATCH that carries at least one profile field. Treating every
absent row as a 404 on PATCH would leave an API-only candidate with no way to
complete onboarding, so a non-empty PATCH is create-or-update. An empty PATCH
is not an onboarding action and stays a 404.

**The response is a whitelist.** It names the columns this resource owns. The
model also carries `skills`, `journey_timeline`, `match_scores`,
`visibility_tier` and `is_promoted`; none of those belongs to onboarding, and
`visibility_tier`/`is_promoted` are discovery controls that REQ-FR-053 says may
never enter ranking. Keeping them out of the serializer means a later view
change cannot accidentally expose or accept them.
"""

from __future__ import annotations

from rest_framework import serializers

from candidates.models import CandidateProfile


class CandidateProfileSerializer(serializers.ModelSerializer):
    """The `GET`/`PATCH /api/v1/candidates/me/` response body.

    Exactly the four fields Complete Doc §C.12 names for this resource. The row
    `id`, the owner, the timestamps and the model's skills/journey/match/paid
    columns are absent on purpose: the route is `/me/`, so the caller already
    knows which profile it is, and REQ-FR-053's discovery controls do not belong
    in an onboarding response.
    """

    class Meta:
        model = CandidateProfile
        fields = (
            "title",
            "bio",
            "location",
            "remote_ok",
        )
        read_only_fields = fields


class CandidateProfileUpdateSerializer(serializers.Serializer):
    """The `PATCH /api/v1/candidates/me/` body.

    All four fields are optional because the verb is PATCH: a caller may update
    one field without resending the others. `title` carries the model's
    200-character limit; `bio` and `location` are TEXT columns with no documented
    length. Empty strings are allowed -- the model stores "not provided" as an
    empty string rather than NULL, so the API must accept that spelling.

    Only these four keys are declared. DRF ignores undeclared keys, which is the
    whitelist: a body carrying `user`, `skills`, `visibility_tier` or
    `is_promoted` succeeds while changing none of them.
    """

    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    remote_ok = serializers.BooleanField(required=False)
