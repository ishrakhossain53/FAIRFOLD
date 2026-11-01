"""Page #36's address / country / city selects (REQ-FR-025, batch 1.50)."""

from __future__ import annotations

import pytest
from django.test import Client

from employers.models import EmployerProfile
from matching.models import Job

pytestmark = pytest.mark.django_db

NEW_URL = "/employer/jobs/new/"
CITIES_URL = "/employer/jobs/cities/"


def edit_url(job_id) -> str:
    return f"/employer/jobs/{job_id}/edit/"


def client_for(user) -> Client:
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def employer(make_user):
    return make_user("employer_hr", email="hr@example.com")


@pytest.fixture
def profile(employer):
    return EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")


@pytest.fixture
def job(profile):
    return Job.objects.create(employer=profile, title="Backend Engineer")


class TestTheForm:
    def test_the_legacy_location_input_is_gone_and_the_three_fields_are_there(
        self, employer, profile
    ):
        content = client_for(employer).get(NEW_URL).content.decode()

        assert 'name="address_line"' in content
        assert 'name="country_code"' in content
        assert 'name="city"' in content
        assert 'name="location"' not in content
        assert "Bangladesh" in content
        assert "Select a country first" in content

    def test_the_country_select_is_wired_to_the_city_endpoint(self, employer, profile):
        content = client_for(employer).get(NEW_URL).content.decode()

        assert 'hx-get="/employer/jobs/cities/"' in content
        assert 'hx-target="#id_city"' in content

    def test_editing_renders_the_stored_city_as_selected(self, employer, profile, job):
        job.country_code = "BD"
        job.city = "Dhaka"
        job.save(update_fields=["country_code", "city"])

        content = client_for(employer).get(edit_url(job.pk)).content.decode()

        assert 'value="Dhaka" selected' in content

    def test_a_stored_city_outside_the_list_remains_editable(
        self, employer, profile, job
    ):
        job.country_code = "BD"
        job.city = "A village not in cities15000"
        job.save(update_fields=["country_code", "city"])

        content = client_for(employer).get(edit_url(job.pk)).content.decode()

        assert "A village not in cities15000" in content

        response = client_for(employer).post(
            edit_url(job.pk),
            {
                "title": job.title,
                "country_code": "BD",
                "city": "A village not in cities15000",
                "experience_level": "",
            },
        )

        assert response.status_code == 302
        job.refresh_from_db()
        assert job.city == "A village not in cities15000"

    def test_a_save_stores_the_three_structured_fields(self, employer, profile):
        response = client_for(employer).post(
            NEW_URL,
            {
                "title": "Backend Engineer",
                "address_line": "12 Motijheel",
                "country_code": "BD",
                "city": "Dhaka",
                "experience_level": "senior",
            },
        )

        assert response.status_code == 302
        job = Job.objects.get()
        assert job.address_line == "12 Motijheel"
        assert job.city == "Dhaka"
        assert job.country_code == "BD"
        assert job.display_location == "Dhaka, Bangladesh"

    def test_a_city_without_a_country_is_a_field_error(self, employer, profile):
        response = client_for(employer).post(
            NEW_URL,
            {
                "title": "Backend Engineer",
                "city": "Dhaka",
                "experience_level": "",
            },
        )

        assert response.status_code == 200
        assert "country_code" in response.context["form"].errors
        assert Job.objects.count() == 0

    def test_changing_the_country_does_not_keep_the_old_city(
        self, employer, profile, job
    ):
        job.country_code = "BD"
        job.city = "Dhaka"
        job.save(update_fields=["country_code", "city"])

        response = client_for(employer).post(
            edit_url(job.pk),
            {
                "title": job.title,
                "country_code": "GB",
                "city": "Dhaka",
                "experience_level": "",
            },
        )

        assert response.status_code == 200
        assert "city" in response.context["form"].errors
        job.refresh_from_db()
        assert job.country_code == "BD"

    def test_a_city_outside_the_selected_country_is_a_field_error(
        self, employer, profile
    ):
        response = client_for(employer).post(
            NEW_URL,
            {
                "title": "Backend Engineer",
                "country_code": "BD",
                "city": "London",
                "experience_level": "",
            },
        )

        assert response.status_code == 200
        assert "city" in response.context["form"].errors
        assert Job.objects.count() == 0


class TestTheCityEndpoint:
    def test_bangladesh_returns_its_cities_with_regions(self, employer, profile):
        response = client_for(employer).get(CITIES_URL, {"country_code": "BD"})

        assert response.status_code == 200
        content = response.content.decode()
        assert "Dhaka" in content
        assert "—" in content
        assert "London" not in content

    def test_an_empty_country_returns_the_placeholder(self, employer, profile):
        content = client_for(employer).get(CITIES_URL).content.decode()

        assert "Select a country first" in content

    def test_a_country_without_cities_says_so(self, employer, profile):
        content = (
            client_for(employer)
            .get(CITIES_URL, {"country_code": "AQ"})
            .content.decode()
        )

        assert "No cities listed for this country" in content

    def test_an_unknown_country_does_not_error(self, employer, profile):
        response = client_for(employer).get(CITIES_URL, {"country_code": "ZZ"})

        assert response.status_code == 200
        assert "No cities listed for this country" in response.content.decode()

    def test_post_is_method_not_allowed(self, employer, profile):
        response = client_for(employer).post(CITIES_URL, {"country_code": "BD"})

        assert response.status_code == 405

    def test_a_candidate_is_forbidden(self, make_user):
        candidate = make_user("candidate", email="candidate@example.com")

        response = client_for(candidate).get(CITIES_URL, {"country_code": "BD"})

        assert response.status_code == 403

    def test_an_anonymous_visitor_is_sent_to_login(self):
        response = Client().get(CITIES_URL, {"country_code": "BD"})

        assert response.status_code == 302
        assert "/login/" in response["Location"]
        assert "next=" in response["Location"]
