"""Structured job location on the model (REQ-FR-025, amended 2026-10-30)."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from employers.models import EmployerProfile
from matching.models import Job

pytestmark = pytest.mark.django_db


@pytest.fixture
def profile(make_user):
    user = make_user("employer_hr")
    return EmployerProfile.objects.create(user=user, company_name="Acme Ltd")


def make_job(profile, **overrides) -> Job:
    values = {"employer": profile, "title": "Backend Engineer"}
    values.update(overrides)
    return Job.objects.create(**values)


def test_structured_location_is_the_display_string(profile):
    job = make_job(profile, city="Dhaka", country_code="BD", location="Old value")

    assert job.display_location == "Dhaka, Bangladesh"


def test_the_country_alone_is_a_display_string(profile):
    job = make_job(profile, country_code="BD")

    assert job.display_location == "Bangladesh"


def test_address_is_the_fallback_when_no_city_or_country(profile):
    job = make_job(profile, address_line="12 Motijheel")

    assert job.display_location == "12 Motijheel"


def test_a_legacy_row_falls_back_to_location(profile):
    job = make_job(profile, location="Sylhet")

    assert job.display_location == "Sylhet"


def test_a_city_without_a_country_fails_validation(profile):
    job = Job(employer=profile, title="Role", city="Dhaka")

    with pytest.raises(ValidationError) as excinfo:
        job.full_clean()

    assert "country_code" in excinfo.value.message_dict


def test_an_unknown_country_code_fails_validation(profile):
    job = Job(employer=profile, title="Role", country_code="ZZ")

    with pytest.raises(ValidationError) as excinfo:
        job.full_clean()

    assert "country_code" in excinfo.value.message_dict
