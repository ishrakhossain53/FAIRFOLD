"""Pages #40/#41 (S12/S13): the employer application inbox and review.

REQ-FR-029 is the requirement these tests exist for: an employer moves an
application through statuses in a browser and **never** sees the candidate's
name, email, photo or internal UUID. The alias (REQ-FR-054) is the row's whole
identity, on the list, on the review page, on the confirmation page and in the
audit entry the decision writes.

Two things are deliberately not tested here because they belong to the batch that
owns them: the transition matrix and the gate rule are `matching.services`'
(batch 1.41, `tests/matching/test_application_decision_api.py`), and the
candidate notification is batch 1.43's (`tests/notifications/`). What is tested
here is that the page reads that table rather than keeping a second copy of it,
and that the confirmation page is a GET that writes nothing.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from accounts.models import User
from candidates.models import CandidateProfile
from core.models import AuditLogEntry
from employers.models import EmployerProfile
from matching.models import Application, Job

pytestmark = pytest.mark.django_db

Status = Application.Status
Gate = Application.AssessmentGateStatus

CANDIDATE_EMAIL = "secret-candidate@example.com"
CANDIDATE_FIRST = "Ayesha"
CANDIDATE_LAST = "Rahman"


# --------------------------------------------------------------------- fixtures


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
def candidate_user():
    return User.objects.create_user(
        CANDIDATE_EMAIL,
        "not-used-in-these-tests",
        first_name=CANDIDATE_FIRST,
        last_name=CANDIDATE_LAST,
    )


@pytest.fixture
def candidate(candidate_user):
    return CandidateProfile.objects.create(
        user=candidate_user,
        title="Staff Platform Engineer at a named startup",
        location="Dhaka",
        skills=["Python"],
    )


@pytest.fixture
def job(profile):
    return Job.objects.create(employer=profile, title="Backend Engineer")


@pytest.fixture
def application(job, candidate):
    return Application.objects.create(job=job, candidate=candidate)


@pytest.fixture
def inbox_url(job):
    return reverse("employer_portal:job-applications", args=[job.pk])


@pytest.fixture
def review_url(application):
    return reverse("employer_portal:application-review", args=[application.pk])


@pytest.fixture
def shortlist_url(application):
    return reverse("employer_portal:application-shortlist", args=[application.pk])


@pytest.fixture
def reject_url(application):
    return reverse("employer_portal:application-reject", args=[application.pk])


def add_candidate(job, *, status=Status.APPLIED, gate=Gate.NOT_REQUIRED, **profile):
    """A second application on the same job, with its own candidate account."""
    user = User.objects.create_user(
        f"candidate-{User.objects.count()}@example.com", "not-used-in-these-tests"
    )
    candidate = CandidateProfile.objects.create(user=user, **profile)
    return Application.objects.create(
        job=job, candidate=candidate, status=status, assessment_gate_status=gate
    )


def alias_of(application) -> str:
    """The alias the pages must render.

    Read through the service, not the table: a test that asserts an alias is
    *absent* from a page has to create it first, and the page creates it only for
    the rows it renders.
    """
    from candidates.services import alias_for

    return alias_for(application.job.employer, application.candidate)


# ------------------------------------------------------------------ the inbox


def test_the_inbox_lists_the_jobs_applications(client, employer, application):
    client.force_login(employer)

    response = client.get(
        reverse("employer_portal:job-applications", args=[application.job_id])
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Applications" in content
    assert alias_of(application) in content


def test_the_inbox_is_scoped_to_one_job(client, employer, profile, application):
    other_job = Job.objects.create(employer=profile, title="Data Engineer")
    other_application = add_candidate(other_job)

    client.force_login(employer)
    response = client.get(
        reverse("employer_portal:job-applications", args=[application.job_id])
    )

    content = response.content.decode()
    assert "1 application." in content
    assert alias_of(other_application) not in content


def test_a_row_links_to_the_review_page(client, employer, application):
    client.force_login(employer)

    content = client.get(
        reverse("employer_portal:job-applications", args=[application.job_id])
    ).content.decode()

    assert (
        reverse("employer_portal:application-review", args=[application.pk]) in content
    )


def test_the_inbox_shows_the_status_and_the_gate(client, employer, application):
    application.status = Status.SHORTLISTED
    application.assessment_gate_status = Gate.FAILED
    application.save(update_fields=["status", "assessment_gate_status"])

    client.force_login(employer)
    content = client.get(
        reverse("employer_portal:job-applications", args=[application.job_id])
    ).content.decode()

    assert "Shortlisted" in content
    assert "Assessment not passed" in content


def test_the_inbox_shows_no_candidate_identity(client, employer, application):
    """REQ-FR-029: the alias is the row's whole identity."""
    client.force_login(employer)

    content = client.get(
        reverse("employer_portal:job-applications", args=[application.job_id])
    ).content.decode()

    assert alias_of(application) in content
    assert CANDIDATE_EMAIL not in content
    assert CANDIDATE_FIRST not in content
    assert CANDIDATE_LAST not in content
    assert str(application.candidate_id) not in content
    # The free-text headline is not rendered either: it can name an employer.
    assert "Staff Platform Engineer at a named startup" not in content


def test_each_employer_sees_their_own_alias(
    client, employer, other_employer, application
):
    from candidates.services import alias_for

    theirs = alias_for(application.job.employer, application.candidate)
    other_profile = EmployerProfile.objects.create(
        user=other_employer, company_name="Beta Ltd"
    )
    mine = alias_for(other_profile, application.candidate)
    assert theirs != mine

    client.force_login(employer)
    content = client.get(
        reverse("employer_portal:job-applications", args=[application.job_id])
    ).content.decode()

    assert theirs in content
    assert mine not in content


def test_the_status_filter_selects_one_status(client, employer, job, application):
    shortlisted = add_candidate(job, status=Status.SHORTLISTED)

    client.force_login(employer)
    content = client.get(
        reverse("employer_portal:job-applications", args=[job.pk]),
        {"status": Status.SHORTLISTED},
    ).content.decode()

    assert alias_of(shortlisted) in content
    assert alias_of(application) not in content


def test_an_unknown_status_filter_shows_everything(client, employer, job, application):
    """Page #28's rule: a hand-edited `?status=` is not an error page."""
    client.force_login(employer)

    response = client.get(
        reverse("employer_portal:job-applications", args=[job.pk]),
        {"status": "bogus"},
    )

    assert response.status_code == 200
    assert alias_of(application) in response.content.decode()


def test_the_tabs_count_the_rows(client, employer, job, application):
    add_candidate(job, status=Status.SHORTLISTED)

    client.force_login(employer)
    content = client.get(
        reverse("employer_portal:job-applications", args=[job.pk])
    ).content.decode()

    # All 2, Applied 1, Shortlisted 1 -- and no tab for a status with no rows.
    assert "All" in content
    assert "Applied" in content
    assert "Shortlisted" in content
    assert "Rejected" not in content


def test_a_filter_with_no_rows_offers_a_way_back(client, employer, job, application):
    """W28: the filter state is where an employer concludes the page is broken."""
    client.force_login(employer)

    content = client.get(
        reverse("employer_portal:job-applications", args=[job.pk]),
        {"status": Status.REJECTED},
    ).content.decode()

    assert "No applications with this status." in content
    assert "Show all 1 application" in content


def test_a_job_with_no_applications_shows_the_empty_state(client, employer, job):
    client.force_login(employer)

    content = client.get(
        reverse("employer_portal:job-applications", args=[job.pk])
    ).content.decode()

    assert "No applications yet." in content


def test_the_inbox_is_paginated(client, employer, job, application):
    for _ in range(20):
        add_candidate(job)

    client.force_login(employer)
    first = client.get(reverse("employer_portal:job-applications", args=[job.pk]))
    second = client.get(
        reverse("employer_portal:job-applications", args=[job.pk]), {"page": 2}
    )

    assert "21 applications." in first.content.decode()
    assert alias_of(application) in second.content.decode()
    assert "Next ›" in first.content.decode()


def test_another_employers_job_is_a_404(client, other_profile, job):
    client.force_login(other_profile.user)

    response = client.get(reverse("employer_portal:job-applications", args=[job.pk]))

    assert response.status_code == 404


def test_an_unknown_job_is_a_404(client, employer, profile):
    client.force_login(employer)

    response = client.get(
        reverse(
            "employer_portal:job-applications",
            args=["00000000-0000-0000-0000-000000000000"],
        )
    )

    assert response.status_code == 404


def test_a_candidate_cannot_open_the_inbox(client, candidate_user, job):
    client.force_login(candidate_user)

    response = client.get(reverse("employer_portal:job-applications", args=[job.pk]))

    assert response.status_code == 403


def test_anonymous_visitors_are_sent_to_login(client, inbox_url):
    response = client.get(inbox_url)

    assert response.status_code == 302
    assert "/login/" in response["Location"]


def test_an_employer_without_a_profile_is_sent_to_onboarding(client, make_user, job):
    client.force_login(make_user("employer_hr"))

    response = client.get(reverse("employer_portal:job-applications", args=[job.pk]))

    assert response.status_code == 302
    assert response["Location"] == reverse("employer_portal:onboarding")


# ----------------------------------------------------------- the review page


def test_the_review_page_shows_the_alias_and_the_actions(
    client, employer, application, review_url
):
    client.force_login(employer)

    content = client.get(review_url).content.decode()

    assert alias_of(application) in content
    assert "Shortlist" in content
    assert "Reject" in content
    assert "Applied" in content


def test_the_review_page_shows_no_candidate_identity(
    client, employer, application, review_url
):
    client.force_login(employer)

    content = client.get(review_url).content.decode()

    assert alias_of(application) in content
    assert CANDIDATE_EMAIL not in content
    assert CANDIDATE_FIRST not in content
    assert CANDIDATE_LAST not in content
    assert str(application.candidate_id) not in content


def test_a_pending_gate_blocks_shortlist_with_a_reason(
    client, employer, application, review_url
):
    """W27: `aria-disabled`, still focusable, and the reason is described by it."""
    application.assessment_gate_status = Gate.PENDING
    application.save(update_fields=["assessment_gate_status"])

    client.force_login(employer)
    content = client.get(review_url).content.decode()

    assert 'aria-disabled="true"' in content
    assert 'aria-describedby="shortlist-reason"' in content
    assert "Shortlisting is blocked until the required assessment is passed." in content
    # Reject is not gated: declining someone who never sat it must stay possible.
    assert (
        reverse("employer_portal:application-reject", args=[application.pk]) in content
    )


def test_a_failed_gate_blocks_shortlist(client, employer, application, review_url):
    application.assessment_gate_status = Gate.FAILED
    application.save(update_fields=["assessment_gate_status"])

    client.force_login(employer)
    content = client.get(review_url).content.decode()

    assert "Assessment not passed" in content
    assert (
        reverse("employer_portal:application-shortlist", args=[application.pk])
        not in content
    )


def test_a_passed_gate_allows_shortlist(client, employer, application, review_url):
    application.assessment_gate_status = Gate.PASSED
    application.save(update_fields=["assessment_gate_status"])

    client.force_login(employer)
    content = client.get(review_url).content.decode()

    assert (
        reverse("employer_portal:application-shortlist", args=[application.pk])
        in content
    )


def test_not_matched_can_be_rejected_but_not_shortlisted(
    client, employer, application, review_url
):
    """G3: a filtered row is reviewable, not rejected -- and not directly shortlistable."""
    application.status = Status.NOT_MATCHED
    application.save(update_fields=["status"])

    client.force_login(employer)
    content = client.get(review_url).content.decode()

    assert "must be reviewed before it can be shortlisted" in content
    assert (
        reverse("employer_portal:application-shortlist", args=[application.pk])
        not in content
    )
    assert (
        reverse("employer_portal:application-reject", args=[application.pk]) in content
    )


def test_a_shortlisted_application_says_so_instead_of_offering_the_button(
    client, employer, application, review_url
):
    application.status = Status.SHORTLISTED
    application.save(update_fields=["status"])

    client.force_login(employer)
    content = client.get(review_url).content.decode()

    assert "Already shortlisted" in content
    assert (
        reverse("employer_portal:application-shortlist", args=[application.pk])
        not in content
    )


def test_a_rejected_application_offers_no_action(
    client, employer, application, review_url
):
    application.status = Status.REJECTED
    application.save(update_fields=["status"])

    client.force_login(employer)
    content = client.get(review_url).content.decode()

    assert "Already rejected" in content
    assert (
        reverse("employer_portal:application-reject", args=[application.pk])
        not in content
    )


def test_a_hired_application_offers_no_action(
    client, employer, application, review_url
):
    application.status = Status.HIRED
    application.save(update_fields=["status"])

    client.force_login(employer)
    content = client.get(review_url).content.decode()

    assert "A hired application cannot be rejected." in content


def test_another_employers_application_is_a_404(client, other_employer, review_url):
    client.force_login(other_employer)

    assert client.get(review_url).status_code == 404


def test_a_candidate_cannot_open_the_review_page(client, candidate_user, review_url):
    client.force_login(candidate_user)

    assert client.get(review_url).status_code == 403


# --------------------------------------------------- the confirmation pages


def test_the_confirmation_page_changes_nothing(
    client, employer, application, shortlist_url
):
    """A GET renders the confirmation; the POST is the only write."""
    client.force_login(employer)

    response = client.get(shortlist_url)

    assert response.status_code == 200
    assert "What happens" in response.content.decode()
    application.refresh_from_db()
    assert application.status == Status.APPLIED
    assert not AuditLogEntry.objects.exists()


def test_the_confirmation_page_names_the_alias_and_the_target(
    client, employer, application, shortlist_url
):
    client.force_login(employer)

    content = client.get(shortlist_url).content.decode()

    assert alias_of(application) in content
    assert "Shortlisted" in content
    # The form posts to the shortlist route, so the target cannot be edited.
    assert shortlist_url in content
    assert (
        reverse("employer_portal:application-reject", args=[application.pk])
        not in content
    )


def test_posting_the_confirmation_shortlists(
    client, employer, application, shortlist_url, review_url
):
    client.force_login(employer)

    response = client.post(shortlist_url, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1][0] == review_url
    application.refresh_from_db()
    assert application.status == Status.SHORTLISTED
    assert application.decided_by == employer
    assert application.shortlisted_at is not None
    assert "Shortlisted. The candidate has been notified." in response.content.decode()


def test_posting_the_confirmation_rejects(client, employer, application, reject_url):
    client.force_login(employer)

    response = client.post(reject_url, follow=True)

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == Status.REJECTED
    assert "Rejected. The candidate has been notified." in response.content.decode()


def test_the_decision_writes_one_audit_entry_without_candidate_identity(
    client, employer, application, shortlist_url
):
    client.force_login(employer)

    client.post(shortlist_url)

    entry = AuditLogEntry.objects.get()
    assert entry.action == "application.shortlisted"
    assert entry.resource_id == application.pk
    assert entry.actor == employer
    rendered = f"{entry.action} {entry.details} {entry.resource_type}"
    assert CANDIDATE_EMAIL not in rendered
    assert CANDIDATE_FIRST not in rendered
    assert alias_of(application) not in rendered


def test_a_gate_blocked_post_is_refused(client, employer, application, shortlist_url):
    application.assessment_gate_status = Gate.PENDING
    application.save(update_fields=["assessment_gate_status"])

    client.force_login(employer)
    response = client.post(shortlist_url, follow=True)

    assert response.status_code == 200
    assert (
        "Shortlisting is blocked until the required assessment is passed."
        in response.content.decode()
    )
    application.refresh_from_db()
    assert application.status == Status.APPLIED
    assert not AuditLogEntry.objects.exists()


def test_a_repeated_post_is_a_noop(client, employer, application, shortlist_url):
    client.force_login(employer)

    client.post(shortlist_url)
    response = client.post(shortlist_url, follow=True)

    assert "This application is already shortlisted." in response.content.decode()
    assert AuditLogEntry.objects.count() == 1


def test_the_confirmation_page_for_a_blocked_action_offers_no_button(
    client, employer, application, shortlist_url
):
    application.assessment_gate_status = Gate.FAILED
    application.save(update_fields=["assessment_gate_status"])

    client.force_login(employer)
    content = client.get(shortlist_url).content.decode()

    assert "This action is not available" in content
    # No form posts to the decision route: the only submit button left is the
    # base template's log-out control.
    assert f'action="{shortlist_url}"' not in content
    assert "Shortlisting is blocked until the required assessment is passed." in content


def test_the_confirmation_page_for_a_noop_offers_no_button(
    client, employer, application, shortlist_url
):
    application.status = Status.SHORTLISTED
    application.save(update_fields=["status"])

    client.force_login(employer)
    content = client.get(shortlist_url).content.decode()

    assert "Nothing to do" in content
    assert "already shortlisted" in content


def test_a_candidate_cannot_post_a_decision(
    client, candidate_user, application, shortlist_url
):
    client.force_login(candidate_user)

    response = client.post(shortlist_url)

    assert response.status_code == 403
    application.refresh_from_db()
    assert application.status == Status.APPLIED


def test_another_employer_cannot_post_a_decision(
    client, other_employer, application, shortlist_url
):
    client.force_login(other_employer)

    response = client.post(shortlist_url)

    assert response.status_code == 404
    application.refresh_from_db()
    assert application.status == Status.APPLIED


def test_anonymous_cannot_post_a_decision(client, application, shortlist_url):
    response = client.post(shortlist_url)

    assert response.status_code == 302
    application.refresh_from_db()
    assert application.status == Status.APPLIED


def test_the_review_page_after_shortlisting_still_shows_the_alias(
    client, employer, application, shortlist_url, review_url
):
    """REQ-FR-054: shortlisting is not a reveal; that is a separate audited action."""
    client.force_login(employer)
    client.post(shortlist_url)

    content = client.get(review_url).content.decode()

    assert alias_of(application) in content
    assert CANDIDATE_EMAIL not in content
    assert CANDIDATE_FIRST not in content
