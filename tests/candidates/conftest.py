"""Fixtures for the candidates tests.

Same shape as `tests/accounts/conftest.py`: the role groups are loaded from
`core/fixtures/groups.json` rather than created here, because the fixture is the
D-2 source of truth. Pytest does not share a sibling app's `conftest.py`, so the
two helpers are repeated locally rather than making every accounts test import a
candidates module.
"""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from accounts.models import User


@pytest.fixture
def resume_storage(tmp_path, settings):
    """Django's default storage, rooted at a per-test temporary directory.

    The resume endpoints read and delete objects through `default_storage`, so
    the tests need a real backend without touching the repository's `media/`
    directory. Overriding `STORAGES` also resets `default_storage`, which
    overriding only `MEDIA_ROOT` does not reliably do once its location is
    cached.
    """
    settings.STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(tmp_path)},
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
    return tmp_path


@pytest.fixture
def put_object(resume_storage):
    """Write bytes at a storage key, creating parent directories."""

    def _put(key: str, data: bytes):
        path = resume_storage / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    return _put


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
