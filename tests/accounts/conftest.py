"""Shared fixtures for the accounts tests.

The role groups are loaded from `core/fixtures/groups.json`, not created with
`Group.objects.create`. The fixture is the source of truth (decision D-2), so a
test that creates its own `candidate` group would keep passing after the fixture
lost the role.
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
    """Build a user and put them in the named groups.

    Emails are generated because the address is unique and most tests do not care
    what it is; pass `email=` when the test asserts on it.
    """

    def _make_user(*roles: str, **extra) -> User:
        email = extra.pop("email", f"user-{uuid.uuid4().hex[:12]}@example.com")
        password = extra.pop("password", None)
        user = User.objects.create_user(email, password, **extra)
        for role in roles:
            user.groups.add(Group.objects.get(name=role))
        return user

    return _make_user
