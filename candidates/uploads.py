"""Server-side presigning and stored-object checks for resumes (REQ-FR-010, 1.19-1.20).

Two rules shape the upload half of this module:

**The key is generated here, never by the client.** REQ-FR-010 says Django stores
only the S3 key, and a browser-supplied key would let one candidate choose a path
belonging to another, or a name that reveals the original filename. The key is
``resumes/<candidate uuid>/<random uuid><extension>``, where the extension comes
from the MIME allow-list and the random part from :func:`uuid.uuid4`.

**Bytes never pass through Django on upload.** The browser PUTs straight to
object storage; this module only signs the request. That is why there is no file
upload view, no temporary file and no ``request.FILES`` on that path.

The completion half looks at what actually arrived: the object's real size and
the first :data:`SNIFF_BYTES` for libmagic -- never the filename, the extension
or the browser's ``Content-Type``. A rejected object is discarded. The ClamAV
scan then streams the object straight to the daemon (``candidates.scanner``);
neither path writes resume bytes to the database or to a log.
"""

from __future__ import annotations

import uuid

import magic
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage

from candidates.models import CandidateResume
from core.storage import StorageError, bucket_name, s3_client

# Namespaced so lifecycle rules, metrics and a future "delete all resumes" job
# can select every resume without knowing candidate ids.
RESUME_KEY_PREFIX = "resumes"

# libmagic needs the container header, not the whole file. 2 KiB is the
# conventional sniff window and is far below any resume size, so the completion
# check does not download a 10 MB object to learn it is a PDF.
SNIFF_BYTES = 2048

# S3's ways of saying "no object at this key". MinIO answers 404/NoSuchKey; AWS
# answers 404/NoSuchKey or 404/NotFound depending on the operation.
_MISSING_OBJECT_CODES = {"404", "NoSuchKey", "NotFound"}

# Every exception a storage backend can raise while reading: local filesystem
# (OSError), S3 (ClientError/BotoCoreError), our own translation, and a backend
# that is not configured at all.
_STORAGE_ERRORS = (
    OSError,
    ClientError,
    BotoCoreError,
    StorageError,
    ImproperlyConfigured,
)


class UnsupportedResumeType(ValueError):
    """The declared content type is not in ``RESUME_ALLOWED_MIME_TYPES``."""


class ResumeUploadUnavailable(RuntimeError):
    """Object storage could not sign a URL or read the stored object.

    The caller must not leave a ``pending`` row behind when signing failed: no
    URL was issued, so no bytes can ever arrive for it.
    """


class UploadMissing(RuntimeError):
    """No object exists at the key yet.

    Distinct from :class:`UploadProblem` because the upload may still be in
    flight: the row stays ``pending`` and the client can retry completion.
    """


class UploadProblem(RuntimeError):
    """The stored object failed a check.

    The message is deliberately safe to store in `status_reason`: it names the
    limit or the detected type, never the filename or any file content.
    """


def extension_for(content_type: str) -> str:
    """Return the allow-listed extension for ``content_type``.

    The lookup, rather than string surgery on a filename, is what makes
    ``cv.exe`` stored as ``.pdf`` impossible: an unlisted type raises instead of
    falling back to whatever the client sent.
    """
    try:
        return settings.RESUME_ALLOWED_MIME_TYPES[content_type]
    except KeyError as exc:
        allowed = ", ".join(sorted(settings.RESUME_ALLOWED_MIME_TYPES))
        raise UnsupportedResumeType(
            f"Unsupported resume type {content_type!r}. Allowed: {allowed}."
        ) from exc


def build_resume_key(candidate_id: uuid.UUID, content_type: str) -> str:
    """A candidate-scoped, unguessable object key with an allowed extension."""
    extension = extension_for(content_type)
    return f"{RESUME_KEY_PREFIX}/{candidate_id}/{uuid.uuid4().hex}{extension}"


def presign_resume_put(*, key: str, content_type: str, expires_in: int) -> str:
    """Return a presigned ``put_object`` URL for exactly ``key`` and ``type``.

    ``ContentType`` is part of the signature, so an upload that sends a different
    type is refused by the object store. The declared type is therefore enforced
    twice: once when the URL is issued and once when the bytes arrive.
    """
    try:
        client = s3_client()
        bucket = bucket_name()
    except StorageError as exc:
        # The message names the missing setting and carries no credentials, so
        # it is safe to surface to the caller.
        raise ResumeUploadUnavailable(str(exc)) from exc

    try:
        return client.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )
    except (BotoCoreError, ClientError) as exc:
        # botocore text is not interpolated: a ClientError can carry request
        # metadata, and this message reaches the client and possibly a log.
        raise ResumeUploadUnavailable("Could not sign the upload URL.") from exc


def _is_missing_object(exc: Exception) -> bool:
    """True when a backend error means "there is no object", not "it failed"."""
    if isinstance(exc, FileNotFoundError):
        return True
    if isinstance(exc, ClientError):
        code = str(exc.response.get("Error", {}).get("Code", ""))
        return code in _MISSING_OBJECT_CODES
    return False


def inspect_upload(key: str, *, max_bytes: int) -> tuple[int, str]:
    """Check the stored object and return ``(size, sniffed_mime_type)``.

    The size is read from the backend, not from the row: the declared size was
    only a gate for issuing the URL, and the client controls every byte that
    arrived afterwards. The MIME type comes from libmagic over the first
    :data:`SNIFF_BYTES` of the object, never from the extension or from the
    `Content-Type` the browser claimed.

    Raises :class:`UploadMissing` when there is nothing at the key,
    :class:`UploadProblem` when the object exists but fails a check, and
    :class:`ResumeUploadUnavailable` when storage itself is broken.
    """
    try:
        size = default_storage.size(key)
        with default_storage.open(key, "rb") as handle:
            prefix = handle.read(SNIFF_BYTES)
    except _STORAGE_ERRORS as exc:
        if _is_missing_object(exc):
            raise UploadMissing("no object at the key") from exc
        raise ResumeUploadUnavailable("stored object could not be read") from exc

    if size <= 0:
        raise UploadProblem("empty file")
    if size > max_bytes:
        raise UploadProblem(f"file larger than the {max_bytes}-byte limit")

    try:
        sniffed = magic.from_buffer(prefix, mime=True)
    except magic.MagicException as exc:
        # A broken libmagic must not become "unknown, therefore allowed".
        raise UploadProblem("file type could not be determined") from exc
    return size, sniffed


def discard_object(key: str) -> None:
    """Delete an object we have rejected. Best effort: the row is the record.

    A rejected upload must not stay retrievable in the bucket. If the delete
    itself fails, the resume is still rejected; retrying the deletion is an
    operator job, not a reason to leave the row in a limbo state.
    """
    try:
        default_storage.delete(key)
    except _STORAGE_ERRORS:
        pass


def mark_rejected(resume: CandidateResume, reason: str) -> None:
    """Move a resume to `rejected`, record why, and discard the bytes."""
    resume.status = CandidateResume.Status.REJECTED
    resume.status_reason = reason
    resume.save(update_fields=["status", "status_reason"])
    discard_object(resume.file_key)
