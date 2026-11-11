"""Tests for the resume embedding Celery task (REQ-FR-013, REQ-FR-053, batch 2.13)."""

from __future__ import annotations

import math
from unittest.mock import patch

import pytest

from ai.embeddings import EmbeddingError
from candidates.models import CandidateProfile, CandidateResume
from candidates.tasks import EMBEDDING_FAILED_REASON, embed_resume

pytestmark = pytest.mark.django_db


def _stub_embed(text: str) -> list[float]:
    vec = [0.0] * 384
    vec[0] = 1.0
    return vec


@pytest.fixture
def profile(make_user):
    user = make_user("candidate")
    return CandidateProfile.objects.create(user=user)


@pytest.fixture
def extracted_resume(profile):
    return CandidateResume.objects.create(
        candidate=profile,
        file_key=f"resumes/{profile.id}/sample.pdf",
        original_filename="sample.pdf",
        file_size=2048,
        mime_type="application/pdf",
        raw_text_hash="b" * 64,
        status=CandidateResume.Status.EXTRACTED,
        extracted_text=(
            "[PERSON]\n[EMAIL] | [PHONE]\n"
            "Senior Python Developer with 6 years of Django and PostgreSQL experience."
        ),
    )


class TestEmbedResumeTask:
    def test_transitions_extracted_to_embedded_and_stores_384_vector(
        self, profile, extracted_resume
    ):
        captured_texts: list[str] = []

        def fake_embed(text: str) -> list[float]:
            captured_texts.append(text)
            return _stub_embed(text)

        with patch("candidates.tasks.embed", side_effect=fake_embed):
            embed_resume(str(extracted_resume.id))

        extracted_resume.refresh_from_db()
        profile.refresh_from_db()

        assert extracted_resume.status == CandidateResume.Status.EMBEDDED
        assert extracted_resume.status_reason == ""
        assert extracted_resume.processed_at is not None
        assert profile.resume_embedding is not None
        assert len(profile.resume_embedding) == 384
        assert math.isclose(float(profile.resume_embedding[0]), 1.0, rel_tol=1e-6)
        assert captured_texts == [extracted_resume.extracted_text]

    def test_idempotent_when_already_embedded(self, profile, extracted_resume):
        with patch("candidates.tasks.embed", side_effect=_stub_embed) as mock_embed:
            embed_resume(str(extracted_resume.id))
            embed_resume(str(extracted_resume.id))

        assert mock_embed.call_count == 1
        extracted_resume.refresh_from_db()
        assert extracted_resume.status == CandidateResume.Status.EMBEDDED

    def test_re_embedding_a_newer_resume_updates_profile_cleanly(
        self, profile, extracted_resume
    ):
        vec_a = [1.0] + [0.0] * 383
        vec_b = [0.0, 1.0] + [0.0] * 382

        with patch("candidates.tasks.embed", return_value=vec_a):
            embed_resume(str(extracted_resume.id))

        profile.refresh_from_db()
        assert math.isclose(float(profile.resume_embedding[0]), 1.0, rel_tol=1e-6)

        second_resume = CandidateResume.objects.create(
            candidate=profile,
            file_key=f"resumes/{profile.id}/second.pdf",
            original_filename="second.pdf",
            file_size=2048,
            mime_type="application/pdf",
            raw_text_hash="d" * 64,
            status=CandidateResume.Status.EXTRACTED,
            extracted_text="Updated resume with Rust and Kubernetes experience.",
        )

        with patch("candidates.tasks.embed", return_value=vec_b):
            embed_resume(str(second_resume.id))

        second_resume.refresh_from_db()
        profile.refresh_from_db()
        assert second_resume.status == CandidateResume.Status.EMBEDDED
        assert math.isclose(float(profile.resume_embedding[0]), 0.0, abs_tol=1e-6)
        assert math.isclose(float(profile.resume_embedding[1]), 1.0, rel_tol=1e-6)

    def test_visibility_tier_and_is_promoted_never_enter_embedding(self, make_user):
        """REQ-FR-053: paid visibility fields must have zero influence on the embedded text."""
        u_std = make_user("candidate")
        u_pro = make_user("candidate")
        p_std = CandidateProfile.objects.create(
            user=u_std,
            visibility_tier=CandidateProfile.VisibilityTier.STANDARD,
            is_promoted=False,
        )
        p_pro = CandidateProfile.objects.create(
            user=u_pro,
            visibility_tier=CandidateProfile.VisibilityTier.PROMOTED,
            is_promoted=True,
        )
        identical_text = "Backend Engineer skilled in Python, Celery, and PostgreSQL."
        r_std = CandidateResume.objects.create(
            candidate=p_std,
            file_key=f"resumes/{p_std.id}/r.pdf",
            original_filename="r.pdf",
            file_size=1024,
            mime_type="application/pdf",
            raw_text_hash="2" * 64,
            status=CandidateResume.Status.EXTRACTED,
            extracted_text=identical_text,
        )
        r_pro = CandidateResume.objects.create(
            candidate=p_pro,
            file_key=f"resumes/{p_pro.id}/r.pdf",
            original_filename="r.pdf",
            file_size=1024,
            mime_type="application/pdf",
            raw_text_hash="4" * 64,
            status=CandidateResume.Status.EXTRACTED,
            extracted_text=identical_text,
        )

        seen_inputs: list[str] = []

        def spy_embed(text: str) -> list[float]:
            seen_inputs.append(text)
            return _stub_embed(text)

        with patch("candidates.tasks.embed", side_effect=spy_embed):
            embed_resume(str(r_std.id))
            embed_resume(str(r_pro.id))

        assert seen_inputs == [identical_text, identical_text]
        assert "promoted" not in seen_inputs[1].lower()
        p_std.refresh_from_db()
        p_pro.refresh_from_db()
        assert list(p_std.resume_embedding) == list(p_pro.resume_embedding)

    def test_embedding_failure_marks_resume_failed_and_never_leaves_stuck(
        self, profile, extracted_resume
    ):
        with patch(
            "candidates.tasks.embed",
            side_effect=EmbeddingError("model out of memory"),
        ):
            embed_resume(str(extracted_resume.id))

        extracted_resume.refresh_from_db()
        profile.refresh_from_db()
        assert extracted_resume.status == CandidateResume.Status.FAILED
        assert extracted_resume.status_reason == EMBEDDING_FAILED_REASON
        assert profile.resume_embedding is None

    def test_empty_extracted_text_marks_resume_failed(self, profile):
        resume = CandidateResume.objects.create(
            candidate=profile,
            file_key=f"resumes/{profile.id}/blank.pdf",
            original_filename="blank.pdf",
            file_size=1024,
            mime_type="application/pdf",
            raw_text_hash="f" * 64,
            status=CandidateResume.Status.EXTRACTED,
            extracted_text="   ",
        )
        with patch("candidates.tasks.embed") as mock_embed:
            embed_resume(str(resume.id))

        mock_embed.assert_not_called()
        resume.refresh_from_db()
        assert resume.status == CandidateResume.Status.FAILED
        assert resume.status_reason == EMBEDDING_FAILED_REASON

    def test_missing_or_invalid_resume_id_is_noop(self):
        embed_resume("00000000-0000-0000-0000-000000000000")
        embed_resume("not-a-uuid")
