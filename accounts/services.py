"""Account services: registration and role assignment.

`register_user` is the one place that creates a self-registered account. It
normalises the email, applies every `AUTH_PASSWORD_VALIDATORS` rule, assigns the
signup role and writes the audit entry inside one transaction, so a failure
leaves no half-created user. The HTTP layer (batch 1.5) must treat "created" and
"email already exists" identically -- see the function's docstring.

`assign_role` is the one place that adds a role to a user. Roles are Django
**groups**, seeded from `core/fixtures/groups.json` (REQ-FR-047, decision D-2).
There is no `role` column, so nothing in the database stops a second, conflicting
group from being added. `assign_role` is that stop: REQ-FR-045 says an employer
cannot hold both the candidate and employer roles.

What "mutual exclusivity" means here, precisely:

* `candidate` conflicts with the employer-side roles (`EMPLOYER_ROLES`);
* the two employer-side roles do **not** conflict with each other — an
  `employer_hr` who becomes `employer_manager` keeps both, and nothing in the
  requirements says to remove the old one;
* `interviewer` is outside the rule. REQ-FR-045 forbids candidate + employer;
  REQ-FR-047 presents `interviewer` as another employer-team role and says
  nothing about candidates holding it, so widening the rule would reject a
  combination the requirements allow.

The group is fetched with `get()`, never `get_or_create()`. A typo must raise,
not create a fifth group that no seed, fixture or requirement knows about — a
`role` that exists in `auth_group` but not in `ROLES` is exactly the drift the
group-as-role design is meant to avoid.

Assignment is idempotent: adding a role the user already holds is a no-op, so a
retried invitation-acceptance request does not fail.

The third concern is **email verification** (REQ-FR-001, decision D-3). The
token is a `TimestampSigner` signature over the encoded user id, not a database
row and not the id itself. Verification flips `email_verified` exactly once,
under a row lock, so a link opened twice (or in two tabs) cannot succeed twice.
Resending is throttled per user through the cache, not the database: the cooldown
must not be able to take the `users` table down, and it expires by itself.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from accounts.models import (
    CANDIDATE_ROLE,
    EMPLOYER_HR_ROLE,
    EMPLOYER_ROLES,
    ROLES,
    User,
)
from core.models import AuditLogEntry

# The roles a person may choose at signup. REQ-FR-001's form offers "Candidate"
# or "Employer" (design.md page 6); the employer choice is the base employer
# group, `employer_hr`. `employer_manager` is a promotion an employer admin makes,
# and `interviewer` is an invitation (REQ-FR-047), so neither can be self-assigned.
SELF_ASSIGNABLE_ROLES = (CANDIDATE_ROLE, EMPLOYER_HR_ROLE)

# The action recorded on a successful signup. `AuditLogEntry.details` carries the
# role only: the email and names are the fields the DDL marks personal, and this
# table is the one a compliance export would not expect to contain them.
REGISTRATION_AUDIT_ACTION = "user_registered"
REGISTRATION_RESOURCE_TYPE = "user"


class RoleConflictError(ValueError):
    """A role would give the user both sides of the platform (REQ-FR-045).

    Deliberately a `ValueError`: a registration or team view can treat it as a
    bad request without importing a service-specific type, while callers that
    need to distinguish it still can.

    The message names groups, never a person. It can reach a log line or an API
    error body, and an email or name there is PII (AGENTS.md privacy invariants).
    """


def assign_role(user: User, role: str) -> Group:
    """Add `role` to `user`, or refuse if it conflicts with a held role.

    Returns the `Group` that was added (or was already there), so a caller that
    writes an audit entry does not need a second query.

    Raises:
        ValueError: `role` is not in `ROLES`. This also catches case mistakes
            ("Candidate"), which would otherwise create a second group that no
            `has_role` check ever reads.
        RoleConflictError: the user holds a role on the other side of the
            candidate/employer split (REQ-FR-045).
        Group.DoesNotExist: the role is valid but the fixture has not been
            loaded. That is a deployment error (`manage.py seed`), not something
            to paper over by creating the group here.
    """
    if role not in ROLES:
        raise ValueError(f"Unknown role {role!r}. Known roles: {', '.join(ROLES)}.")

    group = Group.objects.get(name=role)

    # Only the two platform sides conflict. `interviewer` has no counterpart, so
    # it gets an empty tuple rather than the `else` branch — an `else` here is
    # what made an interviewer refuse to sit next to a candidate role.
    conflicting: tuple[str, ...] = ()
    if role == CANDIDATE_ROLE:
        conflicting = EMPLOYER_ROLES
    elif role in EMPLOYER_ROLES:
        conflicting = (CANDIDATE_ROLE,)

    # The check and the insert must see the same membership, or two concurrent
    # requests (invitation acceptance and registration, say) can each pass the
    # check and leave the user holding both sides. The row lock makes the second
    # request wait and then see the first one's group.
    with transaction.atomic():
        locked = User.objects.select_for_update().get(pk=user.pk)
        held = set(
            locked.groups.filter(name__in=conflicting).values_list("name", flat=True)
        )
        if held:
            raise RoleConflictError(
                f"Cannot assign role {role!r}: the user already holds "
                f"{', '.join(sorted(held))}. A user cannot be both a candidate "
                f"and an employer (REQ-FR-045)."
            )
        locked.groups.add(group)

    return group


class RoleNotSelfAssignableError(ValueError):
    """A signup tried to claim a role the public form may not grant.

    A `ValueError` for the same reason as `RoleConflictError`: the future view
    can treat it as a bad request without importing a service-specific type,
    while callers that need to distinguish it still can.

    The message names the role, never the person. It can reach a log line and an
    API error body, where an email or name would be PII.
    """


def _email_taken(email: str) -> bool:
    """True when an account already uses this normalised address.

    A separate function so a test can simulate the address appearing between
    the check and the insert, which is the one race a unique constraint cannot
    turn into a friendly answer.
    """
    return User.objects.filter(email=email).exists()


def register_user(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str,
) -> User | None:
    """Create an unverified account and assign its signup role (REQ-FR-001).

    Returns the new `User`, or `None` when the email already has an account.

    **Why `None` rather than an exception.** REQ-FR-001 tells the caller to send
    a verification email; a public signup endpoint must not tell an anonymous
    caller whether an address is registered, because that turns the form into an
    account-enumeration oracle. Returning `None` lets the batch 1.5 view take
    the same path (same status, same body) for both outcomes: it sends the
    verification email only when a user was created and otherwise discards the
    request. An exception named "already registered" invites a view to catch it
    and return a distinguishable error, which is the leak.

    **Atomicity.** The user, the group membership and the audit entry are one
    transaction. `assign_role` opens its own savepoint; a missing seeded group or
    a failed audit insert rolls the user back with them (`Done when`: no
    half-created users).

    **Validation.** The email is stripped and normalised exactly as
    `UserManager` stores it (whole address lowercased), then checked with
    Django's `validate_email`. The password runs through every configured
    `AUTH_PASSWORD_VALIDATORS` entry, with a provisional user so the
    name/email-similarity rule applies. Validation happens before the duplicate
    check, so a weak password on an existing address is refused for the same
    reason as on a new one.

    Raises:
        ValidationError: the email is missing or malformed, or the password is
            missing or fails a validator.
        RoleNotSelfAssignableError: `role` is not a documented role or is a role
            the signup form may not grant (REQ-FR-045, REQ-FR-047).
        Group.DoesNotExist: the role is valid but `manage.py seed` has not run.
            That is a deployment error, not something to paper over.
    """
    if role not in ROLES:
        raise RoleNotSelfAssignableError(
            f"Unknown role {role!r}. Known roles: {', '.join(ROLES)}."
        )
    if role not in SELF_ASSIGNABLE_ROLES:
        raise RoleNotSelfAssignableError(
            f"Role {role!r} cannot be self-assigned at signup. "
            f"Choose one of: {', '.join(SELF_ASSIGNABLE_ROLES)}."
        )

    if not isinstance(email, str) or not email.strip():
        raise ValidationError("An email address is required.")
    normalised_email = User.objects.normalize_email(email.strip()).lower()
    validate_email(normalised_email)

    if not isinstance(password, str) or not password:
        raise ValidationError("A password is required.")
    # An unsaved user, so `UserAttributeSimilarityValidator` can compare the
    # password with the email and names the account will actually have.
    provisional = User(
        email=normalised_email, first_name=first_name, last_name=last_name
    )
    validate_password(password, provisional)

    if _email_taken(normalised_email):
        return None

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=normalised_email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            assign_role(user, role)
            AuditLogEntry.objects.create(
                actor=user,
                action=REGISTRATION_AUDIT_ACTION,
                resource_type=REGISTRATION_RESOURCE_TYPE,
                resource_id=user.id,
                details={"role": role},
            )
    except IntegrityError:
        # The pre-check passed but another request inserted the same address
        # first. `_email_taken` distinguishes that from a real integrity fault:
        # the user row was rolled back, so a True answer can only come from the
        # other request.
        if _email_taken(normalised_email):
            return None
        raise

    return user


# ---------------------------------------------------------------------------
# Email verification (REQ-FR-001, decision D-3)
# ---------------------------------------------------------------------------

# A distinct salt, not the default. `SECRET_KEY` signs every `signing` use in the
# project, so without a namespace a password-reset token (batch 1.10) could be
# replayed here as a verification token. The salt is a constant, not a secret:
# changing it invalidates every outstanding link, which is the intended way to
# revoke them all at once.
VERIFICATION_TOKEN_SALT = "accounts.email_verification"

# Prefix of the per-user cooldown key. Exposed because a test deletes one user's
# key to simulate the window passing; a test that rebuilt the string itself
# would keep passing after the service changed it.
RESEND_THROTTLE_KEY_PREFIX = "email-verification:resend"


class VerificationError(ValueError):
    """A verification link could not be used.

    A `ValueError` so the batch 1.5 view can map it to a 400 without importing a
    service-specific type, while callers that need a distinct response (an
    already-verified click, say) can still catch the subclass.

    Messages never contain the token, the user id or the email. This text can
    reach a log line and an API error body, and the token is a bearer credential.
    """


class VerificationTokenExpired(VerificationError):
    """The signature is genuine but older than the configured lifetime."""


class InvalidVerificationToken(VerificationError):
    """The token is malformed, tampered with, or names no user."""


class EmailAlreadyVerified(VerificationError):
    """A usable token was presented for an account that is already verified.

    Kept separate from `InvalidVerificationToken` so batch 1.5 can show the
    success state (design.md page #11) instead of "this link is invalid".
    """


def resend_throttle_cache_key(user: User) -> str:
    """Cache key for `user`'s resend cooldown.

    Per user, not per address: the caller already holds the account, and a
    lookup by email here would turn the resend view into an enumeration oracle.
    """
    return f"{RESEND_THROTTLE_KEY_PREFIX}:{user.pk}"


def make_verification_token(user: User) -> str:
    """Return a signed, expiring token for `user` (REQ-FR-001, D-3).

    The token is **not** the user id. The id is base64-encoded first, then signed
    with a timestamp and an HMAC, so the literal id is not readable in the link
    and the value cannot be guessed, edited or replayed after the lifetime in
    `EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS`. Using the raw id would make every
    account verifiable by anyone who could guess one. The encoding is not
    secrecy — the signature is what stops tampering — it keeps internal ids out
    of mail logs, browser history and referrer headers.

    The clock starts when the token is created, which is why the sending task
    generates it rather than the caller: a queued task must not spend the link's
    lifetime waiting in the broker.
    """
    payload = urlsafe_base64_encode(str(user.pk).encode())
    return TimestampSigner(salt=VERIFICATION_TOKEN_SALT).sign(payload)


def verify_email(token: str) -> User:
    """Mark the token's account as verified and return it.

    Exactly once: the row is locked and re-read inside the transaction, so two
    requests with the same link cannot both flip the flag. The second one raises
    `EmailAlreadyVerified`.

    Raises:
        VerificationTokenExpired: the signature is older than the configured
            lifetime.
        InvalidVerificationToken: the token is malformed, tampered with, or the
            account no longer exists. One error for all three: telling an
            anonymous caller which one it was helps nobody legitimate.
        EmailAlreadyVerified: the account was already verified, by this token or
            another one.
    """
    if not isinstance(token, str) or not token.strip():
        raise InvalidVerificationToken("A verification token is required.")

    try:
        signed_user_id = TimestampSigner(salt=VERIFICATION_TOKEN_SALT).unsign(
            token.strip(),
            max_age=settings.EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS,
        )
    except SignatureExpired as exc:
        raise VerificationTokenExpired(
            "This verification link has expired. Request a new one."
        ) from exc
    except BadSignature as exc:
        raise InvalidVerificationToken("This verification link is invalid.") from exc

    try:
        user_id = uuid.UUID(urlsafe_base64_decode(signed_user_id).decode())
    except (AttributeError, TypeError, ValueError) as exc:
        raise InvalidVerificationToken("This verification link is invalid.") from exc

    try:
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user_id)
            if user.email_verified:
                raise EmailAlreadyVerified("This email address is already verified.")
            user.email_verified = True
            user.save(update_fields=["email_verified"])
    except User.DoesNotExist as exc:
        raise InvalidVerificationToken("This verification link is invalid.") from exc

    return user


def _dispatch_verification_email(user: User) -> None:
    """Queue the task for after the surrounding transaction commits.

    The task looks the user up by id. Dispatching inside `register_user`'s
    transaction would race the commit: a worker can pick the task up before the
    row is visible, find nothing, and drop the only verification email. In
    autocommit, `on_commit` runs the callback immediately.
    """
    # Imported here, not at module scope: `accounts.tasks` imports the token
    # helper from this module.
    from accounts.tasks import send_verification_email

    user_id = str(user.pk)
    transaction.on_commit(lambda: send_verification_email.delay(user_id))


def queue_verification_email(user: User) -> None:
    """Send the first verification email and start the resend cooldown.

    Registration calls this once, after the account exists. Starting the
    cooldown here is what makes design.md X02's "available in 0:45" true on the
    pending page: without it the first click would send a second email at once.
    """
    cache.add(
        resend_throttle_cache_key(user),
        1,
        timeout=settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
    )
    _dispatch_verification_email(user)


def resend_verification_email(user: User) -> bool:
    """Queue another verification email unless the cooldown is running.

    Returns True when a send was queued. False means the account is already
    verified, is inactive, or is inside its cooldown. Batch 1.5 must answer all
    three identically, so the boolean is for tests, not for an error body.

    `cache.add` is the throttle: it sets the key only if it is absent, atomically,
    so two concurrent resends cannot both pass the check the way a
    `get`-then-`set` would. The key is written before dispatch on purpose -- a
    provider outage must not turn into a retry loop.
    """
    if user.email_verified or not user.is_active:
        return False

    if not cache.add(
        resend_throttle_cache_key(user),
        1,
        timeout=settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
    ):
        return False

    _dispatch_verification_email(user)
    return True
