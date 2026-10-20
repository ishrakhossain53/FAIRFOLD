"""DRF permission classes for the documented roles (REQ-FR-038, REQ-FR-047, D-2).

Four classes, matching the four role questions a view asks: is this a candidate,
an employer, an employer manager, or a platform administrator?

**Where the answer comes from.** Group membership, through the `User.is_*`
properties. These classes do not call `has_perm`: the seeded groups carry no
permission codenames — the requirements define roles, not codenames — and
inventing one here would be a spec change rather than code. `has_perm` remains
the mechanism for object- and action-level checks in later apps.

**D-2 vocabulary.** The employer-admin role is `employer_manager`. The class is
named `IsEmployerAdmin` to match the existing `User.is_employer_admin` helper
that the characterization tests pin; it checks the `employer_manager` group.
"Admin" on its own is not a group: D-2 keeps `admin` as `is_staff`/`is_superuser`
(Complete Doc RBAC row; `prd.md` §10.1), so `IsPlatformAdmin` checks those flags
and never `has_role("admin")`.

**`is_active` is checked as well.** JWT and session authentication already reject
an inactive user, so this is redundant in the normal path — but a permission class
is the last check before a view runs, and a hand-built request (a test, a
signal-triggered call, a future authentication backend) must not pass it either.

Every class denies an anonymous user: DRF's global default is `IsAuthenticated`,
and a view that opts into one of these must not accidentally opt out of login.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


def _active_user(request: Request):
    """The authenticated, active user on `request`, or None.

    Returning None for an anonymous or inactive user keeps every subclass's
    `has_permission` a single expression instead of repeating the same guards.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or not user.is_active:
        return None
    return user


class _RolePermission(BasePermission):
    """Base class: allow exactly the users whose role property is true."""

    role_property = ""

    def has_permission(self, request: Request, view: APIView | None) -> bool:
        user = _active_user(request)
        if user is None:
            return False
        return bool(getattr(user, self.role_property))


class IsCandidate(_RolePermission):
    """The `candidate` group only (REQ-FR-045)."""

    role_property = "is_candidate"


class IsEmployer(_RolePermission):
    """`employer_hr` or `employer_manager` (REQ-FR-047).

    Not `interviewer`: that role may read an interview it is assigned to, but it
    is not an employer for job, company-profile or team management.
    """

    role_property = "is_employer"


class IsEmployerAdmin(_RolePermission):
    """`employer_manager` only — team and company settings (REQ-FR-038, D-2)."""

    role_property = "is_employer_admin"


class IsPlatformAdmin(BasePermission):
    """A platform administrator: `is_staff` or `is_superuser` (D-2).

    Not a group. `admin` in the requirements means the staff flag, so a user in
    no role group at all can pass this — and a user in every role group passes
    only if the flag is set.
    """

    def has_permission(self, request: Request, view: APIView | None) -> bool:
        user = _active_user(request)
        if user is None:
            return False
        # `create_superuser` sets both flags, but a superuser with `is_staff`
        # cleared by hand is still an administrator in the docs' wording
        # ("`is_staff`/`is_superuser`"), so accept either.
        return bool(user.is_staff or user.is_superuser)
