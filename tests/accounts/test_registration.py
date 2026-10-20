"""Tests for `accounts.services.register_user` (REQ-FR-001).

Five things are pinned here because each is easy to get subtly wrong:

* the account is created **unverified** — `email_verified=False` is what makes
  the verification step in batch 1.4 meaningful;
* only the two self-assignable roles are accepted (REQ-FR-045, REQ-FR-047);
* the password runs through `AUTH_PASSWORD_VALIDATORS`, not just a length check;
* a duplicate email is indistinguishable from success at the service boundary,
  because the future API must not become an account-enumeration oracle;
* the user, the role and the audit entry are one transaction, so a failure on
  the last two does not leave a user who cannot log in or has no role.

The audit entry is asserted to contain no email or name: `AuditLogEntry` is the
one table a compliance export would not expect to find PII in (AGENTS.md).
"""

from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from accounts import services
from accounts.models import ROLES, User
from accounts.services import (
    REGISTRATION_AUDIT_ACTION,
    SELF_ASSIGNABLE_ROLES,
    RoleNotSelfAssignableError,
    register_user,
)
from core.models import AuditLogEntry

pytestmark = pytest.mark.django_db

# Long enough, not numeric, not in the common-password list and not similar to
# the names used below. A famous xkcd password is a bad test constant: several
# of them are in Django's common-password list.
STRONG_PASSWORD = "Wanderlust7Quartz-Meadow"


def _register(email="ada@example.com", role="candidate", **overrides):
    """Call `register_user` with valid defaults and one changed field."""
    fields = {
        "email": email,
        "password": STRONG_PASSWORD,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "role": role,
        **overrides,
    }
    return register_user(**fields)


class TestSuccessfulRegistration:
    def test_creates_an_unverified_candidate(self, role_groups):
        user = _register()

        assert user is not None
        fresh = User.objects.get(pk=user.pk)
        assert fresh.email_verified is False
        assert fresh.is_active is True
        assert fresh.has_role("candidate") is True
        assert fresh.groups.count() == 1

    def test_employer_signup_gets_the_base_employer_role(self, role_groups):
        # design.md page 6 offers "Candidate" or "Employer". The employer choice
        # is `employer_hr`; `employer_manager` is a later promotion and
        # `interviewer` is an invitation, so neither is self-assignable.
        user = _register(role="employer_hr")

        assert user is not None
        assert user.has_role("employer_hr") is True
        assert user.is_employer is True
        assert user.is_employer_admin is False

    def test_password_is_stored_as_a_hash_not_as_text(self, role_groups):
        user = _register()

        assert user.password != STRONG_PASSWORD
        assert user.check_password(STRONG_PASSWORD) is True

    def test_returns_the_created_user(self, role_groups):
        user = _register()

        assert isinstance(user, User)
        assert User.objects.filter(pk=user.pk).exists()

    def test_only_candidate_and_the_base_employer_role_are_self_assignable(self):
        # Pinned literally as well as used in the parametrisation below: adding a
        # role to the constant must be a deliberate edit with a failing test.
        assert SELF_ASSIGNABLE_ROLES == ("candidate", "employer_hr")

    @pytest.mark.parametrize("role", SELF_ASSIGNABLE_ROLES)
    def test_every_self_assignable_role_is_accepted(self, role_groups, role):
        # The parametrisation reads the constant, so adding a role to the public
        # form without adding it here fails rather than silently going untested.
        user = _register(role=role)
        assert user is not None
        assert user.has_role(role) is True


class TestEmailNormalisation:
    def test_strips_and_lowercases_the_whole_address(self, role_groups):
        user = _register(email="  Ada@Example.COM  ")

        assert user is not None
        assert user.email == "ada@example.com"
        assert User.objects.filter(email="ada@example.com").count() == 1

    @pytest.mark.parametrize("email", ["", "   ", "not-an-email", "ada@example"])
    def test_rejects_a_missing_or_malformed_address(self, role_groups, email):
        with pytest.raises(ValidationError):
            _register(email=email)

        assert User.objects.count() == 0
        assert AuditLogEntry.objects.count() == 0


class TestDuplicateEmail:
    def test_returns_none_and_creates_nothing(self, role_groups):
        existing = User.objects.create_user("ada@example.com", STRONG_PASSWORD)

        result = _register(email="ada@example.com")

        assert result is None
        assert User.objects.count() == 1
        existing.refresh_from_db()
        assert existing.check_password(STRONG_PASSWORD) is True
        assert AuditLogEntry.objects.count() == 0

    def test_the_existing_address_is_matched_after_normalisation(self, role_groups):
        User.objects.create_user("ada@example.com", STRONG_PASSWORD)

        assert _register(email="  ADA@Example.com ") is None
        assert User.objects.count() == 1

    def test_a_duplicate_that_appears_after_the_check_is_absorbed(
        self, monkeypatch, role_groups
    ):
        # The pre-check passed, then another request inserted the address first.
        # The second `_email_taken` call is the real one, so the IntegrityError
        # is recognised as a duplicate rather than re-raised as a server fault.
        User.objects.create_user("ada@example.com", STRONG_PASSWORD)
        real = services._email_taken
        calls: list[str] = []

        def fake(email: str) -> bool:
            calls.append(email)
            return False if len(calls) == 1 else real(email)

        monkeypatch.setattr(services, "_email_taken", fake)

        assert _register(email="ada@example.com") is None
        assert User.objects.filter(email="ada@example.com").count() == 1

    def test_a_real_integrity_error_is_not_swallowed(self, monkeypatch, role_groups):
        # If the IntegrityError is not about the email, the caller must see it.
        # `_email_taken` stays False, so the handler re-raises.
        monkeypatch.setattr(services, "_email_taken", lambda email: False)

        def explode(**kwargs):
            raise services.IntegrityError("unrelated constraint")

        monkeypatch.setattr(services.User.objects, "create_user", explode)

        with pytest.raises(services.IntegrityError):
            _register()


class TestPasswordValidation:
    @pytest.mark.parametrize(
        "password",
        [
            "short",  # MinimumLengthValidator (min_length=12)
            "123456789012345",  # NumericPasswordValidator
            "startfinding",  # CommonPasswordValidator; 12 chars, so length passes
        ],
    )
    def test_weak_passwords_are_refused(self, role_groups, password):
        with pytest.raises(ValidationError):
            _register(password=password)

        assert User.objects.count() == 0
        assert AuditLogEntry.objects.count() == 0

    @pytest.mark.parametrize("password", ["", None])
    def test_a_missing_password_is_refused(self, role_groups, password):
        with pytest.raises(ValidationError):
            _register(password=password)

        assert User.objects.count() == 0

    def test_the_similarity_check_uses_the_new_accounts_own_name(self, role_groups):
        # The validator needs a user object to compare against; passing None
        # would make this test pass while the real check never ran.
        with pytest.raises(ValidationError):
            _register(first_name="Alexandra", password="alexandra12345")

        assert User.objects.count() == 0


class TestForbiddenRoles:
    @pytest.mark.parametrize(
        "role",
        ["employer_manager", "interviewer", "admin", "employer", "", "Candidate"],
    )
    def test_a_role_the_public_form_may_not_grant_is_refused(self, role_groups, role):
        # `admin` is a flag in D-2, not a group; `employer` is the form label, not
        # a group name; `Candidate` is a case mistake that must not create a
        # second group no `has_role` check reads.
        with pytest.raises(RoleNotSelfAssignableError):
            _register(role=role)

        assert User.objects.count() == 0
        assert AuditLogEntry.objects.count() == 0
        # The seeded groups themselves are loaded by `role_groups`; what must not
        # exist is a *new* group for an unknown spelling such as "Candidate".
        if role not in ROLES:
            assert not Group.objects.filter(name=role).exists()

    def test_the_error_is_a_value_error_and_names_no_person(self, role_groups):
        with pytest.raises(RoleNotSelfAssignableError) as excinfo:
            _register(role="interviewer")

        message = str(excinfo.value)
        assert "ada@example.com" not in message
        assert "interviewer" in message
        assert isinstance(excinfo.value, ValueError)


class TestTransaction:
    def test_a_failed_role_assignment_leaves_no_user(self, monkeypatch, role_groups):
        def boom(user, role):
            raise RuntimeError("role assignment failed")

        monkeypatch.setattr(services, "assign_role", boom)

        with pytest.raises(RuntimeError):
            _register()

        assert not User.objects.filter(email="ada@example.com").exists()
        assert AuditLogEntry.objects.count() == 0

    def test_a_missing_seeded_group_rolls_the_user_back(self):
        # No `role_groups` fixture: `manage.py seed` has not run, which is a
        # deployment error. It must still leave no half-created user behind.
        with pytest.raises(Group.DoesNotExist):
            _register()

        assert not User.objects.filter(email="ada@example.com").exists()
        assert AuditLogEntry.objects.count() == 0


class TestRegistrationAudit:
    def test_writes_exactly_one_entry_for_the_new_user(self, role_groups):
        user = _register()

        entry = AuditLogEntry.objects.get()
        assert entry.action == REGISTRATION_AUDIT_ACTION
        assert entry.actor_id == user.id
        assert entry.resource_type == "user"
        assert entry.resource_id == user.id
        assert entry.details == {"role": "candidate"}

    def test_the_entry_holds_no_email_or_name(self, role_groups):
        _register(email="ada@example.com", first_name="Ada", last_name="Lovelace")

        entry = AuditLogEntry.objects.get()
        rendered = " ".join(
            [
                entry.action,
                entry.resource_type or "",
                str(entry.resource_id or ""),
                json.dumps(entry.details, sort_keys=True),
                entry.result or "",
                entry.user_agent or "",
                entry.ip_address or "",
                str(entry),
            ]
        )

        assert "ada@example.com" not in rendered
        assert "Lovelace" not in rendered
        # "Ada" alone is checked in the structured fields, not the whole string:
        # the action name and ISO timestamp contain no such word, but asserting
        # a three-letter substring against a timestamp invites a flake.
        assert "Ada" not in json.dumps(entry.details)
        assert "Ada" not in str(entry)

    def test_two_registrations_write_two_entries(self, role_groups):
        _register(email="ada@example.com")
        _register(email="grace@example.com", first_name="Grace", last_name="Hopper")

        assert AuditLogEntry.objects.count() == 2
