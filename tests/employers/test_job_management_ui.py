"""Employer job management pages (REQ-FR-025-027, pages #35-#37, batch 1.30).

What these assert beyond "the page renders":

* the portal is employer-only and profile-only: anonymous gets the login
  redirect with `next`, a candidate or a platform admin gets 403, and an
  employer who has not onboarded is sent to onboarding with a sentence rather
  than shown a form with nowhere to save;
* another employer's job id is a 404 on every page and every action, the same
  answer as an id that does not exist;
* page #35's tabs filter by status and each count is the count for that status;
  an unrecognised `status` falls back to Active instead of raising;
* the "New" column counts `applied` only -- once an application is screened it
  is no longer new;
* page #36 sets `draft` itself, so a POST that carries `status=active` cannot
  publish; the same form drives auto-save, and an invalid auto-save says so
  without changing the row or writing an audit entry;
* page #37's funnel is a table of stage counts, and the buttons offered depend
  on the posting state;
* every state action is POST-only, CSRF-protected and audited, and a conflict
  leaves the job where it was with the API's sentence;
* employer-entered text is escaped on every page.
"""

from __future__ import annotations

import uuid

import pytest
from django.test import Client

from accounts.models import User
from candidates.models import CandidateProfile
from core.models import AuditLogEntry
from employers.models import EmployerProfile
from matching.models import Application, Job

pytestmark = pytest.mark.django_db

JOBS_URL = "/employer/jobs/"
NEW_URL = "/employer/jobs/new/"


def overview_url(job_id) -> str:
    return f"/employer/jobs/{job_id}/"


def edit_url(job_id) -> str:
    return f"/employer/jobs/{job_id}/edit/"


def action_url(job_id, action: str) -> str:
    return f"/employer/jobs/{job_id}/{action}/"


@pytest.fixture
def employer(make_user):
    return make_user("employer_hr", email="hr@example.com")


@pytest.fixture
def profile(employer):
    return EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")


@pytest.fixture
def job(profile):
    return Job.objects.create(
        employer=profile,
        title="Backend Engineer",
        description="Build and run the screening API.",
        location="Dhaka",
    )


def client_for(user) -> Client:
    client = Client()
    client.force_login(user)
    return client


def make_candidate(index: int) -> CandidateProfile:
    user = User.objects.create_user(
        f"candidate{index}@example.com", "not-used-in-tests"
    )
    return CandidateProfile.objects.create(user=user, title="Developer")


def make_application(job: Job, index: int, status=Application.Status.APPLIED):
    return Application.objects.create(
        job=job, candidate=make_candidate(index), status=status
    )


class TestAccess:
    def test_anonymous_is_redirected_to_login(self):
        response = Client().get(JOBS_URL)

        assert response.status_code == 302
        assert response["Location"].startswith("/login/")
        assert "next=/employer/jobs/" in response["Location"]

    def test_a_candidate_is_403(self, make_user):
        response = client_for(make_user("candidate")).get(JOBS_URL)

        assert response.status_code == 403

    def test_a_platform_admin_is_403(self):
        admin = User.objects.create_superuser("admin@example.com")

        response = client_for(admin).get(JOBS_URL)

        assert response.status_code == 403

    def test_an_employer_without_a_profile_is_sent_to_onboarding(self, make_user):
        employer = make_user("employer_hr")

        response = client_for(employer).get(JOBS_URL)

        assert response.status_code == 302
        assert response["Location"] == "/employer/onboarding/"

    def test_another_employers_job_is_404_everywhere(self, job, make_user):
        other = make_user("employer_hr")
        EmployerProfile.objects.create(user=other, company_name="Other Ltd")
        client = client_for(other)

        assert client.get(overview_url(job.pk)).status_code == 404
        assert client.get(edit_url(job.pk)).status_code == 404
        assert client.post(action_url(job.pk, "activate")).status_code == 404
        assert client.post(action_url(job.pk, "delete")).status_code == 404

        job.refresh_from_db()
        assert job.status == Job.Status.DRAFT


class TestJobsList:
    def test_an_empty_active_tab_explains_itself(self, employer, profile):
        response = client_for(employer).get(JOBS_URL)

        assert response.status_code == 200
        assert "No active jobs yet." in response.content.decode()
        assert "New job" in response.content.decode()

    def test_the_active_tab_is_the_default(self, employer, profile):
        Job.objects.create(employer=profile, title="Draft role")
        Job.objects.create(
            employer=profile, title="Live role", status=Job.Status.ACTIVE
        )

        content = client_for(employer).get(JOBS_URL).content.decode()

        assert "Live role" in content
        assert "Draft role" not in content

    def test_the_tabs_carry_a_count_for_each_status(self, employer, profile):
        Job.objects.create(employer=profile, title="One")
        Job.objects.create(employer=profile, title="Two", status=Job.Status.ACTIVE)
        Job.objects.create(employer=profile, title="Three", status=Job.Status.CLOSED)

        content = client_for(employer).get(JOBS_URL).content.decode()

        assert "Draft (1)" in content
        assert "Active (1)" in content
        assert "Closed (1)" in content
        assert "Paused (0)" in content

    def test_the_tab_filters_by_status(self, employer, profile):
        Job.objects.create(employer=profile, title="Draft role")
        Job.objects.create(
            employer=profile, title="Live role", status=Job.Status.ACTIVE
        )

        content = client_for(employer).get(f"{JOBS_URL}?status=draft").content.decode()

        assert "Draft role" in content
        assert "Live role" not in content

    def test_an_unknown_tab_falls_back_to_active(self, employer, profile):
        Job.objects.create(
            employer=profile, title="Live role", status=Job.Status.ACTIVE
        )

        response = client_for(employer).get(f"{JOBS_URL}?status=archived")

        assert response.status_code == 200
        assert "Live role" in response.content.decode()

    def test_the_row_reports_applicants_new_and_last_activity(
        self, employer, profile, job
    ):
        make_application(job, 1)
        make_application(job, 2)
        make_application(job, 3, status=Application.Status.SCREENED)

        response = client_for(employer).get(f"{JOBS_URL}?status=draft")

        row = response.context["jobs"][0]
        assert row.applicant_count == 3
        assert row.new_count == 2
        assert row.last_activity is not None
        assert "3" in response.content.decode()

    def test_only_drafts_offer_edit_and_delete(self, employer, profile, job):
        Job.objects.create(
            employer=profile, title="Live role", status=Job.Status.ACTIVE
        )

        draft_content = (
            client_for(employer).get(f"{JOBS_URL}?status=draft").content.decode()
        )
        active_content = (
            client_for(employer).get(f"{JOBS_URL}?status=active").content.decode()
        )

        assert f"/employer/jobs/{job.pk}/edit/" in draft_content
        assert "Delete" in draft_content
        assert "/edit/" not in active_content
        assert "Delete" not in active_content

    def test_the_title_is_escaped(self, employer, profile):
        Job.objects.create(employer=profile, title='<script>alert("x")</script>')

        content = client_for(employer).get(f"{JOBS_URL}?status=draft").content.decode()

        assert '<script>alert("x")</script>' not in content
        assert "&lt;script&gt;" in content

    def test_another_employers_jobs_are_not_listed(self, employer, profile, make_user):
        other = make_user("employer_hr")
        other_profile = EmployerProfile.objects.create(
            user=other, company_name="Other Ltd"
        )
        Job.objects.create(
            employer=other_profile, title="Their role", status=Job.Status.ACTIVE
        )

        content = client_for(employer).get(JOBS_URL).content.decode()

        assert "Their role" not in content


class TestCreate:
    def test_the_form_renders_the_writable_fields(self, employer, profile):
        content = client_for(employer).get(NEW_URL).content.decode()

        assert "New job" in content
        assert 'name="title"' in content
        assert 'name="description"' in content
        assert 'name="experience_level"' in content
        assert 'name="remote_allowed"' in content
        # Not writable from the page: publishing is the Activate action.
        assert 'name="status"' not in content
        assert 'name="employer"' not in content

    def test_a_valid_post_creates_a_draft_and_audits_it(self, employer, profile):
        response = client_for(employer).post(
            NEW_URL,
            {
                "title": "Data Engineer",
                "description": "Pipelines.",
                "location": "Remote",
                "remote_allowed": "on",
                "experience_level": "senior",
            },
        )

        job = Job.objects.get()
        assert response.status_code == 302
        assert response["Location"] == edit_url(job.pk)
        assert job.status == Job.Status.DRAFT
        assert job.employer == profile
        assert job.remote_allowed is True

        entry = AuditLogEntry.objects.get()
        assert entry.action == "job.created"
        assert entry.details == {"title": "Data Engineer", "status": "draft"}

    def test_status_in_the_body_cannot_publish(self, employer, profile):
        client_for(employer).post(
            NEW_URL, {"title": "Data Engineer", "status": "active"}
        )

        assert Job.objects.get().status == Job.Status.DRAFT

    def test_a_missing_title_re_renders_with_the_error(self, employer, profile):
        response = client_for(employer).post(NEW_URL, {"title": ""})

        assert response.status_code == 200
        assert "This field is required." in response.content.decode()
        assert Job.objects.count() == 0
        assert AuditLogEntry.objects.count() == 0

    def test_a_draft_may_be_created_without_a_description(self, employer, profile):
        response = client_for(employer).post(NEW_URL, {"title": "Minimal role"})

        assert response.status_code == 302
        assert Job.objects.get().description == ""

    def test_a_post_without_a_csrf_token_is_rejected(self, employer, profile):
        client = Client(enforce_csrf_checks=True)
        client.force_login(employer)

        response = client.post(NEW_URL, {"title": "No token"})

        assert response.status_code == 403
        assert Job.objects.count() == 0


class TestEdit:
    def test_the_form_shows_the_stored_values(self, employer, profile, job):
        content = client_for(employer).get(edit_url(job.pk)).content.decode()

        assert "Edit job" in content
        assert "Backend Engineer" in content
        assert "Build and run the screening API." in content

    def test_a_save_updates_the_draft_and_audits_the_field_names(
        self, employer, profile, job
    ):
        response = client_for(employer).post(
            edit_url(job.pk),
            {
                "title": "Senior Backend Engineer",
                "description": job.description,
                "location": "Remote",
                "remote_allowed": "on",
                "experience_level": "senior",
            },
        )

        job.refresh_from_db()
        assert response.status_code == 302
        assert job.title == "Senior Backend Engineer"
        assert job.location == "Remote"
        assert job.remote_allowed is True

        entry = AuditLogEntry.objects.get()
        assert entry.action == "job.updated"
        assert entry.details == {
            "changed": ["experience_level", "location", "remote_allowed", "title"]
        }

    def test_a_save_that_changes_nothing_writes_no_entry(self, employer, profile, job):
        # A browser submits every control, so an unchanged save is the full
        # current payload -- not just the title (which would clear the rest).
        client_for(employer).post(
            edit_url(job.pk),
            {
                "title": job.title,
                "description": job.description,
                "location": job.location,
                "experience_level": "",
            },
        )

        assert AuditLogEntry.objects.count() == 0

    @pytest.mark.parametrize(
        "status", [Job.Status.ACTIVE, Job.Status.PAUSED, Job.Status.CLOSED]
    )
    def test_a_published_job_redirects_to_its_overview(
        self, employer, profile, job, status
    ):
        Job.objects.filter(pk=job.pk).update(status=status)

        response = client_for(employer).get(edit_url(job.pk), follow=True)

        assert response.redirect_chain[-1][0] == overview_url(job.pk)
        assert "Only a draft job can be edited." in response.content.decode()

    def test_an_invalid_save_keeps_the_row_unchanged(self, employer, profile, job):
        response = client_for(employer).post(
            edit_url(job.pk), {"title": "   ", "description": "new"}
        )

        assert response.status_code == 200
        job.refresh_from_db()
        assert job.title == "Backend Engineer"
        assert job.description == "Build and run the screening API."
        assert AuditLogEntry.objects.count() == 0


class TestAutosave:
    def test_a_change_is_saved_and_reported(self, employer, profile, job):
        response = client_for(employer).post(
            action_url(job.pk, "autosave"),
            {
                "title": "Backend Engineer II",
                "description": job.description,
                "location": job.location,
                "experience_level": "",
            },
        )

        assert response.status_code == 200
        content = response.content.decode()
        assert "Draft saved" in content
        assert 'aria-live="polite"' in content
        job.refresh_from_db()
        assert job.title == "Backend Engineer II"
        assert AuditLogEntry.objects.get().details == {"changed": ["title"]}

    def test_an_invalid_autosave_says_so_and_changes_nothing(
        self, employer, profile, job
    ):
        response = client_for(employer).post(
            action_url(job.pk, "autosave"), {"title": ""}
        )

        content = response.content.decode()
        assert response.status_code == 200
        assert "Not saved" in content
        job.refresh_from_db()
        assert job.title == "Backend Engineer"
        assert AuditLogEntry.objects.count() == 0

    def test_an_unchanged_autosave_writes_no_entry(self, employer, profile, job):
        response = client_for(employer).post(
            action_url(job.pk, "autosave"),
            {
                "title": job.title,
                "description": job.description,
                "location": job.location,
                "experience_level": "",
            },
        )

        assert response.status_code == 200
        assert AuditLogEntry.objects.count() == 0

    def test_a_published_job_cannot_be_autosaved(self, employer, profile, job):
        Job.objects.filter(pk=job.pk).update(status=Job.Status.ACTIVE)

        response = client_for(employer).post(
            action_url(job.pk, "autosave"), {"title": "Renamed"}
        )

        assert response.status_code == 409
        job.refresh_from_db()
        assert job.title == "Backend Engineer"

    def test_autosave_is_post_only(self, employer, profile, job):
        response = client_for(employer).get(action_url(job.pk, "autosave"))

        assert response.status_code == 405


class TestOverview:
    def test_the_funnel_counts_each_stage(self, employer, profile, job):
        make_application(job, 1)
        make_application(job, 2)
        make_application(job, 3, status=Application.Status.SHORTLISTED)

        response = client_for(employer).get(overview_url(job.pk))

        stages = {
            stage["label"]: stage["count"] for stage in response.context["stages"]
        }
        assert stages == {
            "Applied": 2,
            "Screened": 0,
            "Shortlisted": 1,
            "Interview": 0,
            "Offer": 0,
        }
        assert response.context["applicant_total"] == 3
        assert "3 applications in total." in response.content.decode()

    def test_the_funnel_has_a_column_header_per_stage(self, employer, profile, job):
        content = client_for(employer).get(overview_url(job.pk)).content.decode()

        assert content.count('<th scope="col"') == 5
        for label in ("Applied", "Screened", "Shortlisted", "Interview", "Offer"):
            assert f">{label}</th>" in content

    def test_an_empty_pipeline_says_so(self, employer, profile, job):
        content = client_for(employer).get(overview_url(job.pk)).content.decode()

        assert "Nothing has been submitted to this job yet." in content

    def test_a_draft_offers_activate_edit_and_delete(self, employer, profile, job):
        content = client_for(employer).get(overview_url(job.pk)).content.decode()

        assert "Activate" in content
        assert action_url(job.pk, "activate") in content
        assert edit_url(job.pk) in content
        assert action_url(job.pk, "delete") in content
        assert action_url(job.pk, "pause") not in content

    def test_an_active_job_offers_pause_and_close(self, employer, profile, job):
        Job.objects.filter(pk=job.pk).update(status=Job.Status.ACTIVE)

        content = client_for(employer).get(overview_url(job.pk)).content.decode()

        assert action_url(job.pk, "pause") in content
        assert action_url(job.pk, "close") in content
        assert action_url(job.pk, "activate") not in content

    def test_a_paused_job_offers_resume_and_close(self, employer, profile, job):
        Job.objects.filter(pk=job.pk).update(status=Job.Status.PAUSED)

        content = client_for(employer).get(overview_url(job.pk)).content.decode()

        assert "Resume" in content
        assert action_url(job.pk, "activate") in content
        assert action_url(job.pk, "close") in content
        assert action_url(job.pk, "pause") not in content

    def test_a_closed_job_offers_no_state_action(self, employer, profile, job):
        Job.objects.filter(pk=job.pk).update(status=Job.Status.CLOSED)

        content = client_for(employer).get(overview_url(job.pk)).content.decode()

        assert "This job is closed." in content
        assert action_url(job.pk, "activate") not in content
        assert action_url(job.pk, "pause") not in content
        assert action_url(job.pk, "close") not in content

    def test_the_description_is_escaped(self, employer, profile, job):
        Job.objects.filter(pk=job.pk).update(
            description='<img src=x onerror="alert(1)">'
        )

        content = client_for(employer).get(overview_url(job.pk)).content.decode()

        assert '<img src=x onerror="alert(1)">' not in content
        assert "&lt;img" in content


class TestStateActions:
    def test_activate_publishes_and_audits(self, employer, profile, job):
        response = client_for(employer).post(
            action_url(job.pk, "activate"), follow=True
        )

        job.refresh_from_db()
        assert job.status == Job.Status.ACTIVE
        assert "Job activated." in response.content.decode()
        assert AuditLogEntry.objects.get().details == {
            "from": "draft",
            "to": "active",
        }

    def test_activating_an_active_job_is_a_no_op_message(self, employer, profile, job):
        Job.objects.filter(pk=job.pk).update(status=Job.Status.ACTIVE)

        response = client_for(employer).post(
            action_url(job.pk, "activate"), follow=True
        )

        assert "This job is already active." in response.content.decode()
        assert AuditLogEntry.objects.count() == 0

    def test_pause_stops_a_live_job(self, employer, profile, job):
        Job.objects.filter(pk=job.pk).update(status=Job.Status.ACTIVE)

        response = client_for(employer).post(action_url(job.pk, "pause"), follow=True)

        job.refresh_from_db()
        assert job.status == Job.Status.PAUSED
        assert "Job paused." in response.content.decode()

    def test_close_retires_a_live_job(self, employer, profile, job):
        Job.objects.filter(pk=job.pk).update(status=Job.Status.PAUSED)

        response = client_for(employer).post(action_url(job.pk, "close"), follow=True)

        job.refresh_from_db()
        assert job.status == Job.Status.CLOSED
        assert "Job closed." in response.content.decode()

    def test_closing_a_draft_is_refused(self, employer, profile, job):
        response = client_for(employer).post(action_url(job.pk, "close"), follow=True)

        job.refresh_from_db()
        assert job.status == Job.Status.DRAFT
        assert (
            "Only an active or paused job can be closed." in response.content.decode()
        )
        assert AuditLogEntry.objects.count() == 0

    def test_a_closed_job_cannot_be_reactivated(self, employer, profile, job):
        Job.objects.filter(pk=job.pk).update(status=Job.Status.CLOSED)

        response = client_for(employer).post(
            action_url(job.pk, "activate"), follow=True
        )

        job.refresh_from_db()
        assert job.status == Job.Status.CLOSED
        assert "A closed job cannot be reactivated." in response.content.decode()

    def test_delete_removes_a_draft_and_audits_it(self, employer, profile, job):
        response = client_for(employer).post(action_url(job.pk, "delete"), follow=True)

        assert response.redirect_chain[-1][0] == JOBS_URL
        assert "Draft deleted." in response.content.decode()
        assert not Job.objects.filter(pk=job.pk).exists()

        entry = AuditLogEntry.objects.get()
        assert entry.action == "job.deleted"
        assert entry.resource_id == job.pk
        assert entry.details == {"title": "Backend Engineer"}

    def test_delete_refuses_a_published_job(self, employer, profile, job):
        Job.objects.filter(pk=job.pk).update(status=Job.Status.ACTIVE)

        response = client_for(employer).post(action_url(job.pk, "delete"), follow=True)

        assert Job.objects.filter(pk=job.pk).exists()
        assert "Only a draft job can be deleted." in response.content.decode()
        assert AuditLogEntry.objects.count() == 0

    @pytest.mark.parametrize("action", ["activate", "pause", "close", "delete"])
    def test_actions_are_post_only(self, employer, profile, job, action):
        response = client_for(employer).get(action_url(job.pk, action))

        assert response.status_code == 405
        job.refresh_from_db()
        assert job.status == Job.Status.DRAFT

    def test_an_action_without_a_csrf_token_is_rejected(self, employer, profile, job):
        client = Client(enforce_csrf_checks=True)
        client.force_login(employer)

        response = client.post(action_url(job.pk, "activate"))

        assert response.status_code == 403
        job.refresh_from_db()
        assert job.status == Job.Status.DRAFT

    def test_an_unknown_job_is_404(self, employer, profile):
        response = client_for(employer).post(action_url(uuid.uuid4(), "activate"))

        assert response.status_code == 404
