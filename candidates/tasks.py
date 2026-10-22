"""Candidate dashboard, resume upload, journey mapping and profile.

Celery tasks. Registered by `config.celery` autodiscovery, which imports this
module at worker startup.

A task must be **safe to run twice**. Celery retries on worker death without
knowing whether the first attempt finished, so anything that writes a row also
needs an idempotency key or a natural unique constraint.
"""

from __future__ import annotations

from botocore.exceptions import BotoCoreError, ClientError
from celery import shared_task
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.storage import default_storage

from candidates.models import CandidateResume
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
