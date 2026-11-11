"""AI matching engine, pgvector storage and ranking.

Celery tasks. Registered by `config.celery` autodiscovery, which imports this
module at worker startup.

A task must be **safe to run twice**. Celery retries on worker death without
knowing whether the first attempt finished, so anything that writes a row also
needs an idempotency key or a natural unique constraint.
"""

from __future__ import annotations

from collections.abc import Iterable

from celery import shared_task
from celery.exceptions import CeleryError
from django.core.exceptions import ValidationError
from django.db import transaction
from kombu.exceptions import OperationalError

from ai.embeddings import EmbeddingError, embed
from matching.models import Job

#: Fields on :class:`matching.models.Job` that determine its canonical embedding text.
JOB_EMBEDDING_FIELDS: frozenset[str] = frozenset(
    {
        "title",
        "description",
        "responsibilities",
        "requirements",
        "nice_to_have",
    }
)


def build_job_embedding_text(job: Job) -> str:
    """Assemble the canonical text embedded into ``Job.description_embedding``.

    Combines title, description, responsibilities, requirements, nice-to-have
    and any attached canonical skill names in a deterministic order. Never
    includes employer identity, company name, or location metadata.
    """
    sections: list[str] = []
    if job.title and job.title.strip():
        sections.append(f"Title: {job.title.strip()}")
    if job.description and job.description.strip():
        sections.append(f"Description: {job.description.strip()}")
    if job.responsibilities and job.responsibilities.strip():
        sections.append(f"Responsibilities: {job.responsibilities.strip()}")
    if job.requirements and job.requirements.strip():
        sections.append(f"Requirements: {job.requirements.strip()}")
    if job.nice_to_have and job.nice_to_have.strip():
        sections.append(f"Nice to have: {job.nice_to_have.strip()}")

    skill_names = sorted(
        {
            js.skill.canonical_name.strip()
            for js in job.job_skills.select_related("skill").all()
            if js.skill.canonical_name and js.skill.canonical_name.strip()
        }
    )
    if skill_names:
        sections.append(f"Skills: {', '.join(skill_names)}")

    return "\n\n".join(sections)


def has_job_embedding_field_changed(changed_fields: Iterable[str]) -> bool:
    """Return True if any field in ``changed_fields`` affects the job embedding."""
    return bool(JOB_EMBEDDING_FIELDS.intersection(changed_fields))


def queue_embed_job(job_id: str) -> None:
    """Best-effort dispatch of :func:`embed_job` (safe when broker is offline in tests)."""
    try:
        embed_job.delay(str(job_id))
    except (CeleryError, OperationalError):
        pass


@shared_task(ignore_result=True)
def embed_job(job_id: str) -> None:
    """Compute and store ``Job.description_embedding`` (384 dims) for ``job_id``.

    REQ-FR-013, AD-004 (batch 2.14). Idempotent and safe if the job no longer
    exists or has no embeddable text.
    """
    try:
        job = Job.objects.prefetch_related("job_skills__skill").get(pk=job_id)
    except (Job.DoesNotExist, ValidationError, TypeError, ValueError):
        return

    text = build_job_embedding_text(job)
    if not text.strip():
        return

    try:
        vector = embed(text)
    except (EmbeddingError, ValueError, TypeError):
        return

    with transaction.atomic():
        Job.objects.filter(pk=job.pk).update(description_embedding=vector)
