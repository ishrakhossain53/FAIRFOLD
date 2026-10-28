"""Employer application inbox API (REQ-FR-029, REQ-FR-054, batch 1.40).

Complete Doc §C.12:

    GET /api/v1/jobs/{id}/applications/   # ?status=not_matched shows the
                                          # filter-excluded candidates

What these tests pin down:

* **ownership is the caller's profile.** Another employer's job is the same 404
  as an id that exists nowhere, so the route cannot be used to enumerate
  postings or to read another company's applications.
* **identity is the alias.** REQ-FR-054: the row carries the per-employer alias,
  and the body holds no name, email, photo, contact detail or internal candidate
  UUID. The assertion is on the raw response text as well as the parsed keys, so
  a renamed or nested field still fails.
* **the same employer sees the same alias across its jobs**, and two employers
  see different labels for one candidate -- otherwise the two inboxes could be
  joined.
* **a `not_matched` row is listed, not hidden** (Gap G3), and `?status=` filters
  on one pipeline value; an unknown value is a 400 rather than an ignored
  parameter.
* **Phase 1 has no ranking.** The order is newest-first with a tie-break, and
  `match_score` is present and null; the field is proved wired by setting a
  score by hand.
* **filter outcomes are not decisions.** `not_matched_reason`,
  `filter_rules_version`, `match_rationale` and the override columns belong to
  later batches and must not leak into this body.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from candidates.models import CandidateAlias, CandidateProfile
from employers.models import EmployerProfile
from matching.models import Application, Job

pytestmark = pytest.mark.django_db

# Written out rather than derived from the serializer: a field added without a
# decision must fail here instead of widening the contract silently.
EXPECTED_FIELDS = {
    "id",
    "candidate",
    "status",
    "status_display",
    "match_score",
    "screening_status",
    "created_at",
}

# Exactly `candidates.services.candidate_for_employer()` (batch 1.35).
EXPECTED_CANDIDATE_FIELDS = {"alias", "title", "location", "remote_ok", "skills"}

ONBOARDING_DETAIL = "No employer profile yet. Complete onboarding first."


def api_client(user) -> APIClient:
    """A real JWT client for `user`; no forced authentication."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


def inbox_url(job) -> str:
    return f"/api/v1/jobs/{job.pk}/applications/"


@pytest.fixture
def employer(make_user):
    return make_user("employer_hr")


@pytest.fixture
def profile(employer):
    return EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")


@pytest.fixture
def other_employer(make_user):
    return make_user("employer_hr")


@pytest.fixture
def other_profile(other_employer):
    return EmployerProfile.objects.create(user=other_employer, company_name="Beta Ltd")


@pytest.fixture
def job(profile):
    return Job.objects.create(
        employer=profile,
        title="Backend Engineer",
        location="Dhaka",
        status=Job.Status.ACTIVE,
    )


@pytest.fixture
def candidate(make_user):
    """A profile whose identity is recognisable in the raw response."""
    user = make_user(
        "candidate",
        email="distinctive-candidate@example.com",
        first_name="Zubaida",
        last_name="Rahman",
    )
    return CandidateProfile.objects.create(
        user=user,
        title="Backend developer",
        location="Dhaka",
        skills=["Python", "PostgreSQL"],
    )


@pytest.fixture
def other_candidate(make_user):
    return CandidateProfile.objects.create(
        user=make_user("candidate", first_name="Second", last_name="Applicant"),
        title="Data engineer",
    )


def make_job(profile, **overrides) -> Job:
    fields = {
        "employer": profile,
        "title": "Backend Engineer",
        "status": Job.Status.ACTIVE,
    }
    fields.update(overrides)
    return Job.objects.create(**fields)


def make_candidate(make_user, **overrides) -> CandidateProfile:
    """A throwaway applicant. Distinct users, so `UNIQUE(job, candidate)` holds."""
    fields = {"user": make_user("candidate")}
    fields.update(overrides)
    return CandidateProfile.objects.create(**fields)


def make_application(candidate, job, **overrides) -> Application:
    fields = {"candidate": candidate, "job": job}
    fields.update(overrides)
    return Application.objects.create(**fields)


# ---------------------------------------------------------------------------
# Access
# ---------------------------------------------------------------------------


class TestAccess:
    def test_anonymous_is_401_and_gets_no_page(self, job):
        response = APIClient().get(inbox_url(job))

        assert response.status_code == 401
        assert "results" not in response.json()

    def test_a_candidate_is_403(self, make_user, job):
        response = api_client(make_user("candidate")).get(inbox_url(job))

        assert response.status_code == 403

    def test_an_interviewer_is_403(self, make_user, job):
        """D-2: an interviewer reads an assigned interview, not a job's inbox."""
        response = api_client(make_user("interviewer")).get(inbox_url(job))

        assert response.status_code == 403

    def test_a_platform_admin_is_403(self, make_user, job):
        """`is_staff` is not an employer role; D-2 keeps the two separate."""
        response = api_client(make_user(is_staff=True)).get(inbox_url(job))

        assert response.status_code == 403

    @pytest.mark.parametrize("role", ["employer_hr", "employer_manager"])
    def test_both_employer_roles_may_read_their_own_inbox(
        self, make_user, role, candidate
    ):
        user = make_user(role)
        profile = EmployerProfile.objects.create(user=user, company_name="Acme Ltd")
        job = make_job(profile)
        make_application(candidate, job)

        response = api_client(user).get(inbox_url(job))

        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_an_employer_without_a_profile_is_404(self, make_user, job):
        """Onboarding precedes any job (REQ-FR-045), exactly as on `/me/`."""
        response = api_client(make_user("employer_hr")).get(inbox_url(job))

        assert response.status_code == 404
        assert response.json()["detail"] == ONBOARDING_DETAIL

    def test_an_unknown_job_is_404(self, employer):
        response = api_client(employer).get(
            "/api/v1/jobs/00000000-0000-0000-0000-000000000000/applications/"
        )

        assert response.status_code == 404

    def test_another_employers_job_is_the_same_404_as_an_unknown_one(
        self, employer, profile, other_profile, candidate
    ):
        """Ownership is in the lookup: a 403 would confirm the job exists."""
        theirs = make_job(other_profile)
        make_application(candidate, theirs)

        response = api_client(employer).get(inbox_url(theirs))
        unknown = api_client(employer).get(
            "/api/v1/jobs/00000000-0000-0000-0000-000000000000/applications/"
        )

        assert response.status_code == 404
        assert response.json() == unknown.json()
        assert str(candidate.pk) not in response.content.decode()

    def test_the_inbox_is_read_only(self, employer, job):
        response = api_client(employer).post(inbox_url(job), {}, format="json")

        assert response.status_code == 405


# ---------------------------------------------------------------------------
# Contents
# ---------------------------------------------------------------------------


class TestList:
    def test_a_job_with_no_applications_gets_an_empty_page(self, employer, job):
        body = api_client(employer).get(inbox_url(job)).json()

        assert body["count"] == 0
        assert body["results"] == []

    def test_every_applicant_to_this_job_is_listed_once(
        self, employer, job, candidate, other_candidate
    ):
        mine = make_application(candidate, job)
        theirs = make_application(other_candidate, job)

        body = api_client(employer).get(inbox_url(job)).json()

        assert body["count"] == 2
        assert {row["id"] for row in body["results"]} == {
            str(mine.id),
            str(theirs.id),
        }

    def test_another_of_the_employers_jobs_is_a_separate_inbox(
        self, employer, job, candidate, other_candidate
    ):
        this_job = make_application(candidate, job)
        other_job = make_application(other_candidate, make_job(job.employer))

        body = api_client(employer).get(inbox_url(job)).json()

        assert body["count"] == 1
        assert body["results"][0]["id"] == str(this_job.id)
        assert str(other_job.id) not in {row["id"] for row in body["results"]}

    def test_a_candidate_applying_to_two_employers_appears_in_both_inboxes(
        self, employer, profile, other_employer, other_profile, candidate
    ):
        """Access is granted by the job, so a shared candidate is expected --
        with a different label on each side (asserted in `TestIdentity`)."""
        our_job = make_job(profile)
        their_job = make_job(other_profile)
        make_application(candidate, our_job)
        make_application(candidate, their_job)

        ours = api_client(employer).get(inbox_url(our_job)).json()
        theirs = api_client(other_employer).get(inbox_url(their_job)).json()

        assert ours["count"] == 1
        assert theirs["count"] == 1

    def test_newest_first(self, employer, job, candidate, other_candidate):
        older = make_application(candidate, job)
        newer = make_application(other_candidate, job)
        Application.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(days=1)
        )

        body = api_client(employer).get(inbox_url(job)).json()

        assert [row["id"] for row in body["results"]] == [
            str(newer.id),
            str(older.id),
        ]

    def test_the_body_is_an_application_and_the_alias(self, employer, job, candidate):
        application = make_application(candidate, job)

        row = api_client(employer).get(inbox_url(job)).json()["results"][0]

        assert set(row) == EXPECTED_FIELDS
        assert set(row["candidate"]) == EXPECTED_CANDIDATE_FIELDS
        assert row["id"] == str(application.id)
        assert row["status"] == Application.Status.APPLIED
        assert row["status_display"] == "Applied"
        assert row["screening_status"] == Application.ScreeningStatus.NOT_SCREENED
        assert row["candidate"]["title"] == "Backend developer"
        assert row["candidate"]["location"] == "Dhaka"
        assert row["candidate"]["remote_ok"] is True
        assert row["candidate"]["skills"] == ["Python", "PostgreSQL"]

    @pytest.mark.parametrize("status", Application.Status.values)
    def test_every_pipeline_status_is_returned_with_its_label(
        self, employer, job, candidate, status
    ):
        make_application(candidate, job, status=status)

        row = api_client(employer).get(inbox_url(job)).json()["results"][0]

        assert row["status"] == status
        assert row["status_display"] == Application.Status(status).label

    def test_an_application_to_a_closed_job_stays_in_the_inbox(
        self, employer, job, candidate
    ):
        """The application is the record; closing the posting must not make a
        candidate vanish from the employer's list."""
        application = make_application(candidate, job)
        job.status = Job.Status.CLOSED
        job.save(update_fields=["status"])

        body = api_client(employer).get(inbox_url(job)).json()

        assert body["count"] == 1
        assert body["results"][0]["id"] == str(application.id)

    def test_the_match_score_fields_are_empty_until_phase_2(
        self, employer, job, candidate
    ):
        make_application(candidate, job)

        row = api_client(employer).get(inbox_url(job)).json()["results"][0]

        assert row["match_score"] is None

    def test_a_stored_score_is_exposed(self, employer, job, candidate):
        """Proves the field is wired, not hard-coded to null."""
        make_application(candidate, job, match_score=87)

        row = api_client(employer).get(inbox_url(job)).json()["results"][0]

        assert row["match_score"] == 87

    def test_page_size_is_honoured(self, employer, job, make_user):
        for _ in range(3):
            make_application(make_candidate(make_user), job)

        body = api_client(employer).get(f"{inbox_url(job)}?page_size=1").json()

        assert body["count"] == 3
        assert body["page_size"] == 1
        assert len(body["results"]) == 1
        assert body["next"] is not None

    def test_page_size_is_capped_at_the_project_ceiling(self, employer, job, candidate):
        make_application(candidate, job)

        body = api_client(employer).get(f"{inbox_url(job)}?page_size=1000").json()

        assert body["page_size"] == 100


# ---------------------------------------------------------------------------
# Identity: the alias, and nothing else
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_the_row_carries_this_employers_alias(
        self, employer, profile, job, candidate
    ):
        make_application(candidate, job)

        row = api_client(employer).get(inbox_url(job)).json()["results"][0]

        stored = CandidateAlias.objects.get(employer=profile, candidate=candidate)
        assert row["candidate"]["alias"] == stored.alias

    def test_no_name_email_photo_or_internal_id_in_the_body(
        self, employer, job, candidate
    ):
        make_application(candidate, job)

        raw = api_client(employer).get(inbox_url(job)).content.decode()
        user = candidate.user

        # Values: the candidate's own data must not appear anywhere.
        assert str(candidate.pk) not in raw
        assert str(user.pk) not in raw
        assert user.email not in raw
        assert user.first_name not in raw
        assert user.last_name not in raw

        # Keys: a renamed field would carry the same data.
        for forbidden in (
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "photo",
            "avatar",
            "resume",
        ):
            assert forbidden not in raw

    def test_the_alias_is_stable_across_that_employers_jobs(
        self, employer, profile, job, candidate
    ):
        """REQ-FR-054: the same employer sees the same label on every posting."""
        second_job = make_job(profile)
        make_application(candidate, job)
        make_application(candidate, second_job)

        first = api_client(employer).get(inbox_url(job)).json()["results"][0]
        second = api_client(employer).get(inbox_url(second_job)).json()["results"][0]

        assert first["candidate"]["alias"] == second["candidate"]["alias"]

    def test_two_employers_see_different_aliases_for_one_candidate(
        self, employer, profile, other_employer, other_profile, candidate
    ):
        """Otherwise the two inboxes could be joined on the label."""
        our_job = make_job(profile)
        their_job = make_job(other_profile)
        make_application(candidate, our_job)
        make_application(candidate, their_job)

        ours = api_client(employer).get(inbox_url(our_job)).json()["results"][0]
        theirs = (
            api_client(other_employer).get(inbox_url(their_job)).json()["results"][0]
        )

        assert ours["candidate"]["alias"] != theirs["candidate"]["alias"]
        assert CandidateAlias.objects.filter(candidate=candidate).count() == 2

    def test_the_alias_is_created_once_and_reused(
        self, employer, profile, job, candidate
    ):
        """A second visit must not mint a second label for the same pair."""
        make_application(candidate, job)

        first = api_client(employer).get(inbox_url(job)).json()["results"][0]
        second = api_client(employer).get(inbox_url(job)).json()["results"][0]

        assert first["candidate"]["alias"] == second["candidate"]["alias"]
        assert CandidateAlias.objects.filter(employer=profile).count() == 1

    def test_decision_and_filter_columns_are_not_exposed(
        self, employer, job, candidate
    ):
        """Gap G3 and REQ-FR-052 own these payloads; 1.40 must not pre-empt them."""
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

        raw = api_client(employer).get(inbox_url(job)).content.decode()

        for forbidden in (
            "not_matched_reason",
            "filter_rules_version",
            "match_rationale",
            "decision_override",
            "assessment_gate_status",
            "requires 5 years of Python",
        ):
            assert forbidden not in raw


# ---------------------------------------------------------------------------
# ?status=
# ---------------------------------------------------------------------------


class TestStatusFilter:
    def test_a_not_matched_application_is_listed_not_hidden(
        self, employer, job, candidate
    ):
        """Gap G3: a hard-filter outcome stays reviewable."""
        application = make_application(
            candidate, job, status=Application.Status.NOT_MATCHED
        )

        body = api_client(employer).get(inbox_url(job)).json()

        assert body["count"] == 1
        assert body["results"][0]["id"] == str(application.id)

    @pytest.mark.parametrize("status", Application.Status.values)
    def test_the_filter_selects_one_status(
        self, employer, job, candidate, other_candidate, status
    ):
        other_status = (
            Application.Status.REJECTED
            if status != Application.Status.REJECTED
            else Application.Status.APPLIED
        )
        mine = make_application(candidate, job, status=status)
        make_application(other_candidate, job, status=other_status)

        body = api_client(employer).get(f"{inbox_url(job)}?status={status}").json()

        assert body["count"] == 1
        assert body["results"][0]["id"] == str(mine.id)
        assert body["results"][0]["status"] == status

    def test_the_filter_is_scoped_to_the_job(
        self, employer, job, candidate, other_candidate
    ):
        make_application(candidate, job)
        other = make_application(
            other_candidate,
            make_job(job.employer),
            status=Application.Status.SHORTLISTED,
        )

        body = api_client(employer).get(f"{inbox_url(job)}?status=shortlisted").json()

        assert body["count"] == 0
        assert str(other.id) not in {row["id"] for row in body["results"]}

    def test_an_unknown_status_is_400(self, employer, job):
        response = api_client(employer).get(f"{inbox_url(job)}?status=maybe")

        assert response.status_code == 400
        assert "status" in response.json()

    def test_a_blank_status_means_no_filter(self, employer, job, candidate):
        make_application(candidate, job, status=Application.Status.REJECTED)

        body = api_client(employer).get(f"{inbox_url(job)}?status=").json()

        assert body["count"] == 1
