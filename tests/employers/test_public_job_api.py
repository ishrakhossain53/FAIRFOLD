"""Public job list and detail API tests (REQ-FR-042, batch 1.31).

The public board is the one surface that serves employer content to anonymous
callers, so these tests pin three things beyond the happy path:

* **Only `active` jobs are reachable.** A draft, paused or closed job is a 404 on
  the detail route and never appears in the list. 404 rather than 403 is
  Complete Doc §C.12's rule: a 403 confirms that the job exists.
* **The employer name is withheld unless `show_company_name` is on.** The
  concealment tests inspect the raw JSON, not just `employer_name`, because a
  hidden name under another key is still a leak. They also inspect the 404 body:
  an error message that names the company defeats the concealment.
* **The serializer is a whitelist.** No owner, screening config, model name or
  cost estimate is exposed. Those columns exist on `Job` and would otherwise
  travel with a `ModelSerializer` default field set.

Both routes are open to guests and to every signed-in role; the authorization
matrix records the 200/404 answers separately.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from employers.models import EmployerProfile
from matching.models import Job

pytestmark = pytest.mark.django_db

LIST_URL = "/api/v1/jobs/public/"
DETAIL_URL = "/api/v1/jobs/public/{job_id}/"

# Distinctive strings: a substring match against "Acme" would pass by accident
# on an unrelated word, and these tests are the only thing standing between a
# company name and an anonymous caller.
HIDDEN_NAME = "Hidden Labs 4f8c"
SHOWN_NAME = "Shown Labs 91ad"

LIST_FIELDS = {
    "id",
    "title",
    "location",
    "remote_allowed",
    "experience_level",
    "employer_name",
    "skills",
    "created_at",
}

DETAIL_FIELDS = LIST_FIELDS | {
    "description",
    "responsibilities",
    "requirements",
    "nice_to_have",
    "updated_at",
}

# Keys that would carry employer identity or unpublished employer/AI state.
FORBIDDEN_KEYS = {
    "company_name",
    "employer",
    "employer_id",
    "user",
    "user_id",
    "industry",
    "company_size",
    "screening_config",
    "screening_questions",
    "ai_model_used",
    "cost_estimate",
    "status",
}


def api_client(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


def make_job(profile: EmployerProfile, **overrides) -> Job:
    values = {
        "title": "Backend Engineer",
        "description": "Build and run the screening API.",
        "responsibilities": "Own the matching service.",
        "requirements": "Four years with Django.",
        "nice_to_have": "pgvector experience.",
        "location": "Dhaka",
        "remote_allowed": True,
        "experience_level": Job.ExperienceLevel.SENIOR,
        "status": Job.Status.ACTIVE,
    }
    values.update(overrides)
    return Job.objects.create(employer=profile, **values)


def age_job(job: Job, *, days: int) -> None:
    """Move a job's creation time, because `auto_now_add` ignores it on create."""
    Job.objects.filter(pk=job.pk).update(
        created_at=timezone.now() - timedelta(days=days)
    )


def json_keys(value) -> set[str]:
    """Every key in a parsed JSON body, nested objects and arrays included."""
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(key)
            keys |= json_keys(item)
    elif isinstance(value, list):
        for item in value:
            keys |= json_keys(item)
    return keys


def assert_no_hidden_identity(response) -> None:
    """The name and the employer-only keys are absent from the whole body."""
    raw = response.content.decode()
    assert HIDDEN_NAME not in raw
    assert "company_name" not in raw
    assert not (json_keys(response.json()) & FORBIDDEN_KEYS)


@pytest.fixture
def employer(make_user):
    return make_user("employer_hr")


@pytest.fixture
def profile(employer):
    """An employer who has **not** opted into public disclosure."""
    return EmployerProfile.objects.create(user=employer, company_name=HIDDEN_NAME)


class TestListIsPublic:
    def test_a_guest_gets_a_page_of_active_jobs(self, profile):
        job = make_job(profile)

        response = APIClient().get(LIST_URL)

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["results"][0]["id"] == str(job.pk)

    @pytest.mark.parametrize("role", ["candidate", "employer_hr", "interviewer"])
    def test_a_signed_in_user_can_list_jobs(self, make_user, profile, role):
        make_job(profile)

        response = api_client(make_user(role)).get(LIST_URL)

        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_a_platform_admin_can_list_jobs(self, profile):
        make_job(profile)
        admin = User.objects.create_superuser("admin@example.com")

        response = api_client(admin).get(LIST_URL)

        assert response.status_code == 200


class TestListScope:
    def test_only_active_jobs_are_listed(self, profile):
        active = make_job(profile, title="Active")
        make_job(profile, title="Draft", status=Job.Status.DRAFT)
        make_job(profile, title="Paused", status=Job.Status.PAUSED)
        make_job(profile, title="Closed", status=Job.Status.CLOSED)

        body = APIClient().get(LIST_URL).json()

        assert body["count"] == 1
        assert [row["id"] for row in body["results"]] == [str(active.pk)]

    def test_newest_first(self, profile):
        older = make_job(profile, title="Older")
        newer = make_job(profile, title="Newer")
        age_job(older, days=2)

        body = APIClient().get(LIST_URL).json()

        assert [row["id"] for row in body["results"]] == [
            str(newer.pk),
            str(older.pk),
        ]

    def test_the_list_is_paginated(self, profile):
        for index in range(3):
            make_job(profile, title=f"Job {index}")

        first = APIClient().get(LIST_URL, {"page_size": 2})
        second = APIClient().get(LIST_URL, {"page_size": 2, "page": 2})

        assert first.status_code == 200
        assert first.json()["count"] == 3
        assert first.json()["num_pages"] == 2
        assert len(first.json()["results"]) == 2
        assert first.json()["next"] is not None
        assert len(second.json()["results"]) == 1

    def test_an_empty_board_is_an_empty_page(self):
        response = APIClient().get(LIST_URL)

        assert response.status_code == 200
        assert response.json()["count"] == 0
        assert response.json()["results"] == []

    def test_a_page_beyond_the_end_is_404_and_names_nobody(self, profile):
        make_job(profile)

        response = APIClient().get(LIST_URL, {"page": 99})

        assert response.status_code == 404
        assert_no_hidden_identity(response)


class TestDetail:
    def test_a_guest_opens_an_active_job(self, profile):
        job = make_job(profile)

        response = APIClient().get(DETAIL_URL.format(job_id=job.pk))

        assert response.status_code == 200
        assert response.json()["id"] == str(job.pk)

    def test_a_signed_in_user_opens_an_active_job(self, make_user, profile):
        job = make_job(profile)
        candidate = make_user("candidate")

        response = api_client(candidate).get(DETAIL_URL.format(job_id=job.pk))

        assert response.status_code == 200

    def test_the_detail_carries_the_job_text(self, profile):
        job = make_job(profile)

        body = APIClient().get(DETAIL_URL.format(job_id=job.pk)).json()

        assert body["title"] == "Backend Engineer"
        assert body["description"] == "Build and run the screening API."
        assert body["responsibilities"] == "Own the matching service."
        assert body["requirements"] == "Four years with Django."
        assert body["nice_to_have"] == "pgvector experience."
        assert body["location"] == "Dhaka"
        assert body["remote_allowed"] is True
        assert body["experience_level"] == "senior"

    @pytest.mark.parametrize(
        "status",
        [Job.Status.DRAFT, Job.Status.PAUSED, Job.Status.CLOSED],
    )
    def test_a_non_active_job_is_404_not_403(self, profile, status):
        """404 is the documented answer: a 403 confirms the id exists."""
        job = make_job(profile, title="Unpublished 7c1e", status=status)

        response = APIClient().get(DETAIL_URL.format(job_id=job.pk))

        assert response.status_code == 404
        assert response.json()["detail"] == "Not found."
        assert job.title not in response.content.decode()
        assert_no_hidden_identity(response)

    def test_an_unknown_id_is_404(self, profile):
        response = APIClient().get(
            DETAIL_URL.format(job_id="00000000-0000-0000-0000-000000000000")
        )

        assert response.status_code == 404
        assert_no_hidden_identity(response)


class TestResponseShape:
    def test_the_list_is_a_card_whitelist(self, profile):
        make_job(profile)

        body = APIClient().get(LIST_URL).json()

        assert set(body["results"][0]) == LIST_FIELDS

    def test_the_detail_is_a_whitelist(self, profile):
        job = make_job(profile)

        body = APIClient().get(DETAIL_URL.format(job_id=job.pk)).json()

        assert set(body) == DETAIL_FIELDS

    def test_unpublished_and_ai_columns_never_serialize(self, profile):
        """`ModelSerializer` defaults would ship these; the field list must not."""
        job = make_job(
            profile,
            ai_model_used="internal-model-x",
            cost_estimate=Decimal("1.2500"),
            screening_config={"filters": {"min_years": 3}},
            screening_questions=[{"prompt": "secret-question"}],
        )

        list_raw = APIClient().get(LIST_URL).content.decode()
        detail_raw = APIClient().get(DETAIL_URL.format(job_id=job.pk)).content.decode()

        for raw in (list_raw, detail_raw):
            assert "internal-model-x" not in raw
            assert "1.2500" not in raw
            assert "min_years" not in raw
            assert "secret-question" not in raw


class TestEmployerNameConcealment:
    def test_hidden_by_default_in_the_list_for_a_guest(self, profile):
        make_job(profile)

        response = APIClient().get(LIST_URL)

        assert response.status_code == 200
        assert response.json()["results"][0]["employer_name"] is None
        assert_no_hidden_identity(response)

    def test_hidden_by_default_in_the_list_for_a_signed_in_user(
        self, make_user, profile
    ):
        make_job(profile)

        response = api_client(make_user("candidate")).get(LIST_URL)

        assert response.json()["results"][0]["employer_name"] is None
        assert_no_hidden_identity(response)

    def test_hidden_by_default_in_the_detail_for_a_guest(self, profile):
        job = make_job(profile)

        response = APIClient().get(DETAIL_URL.format(job_id=job.pk))

        assert response.json()["employer_name"] is None
        assert_no_hidden_identity(response)

    def test_hidden_by_default_in_the_detail_for_a_signed_in_user(
        self, make_user, profile
    ):
        job = make_job(profile)
        employer_user = make_user("employer_hr")

        response = api_client(employer_user).get(DETAIL_URL.format(job_id=job.pk))

        assert response.json()["employer_name"] is None
        assert_no_hidden_identity(response)

    def test_shown_when_the_employer_opts_in(self, make_user):
        user = make_user("employer_hr")
        profile = EmployerProfile.objects.create(
            user=user, company_name=SHOWN_NAME, show_company_name=True
        )
        job = make_job(profile)

        list_body = APIClient().get(LIST_URL).json()
        detail_body = APIClient().get(DETAIL_URL.format(job_id=job.pk)).json()

        assert list_body["results"][0]["employer_name"] == SHOWN_NAME
        assert detail_body["employer_name"] == SHOWN_NAME

    def test_one_opt_in_does_not_reveal_another_employer(self, make_user, profile):
        make_job(profile, title="Hidden job")

        shown_user = make_user("employer_hr")
        shown = EmployerProfile.objects.create(
            user=shown_user, company_name=SHOWN_NAME, show_company_name=True
        )
        make_job(shown, title="Shown job")

        response = APIClient().get(LIST_URL)
        names = {
            row["title"]: row["employer_name"] for row in response.json()["results"]
        }

        assert names == {"Hidden job": None, "Shown job": SHOWN_NAME}
        assert HIDDEN_NAME not in response.content.decode()

    def test_an_opted_in_employer_with_no_name_returns_null(self, make_user):
        user = make_user("employer_hr")
        profile = EmployerProfile.objects.create(
            user=user, company_name="", show_company_name=True
        )
        make_job(profile)

        body = APIClient().get(LIST_URL).json()

        assert body["results"][0]["employer_name"] is None

    def test_a_hidden_name_is_absent_from_every_nested_key(self, profile):
        """The nested walk is the point: a renamed or nested key still leaks."""
        make_job(profile)

        for response in (
            APIClient().get(LIST_URL),
            APIClient().get(DETAIL_URL.format(job_id=make_job(profile).pk)),
        ):
            keys = json_keys(response.json())
            assert not (keys & FORBIDDEN_KEYS), keys & FORBIDDEN_KEYS
            assert HIDDEN_NAME not in response.content.decode()
