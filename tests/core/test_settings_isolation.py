"""Tests for the settings-pollution guard in `test_production_settings.py`.

`production.py` does `from base import *`, which copies *references*. Importing it
therefore rewrites the live `DATABASES` dict, and a test session that imports it
without restoring leaves `sslmode="require"` in place -- so test-database teardown
fails with "server does not support SSL, but SSL was required".

That failure is worth guarding directly, because the guard is subtle and its
absence is silent. `_restore_in_place` has already shipped two versions that both
looked correct and both restored nothing:

1. `snapshot = deepcopy(...)` then reassigning `settings.DATABASES = snapshot` --
   replaced the top-level name while the live connection kept its reference.
2. `live.clear(); live.update(snapshot)` -- clearing *before* the loop meant
   `live.get(key)` was always `None`, so nested dicts were replaced anyway.

Both produced a passing suite. Only the third version recurses in place. These
tests exist so that version cannot be silently reverted to either of the others.
"""

from __future__ import annotations

import copy

from django.conf import settings as django_settings

from tests.core.test_production_settings import _restore_in_place


class TestRestoreInPlace:
    def test_restores_a_changed_scalar(self):
        live = {"sslmode": "require"}
        _restore_in_place(live, {"sslmode": "prefer"})
        assert live == {"sslmode": "prefer"}

    def test_restores_a_nested_value_without_replacing_the_dict(self):
        # The property that matters. Django caches a reference to the nested
        # OPTIONS dict; replacing it leaves the connection reading stale config.
        options = {"sslmode": "require"}
        live = {"default": {"OPTIONS": options}}
        held_by_connection = live["default"]["OPTIONS"]

        snapshot = copy.deepcopy(live)
        _restore_in_place(live, snapshot)
        _restore_in_place(live, {"default": {"OPTIONS": {"sslmode": "prefer"}}})

        assert held_by_connection["sslmode"] == "prefer"

    def test_removes_keys_the_snapshot_does_not_have(self):
        live = {"default": {"OPTIONS": {"sslmode": "require"}, "EXTRA": 1}}
        _restore_in_place(live, {"default": {"OPTIONS": {"sslmode": "prefer"}}})
        assert "EXTRA" not in live["default"]

    def test_handles_a_key_absent_from_the_live_dict(self):
        live: dict = {}
        _restore_in_place(live, {"default": {"OPTIONS": {"sslmode": "prefer"}}})
        assert live == {"default": {"OPTIONS": {"sslmode": "prefer"}}}

    def test_is_idempotent(self):
        live = {"default": {"OPTIONS": {"sslmode": "require"}}}
        snapshot = {"default": {"OPTIONS": {"sslmode": "prefer"}}}
        _restore_in_place(live, snapshot)
        once = copy.deepcopy(live)
        _restore_in_place(live, snapshot)
        assert live == once


class TestLiveSettingsAreNotPolluted:
    def test_the_session_database_settings_are_intact(self):
        """The end-to-end check: the running session kept CI's sslmode.

        Reading the value is enough -- by the time this runs, every
        `production_settings` fixture has torn down, so a leaked
        `sslmode="require"` is directly visible here.
        """
        assert django_settings.DATABASES["default"]["OPTIONS"]["sslmode"] == "prefer"

    def test_the_connection_agrees_with_the_settings(self):
        # A half-restored state is worse than either extreme: the settings object
        # says one thing and the live connection another, and which one wins
        # depends on timing rather than on code.
        from django.db import connections

        connection = connections["default"]
        if not connection.settings_dict:
            pytest_skip_unconfigured_connection()
        assert (
            connection.settings_dict["OPTIONS"]["sslmode"]
            == django_settings.DATABASES["default"]["OPTIONS"]["sslmode"]
        )


def pytest_skip_unconfigured_connection() -> None:
    """No live connection configured -- nothing to compare against.

    Reaching here means no test in this session has touched the database, so the
    comparison the caller wanted does not apply.
    """
    import pytest

    pytest.skip("no database connection has been established in this session")
