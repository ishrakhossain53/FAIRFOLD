"""Public job-board pages #4 and #5 (REQ-FR-042, batch 1.33).

The API tests in `test_public_job_api.py` pin the JSON contract. These pin the
HTML surface, and the extra risk is concealment in a template: a view that
passes the right context can still leak through `job.employer.company_name` or
through an error message. Every concealment test therefore inspects the raw
response body, not the visible text.

The board is also the first anonymous page with user-supplied query values, so
the tests cover the 400 state and the escaping of employer-authored Markdown.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from core.models import Skill
from employers.models import EmployerProfile
from matching.models import Job, JobSkill

pytestmark = pytest.mark.django_db

LIST_URL = "/jobs/"
HIDDEN_NAME = "Hidden Labs 4f8c"
SHOWN_NAME = "Shown Labs 91ad"


@pytest.fixture
def profile(make_user):
    user = make_user("employer_hr")
    return EmployerProfile.objects.create(user=user, company_name=HIDDEN_NAME)


@pytest.fixture
def shown_profile(make_user):
    user = make_user("employer_hr")
    return EmployerProfile.objects.create(
        user=user,
        company_name=SHOWN_NAME,
        show_company_name=True,
    )


def make_job(profile: EmployerProfile, *, skills=(), **overrides) -> Job:
    values = {
        "title": "Backend Engineer",
        "description": "Build the screening API.",
        "location": "Dhaka",
        "remote_allowed": True,
        "experience_level": Job.ExperienceLevel.SENIOR,
        "status": Job.Status.ACTIVE,
    }
    values.update(overrides)
    job = Job.objects.create(employer=profile, **values)
    for name in skills:
        skill, _ = Skill.objects.get_or_create(canonical_name=name)
        JobSkill.objects.create(job=job, skill=skill)
    return job


class TestBoard:
    def test_a_guest_opens_the_board_and_sees_active_jobs(self, profile):
        make_job(profile, title="Visible role")
        make_job(profile, title="Draft role", status=Job.Status.DRAFT)
        make_job(profile, title="Paused role", status=Job.Status.PAUSED)
        make_job(profile, title="Closed role", status=Job.Status.CLOSED)

        response = Client().get(LIST_URL)

        assert response.status_code == 200
        assert b"Visible role" in response.content
        for hidden in (b"Draft role", b"Paused role", b"Closed role"):
            assert hidden not in response.content

    def test_the_board_links_to_the_job_page(self, profile):
        job = make_job(profile)

        response = Client().get(LIST_URL)

        assert f'href="/jobs/{job.pk}/"' in response.content.decode()

    def test_the_hidden_employer_name_is_not_in_the_html(self, profile):
        make_job(profile)

        response = Client().get(LIST_URL)

        assert HIDDEN_NAME.encode() not in response.content

    def test_an_opted_in_employer_name_is_shown(self, shown_profile):
        make_job(shown_profile)

        response = Client().get(LIST_URL)

        assert SHOWN_NAME.encode() in response.content

    def test_skills_are_rendered_as_text(self, profile):
        make_job(profile, skills=["PostgreSQL", "Django", "Python"])

        response = Client().get(LIST_URL)

        assert b"PostgreSQL" in response.content
        assert b"Django" in response.content
        assert b"Python" in response.content

    def test_the_count_and_newest_first_label_are_announced(self, profile):
        make_job(profile, title="One")
        make_job(profile, title="Two")

        response = Client().get(LIST_URL)

        assert b"2 jobs" in response.content
        assert b"Newest first" in response.content
        assert b'aria-live="polite"' in response.content

    def test_the_public_board_is_linked_from_the_global_nav(self, profile):
        response = Client().get("/")

        assert b'href="/jobs/"' in response.content


class TestSearchAndFilters:
    @pytest.fixture
    def jobs(self, profile):
        return {
            "backend": make_job(
                profile,
                title="Backend Engineer",
                location="Dhaka",
                remote_allowed=True,
                experience_level="senior",
                skills=["Python"],
            ),
            "frontend": make_job(
                profile,
                title="Frontend Engineer",
                location="Dhaka",
                remote_allowed=False,
                experience_level="senior",
                skills=["JavaScript"],
            ),
            "data": make_job(
                profile,
                title="Data Analyst",
                location="Sylhet",
                remote_allowed=True,
                experience_level="entry",
                skills=["SQL"],
            ),
            "intern": make_job(
                profile,
                title="Backend Intern",
                location="Dhaka",
                remote_allowed=True,
                experience_level="entry",
                skills=["Python"],
            ),
        }

    def test_the_four_filters_combine(self, jobs):
        response = Client().get(
            LIST_URL,
            {
                "q": "python",
                "location": "Dhaka",
                "remote": "true",
                "experience_level": "entry",
            },
        )

        content = response.content.decode()
        assert response.status_code == 200
        assert "Backend Intern" in content
        assert "Backend Engineer" not in content
        assert "Frontend Engineer" not in content
        assert "Data Analyst" not in content
        assert "1 job" in content

    def test_search_reaches_the_title_and_skill(self, jobs):
        by_title = Client().get(LIST_URL, {"q": "frontend"}).content.decode()
        by_skill = Client().get(LIST_URL, {"q": "sql"}).content.decode()

        assert "Frontend Engineer" in by_title
        assert "Backend Engineer" not in by_title
        assert "Data Analyst" in by_skill
        assert "Backend Engineer" not in by_skill

    def test_a_filter_chip_can_remove_one_filter(self, jobs):
        response = Client().get(
            LIST_URL, {"q": "python", "remote": "true", "experience_level": "entry"}
        )

        content = response.content.decode()
        assert "Remove filter: Remote" in content
        assert "Remove filter: Level: Entry" in content
        # The remove link keeps the other filters and drops only `remote`.
        assert "?q=python&amp;experience_level=entry" in content

    def test_clear_filters_resets_every_filter(self, jobs):
        response = Client().get(LIST_URL, {"q": "python", "remote": "true"})

        content = response.content.decode()
        assert 'href="/jobs/"' in content
        assert "Clear filters" in content

    def test_no_results_has_a_clear_state(self, jobs):
        response = Client().get(LIST_URL, {"q": "quantum-basket-weaving"})

        content = response.content.decode()
        assert response.status_code == 200
        assert "0 jobs" in content
        assert "No jobs match." in content
        assert "Clear filters" in content

    def test_an_unknown_level_is_a_400_page_not_a_traceback(self, jobs):
        response = Client().get(LIST_URL, {"experience_level": "principal"})

        content = response.content.decode()
        assert response.status_code == 400
        assert "Check the filters" in content
        assert "Experience level" in content
        assert "principal" in content
        assert "Backend Engineer" not in content

    def test_a_non_boolean_remote_is_a_400_page(self, jobs):
        response = Client().get(LIST_URL, {"remote": "maybe"})

        assert response.status_code == 400
        assert b"Check the filters" in response.content


class TestPagination:
    def test_page_two_keeps_the_search_term(self, profile):
        for index in range(25):
            make_job(profile, title=f"Python role {index:02d}", skills=["Python"])

        response = Client().get(LIST_URL, {"q": "python"})

        content = response.content.decode()
        assert "?q=python&amp;page=2" in content
        assert 'rel="next"' in content

    def test_the_second_page_renders_the_remainder(self, profile):
        for index in range(25):
            make_job(profile, title=f"Role {index:02d}")

        response = Client().get(LIST_URL, {"page": 2})

        assert response.status_code == 200
        # Newest first: 25 roles, page 2 is the five oldest rows.
        assert response.content.count(b"Posted") == 5
        assert b"25 jobs" in response.content

    def test_a_bad_page_number_is_clamped_not_a_404(self, profile):
        make_job(profile)

        response = Client().get(LIST_URL, {"page": "not-a-number"})

        assert response.status_code == 200
        assert b"Backend Engineer" in response.content


class TestDetail:
    def test_a_guest_opens_an_active_job(self, profile):
        job = make_job(
            profile,
            description="Own the **screening API**.",
            responsibilities="Review pull requests.",
            requirements="Five years of Python.",
            nice_to_have="Django experience.",
            skills=["Python", "Django"],
        )

        response = Client().get(f"/jobs/{job.pk}/")

        content = response.content.decode()
        assert response.status_code == 200
        assert "Backend Engineer" in content
        assert "<strong>screening API</strong>" in content
        assert "Review pull requests." in content
        assert "Five years of Python." in content
        assert "Django experience." in content
        assert "Python" in content
        assert "Django" in content

    def test_the_hidden_employer_name_is_not_in_the_detail_html(self, profile):
        job = make_job(profile)

        response = Client().get(f"/jobs/{job.pk}/")

        assert HIDDEN_NAME.encode() not in response.content

    def test_an_opted_in_employer_is_named(self, shown_profile):
        job = make_job(shown_profile)

        response = Client().get(f"/jobs/{job.pk}/")

        assert SHOWN_NAME.encode() in response.content

    def test_a_guest_is_asked_to_log_in_with_a_return_path(self, profile):
        job = make_job(profile)

        response = Client().get(f"/jobs/{job.pk}/")

        content = response.content.decode()
        assert "Log in to apply" in content
        assert f"?next=/jobs/{job.pk}/" in content

    def test_a_candidate_sees_an_honest_disabled_apply(self, make_user, profile):
        candidate = make_user("candidate")
        job = make_job(profile)
        client = Client()
        client.force_login(candidate)

        response = client.get(f"/jobs/{job.pk}/")

        content = response.content.decode()
        assert response.status_code == 200
        assert "disabled" in content
        assert "Applying opens in the next release." in content
        # A disabled control, not a POST to an endpoint that does not exist.
        assert 'action="/jobs/' not in content

    def test_an_employer_sees_the_board_without_an_apply_action(
        self, make_user, profile
    ):
        employer = make_user("employer_hr")
        job = make_job(profile)
        client = Client()
        client.force_login(employer)

        response = client.get(f"/jobs/{job.pk}/")

        content = response.content.decode()
        assert response.status_code == 200
        assert "Applications are submitted by candidate accounts." in content
        assert "Log in to apply" not in content

    def test_employer_markdown_is_escaped(self, profile):
        job = make_job(profile, description="<script>alert('x')</script> **safe**")

        response = Client().get(f"/jobs/{job.pk}/")

        content = response.content.decode()
        assert "<script>alert" not in content
        assert "&lt;script&gt;alert" in content
        assert "<strong>safe</strong>" in content

    @pytest.mark.parametrize(
        "status",
        [Job.Status.DRAFT, Job.Status.PAUSED, Job.Status.CLOSED],
    )
    def test_a_non_active_job_is_404(self, profile, status):
        job = make_job(profile, status=status)

        response = Client().get(f"/jobs/{job.pk}/")

        assert response.status_code == 404

    def test_an_unknown_id_is_404(self):
        response = Client().get(f"/jobs/{uuid.uuid4()}/")

        assert response.status_code == 404

    def test_a_newer_job_is_listed_before_an_older_one(self, profile):
        older = make_job(profile, title="Older role")
        make_job(profile, title="Newer role")
        Job.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(days=2)
        )

        content = Client().get(LIST_URL).content.decode()

        assert content.index("Newer role") < content.index("Older role")
