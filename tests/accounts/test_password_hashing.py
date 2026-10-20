"""The password hasher contract (REQ-SEC-001, D-9).

This file exists because `settings.PASSWORD_HASHERS` under `config.settings.ci`
is deliberately **MD5**, so a test that hashed a password through the running
settings would prove nothing about the production hasher. These tests read
`config.settings.base` directly, which is the module `production.py` inherits
from.

`Argon2PasswordHasher` is Argon2**id**. The distinction matters: Argon2i and
Argon2d are different KDFs with different properties, and "we use Argon2" is not
the requirement's wording. `params().type` is the concrete check.
"""

from __future__ import annotations

import argon2.low_level
from django.conf import settings
from django.contrib.auth.hashers import Argon2PasswordHasher

import config.settings.base as base

ORDERED_HASHER = "django.contrib.auth.hashers.Argon2PasswordHasher"


def test_base_settings_try_argon2_first():
    # First, not merely present: `check_password` walks the list in order, so a
    # hasher that is listed but not first is dead configuration for new users.
    assert base.PASSWORD_HASHERS[0] == ORDERED_HASHER


def test_the_pinned_hasher_is_argon2id():
    hasher = Argon2PasswordHasher()
    assert hasher.params().type is argon2.low_level.Type.ID


def test_the_running_test_settings_keep_the_fast_override():
    # Asserted so nobody "fixes" CI to Argon2 and turns every login test into a
    # 100 ms KDF call -- and so it is obvious why the two tests above read the
    # base module instead of live settings.
    assert settings.PASSWORD_HASHERS == [
        "django.contrib.auth.hashers.MD5PasswordHasher"
    ]
