"""Characterization tests for `accounts.User` (REQ-FR-001, REQ-FR-003).

`User` exists before anything depends on it -- it is `AUTH_USER_MODEL` -- so these
tests pin the behaviour that the later batches (registration, login, lockout,
invitations) are allowed to assume. They describe *this* code, not a design we
would prefer: where a test documents a wart, it says so in the assertion message
instead of asserting the behaviour we want, because changing the behaviour is a
maintainer's decision and not a test's.

Two things they deliberately do NOT do:

* No registration, view, serializer or form is touched. Those are batches 1.3+.
* Roles are Django **groups** (REQ-FR-047, `core/fixtures/groups.json`), never a
  column, so every role assertion goes through `has_role`/`groups`.

`TestRolesConstant` needs no database. Everything else is PostgreSQL-only, which
is what `config.settings.ci` runs against; there is no SQLite path.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import ROLES, User
from core.management.commands.seed import load_json_fixture


class TestRolesConstant:
    """`accounts.models.ROLES` is the code's copy of the role vocabulary.

    It is compared with the fixture here rather than trusted, because `seed`
    verifies the *database* against its own constant; an app constant that has
    drifted from `core/fixtures/groups.json` is invisible to that command. The
    fixture is the source of truth (REQ-FR-047 / D-2).
    """

    def test_roles_matches_the_group_fixture(self):
        names = {row["fields"]["name"] for row in load_json_fixture("groups")}
        assert set(ROLES) == names, (
            "accounts.models.ROLES and core/fixtures/groups.json have drifted "
            "apart. The fixture is the source of truth for the role names "
            "(REQ-FR-047); update ROLES to match it."
        )

    def test_roles_has_no_duplicates(self):
        # A repeated name makes the fixture comparison pass while a display list
        # built from ROLES shows the same role twice.
        assert len(ROLES) == len(set(ROLES))


@pytest.mark.django_db
class TestCreateUser:
    def test_lowercases_the_email_on_the_way_in(self):
        user = User.objects.create_user("Ada@Example.COM", "correct horse battery")
        assert user.email == "ada@example.com"

    def test_hashes_a_supplied_password(self):
        user = User.objects.create_user("pw@example.com", "correct horse battery")
        assert user.password != "correct horse battery"
        assert user.check_password("correct horse battery") is True

    def test_sets_an_unusable_password_when_none_is_given(self):
        # `create_user` with no password is the OAuth path (the DDL's
        # `auth_provider`). An account created that way must land on an unusable
        # password, not a blank-but-usable one, or anyone can log into it.
        user = User.objects.create_user("oauth@example.com")
        assert user.has_usable_password() is False
        assert user.check_password("") is False

    def test_defaults_to_an_active_non_staff_non_superuser(self):
        user = User.objects.create_user("plain@example.com")
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_refuses_an_empty_email(self):
        # A user with no email cannot be logged into, and the failure is raised
        # before the insert rather than as a database error.
        with pytest.raises(ValueError):
            User.objects.create_user("")

    def test_the_same_address_in_a_different_case_is_a_duplicate(self):
        # Lower-casing happens in the manager *before* the insert, so the unique
        # index sees one address and the second attempt must collide.
        User.objects.create_user("ada@example.com")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user("ADA@EXAMPLE.COM")
        assert User.objects.filter(email__iexact="ada@example.com").count() == 1


@pytest.mark.django_db
class TestCreateSuperuser:
    def test_sets_staff_and_superuser_and_active(self):
        user = User.objects.create_superuser("root@example.com", "correct horse")
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.is_active is True

    def test_lowercases_the_email_too(self):
        user = User.objects.create_superuser("Root@Example.COM", "correct horse")
        assert user.email == "root@example.com"

    def test_refuses_either_flag_being_explicitly_false(self):
        # The manager raises rather than silently building a "superuser" who
        # cannot use the admin. Both contradictions are checked.
        with pytest.raises(ValueError):
            User.objects.create_superuser("a@example.com", "pw", is_staff=False)
        with pytest.raises(ValueError):
            User.objects.create_superuser("b@example.com", "pw", is_superuser=False)


@pytest.mark.django_db
class TestDirectCreateBypassesTheManager:
    """`User.objects.create(...)` is the ORM, not `create_user`.

    Documented, not endorsed. These two tests describe what the ORM does today, so
    that a later change to the index or a `save()` override shows up as a
    deliberate edit to a test rather than as a silent behaviour change. Whether
    email should be case-insensitively unique is a spec decision; it is reported,
    not fixed here.
    """

    def test_does_not_lowercase_the_email(self):
        user = User.objects.create(email="Direct@Example.COM")
        assert user.email == "Direct@Example.COM"
        assert User.objects.filter(email="Direct@Example.COM").exists()

    def test_two_rows_differing_only_in_case_can_coexist(self):
        User.objects.create(email="Case@example.com")
        User.objects.create(email="case@example.com")
        assert User.objects.filter(email__iexact="case@example.com").count() == 2


@pytest.mark.django_db
class TestIsLocked:
    """`is_locked()` is the supported way to read lockout state (REQ-FR-003).

    Reading `locked_until` directly is the documented mistake: a timestamp in the
    past is still a truthy value, and a view that tests it directly leaves the
    account locked forever.
    """

    def test_not_locked_when_never_locked(self):
        user = User.objects.create_user("free@example.com")
        assert user.locked_until is None
        assert user.is_locked() is False

    def test_locked_while_the_timestamp_is_in_the_future(self):
        user = User.objects.create_user("locked@example.com")
        user.locked_until = timezone.now() + timedelta(minutes=15)
        assert user.is_locked() is True

    def test_not_locked_once_the_timestamp_is_in_the_past(self):
        user = User.objects.create_user("expired@example.com")
        user.locked_until = timezone.now() - timedelta(seconds=1)
        assert user.is_locked() is False
        # The field is still populated: only the method knows it has elapsed.
        assert user.locked_until is not None

    def test_not_locked_at_the_exact_boundary(self):
        # `>` not `>=`: a lockout that has just expired is over.
        user = User.objects.create_user("edge@example.com")
        user.locked_until = timezone.now()
        assert user.is_locked() is False

    def test_reads_the_in_memory_value(self):
        # A login view that sets `locked_until` and asks `is_locked()` before
        # saving must see the lock; a query would return the stale row.
        user = User.objects.create_user("unsaved@example.com")
        user.locked_until = timezone.now() + timedelta(minutes=15)
        assert user.is_locked() is True


@pytest.mark.django_db
class TestHasRole:
    def test_false_before_the_group_is_added(self):
        user = User.objects.create_user("new@example.com")
        assert user.has_role("candidate") is False

    def test_true_once_the_user_is_in_the_group(self):
        user = User.objects.create_user("cand@example.com")
        user.groups.add(Group.objects.get_or_create(name="candidate")[0])
        assert user.has_role("candidate") is True

    def test_matches_the_group_name_exactly(self):
        user = User.objects.create_user("exact@example.com")
        user.groups.add(Group.objects.get_or_create(name="candidate")[0])
        assert user.has_role("candidate") is True
        assert user.has_role("Candidate") is False
        assert user.has_role("employer_manager") is False

    def test_is_candidate_follows_the_group(self):
        user = User.objects.create_user("c@example.com")
        assert user.is_candidate is False
        user.groups.add(Group.objects.get_or_create(name="candidate")[0])
        assert user.is_candidate is True

    def test_is_employer_is_true_for_manager_and_hr_but_not_candidate(self):
        manager = User.objects.create_user("mgr@example.com")
        manager.groups.add(Group.objects.get_or_create(name="employer_manager")[0])
        hr = User.objects.create_user("hr@example.com")
        hr.groups.add(Group.objects.get_or_create(name="employer_hr")[0])
        candidate = User.objects.create_user("cand2@example.com")
        candidate.groups.add(Group.objects.get_or_create(name="candidate")[0])
        assert manager.is_employer is True
        assert hr.is_employer is True
        assert candidate.is_employer is False

    def test_is_employer_admin_alias_tracks_the_manager_group(self):
        # The property still carries its pre-D-2 name while the group it checks is
        # `employer_manager`. The name is left alone here on purpose: renaming it
        # is a separate decision, not something a characterization test should
        # take on.
        user = User.objects.create_user("alias@example.com")
        user.groups.add(Group.objects.get_or_create(name="employer_manager")[0])
        assert user.is_employer_admin is True


@pytest.mark.django_db
class TestRepresentation:
    def test_str_is_the_email_not_the_name(self):
        # The DDL marks the names ENCRYPTED; rendering them into a log line or an
        # admin listing would decrypt them for every string conversion.
        user = User.objects.create_user(
            "Ada@Example.COM", first_name="Ada", last_name="Lovelace"
        )
        assert str(user) == "ada@example.com"
        assert "Ada" not in str(user)
        assert "Lovelace" not in str(user)

    def test_str_is_the_email_when_the_names_are_blank(self):
        user = User.objects.create_user("blank@example.com")
        assert str(user) == "blank@example.com"


@pytest.mark.django_db
class TestIdentity:
    def test_primary_key_is_a_uuid(self):
        user = User.objects.create_user("uuid@example.com")
        assert isinstance(user.id, uuid.UUID)
        assert user.pk == user.id

    def test_ids_are_not_sequential(self):
        first = User.objects.create_user("one@example.com")
        second = User.objects.create_user("two@example.com")
        assert first.id != second.id

    def test_the_login_field_is_the_email(self):
        assert User.USERNAME_FIELD == "email"
        assert User.EMAIL_FIELD == "email"
        assert User._meta.db_table == "users"
