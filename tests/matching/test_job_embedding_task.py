"""Tests for the job embedding Celery task and triggers (REQ-FR-013, AD-004, batch 2.14)."""

from __future__ import annotations

import math
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from core.models import Skill
from employers.models import EmployerProfile
from employers.services import change_job_status, job_status
from matching.models import Job, JobSkill
from matching.tasks import (
    build_job_embedding_text,
    embed_job,
    has_job_embedding_field_changed,
)

pytestmark = pytest.mark.django_db


def _stub_embed(text: str) -> list[float]:
    vec = [0.0] * 384
    vec[0] = 1.0
    return vec


@pytest.fixture
def employer_user(make_user):
    return make_user("employer_hr")


@pytest.fixture
def employer_profile(employer_user):
    return EmployerProfile.objects.create(
        user=employer_user,
        company_name="Confidential Corp",
    )


@pytest.fixture
def draft_job(employer_profile):
    job = Job.objects.create(
        employer=employer_profile,
        title="Senior Backend Engineer",
        description="Design distributed services in Python and Django.",
        responsibilities="Own API reliability and PostgreSQL performance.",
        requirements="5+ years Python, Django, PostgreSQL.",
        nice_to_have="Experience with pgvector and Celery.",
        status=Job.Status.DRAFT,
    )
    s_py, _ = Skill.objects.get_or_create(canonical_name="Python")
    s_pg, _ = Skill.objects.get_or_create(canonical_name="PostgreSQL")
    JobSkill.objects.create(job=job, skill=s_py, required=True)
    JobSkill.objects.create(job=job, skill=s_pg, required=False)
    return job


class TestBuildJobEmbeddingText:
    def test_combines_title_sections_and_skills_without_employer_name(self, draft_job):
        text = build_job_embedding_text(draft_job)
        assert "Title: Senior Backend Engineer" in text
        assert "Description: Design distributed services in Python and Django." in text
        assert (
            "Responsibilities: Own API reliability and PostgreSQL performance." in text
        )
        assert "Requirements: 5+ years Python, Django, PostgreSQL." in text
        assert "Nice to have: Experience with pgvector and Celery." in text
        assert "Skills: PostgreSQL, Python" in text
        assert "Confidential Corp" not in text

    def test_has_job_embedding_field_changed_detects_text_vs_non_text_fields(self):
        assert has_job_embedding_field_changed(["title"]) is True
        assert has_job_embedding_field_changed(["description"]) is True
        assert has_job_embedding_field_changed(["requirements"]) is True
        assert has_job_embedding_field_changed(["remote_allowed", "location"]) is False
        assert has_job_embedding_field_changed([]) is False


class TestEmbedJobTask:
    def test_embeds_job_description_into_384_vector(self, draft_job):
        captured: list[str] = []

        def spy(text: str) -> list[float]:
            captured.append(text)
            return _stub_embed(text)

        with patch("matching.tasks.embed", side_effect=spy):
            embed_job(str(draft_job.id))

        draft_job.refresh_from_db()
        assert draft_job.description_embedding is not None
        assert len(draft_job.description_embedding) == 384
        assert math.isclose(
            float(draft_job.description_embedding[0]), 1.0, rel_tol=1e-6
        )
        assert len(captured) == 1
        assert "Senior Backend Engineer" in captured[0]

    def test_regenerates_embedding_when_job_text_changes(self, draft_job):
        vec_v1 = [1.0] + [0.0] * 383
        vec_v2 = [0.0, 1.0] + [0.0] * 382

        with patch("matching.tasks.embed", return_value=vec_v1):
            embed_job(str(draft_job.id))

        draft_job.refresh_from_db()
        assert math.isclose(
            float(draft_job.description_embedding[0]), 1.0, rel_tol=1e-6
        )

        draft_job.requirements = "7+ years Rust, Tokio, and distributed systems."
        draft_job.save(update_fields=["requirements"])

        with patch("matching.tasks.embed", return_value=vec_v2):
            embed_job(str(draft_job.id))

        draft_job.refresh_from_db()
        assert math.isclose(
            float(draft_job.description_embedding[0]), 0.0, abs_tol=1e-6
        )
        assert math.isclose(
            float(draft_job.description_embedding[1]), 1.0, rel_tol=1e-6
        )

    def test_missing_or_invalid_job_id_is_noop(self):
        embed_job("00000000-0000-0000-0000-000000000000")
        embed_job("not-a-uuid")


class TestJobEmbeddingTriggers:
    def test_activating_job_queues_embed_job_on_commit(
        self,
        draft_job,
        employer_profile,
        employer_user,
        django_capture_on_commit_callbacks,
    ):
        with patch("employers.services.queue_embed_job") as mock_queue:
            with django_capture_on_commit_callbacks(execute=True):
                outcome, job = change_job_status(
                    job_id=draft_job.id,
                    employer=employer_profile,
                    to_status=job_status(Job.Status.ACTIVE),
                    allowed_from=(
                        job_status(Job.Status.DRAFT),
                        job_status(Job.Status.PAUSED),
                    ),
                    audit_action="job.activated",
                    actor=employer_user,
                )
        assert outcome == "changed"
        assert job.status == Job.Status.ACTIVE
        mock_queue.assert_called_once_with(str(draft_job.id))

    def test_pausing_job_does_not_queue_embed_job(
        self,
        draft_job,
        employer_profile,
        employer_user,
        django_capture_on_commit_callbacks,
    ):
        draft_job.status = Job.Status.ACTIVE
        draft_job.save(update_fields=["status"])

        with patch("employers.services.queue_embed_job") as mock_queue:
            with django_capture_on_commit_callbacks(execute=True):
                change_job_status(
                    job_id=draft_job.id,
                    employer=employer_profile,
                    to_status=job_status(Job.Status.PAUSED),
                    allowed_from=(job_status(Job.Status.ACTIVE),),
                    audit_action="job.paused",
                    actor=employer_user,
                )
        mock_queue.assert_not_called()

    def test_patching_text_field_queues_embed_job_while_non_text_field_is_noop(
        self, draft_job, employer_user, django_capture_on_commit_callbacks
    ):
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(employer_user)}"
        )
        url = f"/api/v1/jobs/{draft_job.id}/"

        # Non-text field change -> does not queue embed_job
        with patch("employers.api_views.queue_embed_job") as mock_queue:
            with django_capture_on_commit_callbacks(execute=True):
                res = client.patch(url, {"remote_allowed": True}, format="json")
        assert res.status_code == 200
        mock_queue.assert_not_called()

        # Relevant text field change -> queues embed_job
        with patch("employers.api_views.queue_embed_job") as mock_queue:
            with django_capture_on_commit_callbacks(execute=True):
                res = client.patch(
                    url,
                    {"description": "Updated description with GraphQL and FastAPI."},
                    format="json",
                )
        assert res.status_code == 200
        mock_queue.assert_called_once_with(str(draft_job.id))
