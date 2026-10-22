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

import os

from django.conf import settings
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


class ResumeUploadRequestSerializer(serializers.Serializer):
    """The `POST /api/v1/candidates/resumes/` body (REQ-FR-010, batch 1.19).

    Validate *before* issuing a URL: a wrong type or an oversize file must not
    leave a `pending` row or a signed credential behind.

    `content_type` is checked against `RESUME_ALLOWED_MIME_TYPES` (REQ-SEC-012)
    and is the declared type, not a guess from the extension. `original_filename`
    is metadata only -- it is stored for the candidate's own list (D-5) and is
    never used to build the object key.
    """

    content_type = serializers.CharField(max_length=100)
    file_size = serializers.IntegerField(min_value=1)
    original_filename = serializers.CharField(max_length=500, trim_whitespace=True)

    def validate_content_type(self, value: str) -> str:
        normalized = value.strip().lower()
        allowed = settings.RESUME_ALLOWED_MIME_TYPES
        if normalized not in allowed:
            raise serializers.ValidationError(
                "Unsupported file type. Allowed: " + ", ".join(sorted(allowed)) + "."
            )
        return normalized

    def validate_file_size(self, value: int) -> int:
        limit = settings.MAX_UPLOAD_SIZE_BYTES
        if value > limit:
            raise serializers.ValidationError(
                f"File is larger than the {limit}-byte limit."
            )
        return value

    def validate_original_filename(self, value: str) -> str:
        # Browsers normally send a bare name; older ones send a full Windows
        # path. Keep the name, discard the path, and reject a blank result so a
        # row never stores "" where a filename is expected.
        name = os.path.basename(value.replace("\\", "/")).strip()
        if not name:
            raise serializers.ValidationError("A filename is required.")
        return name


class ResumeUploadTargetSerializer(serializers.Serializer):
    """What the browser needs to perform the PUT, and nothing else."""

    url = serializers.URLField()
    method = serializers.CharField()
    headers = serializers.DictField(child=serializers.CharField())
    expires_in = serializers.IntegerField()


class ResumeUploadResponseSerializer(serializers.Serializer):
    """The `201` body of `POST /api/v1/candidates/resumes/`.

    The storage key is deliberately not echoed: the client already has the URL,
    and the key is storage detail. The original filename is not echoed either --
    the caller sent it, and this response may be rendered in a page.
    """

    id = serializers.UUIDField()
    status = serializers.CharField()
    upload = ResumeUploadTargetSerializer()


class ResumeStatusSerializer(serializers.Serializer):
    """The completion endpoint's body: the row's state, and why if rejected.

    Both `200` (already settled or rejected) and `202` (queued for scanning) use
    this shape, so a client can poll or simply re-post the same call.
    """

    id = serializers.UUIDField()
    status = serializers.CharField()
    status_reason = serializers.CharField(allow_blank=True)
