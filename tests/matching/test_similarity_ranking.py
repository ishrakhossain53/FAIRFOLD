"""Deterministic similarity ranking fixtures and 100-candidate benchmark (REQ-FR-013, REQ-FR-053, batch 2.15)."""

from __future__ import annotations

import math
import time

import pytest

from accounts.models import User
from candidates.models import CandidateProfile
from employers.models import EmployerProfile
from matching.models import Application, Job
from matching.similarity import (
    distance_to_similarity,
    rank_candidates_by_similarity,
    rank_job_applications_by_similarity,
    similarity_to_score,
)

pytestmark = pytest.mark.django_db


def _vec_with_cos(cos_theta: float, ortho_dim: int = 1) -> list[float]:
    """Build a 384-dim unit vector whose dot product with ``e_0`` is ``cos_theta``."""
    sin_theta = math.sqrt(max(0.0, 1.0 - cos_theta * cos_theta))
    vec = [0.0] * 384
    vec[0] = cos_theta
    vec[ortho_dim] = sin_theta
    return vec


@pytest.fixture
def employer_and_job():
    emp_user = User.objects.create_user("sim-emp@example.com", "StrongPassword123!")
    employer = EmployerProfile.objects.create(
        user=emp_user, company_name="Ranking Fixture Ltd"
    )
    job_vec = [0.0] * 384
    job_vec[0] = 1.0
    job = Job.objects.create(
        employer=employer,
        title="Principal Python Engineer",
        description="Distributed systems and vector search.",
        status=Job.Status.ACTIVE,
        description_embedding=job_vec,
    )
    return employer, job


class TestSimilarityHelpers:
    def test_distance_to_similarity_clamps_and_rounds(self):
        assert distance_to_similarity(0.0) == 1.0
        assert distance_to_similarity(0.25) == 0.75
        assert distance_to_similarity(1.0) == 0.0
        assert distance_to_similarity(1.4) == 0.0
        assert distance_to_similarity(-0.0001) == 1.0

    def test_similarity_to_score_maps_to_0_100(self):
        assert similarity_to_score(1.0) == 100
        assert similarity_to_score(0.854) == 85
        assert similarity_to_score(0.856) == 86
        assert similarity_to_score(0.0) == 0


class TestDeterministicRankingFixtures:
    def test_known_fixture_vectors_produce_exact_expected_ranking_order(
        self, employer_and_job
    ):
        """Hand-picked unit vectors with known cosine similarities produce exact rank order."""
        _employer, job = employer_and_job

        # Create 5 fixture candidates in deliberately scrambled insertion order
        specs = [
            ("c_rank3", 0.60, 1),
            ("c_rank1", 0.95, 2),
            ("c_rank5", 0.10, 3),
            ("c_rank2", 0.80, 4),
            ("c_rank4", 0.40, 5),
        ]
        by_label = {}
        for label, cos_val, ortho_idx in specs:
            u = User.objects.create_user(f"{label}@example.com", "StrongPassword123!")
            p = CandidateProfile.objects.create(
                user=u,
                resume_embedding=_vec_with_cos(cos_val, ortho_idx),
            )
            app = Application.objects.create(
                job=job, candidate=p, status=Application.Status.APPLIED
            )
            by_label[label] = (p, app, cos_val)

        # Repeated calls must return the exact same order
        run_1 = rank_job_applications_by_similarity(job)
        run_2 = rank_job_applications_by_similarity(job)
        assert run_1 == run_2

        expected_labels = ["c_rank1", "c_rank2", "c_rank3", "c_rank4", "c_rank5"]
        actual_app_ids = [row.application_id for row in run_1]
        expected_app_ids = [by_label[lbl][1].id for lbl in expected_labels]
        assert actual_app_ids == expected_app_ids

        expected_scores = [95, 80, 60, 40, 10]
        assert [row.score_100 for row in run_1] == expected_scores
        assert [row.rank for row in run_1] == [1, 2, 3, 4, 5]

    def test_tie_breaking_on_equal_similarity_is_deterministic_by_id(
        self, employer_and_job
    ):
        _employer, job = employer_and_job
        identical_vec = _vec_with_cos(0.75, 1)

        apps = []
        for idx in range(4):
            u = User.objects.create_user(f"tie-{idx}@example.com", "StrongPassword123!")
            p = CandidateProfile.objects.create(user=u, resume_embedding=identical_vec)
            apps.append(
                Application.objects.create(
                    job=job, candidate=p, status=Application.Status.APPLIED
                )
            )

        ranked = rank_job_applications_by_similarity(job)
        expected_ids = sorted(a.id for a in apps)
        assert [r.application_id for r in ranked] == expected_ids

    def test_visibility_tier_and_is_promoted_have_zero_effect_on_similarity_or_order(
        self, employer_and_job
    ):
        """REQ-FR-053: promoted/verified tier never boosts a lower-similarity candidate."""
        _employer, job = employer_and_job

        u_std = User.objects.create_user("std-high@example.com", "StrongPassword123!")
        p_std = CandidateProfile.objects.create(
            user=u_std,
            visibility_tier=CandidateProfile.VisibilityTier.STANDARD,
            is_promoted=False,
            resume_embedding=_vec_with_cos(0.82, 1),
        )
        app_std = Application.objects.create(job=job, candidate=p_std)

        u_pro = User.objects.create_user("pro-low@example.com", "StrongPassword123!")
        p_pro = CandidateProfile.objects.create(
            user=u_pro,
            visibility_tier=CandidateProfile.VisibilityTier.PROMOTED,
            is_promoted=True,
            resume_embedding=_vec_with_cos(0.81, 2),
        )
        app_pro = Application.objects.create(job=job, candidate=p_pro)

        ranked = rank_job_applications_by_similarity(job)
        assert [r.application_id for r in ranked] == [app_std.id, app_pro.id]
        assert ranked[0].cosine_similarity > ranked[1].cosine_similarity

    def test_raises_when_job_has_no_description_embedding(self, employer_and_job):
        employer, _ = employer_and_job
        unembedded_job = Job.objects.create(
            employer=employer,
            title="Unembedded Job",
            status=Job.Status.DRAFT,
        )
        with pytest.raises(ValueError, match="description_embedding is required"):
            rank_job_applications_by_similarity(unembedded_job)
        with pytest.raises(ValueError, match="description_embedding is required"):
            rank_candidates_by_similarity(unembedded_job)


class TestHundredCandidateSimilarityBenchmark:
    def test_100_candidates_against_one_job_under_two_seconds(self, employer_and_job):
        """Arch Doc §10 Phase 2 & REQ-NFR-004: 100 candidates vs 1 job in < 2.0s."""
        _employer, job = employer_and_job

        users = [
            User(email=f"bench-{i:03d}@example.com", password="x") for i in range(100)
        ]
        User.objects.bulk_create(users)

        profiles = []
        for i, u in enumerate(users):
            # Cosine similarities strictly decreasing from 0.99 down to 0.00
            cos_val = round(0.99 - (i * 0.0099), 6)
            ortho_dim = 1 + (i % 380)
            profiles.append(
                CandidateProfile(
                    user=u,
                    resume_embedding=_vec_with_cos(cos_val, ortho_dim),
                )
            )
        CandidateProfile.objects.bulk_create(profiles)

        applications = [
            Application(
                job=job,
                candidate=p,
                status=Application.Status.APPLIED,
            )
            for p in profiles
        ]
        Application.objects.bulk_create(applications)

        t0 = time.perf_counter()
        ranked_apps = rank_job_applications_by_similarity(job)
        elapsed_apps = time.perf_counter() - t0

        t1 = time.perf_counter()
        ranked_cands = rank_candidates_by_similarity(
            job, candidates=[p.id for p in profiles]
        )
        elapsed_cands = time.perf_counter() - t1

        assert len(ranked_apps) == 100
        assert len(ranked_cands) == 100
        # Verify monotonic similarity ordering across all 100 candidates
        assert [r.candidate_id for r in ranked_apps] == [p.id for p in profiles]
        assert [r.candidate_id for r in ranked_cands] == [p.id for p in profiles]
        assert (
            elapsed_apps < 2.0
        ), f"100-app similarity took {elapsed_apps:.4f}s (>= 2.0s)"
        assert (
            elapsed_cands < 2.0
        ), f"100-cand similarity took {elapsed_cands:.4f}s (>= 2.0s)"
