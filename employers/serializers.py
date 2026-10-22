"""API serializers for the employer company profile (REQ-FR-045, batch 1.24).

Complete Doc §C.12 lists exactly two operations on this resource:

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
