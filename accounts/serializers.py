"""API serializers for registration and email verification (REQ-FR-001, D-3).

The field list lives here rather than in a view because it *is* the API contract:
drf-spectacular reads these classes to build the OpenAPI document, so a field
added to the view but not to a serializer would be undocumented, and a field
documented but not accepted would be a lie in the schema.

Validation is deliberately not re-implemented. `register_user` remains the single
authority (batch 1.3); the serializer calls the same `validate_password` with the
same provisional user only so that a weak password comes back as a 400 keyed to
`password` instead of a 500. The service runs the validators again, which is
cheap and means a caller that bypasses this serializer still cannot store a weak
password.

`RegisterSerializer` returns validated data; the view calls `register_user` with
it. It deliberately does not implement `create()`: DRF 3.17's `save()` asserts a
non-`None` instance, and the service returns `None` for an address that already
has an account. That `None` is the service's documented anti-enumeration
contract -- the view must answer "created" and "already registered" identically,
and an exception would invite a distinguishable error. `save()` cannot express
it, so the call is explicit in the view.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import ROLES, User
from accounts.services import SELF_ASSIGNABLE_ROLES


class NormalisedEmailField(serializers.EmailField):
    """An address stored exactly the way `users.email` stores it.

    `UserManager._create` and `register_user` strip and lowercase the whole
    address, not just the domain that `BaseUserManager.normalize_email` handles.
    Doing it in the field means the 201 response echoes the value that was
    actually stored and the resend endpoint's lookup matches the row. Without
    it, "Ada@Example.com" would create an account the resend endpoint could not
    find, and the pending page would be a dead end.
    """

    def to_internal_value(self, data: Any) -> str:
        return User.objects.normalize_email(super().to_internal_value(data)).lower()


class RegisterSerializer(serializers.Serializer):
    """The body of `POST /api/v1/auth/register/` (Complete Doc §C.12).

    `role` is a `ChoiceField` over `SELF_ASSIGNABLE_ROLES`, not over `ROLES`: the
    public form may only ever grant `candidate` or `employer_hr` (REQ-FR-045,
    REQ-FR-047). A `ChoiceField` also puts the enum in the OpenAPI document, so a
    client cannot invent `employer_manager` and discover the refusal at runtime.

    `password` keeps whitespace (`trim_whitespace=False`). DRF's default would
    silently strip a leading or trailing space, so the client would send one
    password and the service would hash another.
    """

    email = NormalisedEmailField(max_length=255)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    role = serializers.ChoiceField(choices=SELF_ASSIGNABLE_ROLES)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # The provisional user lets `UserAttributeSimilarityValidator` compare the
        # password with the email and names this account will actually have -- the
        # same comparison `register_user` makes. Skipping it here would report a
        # password as acceptable and then fail in the service.
        provisional = User(
            email=attrs["email"],
            first_name=attrs["first_name"],
            last_name=attrs["last_name"],
        )
        try:
            validate_password(attrs["password"], provisional)
        except DjangoValidationError as exc:
            # Keyed to the field, so page #6 can attach each message to the input
            # that caused it instead of printing a blob above the form.
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs


class ResendVerificationEmailSerializer(serializers.Serializer):
    """The body of `POST /api/v1/auth/verify-email/resend/`.

    An address, not a user id or a token: the caller is on the pending page after
    signup, has no session and holds no credential other than the address they
    typed. The view answers identically whether or not the address exists
    (REQ-FR-001's anti-enumeration requirement, same as page #9's wording).
    """

    email = NormalisedEmailField(max_length=255)


class VerifyEmailSerializer(serializers.Serializer):
    """The body of `POST /api/v1/auth/verify-email/`.

    The token is the value from the emailed link (`accounts.tasks.verification_link`
    puts it in a `?token=` query parameter). It is not validated here beyond being
    non-empty: `verify_email` owns signature, expiry and account checks, and
    duplicating them would give two places to keep in step.
    """

    token = serializers.CharField()


class RegistrationAcceptedSerializer(serializers.Serializer):
    """The 201 body of registration.

    `email_verified` is `False` even when the address already had a verified
    account, because the response must be identical on both paths. The field
    means "this response created or matched an account that still needs the
    verification step", not "the account is unverified" -- a client that wants the
    second question answered has to log in.
    """

    detail = serializers.CharField()
    email = serializers.EmailField()
    email_verified = serializers.BooleanField()


class DetailSerializer(serializers.Serializer):
    """A one-message success body (`{"detail": "..."}`)."""

    detail = serializers.CharField()


class CodedErrorSerializer(serializers.Serializer):
    """A 400 from a service-level check, with a machine-readable `code`.

    `core.exceptions` keys field errors by field and leaves `detail` bodies
    untouched, but DRF drops an exception's `code` when it renders it. Page #11
    has to distinguish "expired" (show "send a new link") from "invalid" (show
    "this link is not valid"), so the view returns the code explicitly.
    """

    detail = serializers.CharField()
    code = serializers.CharField()


# ---------------------------------------------------------------------------
# Login, token refresh, logout and password management (batches 1.8 and 1.10)
# ---------------------------------------------------------------------------


class LoginSerializer(serializers.Serializer):
    """The body of `POST /api/v1/auth/login/` (REQ-FR-002).

    The password keeps its whitespace for the same reason as registration: the
    service hashes exactly what was sent, so trimming here would make the API
    accept a password the account does not have.
    """

    email = NormalisedEmailField(max_length=255)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )


class TokenPairSerializer(serializers.Serializer):
    """SimpleJWT's response shape, declared for the OpenAPI document.

    SimpleJWT builds this body itself; the serializer exists so drf-spectacular
    can describe it. Without it the login and refresh endpoints are omitted from
    the schema, and a generated client has no way to know the field names.
    """

    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class RefreshSerializer(serializers.Serializer):
    """The body of `POST /api/v1/auth/refresh/` and `/logout/`."""

    refresh = serializers.CharField(write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    """The body of `POST /api/v1/auth/password/reset/` (REQ-FR-004).

    Only the address. The response is identical whether or not it exists, so
    there is nothing else the caller can use to test for an account.
    """

    email = NormalisedEmailField(max_length=255)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """The body of `POST /api/v1/auth/password/reset/confirm/`.

    `uid` and `token` are the two values in the emailed link. They are not
    validated here: `reset_password` owns the signature, expiry and reuse
    checks, and a second implementation would be a second place to get the
    one-hour window wrong.
    """

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )


class PasswordChangeSerializer(serializers.Serializer):
    """The body of `POST /api/v1/auth/password/change/` (authenticated).

    `current_password` is required so a borrowed session cannot lock the owner
    out of their own account.
    """

    current_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )


# ---------------------------------------------------------------------------
# Current user (batch 1.12)
# ---------------------------------------------------------------------------


class MeSerializer(serializers.Serializer):
    """The `GET`/`PUT /api/v1/auth/me/` response body (Complete Doc §C.12).

    The declaration *is* the whitelist. It spells out the four fields the
    endpoint may return, so `locked_until`, `failed_login_attempts`,
    `mfa_enabled`, `is_staff` and the group rows -- all present on `User` -- are
    unreachable from here even if a view later passes the model straight to the
    serializer. That matters for `locked_until` in particular: exposing the
    timestamp would tell a client exactly when to retry a password guess.

    `roles` carries the documented role names (D-2), never `Group.pk` values and
    never every group the user happens to hold: a group created for an internal
    permission set is not part of this contract. Filtering through `ROLES` also
    fixes the order, so two clients comparing the list do not see it change
    between requests.
    """

    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()

    def get_roles(self, user: User) -> list[str]:
        held = set(user.groups.values_list("name", flat=True))
        return [role for role in ROLES if role in held]


class MeUpdateSerializer(serializers.Serializer):
    """The `PUT /api/v1/auth/me/` body (Complete Doc §C.12).

    Exactly the two writable columns, and both are required: the documented verb
    is PUT, which replaces the representation, so a body with only `first_name`
    is incomplete rather than a partial edit. A partial client belongs on a
    future PATCH, which §C.12 does not list for this route.

    `email` is deliberately absent. Changing the sign-in address is a
    re-verification flow (REQ-FR-001) and nothing in §C.12 or the requirements
    asks for it here; accepting it would let a caller swap the address that
    owns the account in a single unverified write.

    DRF ignores keys that are not declared, including declared read-only ones.
    That is the documented behaviour relied on by the whitelist tests: a body
    carrying `is_staff` or `groups` succeeds while changing neither.
    """

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
