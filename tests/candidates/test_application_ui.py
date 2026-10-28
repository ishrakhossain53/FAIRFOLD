"""Candidate application tracker and detail UI (REQ-FR-023, batch 1.39).

Pages #28 and #29 (design.md S06/S07). These sit on top of the API tests
(`tests/matching/test_application_list_detail_api.py`) and assert what the
server-rendered pages add:

* the two guards, in order: anonymous to `/login/` with a `next`, a
  non-candidate role to 403, a candidate without a profile to onboarding;
* owner-only detail: another candidate's application is a 404 and none of its
  content is rendered;
* the empty state, the filtered-empty state and the status filter;
* both layouts S06 asks for: a real table on desktop and cards on mobile, from
  one server-rendered row set;
* the status pill is icon + text for every model status, and `not_matched` reads
  as reviewable rather than rejected;
* the score slot is empty ("Not screened yet") until Phase 2, and a score that
  exists is rendered;
* REQ-FR-042: the employer name is only shown when the employer opted in;
* the job's own text is escaped;
* the header gives a candidate a route to the tracker.
"""

from __future__ import annotations

import pytest
from django.test import Client

from candidates.models import CandidateProfile
from employers.models import EmployerProfile
from matching.models import Application, Job

pytestmark = pytest.mark.django_db

LIST_URL = "/candidate/applications/"


@pytest.fixture
def employer(make_user):
    return EmployerProfile.objects.create(
        user=make_user("employer_hr"),
        company_name="Acme Ltd",
    )


@pytest.fixture
def candidate(make_user):
    user = make_user("candidate", email="ada@example.com")
    return CandidateProfile.objects.create(user=user, title="Backend developer")


@pytest.fixture
def signed_in(candidate):
    client = Client()
    client.force_login(candidate.user)
    return client


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


def detail_url(application) -> str:
    return f"{LIST_URL}{application.id}/"


def body(response) -> str:
    return response.content.decode()


class TestAccess:
    def test_anonymous_is_sent_to_login_with_a_next(self):
        response = Client().get(LIST_URL)

        assert response.status_code == 302
        assert response.url == "/login/?next=/candidate/applications/"

    def test_anonymous_detail_is_sent_to_login(self, candidate, job):
        application = make_application(candidate, job)

        response = Client().get(detail_url(application))

        assert response.status_code == 302
        assert response.url.startswith("/login/?next=")

    @pytest.mark.parametrize("role", ["employer_hr", "interviewer"])
    def test_a_non_candidate_role_is_forbidden(self, make_user, candidate, job, role):
        user = make_user(role)
        client = Client()
        client.force_login(user)
        application = make_application(candidate, job)

        assert client.get(LIST_URL).status_code == 403
        assert client.get(detail_url(application)).status_code == 403

    def test_a_platform_admin_is_forbidden(self, make_user, candidate, job):
        user = make_user(is_staff=True)
        client = Client()
        client.force_login(user)
        application = make_application(candidate, job)

        assert client.get(LIST_URL).status_code == 403
        assert client.get(detail_url(application)).status_code == 403

    def test_a_candidate_without_a_profile_is_sent_to_onboarding(self, make_user):
        user = make_user("candidate")
        client = Client()
        client.force_login(user)

        response = client.get(LIST_URL)

        assert response.status_code == 302
        assert response.url == "/candidate/onboarding/"

    def test_a_candidate_without_a_profile_cannot_read_a_detail(
        self, make_user, candidate, job
    ):
        """The lookup is scoped to `request.user`, so no profile means no row."""
        application = make_application(candidate, job)
        user = make_user("candidate")
        client = Client()
        client.force_login(user)

        response = client.get(detail_url(application))

        assert response.status_code == 404
        assert "Backend Engineer" not in body(response)


class TestList:
    def test_the_empty_state_offers_the_job_board(self, signed_in):
        response = signed_in.get(LIST_URL)
        html = body(response)

        assert response.status_code == 200
        assert "My applications" in html
        assert "You haven&#x27;t applied to anything yet." in html or (
            "You haven't applied to anything yet." in html
        )
        assert 'href="/jobs/"' in html

    def test_only_the_callers_applications_are_shown(
        self, signed_in, candidate, job, make_user
    ):
        make_application(candidate, job)
        other = CandidateProfile.objects.create(user=make_user("candidate"))
        theirs = make_application(other, make_job(job.employer, title="Secret Role"))

        html = body(signed_in.get(LIST_URL))

        assert "Backend Engineer" in html
        assert "Secret Role" not in html
        assert str(theirs.id) not in html

    def test_the_status_is_text_and_icon(self, signed_in, candidate, job):
        make_application(candidate, job, status=Application.Status.SHORTLISTED)

        html = body(signed_in.get(LIST_URL))

        assert "Shortlisted" in html
        assert "✔" in html

    def test_not_matched_reads_as_reviewable_not_rejected(
        self, signed_in, candidate, job
    ):
        make_application(candidate, job, status=Application.Status.NOT_MATCHED)

        html = body(signed_in.get(LIST_URL))

        assert "Not matched" in html
        assert "⚑" in html
        # The filter `<select>` lists every status, so the word "Rejected"
        # legitimately appears in the page. What must not appear is the rejected
        # pill's icon: `not_matched` is reviewable, not a rejection (Gap G3).
        assert "✖" not in html

    def test_both_the_table_and_the_cards_are_rendered(self, signed_in, candidate, job):
        """S06 asks for a table on desktop and cards on mobile. Both come from
        the same rows; the inactive one is `display:none`, not a second copy a
        screen reader would read twice."""
        make_application(candidate, job)

        html = body(signed_in.get(LIST_URL))

        assert "<table" in html
        assert "<article" in html
        assert "hidden overflow-x-auto md:block" in html
        assert "md:hidden" in html

    def test_the_detail_link_is_present(self, signed_in, candidate, job):
        application = make_application(candidate, job)

        html = body(signed_in.get(LIST_URL))

        assert f"/candidate/applications/{application.id}/" in html

    def test_the_status_filter_narrows_the_list(self, signed_in, candidate, job):
        make_application(candidate, job, status=Application.Status.SHORTLISTED)
        make_application(
            candidate,
            make_job(job.employer, title="Data Analyst"),
            status=Application.Status.APPLIED,
        )

        html = body(signed_in.get(f"{LIST_URL}?status=shortlisted"))

        assert "Backend Engineer" in html
        assert "Data Analyst" not in html

    def test_an_unknown_status_falls_back_to_all(self, signed_in, candidate, job):
        make_application(candidate, job)

        html = body(signed_in.get(f"{LIST_URL}?status=bogus"))

        assert "Backend Engineer" in html

    def test_a_filter_with_no_rows_offers_the_full_list(
        self, signed_in, candidate, job
    ):
        make_application(candidate, job, status=Application.Status.APPLIED)

        html = body(signed_in.get(f"{LIST_URL}?status=rejected"))

        assert "No applications with this status." in html
        assert "Show all applications" in html
        # The true empty state must not claim the candidate has never applied.
        assert "You haven" not in html

    def test_a_job_title_is_escaped(self, signed_in, candidate, employer):
        job = make_job(employer, title="Alert <script>alert(1)</script>")
        make_application(candidate, job)

        html = body(signed_in.get(LIST_URL))

        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html

    def test_the_match_column_is_empty_before_screening(
        self, signed_in, candidate, job
    ):
        make_application(candidate, job)

        html = body(signed_in.get(LIST_URL))

        assert "Not screened" in html

    def test_a_score_is_shown_when_it_exists(self, signed_in, candidate, job):
        make_application(candidate, job, match_score=72)

        html = body(signed_in.get(LIST_URL))

        assert "72 / 100" in html
        assert "Match score 72 out of 100" in html
        assert "Not screened" not in html

    def test_the_employer_name_is_only_shown_when_disclosed(
        self, signed_in, candidate, job
    ):
        make_application(candidate, job)

        assert "Acme Ltd" not in body(signed_in.get(LIST_URL))

        job.employer.show_company_name = True
        job.employer.save(update_fields=["show_company_name"])

        assert "Acme Ltd" in body(signed_in.get(LIST_URL))

    def test_the_header_links_a_candidate_to_the_tracker(self, signed_in):
        """The tracker's only entry point until the page #15 dashboard lands."""
        html = body(signed_in.get("/candidate/profile/"))

        assert 'href="/candidate/applications/"' in html
        assert "Applications" in html


class TestDetail:
    def test_the_owner_sees_the_application(self, signed_in, candidate, job):
        application = make_application(
            candidate, job, status=Application.Status.SCREENED
        )

        response = signed_in.get(detail_url(application))
        html = body(response)

        assert response.status_code == 200
        assert "Backend Engineer" in html
        assert "Screened" in html
        assert 'aria-current="step"' in html
        assert "Applied" in html
        assert 'href="/candidate/applications/"' in html

    def test_another_candidates_application_is_404(self, signed_in, job, make_user):
        other = CandidateProfile.objects.create(user=make_user("candidate"))
        theirs = make_application(other, make_job(job.employer, title="Secret Role"))

        response = signed_in.get(detail_url(theirs))

        assert response.status_code == 404
        assert "Secret Role" not in body(response)

    def test_an_unknown_id_is_404(self, signed_in):
        response = signed_in.get(f"{LIST_URL}00000000-0000-0000-0000-000000000000/")

        assert response.status_code == 404

    def test_a_malformed_id_is_404(self, signed_in):
        response = signed_in.get(f"{LIST_URL}not-a-uuid/")

        assert response.status_code == 404

    def test_the_score_slot_is_empty_until_phase_2(self, signed_in, candidate, job):
        application = make_application(candidate, job)

        html = body(signed_in.get(detail_url(application)))

        assert "Not screened yet." in html
        assert "Match score" in html

    def test_a_score_is_rendered_with_an_accessible_label(
        self, signed_in, candidate, job
    ):
        application = make_application(candidate, job, match_score=88)

        html = body(signed_in.get(detail_url(application)))

        assert "88" in html
        assert "Match score 88 out of 100" in html
        assert "Not screened yet." not in html

    def test_a_rejected_application_has_no_stepper(self, signed_in, candidate, job):
        application = make_application(
            candidate, job, status=Application.Status.REJECTED
        )

        html = body(signed_in.get(detail_url(application)))

        assert "Rejected" in html
        assert 'aria-current="step"' not in html
        assert "This application is closed." in html

    def test_a_not_matched_application_explains_the_review(
        self, signed_in, candidate, job
    ):
        application = make_application(
            candidate, job, status=Application.Status.NOT_MATCHED
        )

        html = body(signed_in.get(detail_url(application)))

        assert "Not matched" in html
        assert 'aria-current="step"' not in html
        assert "stays available" in html

    def test_an_active_job_links_to_its_public_page(self, signed_in, candidate, job):
        application = make_application(candidate, job)

        html = body(signed_in.get(detail_url(application)))

        assert f'href="/jobs/{job.pk}/"' in html

    def test_a_closed_job_is_not_linked(self, signed_in, candidate, job):
        application = make_application(candidate, job)
        job.status = Job.Status.CLOSED
        job.save(update_fields=["status"])

        html = body(signed_in.get(detail_url(application)))

        assert f'href="/jobs/{job.pk}/"' not in html
        assert "This job is no longer open for applications." in html

    def test_the_employer_name_is_only_shown_when_disclosed(
        self, signed_in, candidate, job
    ):
        application = make_application(candidate, job)

        assert "Acme Ltd" not in body(signed_in.get(detail_url(application)))

        job.employer.show_company_name = True
        job.employer.save(update_fields=["show_company_name"])

        assert "Acme Ltd" in body(signed_in.get(detail_url(application)))
