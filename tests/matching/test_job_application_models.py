"""Model tests for `Job` and `Application` (Arch Doc §5.1, batches 1.26/1.34).

The DDL is the specification, so these assert the parts that are easy to get wrong
when transcribing it: the defaults, the unique `(job, candidate)` pair, both check
constraints, the cascade directions, and the fact that the AI columns start null
rather than at zero.

They deliberately do not snapshot the whole field list: `makemigrations --check`
already proves the model and the migration agree, and a field-list assertion turns
every future column into a test edit without testing anything.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from accounts.models import User
from candidates.models import CandidateProfile
from core.models import Skill
from employers.models import EmployerProfile
from matching.models import Application, Job, JobSkill

pytestmark = pytest.mark.django_db


@pytest.fixture
def employer_profile():
    user = User.objects.create_user("hr@example.com", "not-used-in-these-tests")
    return EmployerProfile.objects.create(user=user, company_name="Acme Ltd")


@pytest.fixture
def candidate_profile():
    user = User.objects.create_user("candidate@example.com", "not-used-in-these-tests")
    return CandidateProfile.objects.create(user=user, title="Backend developer")


@pytest.fixture
def job(employer_profile):
    return Job.objects.create(employer=employer_profile, title="Backend Engineer")


@pytest.fixture
def application(job, candidate_profile):
    return Application.objects.create(job=job, candidate=candidate_profile)


# ------------------------------------------------------------------ the job


def test_a_job_defaults_to_a_draft_with_the_first_config_version(job):
    assert job.status == Job.Status.DRAFT
    assert job.screening_config_version == 1
    assert job.remote_allowed is False
    assert job.screening_questions == []
    assert job.screening_config == {}
    assert job.description == ""
    assert job.experience_level == ""
    assert job.ai_model_used == ""
    assert job.cost_estimate is None
    assert job.created_at is not None
    assert job.updated_at is not None


def test_a_job_is_reachable_from_its_employer(employer_profile, job):
    assert job in employer_profile.jobs.all()


def test_deleting_an_employer_deletes_their_jobs(employer_profile, job):
    employer_profile.delete()
    assert not Job.objects.filter(pk=job.pk).exists()


def test_a_job_title_is_required(employer_profile):
    """The DDL column is NOT NULL, and `""` still satisfies NOT NULL. `full_clean`
    is what forms and serializers call, and it refuses an empty title."""
    job = Job(employer=employer_profile)

    with pytest.raises(ValidationError) as error:
        job.full_clean()

    assert "title" in error.value.message_dict


def test_the_string_form_is_the_title_and_not_the_employer(employer_profile):
    """`EmployerProfile.company_name` is encrypted and may be hidden (REQ-FR-042),
    so it must not be rendered by an admin list that touches this model."""
    job = Job.objects.create(employer=employer_profile, title="Data Engineer")
    assert str(job) == "Data Engineer"


# ------------------------------------------------------------ the application


def test_an_application_defaults_match_the_ddl(application):
    assert application.status == Application.Status.APPLIED
    assert application.match_score is None
    assert application.match_rationale == ""
    assert application.ai_model_used == ""
    assert application.screening_status == Application.ScreeningStatus.NOT_SCREENED
    assert application.screening_attempts == 0
    assert application.screening_started_at is None
    assert application.screened_at is None
    assert application.shortlisted_at is None
    assert application.not_matched_reason == ""
    assert application.filter_rules_version is None
    assert application.assessment_gate_status == (
        Application.AssessmentGateStatus.NOT_REQUIRED
    )
    assert application.decision_override is False
    assert application.decided_by is None
    assert application.created_at is not None


def test_one_candidate_cannot_apply_twice_to_the_same_job(job, candidate_profile):
    Application.objects.create(job=job, candidate=candidate_profile)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Application.objects.create(job=job, candidate=candidate_profile)


def test_an_application_is_reachable_from_both_sides(
    application, job, candidate_profile
):
    assert application in job.applications.all()
    assert application in candidate_profile.applications.all()


def test_deleting_the_job_deletes_its_applications(job, application):
    job.delete()
    assert not Application.objects.filter(pk=application.pk).exists()


def test_deleting_the_candidate_profile_deletes_their_applications(
    application, candidate_profile
):
    candidate_profile.delete()
    assert not Application.objects.filter(pk=application.pk).exists()


def test_the_string_form_never_names_the_candidate(application):
    """REQ-FR-029: employer-facing pages show an alias, never a name or email."""
    rendered = str(application)
    assert "candidate@example.com" not in rendered
    assert "Backend developer" not in rendered
    assert str(application.pk) in rendered


# ------------------------------------------------------- the two DDL checks


def test_an_override_cannot_be_stored_without_a_reason(application):
    """REQ-FR-052: the reason is required by the database, not only the form."""
    application.decision_override = True
    application.decision_override_reason = ""

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            application.save()


def test_an_override_with_a_reason_is_stored(application):
    application.decision_override = True
    application.decision_override_reason = (
        "Portfolio shows Kubernetes the rubric missed"
    )
    application.save()

    application.refresh_from_db()
    assert application.decision_override is True
    assert application.decision_override_reason.startswith("Portfolio")


def test_an_unknown_screening_status_is_refused_by_the_database(application):
    """`ck_screening_status`. Without it a typo in a task reads as a real state."""
    application.screening_status = "halfway"

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            application.save()


# ------------------------------------------------------- the shortlist gate


def test_a_candidate_can_be_shortlisted_when_no_assessment_is_required(application):
    assert application.can_shortlist() is True


@pytest.mark.parametrize(
    "gate, expected",
    [
        (Application.AssessmentGateStatus.PENDING, False),
        (Application.AssessmentGateStatus.FAILED, False),
        (Application.AssessmentGateStatus.PASSED, True),
        (Application.AssessmentGateStatus.NOT_REQUIRED, True),
    ],
)
def test_the_assessment_gate_blocks_shortlisting_in_the_backend(
    application, gate, expected
):
    """REQ-FR-051. A closed gate is a backend refusal, not a disabled button."""
    application.assessment_gate_status = gate
    assert application.can_shortlist() is expected


def test_a_not_matched_candidate_is_not_blocked_by_the_gate(job, candidate_profile):
    """Gap G3: `not_matched` is a filter outcome and stays reviewable, so the
    shortlist predicate must not treat it as a second, hidden gate."""
    application = Application.objects.create(
        job=job,
        candidate=candidate_profile,
        status=Application.Status.NOT_MATCHED,
        not_matched_reason="experience_level",
        filter_rules_version=3,
    )
    assert application.can_shortlist() is True


# --------------------------------------------------------------- job skills


class TestJobSkill:
    """`job_skills` from Arch Doc §5.1 (D-6(c), batch 1.32)."""

    def test_required_defaults_to_true(self, job):
        skill = Skill.objects.create(canonical_name="Python")
        link = JobSkill.objects.create(job=job, skill=skill)

        assert link.required is True

    def test_the_same_skill_cannot_be_attached_twice(self, job):
        skill = Skill.objects.create(canonical_name="Python")
        JobSkill.objects.create(job=job, skill=skill)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                JobSkill.objects.create(job=job, skill=skill)

    def test_deleting_the_job_removes_its_skill_links(self, job):
        skill = Skill.objects.create(canonical_name="Python")
        JobSkill.objects.create(job=job, skill=skill)

        job.delete()

        assert JobSkill.objects.count() == 0

    def test_deleting_the_skill_removes_the_link_but_keeps_the_job(self, job):
        skill = Skill.objects.create(canonical_name="Python")
        JobSkill.objects.create(job=job, skill=skill)

        skill.delete()

        assert JobSkill.objects.count() == 0
        assert Job.objects.filter(pk=job.pk).exists()

    def test_the_job_and_skill_related_names_are_usable(self, job):
        skill = Skill.objects.create(canonical_name="Python")
        JobSkill.objects.create(job=job, skill=skill)

        assert list(job.job_skills.all()) == [JobSkill.objects.get()]
        assert list(skill.required_by_jobs.all()) == [JobSkill.objects.get()]
