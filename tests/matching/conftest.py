"""Fixtures for the matching tests.

Same shape as `tests/employers/conftest.py`: the role groups come from
`core/fixtures/groups.json` (the D-2 source of truth), not from hand-built
groups. Pytest does not share a sibling app's `conftest.py`, so the helper is
repeated locally rather than making every application test import an accounts
module.
"""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from accounts.models import User


@pytest.fixture
def role_groups(db):
    """The seeded role groups, exactly as `manage.py seed` installs them."""
    call_command("loaddata", "groups", verbosity=0)


@pytest.fixture
def make_user(role_groups):
    """Build a user and put them in the named groups."""

    def _make_user(*roles: str, **extra) -> User:
        email = extra.pop("email", f"user-{uuid.uuid4().hex[:12]}@example.com")
        password = extra.pop("password", None)
        user = User.objects.create_user(email, password, **extra)
        for role in roles:
            user.groups.add(Group.objects.get(name=role))
        return user

    return _make_user
