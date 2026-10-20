"""Anonymous auth endpoints: registration and email verification (REQ-FR-001).

All three endpoints are anonymous by necessity: registration happens before an
account exists, and verification happens before the address is trusted. They set
`permission_classes = []` explicitly because `DEFAULT_PERMISSION_CLASSES` is
`IsAuthenticated`; forgetting it makes every signup a 401.

`authentication_classes = []` is deliberate too. With no authentication class,
DRF's `SessionAuthentication` never runs, so CSRF is not enforced here. That is
correct for these routes: they read no session cookie and hold no ambient
authority, so a cross-site POST can only do what the anonymous caller could do
anyway. Leaving `SessionAuthentication` on would instead make a logged-in
employer's browser send a CSRF token to a route that does not need one.

`throttle_scope` maps to `DEFAULT_THROTTLE_RATES` in `config/settings/base.py`.
The per-IP ceiling is the documented unauthenticated rate (Complete Doc §5.5);
the per-account 45-second cooldown in `accounts.services` is the finer limit.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.serializers import (
    CodedErrorSerializer,
    DetailSerializer,
    RegisterSerializer,
    RegistrationAcceptedSerializer,
    ResendVerificationEmailSerializer,
    VerifyEmailSerializer,
)
from accounts.services import (
    EmailAlreadyVerified,
    InvalidVerificationToken,
    VerificationTokenExpired,
    queue_verification_email,
    register_user,
    resend_verification_email,
    verify_email,
)

# The same body whatever happened. Registration cannot say "this address is
# taken" without turning the public form into an account-enumeration oracle
# (`register_user` returns `None` precisely so this stays true).
REGISTRATION_ACCEPTED_DETAIL = (
    "Account created. Check your email to verify your address."
)
EMAIL_VERIFIED_DETAIL = "Email verified."
# Wording borrowed from page #9's reset form ("If that email exists..."): the
# generic answer is what makes the resend endpoint useless for enumeration.
RESEND_DETAIL = "If that address needs verification, we've sent a new link."


class RegisterView(APIView):
    """`POST /api/v1/auth/register/` — create an unverified account.

    Two rules shape this view:

    * **The response must not distinguish a new address from an existing one.**
      `register_user` returns `None` for a duplicate and the view returns the
      identical 201 body. The verification email is sent only on the create path,
      but the caller cannot see that difference (REQ-FR-001, and the reason the
      service returns `None` instead of raising).
    * **The account is unverified when this returns.** REQ-FR-001 requires
      `email_verified=False` until the link is followed; issuing a JWT here would
      let an unverified address use the platform, which REQ-FR-002 forbids.

    `email_verified` in the body is therefore always `False`, even on the
    duplicate path, because it describes what this response did, not the state of
    someone else's account.
    """

    permission_classes: list = []
    authentication_classes: list = []
    throttle_scope = "register"

    @extend_schema(
        request=RegisterSerializer,
        responses={201: RegistrationAcceptedSerializer},
        summary="Register a new account",
        description=(
            "Anonymous. Creates an unverified account and sends the verification "
            "email. Returns the same 201 body when the address is already "
            "registered: the endpoint must not be an account-enumeration oracle "
            "(REQ-FR-001)."
        ),
    )
    def post(self, request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Called explicitly rather than through `serializer.save()`: the service
        # returns `None` for a duplicate address, and DRF's `save()` asserts a
        # non-`None` instance.
        try:
            user = register_user(**serializer.validated_data)
        except DjangoValidationError as exc:
            # `validate()` ran the same email and password checks; this is a guard
            # so that a divergence cannot turn a bad password into a 500.
            raise DRFValidationError({"non_field_errors": exc.messages}) from exc

        # `None` means the address already had an account. Not an error: the
        # caller gets the same answer and no second email.
        if user is not None:
            queue_verification_email(user)

        return Response(
            {
                "detail": REGISTRATION_ACCEPTED_DETAIL,
                "email": serializer.validated_data["email"],
                "email_verified": False,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    """`POST /api/v1/auth/verify-email/` — consume the emailed token.

    Expired and tampered tokens are different 400s, because page #11 has two
    states: "link expired, send a new one" and "this link is not valid". A single
    generic message would leave the user with no action on the expired case.

    An already-verified account returns **200**, not an error. The link was
    legitimate; the flag is already where the caller wants it. Design.md page #11
    calls that the success state, and a 409 here would show an error page to
    someone who did nothing wrong.
    """

    permission_classes: list = []
    authentication_classes: list = []
    throttle_scope = "verify_email"

    @extend_schema(
        request=VerifyEmailSerializer,
        responses={
            200: DetailSerializer,
            400: CodedErrorSerializer,
        },
        summary="Verify an email address",
        description=(
            "Anonymous. Consumes the signed token from the verification email. "
            "400 carries `code: token_expired` or `code: invalid_token`; an "
            "already-verified account returns 200."
        ),
    )
    def post(self, request) -> Response:
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            verify_email(serializer.validated_data["token"])
        except VerificationTokenExpired as exc:
            return Response(
                {"detail": str(exc), "code": "token_expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidVerificationToken as exc:
            return Response(
                {"detail": str(exc), "code": "invalid_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except EmailAlreadyVerified:
            # Deliberately the success body. See the class docstring.
            pass

        return Response({"detail": EMAIL_VERIFIED_DETAIL}, status=status.HTTP_200_OK)


class ResendVerificationEmailView(APIView):
    """`POST /api/v1/auth/verify-email/resend/` — send another link.

    Always 202 with the same body. An unknown address, an address that is already
    verified, and a request inside the 45-second cooldown all take the same path
    through the response, because any difference is an enumeration oracle. The
    boolean from `resend_verification_email` is intentionally discarded.

    The address is looked up here rather than inside the service: the service
    takes a `User` (an authenticated actor in other callers), and the lookup by
    normalised email is the one place that would leak "no such account" if it
    returned early.
    """

    permission_classes: list = []
    authentication_classes: list = []
    throttle_scope = "verify_email"

    @extend_schema(
        request=ResendVerificationEmailSerializer,
        responses={202: DetailSerializer},
        summary="Resend the verification email",
        description=(
            "Anonymous. Always 202 with the same body; the response does not "
            "reveal whether the address exists, is already verified, or is "
            "inside its resend cooldown."
        ),
    )
    def post(self, request) -> Response:
        serializer = ResendVerificationEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email=serializer.validated_data["email"]).first()
        if user is not None:
            resend_verification_email(user)

        return Response({"detail": RESEND_DETAIL}, status=status.HTTP_202_ACCEPTED)
