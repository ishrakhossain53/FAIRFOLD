"""Model tests for `EmployerProfile` (REQ-FR-045, REQ-FR-042, batch 1.23).

The DDL is the specification, so these assert the parts that are easy to get
wrong when transcribing it: the one-to-one owner, the DDL defaults (including
`show_company_name` being off), the nullable `company_size`, the column widths,
the cascade direction, and the two documented deferrals (D-5 encryption, D-2
roles).

They deliberately do not snapshot the whole field list: `makemigrations --check`
already proves the model and the migration agree, and a field-list assertion
would turn every future column into a test edit without testing anything.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction

from accounts.models import User
from employers.models import EmployerProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def employer():
    return User.objects.create_user("hr@example.com", "not-used-in-these-tests")


@pytest.fixture
def profile(employer):
    return EmployerProfile.objects.create(
        user=employer,
        company_name="Acme Ltd",
        industry="Software",
        company_size=40,
    )


def test_a_profile_belongs_to_one_user_and_is_reachable_from_them(profile, employer):
    assert profile.user == employer
    assert employer.employer_profile == profile


def test_a_user_cannot_have_two_profiles(employer):
    EmployerProfile.objects.create(user=employer)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EmployerProfile.objects.create(user=employer)


def test_a_profile_cannot_exist_without_a_user():
    """The DDL column is nullable; §5.2 is 1:1 and REQ-FR-045 creates it for a
    user, so an ownerless profile is a row nobody can reach."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EmployerProfile.objects.create()


def test_defaults_match_the_ddl(employer):
    profile = EmployerProfile.objects.create(user=employer)

    assert profile.company_name == ""
    assert profile.industry == ""
    assert profile.company_size is None
    assert profile.billing_plan == "free"
    assert profile.billing_cycle == "monthly"
    assert profile.stripe_customer_id == ""
    assert profile.created_at is not None


def test_show_company_name_is_off_until_the_employer_opts_in(employer):
    """REQ-FR-042: the public board shows a company name only after opt-in, so
    the default is the requirement, not a convenience."""
    profile = EmployerProfile.objects.create(user=employer)
    assert profile.show_company_name is False

    profile.show_company_name = True
    profile.save()
    profile.refresh_from_db()

    assert profile.show_company_name is True


def test_company_size_accepts_a_value_and_null(profile):
    profile.company_size = 250
    profile.full_clean()
    profile.save()
    profile.refresh_from_db()
    assert profile.company_size == 250

    profile.company_size = None
    profile.full_clean()
    profile.save()
    profile.refresh_from_db()
    assert profile.company_size is None


def test_industry_accepts_the_ddl_width_and_rejects_one_more_character(profile):
    profile.industry = "x" * 100
    profile.full_clean()

    profile.industry = "x" * 101
    with pytest.raises(ValidationError):
        profile.full_clean()


def test_billing_columns_respect_their_ddl_widths(profile):
    profile.billing_plan = "x" * 20
    profile.billing_cycle = "y" * 10
    profile.full_clean()

    profile.billing_plan = "x" * 21
    with pytest.raises(ValidationError):
        profile.full_clean()

    profile.billing_plan = "free"
    profile.billing_cycle = "y" * 11
    with pytest.raises(ValidationError):
        profile.full_clean()


def test_deleting_the_user_deletes_the_profile(profile, employer):
    profile_id = profile.pk

    employer.delete()

    assert not EmployerProfile.objects.filter(pk=profile_id).exists()


def test_deleting_the_profile_keeps_the_user(profile, employer):
    employer_id = employer.pk

    profile.delete()

    assert User.objects.filter(pk=employer_id).exists()


def test_str_never_renders_the_company_name(profile):
    """The DDL encrypts `company_name`, so it is treated as sensitive: a log
    line or an admin list that prints the model must not print the value."""
    assert str(profile) == f"Employer profile {profile.pk}"
    assert "Acme" not in str(profile)


def test_roles_are_not_a_column_on_the_profile(profile):
    """D-2: roles are groups. A `role` column here would be a second source of
    truth for the same permissions."""
    field_names = {field.name for field in EmployerProfile._meta.get_fields()}

    assert "role" not in field_names
    assert "roles" not in field_names


def test_company_name_is_plain_until_d5_is_accepted(profile):
    """Guard on the D-5 deferral, which the DDL alone would contradict.

    An `Encrypted*` field without the §C.8.2 `key_version` rotation plan creates
    rows the rotation procedure cannot read (Complete Doc §C.8.2). If this test
    fails, encryption was switched on: accept D-5, add `key_version` and the
    rotation job, and update this test in the same change.
    """
    field = EmployerProfile._meta.get_field("company_name")

    assert type(field) is models.TextField
    assert profile.company_name == "Acme Ltd"
