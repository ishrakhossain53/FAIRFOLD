"""Candidate application list and detail API (REQ-FR-023, batch 1.38).

Complete Doc §C.12:

    GET /api/v1/candidates/applications/       # List applications (with match scores)
    GET /api/v1/candidates/applications/{id}/  # Get application details

What these tests pin down:

* **owner-only, both verbs.** The candidate comes from `request.user`; another
  candidate's id is indistinguishable from an id that exists nowhere, so a 404
  cannot be used to enumerate rows. A non-candidate is 403 and an anonymous
  caller 401 on both routes.
* **the body is a whitelist.** No candidate identity, no `not_matched_reason`,
  no decision fields and no rationale text -- asserted against the raw response
  body, not only the parsed keys, so a renamed or nested field still fails.
* **status is shown for every pipeline value**, including `not_matched`, which
  Gap G3 says is a filter outcome the employer can review rather than a
  rejection.
* **the match score fields exist and are empty.** `match_score` and `screened_at`
  are null until Phase 2; the test also sets a score by hand to prove the field
  is wired rather than hard-coded.
* **an application to a closed job stays in the history**, because REQ-FR-023
  tracks the application, not the job's current posting state.
* **pagination is the project one**, including its 100-row ceiling.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from candidates.models import CandidateProfile
from employers.models import EmployerProfile
from matching.models import Application, Job

pytestmark = pytest.mark.django_db

URL = "/api/v1/candidates/applications/"

# Written out rather than imported so a silent widening of the serializer fails
# here instead of passing automatically. `match_rationale` is deliberately absent:
# its payload is Phase 2's contract (REQ-FR-024).
EXPECTED_FIELDS = {
    "id",
    "job",
    "status",
    "status_display",
    "match_score",
    "screening_status",
    "created_at",
    "screened_at",
}
EXPECTED_JOB_FIELDS = {
    "id",
    "title",
    "location",
    "remote_allowed",
    "experience_level",
    "employer_name",
}


def api_client(user) -> APIClient:
    """A real JWT client for `user`; no forced authentication."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


def detail_url(application) -> str:
    return f"{URL}{application.id}/"


@pytest.fixture
def employer(make_user):
    return EmployerProfile.objects.create(
        user=make_user("employer_hr"),
        company_name="Acme Ltd",
    )


@pytest.fixture
def candidate(make_user):
    user = make_user(
        "candidate",
        email="ada@example.com",
        first_name="Ada",
        last_name="Lovelace",
    )
    return CandidateProfile.objects.create(user=user, title="Backend developer")


@pytest.fixture
def job(employer):
    return Job.objects.create(
        employer=employer,
        title="Backend Engineer",
        location="Dhaka",
        remote_allowed=True,
        experience_level=Job.ExperienceLevel.SENIOR,
        status=Job.Status.ACTIVE,
    )


def make_job(employer, **overrides) -> Job:
    fields = {
        "employer": employer,
        "title": "Backend Engineer",
        "status": Job.Status.ACTIVE,
    }
    fields.update(overrides)
    return Job.objects.create(**fields)


def make_application(candidate, job, **overrides) -> Application:
    fields = {"candidate": candidate, "job": job}
    fields.update(overrides)
    return Application.objects.create(**fields)


class TestListAccess:
    def test_anonymous_is_401(self):
        response = APIClient().get(URL)

        assert response.status_code == 401
        assert "results" not in response.json()

    @pytest.mark.parametrize("role", ["employer_hr", "employer_manager", "interviewer"])
    def test_an_authenticated_non_candidate_is_403(self, make_user, role):
        user = make_user(role)

        response = api_client(user).get(URL)

        assert response.status_code == 403

    def test_a_platform_admin_is_403(self, make_user):
        user = make_user(is_staff=True)

        response = api_client(user).get(URL)

        assert response.status_code == 403

    def test_a_candidate_without_a_profile_is_404(self, make_user):
        """Onboarding comes first (REQ-FR-009); "no profile" is not "no rows"."""
        user = make_user("candidate")

        response = api_client(user).get(URL)

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "No candidate profile yet. Complete onboarding first."
        )


class TestList:
    def test_a_candidate_with_no_applications_gets_an_empty_page(self, candidate):
        response = api_client(candidate.user).get(URL)

        assert response.status_code == 200
        assert response.json()["count"] == 0
        assert response.json()["results"] == []

    def test_only_the_callers_applications_are_returned(
        self, candidate, job, make_user
    ):
        mine = [make_application(candidate, make_job(job.employer)) for _ in range(2)]

        other = CandidateProfile.objects.create(user=make_user("candidate"))
        theirs = make_application(other, make_job(job.employer))

        body = api_client(candidate.user).get(URL).json()

        returned = {row["id"] for row in body["results"]}
        assert returned == {str(application.id) for application in mine}
        assert str(theirs.id) not in returned
        assert body["count"] == 2

    def test_newest_first(self, candidate, job):
        older = make_application(candidate, job)
        newer = make_application(candidate, make_job(job.employer))
        Application.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        body = api_client(candidate.user).get(URL).json()

        assert [row["id"] for row in body["results"]] == [
            str(newer.id),
            str(older.id),
        ]

    def test_the_body_is_the_application_and_its_job(self, candidate, job):
        application = make_application(candidate, job)

        response = api_client(candidate.user).get(URL)
        row = response.json()["results"][0]

        assert set(row) == EXPECTED_FIELDS
        assert set(row["job"]) == EXPECTED_JOB_FIELDS
        assert row["id"] == str(application.id)
        assert row["job"]["id"] == str(job.pk)
        assert row["job"]["title"] == "Backend Engineer"
        assert row["job"]["location"] == "Dhaka"
        assert row["job"]["remote_allowed"] is True
        assert row["job"]["experience_level"] == "senior"
        assert row["status"] == Application.Status.APPLIED
        assert row["status_display"] == "Applied"
        assert row["screening_status"] == Application.ScreeningStatus.NOT_SCREENED

    def test_the_response_carries_no_candidate_identity(self, candidate, job):
        make_application(candidate, job)

        raw = api_client(candidate.user).get(URL).content.decode()

        assert str(candidate.pk) not in raw
        assert str(candidate.user.pk) not in raw
        assert candidate.user.email not in raw
        assert candidate.user.first_name not in raw
        assert candidate.user.last_name not in raw

    def test_decision_and_filter_columns_are_not_exposed(self, candidate, job):
        """Gap G3 and REQ-FR-052 hold rationale and the override reason; neither
        is part of a candidate read."""
        make_application(
            candidate,
            job,
            status=Application.Status.NOT_MATCHED,
            not_matched_reason="requires 5 years of Python",
            filter_rules_version=3,
            match_rationale='{"claims": []}',
            decision_override=True,
            decision_override_reason="hiring manager asked",
        )

        raw = api_client(candidate.user).get(URL).content.decode()

        assert "not_matched_reason" not in raw
        assert "filter_rules_version" not in raw
        assert "match_rationale" not in raw
        assert "decision_override" not in raw
        assert "requires 5 years of Python" not in raw

    def test_the_employer_name_is_withheld_until_the_employer_opts_in(
        self, candidate, job
    ):
        """REQ-FR-042: the name is null unless `show_company_name` is set, and
        the tracker must not be a second disclosure path."""
        make_application(candidate, job)

        row = api_client(candidate.user).get(URL).json()["results"][0]
        assert row["job"]["employer_name"] is None

        job.employer.show_company_name = True
        job.employer.save(update_fields=["show_company_name"])

        row = api_client(candidate.user).get(URL).json()["results"][0]
        assert row["job"]["employer_name"] == "Acme Ltd"

    def test_an_application_to_a_closed_job_is_still_listed(self, candidate, job):
        """REQ-FR-023 tracks the application. Hiding it because the posting
        closed would make the candidate's history silently shrink."""
        application = make_application(candidate, job)
        job.status = Job.Status.CLOSED
        job.save(update_fields=["status"])

        body = api_client(candidate.user).get(URL).json()

        assert body["count"] == 1
        assert body["results"][0]["id"] == str(application.id)

    @pytest.mark.parametrize("status", Application.Status.values)
    def test_every_pipeline_status_reaches_its_owner(self, candidate, job, status):
        application = make_application(candidate, job, status=status)

        row = api_client(candidate.user).get(URL).json()["results"][0]

        assert row["status"] == status
        assert row["status_display"] == application.get_status_display()

    def test_the_match_score_fields_are_empty_until_phase_2(self, candidate, job):
        make_application(candidate, job)

        row = api_client(candidate.user).get(URL).json()["results"][0]

        assert row["match_score"] is None
        assert row["screened_at"] is None

    def test_page_size_is_honoured(self, candidate, job):
        for _ in range(3):
            make_application(candidate, make_job(job.employer))

        body = api_client(candidate.user).get(f"{URL}?page_size=1").json()

        assert body["count"] == 3
        assert body["page_size"] == 1
        assert len(body["results"]) == 1
        assert body["next"] is not None

    def test_page_size_is_capped_at_the_project_ceiling(self, candidate, job):
        make_application(candidate, job)

        body = api_client(candidate.user).get(f"{URL}?page_size=1000").json()

        assert body["page_size"] == 100

    def test_the_list_is_read_only(self, candidate):
        response = api_client(candidate.user).post(URL, {}, format="json")

        assert response.status_code == 405


class TestDetailAccess:
    def test_anonymous_is_401(self, candidate, job):
        application = make_application(candidate, job)

        response = APIClient().get(detail_url(application))

        assert response.status_code == 401

    @pytest.mark.parametrize("role", ["employer_hr", "employer_manager", "interviewer"])
    def test_an_authenticated_non_candidate_is_403(
        self, make_user, candidate, job, role
    ):
        user = make_user(role)
        application = make_application(candidate, job)

        response = api_client(user).get(detail_url(application))

        assert response.status_code == 403

    def test_a_platform_admin_is_403(self, make_user, candidate, job):
        user = make_user(is_staff=True)
        application = make_application(candidate, job)

        response = api_client(user).get(detail_url(application))

        assert response.status_code == 403


class TestDetail:
    def test_the_owner_gets_the_same_shape_as_a_list_entry(self, candidate, job):
        application = make_application(candidate, job)

        response = api_client(candidate.user).get(detail_url(application))
        body = response.json()

        assert response.status_code == 200
        assert set(body) == EXPECTED_FIELDS
        assert set(body["job"]) == EXPECTED_JOB_FIELDS
        assert body["id"] == str(application.id)

        list_entry = api_client(candidate.user).get(URL).json()["results"][0]
        assert set(body) == set(list_entry)
        assert set(body["job"]) == set(list_entry["job"])

    def test_another_candidates_application_is_404(self, candidate, job, make_user):
        other = CandidateProfile.objects.create(user=make_user("candidate"))
        theirs = make_application(other, job)

        response = api_client(candidate.user).get(detail_url(theirs))

        assert response.status_code == 404
        assert response.json()["detail"] == "Application not found."

    def test_a_candidate_without_a_profile_is_404(self, make_user, candidate, job):
        application = make_application(candidate, job)
        user = make_user("candidate")

        response = api_client(user).get(detail_url(application))

        assert response.status_code == 404
        assert response.json()["detail"] == "Application not found."

    def test_an_unknown_id_is_404(self, candidate):
        response = api_client(candidate.user).get(f"{URL}{uuid.uuid4()}/")

        assert response.status_code == 404

    def test_a_malformed_id_is_404(self, candidate):
        """The `<uuid:pk>` converter rejects it before the view runs."""
        response = api_client(candidate.user).get(f"{URL}not-a-uuid/")

        assert response.status_code == 404

    def test_a_score_written_by_phase_2_is_returned(self, candidate, job):
        """The field is wired, not hard-coded to null."""
        application = make_application(
            candidate,
            job,
            status=Application.Status.SCREENED,
            match_score=72,
            screening_status=Application.ScreeningStatus.COMPLETED,
            screened_at=timezone.now(),
        )

        body = api_client(candidate.user).get(detail_url(application)).json()

        assert body["match_score"] == 72
        assert body["screened_at"] is not None

    @pytest.mark.parametrize("method", ["patch", "delete"])
    def test_the_detail_is_read_only(self, candidate, job, method):
        application = make_application(candidate, job)

        response = getattr(api_client(candidate.user), method)(
            detail_url(application), {}, format="json"
        )

        assert response.status_code == 405
        assert Application.objects.filter(pk=application.pk).exists()
