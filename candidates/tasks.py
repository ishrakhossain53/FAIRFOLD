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
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.storage import default_storage

from candidates.extraction import extract_text
from candidates.models import CandidateResume
from candidates.processing import transition
from candidates.scanner import MalwareDetected, ScanUnavailable, scan_stream
from candidates.uploads import mark_rejected
from core.storage import StorageError

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
    """Extract the stored PDF for `resume_id` and settle it to extracted/failed.

    REQ-FR-012 (batch 2.4). The id, not the model, is the argument for the same
    reason as :func:`scan_resume`: the broker dump must not carry resume metadata.

    **Raw text never reaches the database.** The extraction result is held in
    memory only; the task stores the SHA-256 digest in `raw_text_hash` (for
    deduplication) and then discards the text. The DDL's `extracted_text` column
    holds the PII-stripped text and is written by batch 2.9, not here — so at this
    stage `extracted` means "text was extracted and verified", not "text is stored".

    **Idempotent.** The task runs only while the row is `processing`. A retry
    after the row is already `extracted` or `failed` is a no-op, so a duplicated
    delivery cannot re-extract or overwrite a verdict.

    **Failure carries a code.** An extraction failure stores its failure *code*
    (e.g. `no_text_layer`) in `status_reason`, never the raw text; the resume page
    maps the code back to a user-safe message (batch 2.5).
    """
    try:
        resume = CandidateResume.objects.get(pk=resume_id)
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

    # The digest, not the text: a hash of the raw text cannot be reversed into
    # the candidate's details, and it is what batch 2.9's dedupe compares.
    resume.raw_text_hash = hashlib.sha256(result.text.encode("utf-8")).hexdigest()
    resume.save(update_fields=["raw_text_hash"])

    transition(resume, CandidateResume.Status.EXTRACTED)
