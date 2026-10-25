"""Public job search, filters, ordering and pagination (REQ-FR-042, batch 1.32).

The matrix is the contract: each case states the URL and the titles it must
return, so a filter that silently stops applying fails here rather than in a
manual browse. The cases cover each filter alone, search combined with every
filter, and the negative case where nothing matches.

The query-count test is the N+1 guard. A page of 25 jobs with two skills each
must cost the same number of queries as a page of one; a serializer that walks
`job.employer` or `job.job_skills` without `select_related`/`prefetch_related`
would make that number grow with the page size.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Skill
from employers.models import EmployerProfile
from matching.models import Job, JobSkill

pytestmark = pytest.mark.django_db

URL = "/api/v1/jobs/public/"


@pytest.fixture
def profile(make_user):
    user = make_user("employer_hr")
    return EmployerProfile.objects.create(user=user, company_name="Hidden Labs 4f8c")


def make_job(profile: EmployerProfile, *, skills=(), **overrides) -> Job:
    values = {
        "title": "Backend Engineer",
        "description": "Build and run the screening API.",
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


def titles(response) -> list[str]:
    return [row["title"] for row in response.json()["results"]]


def ids(response) -> set[str]:
    return {row["id"] for row in response.json()["results"]}


class TestKeywordSearch:
    def test_q_matches_the_title_case_insensitively(self, profile):
        match = make_job(profile, title="Backend Engineer")
        make_job(profile, title="Data Analyst")

        response = APIClient().get(URL, {"q": "BACKEND"})

        assert ids(response) == {str(match.pk)}

    def test_q_matches_the_description(self, profile):
        match = make_job(profile, description="You will own the pgvector index.")
        make_job(profile, description="Nothing relevant here.")

        response = APIClient().get(URL, {"q": "pgvector"})

        assert ids(response) == {str(match.pk)}

    def test_q_matches_a_skill_name(self, profile):
        match = make_job(profile, title="Platform role", skills=["Python"])
        make_job(profile, title="Other role", skills=["JavaScript"])

        response = APIClient().get(URL, {"q": "python"})

        assert ids(response) == {str(match.pk)}

    def test_q_does_not_search_fields_the_requirement_omits(self, profile):
        """REQ-FR-042 names title, description and skills. Responsibilities are
        not a search field; widening it silently would be a different contract."""
        make_job(profile, responsibilities="Own the on-call rota")

        response = APIClient().get(URL, {"q": "on-call"})

        assert response.json()["count"] == 0

    def test_a_blank_q_does_not_filter(self, profile):
        make_job(profile, title="One")
        make_job(profile, title="Two")

        response = APIClient().get(URL, {"q": "   "})

        assert response.json()["count"] == 2

    def test_a_term_that_matches_nothing_returns_an_empty_page(self, profile):
        make_job(profile)

        response = APIClient().get(URL, {"q": "quantum-basket-weaving"})

        assert response.json()["count"] == 0
        assert response.json()["results"] == []


class TestFilters:
    def test_location_is_a_case_insensitive_substring(self, profile):
        make_job(profile, title="Dhaka role", location="Dhaka, Bangladesh")
        make_job(profile, title="Sylhet role", location="Sylhet")

        response = APIClient().get(URL, {"location": "dhaka"})

        assert titles(response) == ["Dhaka role"]

    def test_remote_true_returns_only_remote_jobs(self, profile):
        make_job(profile, title="Remote", remote_allowed=True)
        make_job(profile, title="On-site", remote_allowed=False)

        response = APIClient().get(URL, {"remote": "true"})

        assert titles(response) == ["Remote"]

    def test_remote_false_returns_only_non_remote_jobs(self, profile):
        make_job(profile, title="Remote", remote_allowed=True)
        make_job(profile, title="On-site", remote_allowed=False)

        response = APIClient().get(URL, {"remote": "false"})

        assert titles(response) == ["On-site"]

    def test_an_omitted_remote_returns_both(self, profile):
        make_job(profile, title="Remote", remote_allowed=True)
        make_job(profile, title="On-site", remote_allowed=False)

        response = APIClient().get(URL)

        assert set(titles(response)) == {"Remote", "On-site"}

    def test_experience_level_is_exact(self, profile):
        make_job(profile, title="Senior", experience_level="senior")
        make_job(profile, title="Entry", experience_level="entry")

        response = APIClient().get(URL, {"experience_level": "senior"})

        assert titles(response) == ["Senior"]

    def test_a_non_active_job_never_matches_a_filter(self, profile):
        make_job(profile, title="Draft", status=Job.Status.DRAFT, location="Dhaka")

        response = APIClient().get(URL, {"location": "Dhaka"})

        assert response.json()["count"] == 0

    @pytest.mark.parametrize(
        "params",
        [
            {"experience_level": "principal"},
            {"remote": "maybe"},
        ],
    )
    def test_an_invalid_query_parameter_is_400(self, profile, params):
        make_job(profile)

        response = APIClient().get(URL, params)

        assert response.status_code == 400

    def test_an_invalid_page_is_404(self, profile):
        make_job(profile)

        response = APIClient().get(URL, {"page": "not-a-number"})

        assert response.status_code == 404

    def test_an_invalid_page_size_falls_back_to_the_default(self, profile):
        """DRF treats a non-positive page_size as "not supplied". The ceiling
        test below is what protects the endpoint from an oversized request."""
        make_job(profile)

        response = APIClient().get(URL, {"page_size": 0})

        assert response.status_code == 200
        assert response.json()["page_size"] == 20


class TestCombinedMatrix:
    """Each row is a URL and the exact titles it must return.

    The fixture is built once per test by the `jobs` fixture below; the ids are
    stable so the assertions can name titles rather than positions.
    """

    @pytest.fixture
    def jobs(self, profile):
        return {
            "backend_senior": make_job(
                profile,
                title="Backend Engineer",
                location="Dhaka",
                remote_allowed=True,
                experience_level="senior",
                skills=["Python", "Django"],
            ),
            "frontend_senior": make_job(
                profile,
                title="Frontend Engineer",
                location="Dhaka",
                remote_allowed=False,
                experience_level="senior",
                skills=["JavaScript"],
            ),
            "data_entry": make_job(
                profile,
                title="Data Analyst",
                location="Sylhet",
                remote_allowed=True,
                experience_level="entry",
                skills=["SQL"],
            ),
            "backend_intern": make_job(
                profile,
                title="Backend Intern",
                location="Dhaka",
                remote_allowed=True,
                experience_level="entry",
                skills=["Python"],
            ),
        }

    @pytest.mark.parametrize(
        "params,expected",
        [
            ({"q": "engineer"}, {"Backend Engineer", "Frontend Engineer"}),
            ({"q": "python"}, {"Backend Engineer", "Backend Intern"}),
            (
                {"location": "Dhaka"},
                {"Backend Engineer", "Frontend Engineer", "Backend Intern"},
            ),
            (
                {"remote": "true"},
                {"Backend Engineer", "Data Analyst", "Backend Intern"},
            ),
            ({"experience_level": "entry"}, {"Data Analyst", "Backend Intern"}),
            (
                {"q": "backend", "location": "Dhaka", "remote": "true"},
                {"Backend Engineer", "Backend Intern"},
            ),
            (
                {
                    "q": "engineer",
                    "location": "Dhaka",
                    "remote": "true",
                    "experience_level": "senior",
                },
                {"Backend Engineer"},
            ),
            (
                {"q": "python", "experience_level": "entry"},
                {"Backend Intern"},
            ),
            (
                {"q": "engineer", "remote": "false"},
                {"Frontend Engineer"},
            ),
            ({"q": "no-such-term"}, set()),
        ],
    )
    def test_the_combined_filters(self, jobs, params, expected):
        response = APIClient().get(URL, params)

        assert response.status_code == 200
        assert set(titles(response)) == expected


class TestOrderingAndPagination:
    def test_newest_first(self, profile):
        older = make_job(profile, title="Older")
        make_job(profile, title="Newer")
        Job.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(days=2)
        )

        response = APIClient().get(URL)

        assert titles(response) == ["Newer", "Older"]

    def test_a_created_at_tie_is_broken_by_id_for_a_stable_page(self, profile):
        same_time = timezone.now() - timedelta(days=1)
        low = make_job(profile, title="Low id", id=uuid.UUID(int=1))
        high = make_job(profile, title="High id", id=uuid.UUID(int=2))
        Job.objects.filter(pk__in=[low.pk, high.pk]).update(created_at=same_time)

        first = APIClient().get(URL, {"page_size": 1})
        second = APIClient().get(URL, {"page_size": 1, "page": 2})

        assert titles(first) == ["High id"]
        assert titles(second) == ["Low id"]

    def test_page_size_is_capped_at_fifty(self, profile):
        for index in range(51):
            make_job(profile, title=f"Job {index:02d}")

        first = APIClient().get(URL, {"page_size": 500})
        second = APIClient().get(URL, {"page_size": 500, "page": 2})

        assert first.status_code == 200
        assert first.json()["page_size"] == 50
        assert len(first.json()["results"]) == 50
        assert first.json()["num_pages"] == 2
        assert len(second.json()["results"]) == 1

    def test_the_default_page_size_is_twenty(self, profile):
        for index in range(21):
            make_job(profile, title=f"Job {index:02d}")

        response = APIClient().get(URL)

        assert response.json()["page_size"] == 20
        assert len(response.json()["results"]) == 20


class TestSkillsAndQueryCount:
    def test_skill_names_are_sorted_and_carry_no_ids(self, profile):
        job = make_job(profile, skills=["PostgreSQL", "Django", "Python"])

        body = APIClient().get(URL).json()
        row = body["results"][0]

        assert row["skills"] == ["Django", "PostgreSQL", "Python"]
        raw = APIClient().get(URL).content.decode()
        for job_skill in job.job_skills.all():
            assert str(job_skill.skill_id) not in raw
            assert "required" not in raw

    def test_the_detail_includes_the_skills(self, profile):
        job = make_job(profile, skills=["Python"])

        body = APIClient().get(f"{URL}{job.pk}/").json()

        assert body["skills"] == ["Python"]

    def test_a_page_costs_three_queries_whatever_its_size(
        self, profile, django_assert_num_queries
    ):
        """count + page + one prefetch for every job's skills/employer."""
        for index in range(25):
            make_job(profile, title=f"Job {index:02d}", skills=["Python", "Django"])

        with django_assert_num_queries(3):
            response = APIClient().get(URL, {"page_size": 20})

        assert response.status_code == 200
        assert len(response.json()["results"]) == 20
