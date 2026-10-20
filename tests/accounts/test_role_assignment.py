"""Tests for `accounts.services.assign_role` (REQ-FR-045, REQ-FR-047, D-2).

The done-when for this batch is that `assign_role` rejects a second, conflicting
role — so every conflicting pair is asserted in both directions, and the state
after the refusal is re-read from the database rather than trusted to the
in-memory instance. The service is the only guard: roles are groups, and the
database has no constraint that could enforce the rule.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from accounts.models import ROLES, User
from accounts.services import RoleConflictError, assign_role

CONFLICTING_PAIRS = [
    ("candidate", "employer_hr"),
    ("candidate", "employer_manager"),
    ("employer_hr", "candidate"),
    ("employer_manager", "candidate"),
]


class TestAssignRole:
    @pytest.mark.parametrize("role", ROLES)
    def test_assigns_each_documented_role(self, make_user, role):
        user = make_user()
        group = assign_role(user, role)
        assert group.name == role
        assert user.has_role(role) is True

    def test_returns_the_group_so_a_caller_can_audit_without_a_second_query(
        self, make_user
    ):
        user = make_user()
        group = assign_role(user, "candidate")
        assert isinstance(group, Group)
        assert group == Group.objects.get(name="candidate")

    def test_is_idempotent(self, make_user):
        # Invitation acceptance can be retried; a second call must not duplicate
        # the membership or raise.
        user = make_user()
        assign_role(user, "candidate")
        assign_role(user, "candidate")
        assert user.groups.filter(name="candidate").count() == 1

    def test_both_employer_roles_may_be_held_together(self, make_user):
        # REQ-FR-045 forbids candidate + employer, not employer_hr + manager.
        # Promoting an HR user must not require removing the old role.
        user = make_user()
        assign_role(user, "employer_hr")
        assign_role(user, "employer_manager")
        assert user.is_employer is True
        assert user.is_employer_admin is True
        assert user.groups.count() == 2

    def test_interviewer_does_not_conflict_with_candidate(self, make_user):
        # Deliberate reading of REQ-FR-045: it names only the candidate/employer
        # conflict. `interviewer` is an employer-team role in REQ-FR-047, and
        # nothing forbids a candidate from holding it. Locked here so widening
        # the rule has to be a deliberate edit.
        user = make_user("candidate")
        assign_role(user, "interviewer")
        assert user.groups.count() == 2


class TestMutualExclusivity:
    @pytest.mark.parametrize("held, refused", CONFLICTING_PAIRS)
    def test_rejects_a_second_conflicting_role(self, make_user, held, refused):
        user = make_user(held)
        with pytest.raises(RoleConflictError):
            assign_role(user, refused)

        # Re-read: the refusal must have left the database untouched, not just
        # the object the test passed in.
        fresh = User.objects.get(pk=user.pk)
        assert fresh.has_role(refused) is False
        assert fresh.has_role(held) is True
        assert fresh.groups.count() == 1

    def test_conflict_message_names_groups_and_not_the_person(self, make_user):
        # The message can reach a log line or an API error. It must not carry the
        # email or name (AGENTS.md privacy invariants).
        user = make_user("candidate", email="ada@example.com")
        with pytest.raises(RoleConflictError) as excinfo:
            assign_role(user, "employer_hr")

        message = str(excinfo.value)
        assert "ada@example.com" not in message
        assert "candidate" in message
        assert "employer_hr" in message

    def test_conflict_error_is_a_value_error(self):
        # A registration or team view can treat it as a bad request without
        # importing the service-specific type.
        assert issubclass(RoleConflictError, ValueError)


class TestUnknownRoles:
    @pytest.mark.parametrize("role", ["admin", "Candidate", "", "employer_admin"])
    def test_rejects_an_unknown_role_without_creating_a_group(self, make_user, role):
        # `employer_admin` is the pre-D-2 spelling; `admin` is a flag in D-2,
        # not a group. Neither may be created by a typo.
        user = make_user()
        with pytest.raises(ValueError):
            assign_role(user, role)
        assert user.groups.count() == 0
        assert not Group.objects.filter(name=role).exists()

    def test_requires_the_seeded_fixture(self, db):
        # `get()`, not `get_or_create()`: running before `manage.py seed` is a
        # deployment error, and creating the group here would hide it.
        user = User.objects.create_user("noseed@example.com")
        with pytest.raises(Group.DoesNotExist):
            assign_role(user, "candidate")
