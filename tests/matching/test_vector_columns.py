"""Tests for the pgvector columns and extension migration (REQ-FR-013, AD-004, batch 2.12)."""

from __future__ import annotations

import math

import pytest
from django.db import connection
from pgvector.django import CosineDistance

from accounts.models import User
from candidates.models import CandidateProfile
from employers.models import EmployerProfile
from matching.models import Job


def _unit_vector(seed_index: int) -> list[float]:
    vec = [0.0] * 384
    vec[seed_index % 384] = 1.0
    return vec


@pytest.mark.django_db
class TestPgvectorColumns:
    def test_vector_extension_is_installed_in_postgresql(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            row = cursor.fetchone()
        assert row is not None
        assert row[0] == "vector"

    def test_candidate_profile_resume_embedding_round_trip(self):
        user = User.objects.create_user("vec-cand@example.com", "StrongPassword123!")
        profile = CandidateProfile.objects.create(user=user)
        assert profile.resume_embedding is None

        expected = _unit_vector(0)
        profile.resume_embedding = expected
        profile.save(update_fields=["resume_embedding"])

        profile.refresh_from_db()
        assert profile.resume_embedding is not None
        assert len(profile.resume_embedding) == 384
        assert math.isclose(float(profile.resume_embedding[0]), 1.0, rel_tol=1e-6)
        assert math.isclose(float(profile.resume_embedding[1]), 0.0, abs_tol=1e-6)

    def test_job_description_embedding_round_trip(self):
        emp_user = User.objects.create_user("vec-emp@example.com", "StrongPassword123!")
        employer = EmployerProfile.objects.create(
            user=emp_user,
            company_name="Vector Labs",
        )
        job = Job.objects.create(
            employer=employer,
            title="ML Platform Engineer",
            description="Build vector search pipelines.",
        )
        assert job.description_embedding is None

        expected = _unit_vector(5)
        job.description_embedding = expected
        job.save(update_fields=["description_embedding"])

        job.refresh_from_db()
        assert job.description_embedding is not None
        assert len(job.description_embedding) == 384
        assert math.isclose(float(job.description_embedding[5]), 1.0, rel_tol=1e-6)

    def test_cosine_distance_query_over_candidate_profiles(self):
        u1 = User.objects.create_user("vec-c1@example.com", "StrongPassword123!")
        u2 = User.objects.create_user("vec-c2@example.com", "StrongPassword123!")
        p1 = CandidateProfile.objects.create(user=u1)
        p2 = CandidateProfile.objects.create(user=u2)

        p1.resume_embedding = _unit_vector(0)
        p1.save(update_fields=["resume_embedding"])
        p2.resume_embedding = _unit_vector(1)
        p2.save(update_fields=["resume_embedding"])

        query_vec = _unit_vector(0)
        qs = (
            CandidateProfile.objects.filter(id__in=[p1.id, p2.id])
            .annotate(distance=CosineDistance("resume_embedding", query_vec))
            .order_by("distance")
        )
        results = list(qs)
        assert [r.id for r in results] == [p1.id, p2.id]
        assert math.isclose(float(results[0].distance), 0.0, abs_tol=1e-5)
        assert math.isclose(float(results[1].distance), 1.0, abs_tol=1e-5)
