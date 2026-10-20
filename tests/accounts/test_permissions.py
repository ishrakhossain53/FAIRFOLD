"""Fixture-driven tests for the role permission classes (REQ-FR-038, D-2).

The classes are tested against the **seeded** groups, not groups the test made
up: the fixture is the source of truth for the role names, and a test that
creates `employer_manager` itself would not notice the fixture losing it.

Every role is exercised against every class, and a meta-test asserts the matrix
still contains all 16 combinations. A missing row is how a permission test suite
quietly stops covering the class that later gets inverted.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser, Group
from rest_framework.test import APIRequestFactory

from accounts.models import ROLES, User
from accounts.permissions import (
    IsCandidate,
    IsEmployer,
    IsEmployerAdmin,
    IsPlatformAdmin,
)

PERMISSION_CLASSES = (IsCandidate, IsEmployer, IsEmployerAdmin, IsPlatformAdmin)

# role, permission class, expected result. Spelled out rather than derived from
# one rule: `employer_hr` passing IsEmployer but not IsEmployerAdmin is the
# distinction most likely to be implemented backwards.
ROLE_MATRIX = [
    ("candidate", IsCandidate, True),
    ("candidate", IsEmployer, False),
    ("candidate", IsEmployerAdmin, False),
    ("candidate", IsPlatformAdmin, False),
    ("employer_hr", IsCandidate, False),
    ("employer_hr", IsEmployer, True),
    ("employer_hr", IsEmployerAdmin, False),
    ("employer_hr", IsPlatformAdmin, False),
    ("employer_manager", IsCandidate, False),
    ("employer_manager", IsEmployer, True),
    ("employer_manager", IsEmployerAdmin, True),
    ("employer_manager", IsPlatformAdmin, False),
    ("interviewer", IsCandidate, False),
    ("interviewer", IsEmployer, False),
    ("interviewer", IsEmployerAdmin, False),
    ("interviewer", IsPlatformAdmin, False),
]


def _request_for(user):
    """A DRF request carrying `user`, as a view would receive it."""
    request = APIRequestFactory().get("/")
    request.user = user
    return request


class TestSeededRoles:
    def test_fixture_contains_exactly_the_documented_roles(self, role_groups):
        assert set(Group.objects.values_list("name", flat=True)) == set(ROLES)

    def test_admin_is_not_a_group(self, role_groups):
        # D-2: `admin` is `is_staff`/`is_superuser`. A group by that name would be
        # a second, unseeded role that no requirement defines.
        assert not Group.objects.filter(name="admin").exists()


@pytest.mark.django_db
class TestRoleMatrix:
    @pytest.mark.parametrize("role, permission, expected", ROLE_MATRIX)
    def test_each_role_against_each_permission_class(
        self, make_user, role, permission, expected
    ):
        user = make_user(role)
        assert permission().has_permission(_request_for(user), None) is expected

    def test_the_matrix_covers_every_role_and_class(self):
        covered = {(role, permission) for role, permission, _ in ROLE_MATRIX}
        expected = {
            (role, permission) for role in ROLES for permission in PERMISSION_CLASSES
        }
        assert covered == expected, (
            "ROLE_MATRIX has lost a role/permission combination. Every role must "
            "be asserted against every class (batch 1.2 acceptance criterion)."
        )

    def test_a_user_with_no_role_passes_nothing(self, make_user):
        user = make_user()
        for permission in PERMISSION_CLASSES:
            assert permission().has_permission(_request_for(user), None) is False


@pytest.mark.django_db
class TestPlatformAdmin:
    def test_staff_user_in_no_group_is_a_platform_admin(self, make_user):
        user = make_user(is_staff=True)
        assert IsPlatformAdmin().has_permission(_request_for(user), None) is True
        # The staff flag is not a role: it must not leak into the role classes.
        for permission in (IsCandidate, IsEmployer, IsEmployerAdmin):
            assert permission().has_permission(_request_for(user), None) is False

    def test_superuser_is_a_platform_admin(self):
        user = User.objects.create_superuser("root@example.com", "correct horse")
        assert IsPlatformAdmin().has_permission(_request_for(user), None) is True

    def test_superuser_without_staff_is_still_accepted(self):
        # D-2 words admin as "is_staff/is_superuser". create_superuser sets both,
        # but a hand-cleared staff flag must not lock a superuser out.
        user = User.objects.create_superuser("root2@example.com", "correct horse")
        user.is_staff = False
        user.save(update_fields=["is_staff"])
        assert IsPlatformAdmin().has_permission(_request_for(user), None) is True

    def test_a_role_holder_is_not_a_platform_admin(self, make_user):
        # Covered by the matrix too; kept explicit because the failure mode is an
        # employer reaching the admin API through a role group.
        for role in ("candidate", "employer_hr", "employer_manager", "interviewer"):
            user = make_user(role)
            assert (
                IsPlatformAdmin().has_permission(_request_for(user), None) is False
            ), role


@pytest.mark.django_db
class TestDeniedUsers:
    @pytest.mark.parametrize("permission", PERMISSION_CLASSES)
    def test_anonymous_user_is_denied(self, permission):
        request = _request_for(AnonymousUser())
        assert permission().has_permission(request, None) is False

    @pytest.mark.parametrize("permission", PERMISSION_CLASSES)
    def test_inactive_user_is_denied(self, make_user, permission):
        # Authentication rejects inactive users already; this pins the classes so
        # a hand-built request cannot bypass that.
        user = make_user(
            "candidate", "employer_hr", "employer_manager", is_active=False
        )
        assert permission().has_permission(_request_for(user), None) is False

    @pytest.mark.parametrize("permission", PERMISSION_CLASSES)
    def test_inactive_staff_is_denied(self, make_user, permission):
        user = make_user(is_staff=True, is_active=False)
        assert permission().has_permission(_request_for(user), None) is False
