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
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.models import User
from accounts.serializers import (
    CodedErrorSerializer,
    DetailSerializer,
    LoginSerializer,
    MeSerializer,
    MeUpdateSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RefreshSerializer,
    RegisterSerializer,
    RegistrationAcceptedSerializer,
    ResendVerificationEmailSerializer,
    TokenPairSerializer,
    VerifyEmailSerializer,
)
from accounts.services import (
    INVALID_CREDENTIALS_DETAIL,
    AccountLocked,
    EmailAlreadyVerified,
    EmailNotVerified,
    InvalidCredentials,
    InvalidPasswordResetToken,
    InvalidVerificationToken,
    VerificationTokenExpired,
    WrongPassword,
    authenticate_with_lockout,
    change_password,
    queue_verification_email,
    register_user,
    request_password_reset,
    resend_verification_email,
    reset_password,
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


# ---------------------------------------------------------------------------
# Login, refresh and logout (REQ-FR-002, REQ-FR-007, REQ-FR-008, decision D-7)
# ---------------------------------------------------------------------------

# The login endpoint is anonymous: it is how an anonymous caller becomes
# authenticated. `authentication_classes = []` also turns off DRF's CSRF
# enforcement, which is correct here -- the route reads no session cookie, so a
# cross-site POST can do no more than the anonymous caller could do directly.
# Issuing tokens from a cookie-authenticated route is how login CSRF works.


class LoginView(APIView):
    """`POST /api/v1/auth/login/` -- exchange credentials for a JWT pair.

    The credential check is `accounts.services.authenticate_with_lockout`, the
    same function the template login calls. Lockout, the counter reset and the
    audit row therefore have one implementation, not two.

    Error bodies:

    * `401 invalid_credentials` -- unknown address, wrong password or inactive
      account. One message for all three, so the endpoint is not an
      account-existence oracle.
    * `403 email_not_verified` -- the password was right but the address is not
      verified (REQ-FR-001). Only reachable by someone who knows the password,
      so it leaks nothing to a stranger.
    * `423 account_locked` -- a live lockout, with `retry_after` seconds
      (REQ-FR-003). No token is issued, even for a correct password.
    """

    permission_classes: list = []
    authentication_classes: list = []
    throttle_scope = "login"

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: TokenPairSerializer,
            401: CodedErrorSerializer,
            403: CodedErrorSerializer,
            423: CodedErrorSerializer,
        },
        summary="Log in",
        description=(
            "Anonymous. Returns a 15-minute access token and a 7-day refresh "
            "token (D-7). Five consecutive wrong passwords lock the account for "
            "15 minutes; a locked account returns 423 with `retry_after` and no "
            "token. An unverified address returns 403 after a correct password."
        ),
    )
    def post(self, request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = authenticate_with_lockout(
                serializer.validated_data["email"],
                serializer.validated_data["password"],
            )
        except InvalidCredentials:
            return Response(
                {"detail": INVALID_CREDENTIALS_DETAIL, "code": "invalid_credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except EmailNotVerified:
            return Response(
                {
                    "detail": "Verify your email address before signing in.",
                    "code": "email_not_verified",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except AccountLocked as exc:
            return Response(
                {
                    "detail": locked_detail(exc.retry_after),
                    "code": "account_locked",
                    "retry_after": exc.retry_after,
                },
                status=status.HTTP_423_LOCKED,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_200_OK,
        )


class RefreshView(TokenRefreshView):
    """`POST /api/v1/auth/refresh/` -- rotate the refresh token (D-7).

    SimpleJWT's view already does the part that matters: it reads the token,
    rejects one that is expired or blacklisted with 401, and -- because
    `ROTATE_REFRESH_TOKENS` and `BLACKLIST_AFTER_ROTATION` are on -- returns a
    new pair and blacklists the old refresh token in the same request. The
    subclass only opts the endpoint out of authentication (the refresh token is
    the credential) and names it for the schema.
    """

    permission_classes = ()
    authentication_classes = ()


class LogoutView(APIView):
    """`POST /api/v1/auth/logout/` -- blacklist the supplied refresh token.

    The refresh token is the only credential this route needs: it is presented
    in the body, and blacklisting is what makes it unusable afterwards
    (REQ-FR-008). An expired or already-blacklisted token is answered with 401
    rather than a second, different error; either way the client's next refresh
    fails.
    """

    permission_classes: list = []
    authentication_classes: list = []

    @extend_schema(
        request=RefreshSerializer,
        responses={204: None},
        summary="Log out",
        description=(
            "Anonymous. Blacklists the refresh token in the body; a later "
            "refresh with it returns 401. The access token is short-lived and "
            "is not tracked server-side."
        ),
    )
    def post(self, request) -> Response:
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            # Not `AuthenticationFailed`: with `authentication_classes = []` DRF
            # rewrites that to 403 (it has no authenticator to name in a
            # `WWW-Authenticate` header), and the contract here is 401 for a
            # token that cannot be revoked.
            return Response(
                {"detail": "This token is no longer valid.", "code": "invalid_token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Password reset and change (REQ-FR-004)
# ---------------------------------------------------------------------------

PASSWORD_RESET_SENT_DETAIL = "If that email exists, we've sent a link."
PASSWORD_RESET_DONE_DETAIL = "Your password has been reset."
PASSWORD_CHANGED_DETAIL = "Your password has been changed."


class PasswordResetRequestView(APIView):
    """`POST /api/v1/auth/password/reset/` -- email a one-hour link.

    Always 202 with the same body: a different answer for a known address is an
    account-enumeration oracle, and design.md page #9's copy is built around the
    generic sentence. The boolean from `request_password_reset` decides only
    whether a mail is queued.
    """

    permission_classes: list = []
    authentication_classes: list = []
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={202: DetailSerializer},
        summary="Request a password reset",
        description=(
            "Anonymous. Always 202 with the same body, whether or not the "
            "address exists. A known, active address receives a link that "
            "expires in one hour and works once."
        ),
    )
    def post(self, request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request_password_reset(serializer.validated_data["email"])
        if user is not None:
            _dispatch_password_reset(user)

        return Response(
            {"detail": PASSWORD_RESET_SENT_DETAIL},
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetConfirmView(APIView):
    """`POST /api/v1/auth/password/reset/confirm/` -- set the new password.

    Expired, tampered, already-used and unknown-account links all return the
    same 400 `invalid_token`. The four are one state to the user (design.md
    page #10: "This link has expired"), and separating them would confirm which
    accounts exist.

    A success clears the lockout state and revokes outstanding refresh tokens
    (`accounts.services.reset_password`), so a session stolen before the reset
    cannot survive it.
    """

    permission_classes: list = []
    authentication_classes: list = []
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={200: DetailSerializer, 400: CodedErrorSerializer},
        summary="Confirm a password reset",
        description=(
            "Anonymous. Consumes the `uid` + `token` pair from the email. 400 "
            "`invalid_token` covers expired, tampered, reused and unknown. "
            "Success clears lockout state and blacklists existing refresh "
            "tokens."
        ),
    )
    def post(self, request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            reset_password(
                serializer.validated_data["uid"],
                serializer.validated_data["token"],
                serializer.validated_data["new_password"],
            )
        except InvalidPasswordResetToken as exc:
            return Response(
                {"detail": str(exc), "code": "invalid_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DjangoValidationError as exc:
            raise DRFValidationError({"new_password": exc.messages}) from exc

        return Response(
            {"detail": PASSWORD_RESET_DONE_DETAIL}, status=status.HTTP_200_OK
        )


class PasswordChangeView(APIView):
    """`POST /api/v1/auth/password/change/` -- authenticated.

    The current password is required, so a borrowed session cannot change the
    password and lock the owner out. Refresh tokens are deliberately not
    revoked here: the caller is the signed-in owner, and D-7 treats rotation,
    not a password change, as the revocation point. A reset, which may be
    driven by someone who is not signed in, does revoke them.
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordChangeSerializer,
        responses={200: DetailSerializer, 401: CodedErrorSerializer},
        summary="Change password",
        description=(
            "Authenticated. Requires the current password. The new password "
            "runs through every configured validator."
        ),
    )
    def post(self, request) -> Response:
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            change_password(
                request.user,
                serializer.validated_data["current_password"],
                serializer.validated_data["new_password"],
            )
        except WrongPassword as exc:
            raise DRFValidationError({"current_password": [str(exc)]}) from exc
        except DjangoValidationError as exc:
            raise DRFValidationError({"new_password": exc.messages}) from exc

        return Response({"detail": PASSWORD_CHANGED_DETAIL}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Current user (batch 1.12)
# ---------------------------------------------------------------------------


class MeView(APIView):
    """`GET`/`PUT /api/v1/auth/me/` -- the caller's own account.

    The target is always `request.user`. The route has no id in the path and the
    body cannot name a different account, so "own data only" is structural
    rather than a check that a later edit can remove. A user id in the URL would
    have needed an equality test on every method; this needs none.

    `permission_classes` is set explicitly even though `IsAuthenticated` is the
    project default: the endpoint reads and writes one person's row, and batch
    1.13's matrix treats an undeclared permission on a non-public view as a
    finding. There is no role restriction -- every authenticated role owns an
    account -- so the test is authentication, not membership of a group.

    `authentication_classes` is left at the project default on purpose. Unlike
    the anonymous auth routes, this one is reached from the browser session too,
    so `SessionAuthentication` must keep enforcing CSRF on the PUT.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: MeSerializer},
        summary="Get the current user",
        description=(
            "Authenticated. Returns the caller's email, first and last name, "
            "and documented role names. Lockout state, MFA flags, staff flags "
            "and group ids are never included."
        ),
    )
    def get(self, request) -> Response:
        return Response(MeSerializer(request.user).data)

    @extend_schema(
        request=MeUpdateSerializer,
        responses={200: MeSerializer},
        summary="Update the current user",
        description=(
            "Authenticated. Replaces the caller's first and last name; both "
            "are required (PUT, not PATCH). `email` is read-only: changing the "
            "sign-in address needs the verification flow. Any other key in the "
            "body is ignored."
        ),
    )
    def put(self, request) -> Response:
        serializer = MeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.first_name = serializer.validated_data["first_name"]
        user.last_name = serializer.validated_data["last_name"]
        # Named columns, not `save()`: the request must not be able to write
        # anything else on the row even if a future field is added to the
        # serializer by mistake.
        user.save(update_fields=["first_name", "last_name"])

        return Response(MeSerializer(user).data)


def locked_detail(retry_after: int) -> str:
    """'Too many attempts. Try again in 14:32.' (design.md S01 lockout state).

    A helper rather than a format string in two places: the page and the API
    must show the same countdown for the same lock.
    """
    minutes, seconds = divmod(max(0, int(retry_after)), 60)
    return "Too many failed sign-in attempts. " f"Try again in {minutes}:{seconds:02d}."


def _dispatch_password_reset(user) -> None:
    """Queue the email after the surrounding transaction commits.

    Imported lazily because `accounts.tasks` imports the token helper from
    `accounts.services`. `on_commit` matters even though these views are in
    autocommit: a future `ATOMIC_REQUESTS` must not queue a mail for a user row
    that never became visible.
    """
    from django.db import transaction

    from accounts.tasks import send_password_reset_email

    user_id = str(user.pk)
    transaction.on_commit(lambda: send_password_reset_email.delay(user_id))
