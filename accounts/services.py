"""Role assignment: the one place that adds a role to a user.

Roles are Django **groups**, seeded from `core/fixtures/groups.json` (REQ-FR-047,
decision D-2). There is no `role` column, so nothing in the database stops a
second, conflicting group from being added. `assign_role` is that stop:
REQ-FR-045 says an employer cannot hold both the candidate and employer roles.

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
from django.db import transaction

from accounts.models import CANDIDATE_ROLE, EMPLOYER_ROLES, ROLES, User


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
