"""Cosine similarity computation over pgvector embeddings (REQ-FR-013, REQ-FR-053, REQ-NFR-004, batch 2.15).

Computes stage-2 vector similarity for one :class:`matching.models.Job` against
``N`` candidates or applications using PostgreSQL's ``<=>`` cosine distance
operator via ``pgvector.django.CosineDistance``.

Key invariants:

1. **Database-level cosine distance.** ``cosine_similarity = 1.0 - cosine_distance``,
   clamped to ``[0.0, 1.0]`` (and scaled to ``0..100`` integer score via
   :func:`similarity_to_score`).
2. **Deterministic ordering.** Ties on cosine distance are broken deterministically
   by ``application.id`` (or ``candidate.id``) ascending so repeated runs over
   identical embeddings always produce the exact same rank order.
3. **Paid discovery isolation (REQ-FR-053).** Neither ``visibility_tier`` nor
   ``is_promoted`` is read, selected, or weighted anywhere in this module.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from django.db.models import QuerySet
from pgvector.django import CosineDistance

from candidates.models import CandidateProfile
from matching.models import Application, Job


@dataclass(frozen=True)
class CandidateSimilarityRow:
    """One candidate's cosine similarity against a job embedding."""

    candidate_id: UUID
    cosine_distance: float
    cosine_similarity: float
    score_100: int
    rank: int


@dataclass(frozen=True)
class ApplicationSimilarityRow:
    """One application's cosine similarity against its job's embedding."""

    application_id: UUID
    candidate_id: UUID
    cosine_distance: float
    cosine_similarity: float
    score_100: int
    rank: int


def distance_to_similarity(distance: float) -> float:
    """Convert pgvector cosine distance ``1 - cos(theta)`` into ``[0.0, 1.0]``."""
    sim = 1.0 - float(distance)
    if sim < 0.0:
        return 0.0
    if sim > 1.0:
        return 1.0
    return round(sim, 6)


def similarity_to_score(similarity: float) -> int:
    """Map a ``[0.0, 1.0]`` similarity to an integer ``0..100`` match score."""
    clamped = max(0.0, min(1.0, float(similarity)))
    return int(round(clamped * 100))


def rank_candidates_by_similarity(
    job: Job,
    *,
    candidates: QuerySet[CandidateProfile] | Sequence[UUID] | None = None,
) -> list[CandidateSimilarityRow]:
    """Rank candidates with non-null ``resume_embedding`` against ``job.description_embedding``.

    Executes a single PostgreSQL query using ``CosineDistance`` (``<=>``) with a
    deterministic ``(distance, id)`` tie-breaker. Raises :class:`ValueError` if
    ``job.description_embedding`` is missing.
    """
    if job.description_embedding is None:
        raise ValueError("job.description_embedding is required for similarity ranking")

    qs = CandidateProfile.objects.filter(resume_embedding__isnull=False)
    if isinstance(candidates, QuerySet):
        qs = qs.filter(pk__in=candidates.values("pk"))
    elif candidates is not None:
        qs = qs.filter(pk__in=list(candidates))

    annotated = (
        qs.annotate(
            cosine_distance=CosineDistance(
                "resume_embedding", list(job.description_embedding)
            )
        )
        .values_list("id", "cosine_distance")
        .order_by("cosine_distance", "id")
    )

    rows: list[CandidateSimilarityRow] = []
    for idx, (cand_id, raw_dist) in enumerate(annotated, start=1):
        dist = float(raw_dist)
        sim = distance_to_similarity(dist)
        rows.append(
            CandidateSimilarityRow(
                candidate_id=cand_id,
                cosine_distance=dist,
                cosine_similarity=sim,
                score_100=similarity_to_score(sim),
                rank=idx,
            )
        )
    return rows


def rank_job_applications_by_similarity(
    job: Job,
    *,
    application_ids: Sequence[UUID] | None = None,
) -> list[ApplicationSimilarityRow]:
    """Rank a job's applications whose candidate has a ``resume_embedding``.

    Uses a single PostgreSQL query over ``Application`` joined to
    ``CandidateProfile.resume_embedding`` ordered by ``(cosine_distance, id)``.
    Paid visibility fields (``visibility_tier``, ``is_promoted``) are never
    consulted (REQ-FR-053).
    """
    if job.description_embedding is None:
        raise ValueError("job.description_embedding is required for similarity ranking")

    qs = Application.objects.filter(
        job=job,
        candidate__resume_embedding__isnull=False,
    )
    if application_ids is not None:
        qs = qs.filter(pk__in=list(application_ids))

    annotated = (
        qs.annotate(
            cosine_distance=CosineDistance(
                "candidate__resume_embedding", list(job.description_embedding)
            )
        )
        .values_list("id", "candidate_id", "cosine_distance")
        .order_by("cosine_distance", "id")
    )

    rows: list[ApplicationSimilarityRow] = []
    for idx, (app_id, cand_id, raw_dist) in enumerate(annotated, start=1):
        dist = float(raw_dist)
        sim = distance_to_similarity(dist)
        rows.append(
            ApplicationSimilarityRow(
                application_id=app_id,
                candidate_id=cand_id,
                cosine_distance=dist,
                cosine_similarity=sim,
                score_100=similarity_to_score(sim),
                rank=idx,
            )
        )
    return rows
