"""Candidate dashboard, resume upload, journey mapping and profile.

Celery tasks. Registered by `config.celery` autodiscovery, which imports this
module at worker startup.

A task must be **safe to run twice**. Celery retries on worker death without
knowing whether the first attempt finished, so anything that writes a row also
needs an idempotency key or a natural unique constraint.
"""

from __future__ import annotations

import hashlib

from botocore.exceptions import BotoCoreError, ClientError
from celery import shared_task
from celery.exceptions import CeleryError
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from kombu.exceptions import OperationalError

from ai.embeddings import EmbeddingError, embed
from ai.pii import strip_pii
from candidates.extraction import extract_text
from candidates.models import CandidateResume
from candidates.processing import transition
from candidates.scanner import MalwareDetected, ScanUnavailable, scan_stream
from candidates.uploads import mark_rejected
from core.models import AuditLogEntry
from core.storage import StorageError

RESUME_PII_STRIPPED_ACTION = "resume.pii_stripped"
RESUME_AUDIT_RESOURCE_TYPE = "candidate_resume"
EMBEDDING_FAILED_REASON = "embedding_failed"

# Reading the stored object can fail at the storage layer before ClamAV sees a
# byte. These are the same failures `candidates.uploads.inspect_upload` handles.
_READ_ERRORS = (OSError, ClientError, BotoCoreError, StorageError, ImproperlyConfigured)


@shared_task(ignore_result=True)
def scan_resume(resume_id: str) -> None:
    """Scan the stored object for `resume_id` and settle it to clean/rejected.

    The id, not the model, is the argument: Celery serialises to JSON into Redis,
    and a broker dump must not carry a filename or any other resume metadata.

    **Fail closed.** A missing object, an unreadable one, and an unreachable
    daemon all end in `rejected` with a reason. Only an explicit OK from clamd
    produces `clean` (REQ-SEC-012, gap P).

    **Idempotent.** The task runs only while the row is `scanning`. A retry after
    the row is already `clean` or `rejected` is a no-op, so a duplicated delivery
    cannot overwrite a malware verdict.
    """
    try:
        resume = CandidateResume.objects.get(pk=resume_id)
    except (CandidateResume.DoesNotExist, ValidationError, TypeError, ValueError):
        return

    if resume.status != CandidateResume.Status.SCANNING:
        return

    try:
        with default_storage.open(resume.file_key, "rb") as handle:
            scan_stream(handle)
    except MalwareDetected as exc:
        # ClamAV's signature name, not the file or its name: safe for a row and
        # for an audit excerpt.
        mark_rejected(resume, f"malware detected: {exc.signature}")
        return
    except ScanUnavailable:
        mark_rejected(resume, "antivirus unavailable")
        return
    except _READ_ERRORS:
        mark_rejected(resume, "stored file could not be read")
        return

    resume.status = CandidateResume.Status.CLEAN
    resume.status_reason = ""
    resume.save(update_fields=["status", "status_reason"])


@shared_task(ignore_result=True)
def process_resume(resume_id: str) -> None:
    """Extract, PII-strip and persist the stored PDF for `resume_id`.

    REQ-FR-011, REQ-FR-012, REQ-FR-057 (batches 2.4, 2.9). The id, not the
    model, is the argument for the same reason as :func:`scan_resume`: the
    broker dump must not carry resume metadata.

    **Raw text never reaches the database or logs.** The extraction result is
    held in memory only, hashed with SHA-256 into ``raw_text_hash`` (for
    deduplication), passed through :func:`ai.pii.strip_pii` in memory, and only
    the sanitised text is persisted in ``extracted_text``. One append-only
    :class:`core.models.AuditLogEntry` (``resume.pii_stripped``) records the
    per-category redaction counts and ``raw_text_hash`` — never the stripped
    strings or any raw text.

    **Idempotent.** The task runs only while the row is ``processing``. A retry
    after the row is already ``extracted`` or ``failed`` is a no-op, so a
    duplicated delivery cannot re-extract, overwrite a verdict, or write a
    second audit row.

    **Failure carries a code.** An extraction failure stores its failure *code*
    (e.g. ``no_text_layer``) in ``status_reason``, never the raw text; the
    resume page maps the code back to a user-safe message (batch 2.5).
    """
    try:
        resume = CandidateResume.objects.select_related("candidate__user").get(
            pk=resume_id
        )
    except (CandidateResume.DoesNotExist, ValidationError, TypeError, ValueError):
        return

    if resume.status != CandidateResume.Status.PROCESSING:
        return

    try:
        with default_storage.open(resume.file_key, "rb") as handle:
            result = extract_text(handle, max_bytes=settings.MAX_UPLOAD_SIZE_BYTES)
    except _READ_ERRORS:
        transition(
            resume,
            CandidateResume.Status.FAILED,
            reason="stored file could not be read",
        )
        return

    if result.failure is not None:
        transition(resume, CandidateResume.Status.FAILED, reason=result.failure.code)
        return

    raw_hash = hashlib.sha256(result.text.encode("utf-8")).hexdigest()
    user = resume.candidate.user
    known_name = f"{user.first_name} {user.last_name}".strip()
    known_location = resume.candidate.location or ""
    redaction = strip_pii(
        result.text,
        known_name=known_name,
        known_location=known_location,
    )

    with transaction.atomic():
        resume.raw_text_hash = raw_hash
        resume.extracted_text = redaction.text
        resume.save(update_fields=["raw_text_hash", "extracted_text"])
        transition(resume, CandidateResume.Status.EXTRACTED)
        AuditLogEntry.objects.create(
            actor=user,
            action=RESUME_PII_STRIPPED_ACTION,
            resource_type=RESUME_AUDIT_RESOURCE_TYPE,
            resource_id=resume.id,
            details={
                "counts": dict(redaction.counts),
                "total_redactions": redaction.total_redactions,
                "raw_text_hash": raw_hash,
            },
            result="success",
        )
        transaction.on_commit(lambda rid=str(resume.id): _queue_embed_resume(rid))


def _queue_embed_resume(resume_id: str) -> None:
    """Best-effort dispatch of :func:`embed_resume` after extraction commits."""
    try:
        embed_resume.delay(resume_id)
    except (CeleryError, OperationalError):
        pass


@shared_task(ignore_result=True)
def embed_resume(resume_id: str) -> None:
    """Embed the PII-stripped text for `resume_id` into `CandidateProfile.resume_embedding`.

    REQ-FR-013, REQ-FR-053 (batch 2.13).

    **Sanitised text only.** Reads strictly ``resume.extracted_text`` — which was
    already PII-stripped in :func:`process_resume` before persistence — and
    never reads the stored PDF bytes, ``visibility_tier``, or ``is_promoted``
    (REQ-FR-053).

    **Idempotent.** Runs only while ``resume.status == extracted``. If the row is
    already ``embedded``, or in any other status, this task is a no-op.

    **Never left stuck.** If ``extracted_text`` is empty or the embedding model
    raises :class:`ai.embeddings.EmbeddingError` / :class:`ValueError`, the
    resume transitions ``extracted -> failed`` with
    ``status_reason="embedding_failed"`` so the candidate can retry from the UI.
    """
    try:
        resume = CandidateResume.objects.select_related("candidate").get(pk=resume_id)
    except (CandidateResume.DoesNotExist, ValidationError, TypeError, ValueError):
        return

    if resume.status != CandidateResume.Status.EXTRACTED:
        return

    sanitised_text = resume.extracted_text or ""
    if not sanitised_text.strip():
        transition(
            resume,
            CandidateResume.Status.FAILED,
            reason=EMBEDDING_FAILED_REASON,
        )
        return

    try:
        vector = embed(sanitised_text)
    except (EmbeddingError, ValueError, TypeError):
        transition(
            resume,
            CandidateResume.Status.FAILED,
            reason=EMBEDDING_FAILED_REASON,
        )
        return

    with transaction.atomic():
        profile = resume.candidate
        profile.resume_embedding = vector
        profile.save(update_fields=["resume_embedding", "updated_at"])
        transition(resume, CandidateResume.Status.EMBEDDED)
