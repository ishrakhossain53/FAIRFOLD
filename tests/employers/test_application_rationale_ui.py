"""Page #41 (S13) rationale column: evidence, bias status, and the privacy boundary.

REQ-FR-030 (evidence-cited rationale, missing skills, bias status shown) and
REQ-FR-029 (no name, photo, contact detail or internal identifier before
shortlist). The page is employer-only and scoped to the caller's own jobs; both
are asserted here rather than assumed from the decorator.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from accounts.models import User
from ai.bias_audit import record, review_payload
from ai.citation import parse_rationale
from ai.screening import screen_application
from candidates.models import CandidateProfile
from employers.models import EmployerProfile
from matching.models import Application, Job

pytestmark = pytest.mark.django_db

MODEL = "deepseek/deepseek-chat"
CANDIDATE_EMAIL = "secret-candidate@example.com"
CANDIDATE_TITLE = "Staff Platform Engineer at a named startup"

SOURCE = (
    "Backend developer with six years of experience.\n"
    "Built a Django REST API serving 120 req/s at scale.\n"
    "Led a migration from MySQL to PostgreSQL with zero downtime."
)


def payload(**overrides):
    base = {
        "summary": "Strong backend match; both required skills are evidenced.",
        "claims": [
            {
                "claim": "Runs Django in production",
                "evidence": "Built a Django REST API serving 120 req/s at scale.",
                "skills": ["Django"],
            },
            {
                "claim": "Has migrated a relational database",
                "evidence": "Led a migration from MySQL to PostgreSQL with zero downtime.",
                "skills": ["PostgreSQL", "MySQL"],
            },
        ],
        "missing_skills": [
            {"skill": "Kubernetes", "reason": "not mentioned in the resume"}
        ],
    }
    base.update(overrides)
    return base


@pytest.fixture
def employer(make_user):
    return make_user("employer_hr")


@pytest.fixture
def employer_profile(employer):
    return EmployerProfile.objects.create(user=employer, company_name="Acme Ltd")


@pytest.fixture
def candidate():
    user = User.objects.create_user(
        CANDIDATE_EMAIL,
        "not-used-in-these-tests",
        first_name="Ayesha",
        last_name="Rahman",
    )
    return CandidateProfile.objects.create(user=user, title=CANDIDATE_TITLE)


@pytest.fixture
def job(employer_profile):
    return Job.objects.create(employer=employer_profile, title="Backend Engineer")


@pytest.fixture
def application(job, candidate):
    return Application.objects.create(job=job, candidate=candidate)


@pytest.fixture
def page_url(application):
    return reverse("employer_portal:application-rationale", args=[application.pk])


def score(application, *, rationale=None, model=MODEL, actor=None):
    return screen_application(
        application,
        score=72,
        payload=rationale or payload(),
        source_text=SOURCE,
        model_used=model,
        actor=actor,
    )


def test_the_page_shows_every_claim_with_its_evidence(
    client, employer, application, page_url
):
    score(application)
    client.force_login(employer)

    content = client.get(page_url).content.decode()

    assert "AI assessment" in content
    assert "AI-generated" in content
    assert "72" in content
    for claim in payload()["claims"]:
        assert claim["claim"] in content
        assert claim["evidence"] in content
        for skill in claim["skills"]:
            assert skill in content
    assert "Kubernetes" in content
    assert "not mentioned in the resume" in content


def test_the_page_shows_the_bias_status_and_the_advisory_rule(
    client, employer, application, page_url
):
    score(application)
    client.force_login(employer)

    content = client.get(page_url).content.decode()

    assert "Passed" in content
    assert "Advisory only" in content
    assert "never blocks" in content


def test_a_flagged_rationale_is_shown_as_needs_review_and_still_reads(
    client, employer, application, page_url
):
    """design.md 7.7: a flag is a review prompt, not a hidden candidate."""
    score(
        application,
        rationale=payload(
            summary="Good cultural fit; the candidate is young and dynamic."
        ),
    )
    client.force_login(employer)

    content = client.get(page_url).content.decode()

    assert "Needs review" in content
    assert "Good cultural fit" in content
    assert "72" in content


def test_a_reviewed_flag_says_so(client, employer, application, page_url):
    outcome = score(
        application,
        rationale=payload(
            summary="Good cultural fit; the candidate is young and dynamic."
        ),
    )
    record(
        review_payload(
            outcome.audit,
            resource_id=str(application.pk),
            actor_id=employer.pk,
            note="Read the sentence in context",
        )
    )
    client.force_login(employer)

    content = client.get(page_url).content.decode()

    assert "Needs review" in content
    assert "reviewed" in content


def test_the_page_never_shows_candidate_identity(
    client, employer, candidate, application, page_url
):
    """REQ-FR-029. Not the email, not the profile title, not the candidate UUID."""
    score(application)
    client.force_login(employer)

    content = client.get(page_url).content.decode()

    assert CANDIDATE_EMAIL not in content
    assert CANDIDATE_TITLE not in content
    assert str(candidate.pk) not in content
    assert candidate.user.first_name not in content
    assert candidate.user.last_name not in content


def test_an_unscreened_application_shows_the_empty_state(
    client, employer, application, page_url
):
    client.force_login(employer)

    content = client.get(page_url).content.decode()

    assert "No rationale yet" in content
    assert "has not been screened" in content
    assert "Not screened" in content


def test_a_failed_screening_shows_the_error_state(
    client, employer, application, page_url
):
    application.screening_status = Application.ScreeningStatus.FAILED
    application.screening_error = "Provider timed out after 2 attempts."
    application.save(update_fields=["screening_status", "screening_error"])
    client.force_login(employer)

    content = client.get(page_url).content.decode()

    assert "Assessment unavailable" in content
    assert "Provider timed out after 2 attempts." in content


def test_an_unreadable_stored_rationale_shows_the_error_state(
    client, employer, application, page_url
):
    """A data defect is a page state, not a 500, and the score stays visible."""
    application.match_score = 72
    application.match_rationale = "{not json"
    application.screening_status = Application.ScreeningStatus.COMPLETED
    application.save(
        update_fields=["match_score", "match_rationale", "screening_status"]
    )
    client.force_login(employer)

    response = client.get(page_url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Assessment unavailable" in content
    assert "re-screening will replace" in content
    assert "72" in content


def test_the_evidence_rendered_is_the_validated_span(
    client, employer, application, page_url
):
    """The page must render the stored payload, not re-derive it from prose."""
    score(application)
    client.force_login(employer)

    stored = parse_rationale(payload(), source_text=SOURCE)
    content = client.get(page_url).content.decode()

    for claim in stored.claims:
        assert f'<mark class="bg-ai-soft text-ink">{claim.evidence}</mark>' in content


def test_another_employer_cannot_read_the_assessment(client, application, make_user):
    other = make_user("employer_hr")
    EmployerProfile.objects.create(user=other, company_name="Other Ltd")
    client.force_login(other)

    response = client.get(
        reverse("employer_portal:application-rationale", args=[application.pk])
    )

    assert response.status_code == 404


def test_a_candidate_cannot_open_the_page(client, application, make_user):
    candidate_user = make_user("candidate")
    client.force_login(candidate_user)

    response = client.get(
        reverse("employer_portal:application-rationale", args=[application.pk])
    )

    assert response.status_code == 403


def test_an_anonymous_visitor_is_sent_to_login(client, page_url):
    response = client.get(page_url)

    assert response.status_code == 302
    assert "/login/" in response.url
