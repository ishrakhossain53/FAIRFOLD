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
"""

from __future__ import annotations

from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

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
