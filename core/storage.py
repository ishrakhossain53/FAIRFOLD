"""S3-compatible object storage helpers (REQ-FR-010, Arch Doc §6.1).

Three operations live here rather than in management commands, because a test
must be able to call them without going through ``call_command``:

- :func:`ensure_bucket` — create the bucket if it is missing.
- :func:`apply_cors` — install the bucket CORS policy that lets a browser PUT
  a presigned upload from the application origin (batch 1.19).
- :func:`round_trip` — write a few bytes, read them back, delete them.

**Failures are translated, never swallowed.** A wrong access key, a missing
bucket and an unreachable endpoint all surface as :class:`StorageError` with the
S3 error code, because "the upload did not work" is not an error message anyone
can act on. The translation deliberately carries no request headers or
credentials: a botocore ``ClientError`` can hold them, and this text reaches a
container log.

Nothing here knows about candidates, resumes or PII. It is infrastructure, and
the objects it writes are named ``healthchecks/<uuid>.txt`` precisely so a
bucket floor plan never confuses a probe with a real file.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

# Probe objects are namespaced so they can be listed, expired or deleted in one
# prefix, and so an operator can tell them apart from uploads at a glance.
PROBE_PREFIX = "healthchecks"

PROBE_BYTES = b"fairfold object storage round-trip\n"

# PUT and POST are the presigned-upload methods; GET and HEAD are what a browser
# (and a range request) needs when reading through a signed URL.
CORS_METHODS = ["GET", "PUT", "POST", "HEAD"]

# Browsers cache the preflight result; 3000 s keeps a long upload session from
# re-preflighting every request without pinning a stale policy for a day.
CORS_MAX_AGE_SECONDS = 3000

# S3's cheapest way to say "bucket is not there". MinIO answers 404/NoSuchBucket;
# AWS answers 404/NoSuchBucket or 404/NotFound depending on the operation.
_MISSING_BUCKET_CODES = {"404", "NoSuchBucket", "NotFound"}

# Creating a bucket twice is not an error: the entrypoint runs on every start.
_ALREADY_OWNED_CODES = {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}

# MinIO does not implement the S3 `PutBucketCors` API (verified 2026-10-22 against
# a real MinIO release: the call returns `NotImplemented`). Its CORS is
# server-level, configured with `MINIO_API_CORS_ALLOW_ORIGIN`, which the Compose
# stack sets from the same `S3_CORS_ALLOWED_ORIGINS`. AWS S3 and Cloudflare R2 do
# implement the bucket API, so both paths are kept and the caller is told which
# one ran.
_CORS_UNSUPPORTED_CODES = {"NotImplemented", "MethodNotAllowed"}


class StorageError(RuntimeError):
    """Object storage is misconfigured, unreachable, or refused the operation."""


@dataclass(frozen=True)
class CorsPolicy:
    """Outcome of :func:`apply_cors`.

    ``applied`` is False when the endpoint has no bucket CORS API (MinIO) and the
    origins are enforced by the server instead. Reporting that as success would
    hide where the policy actually lives.
    """

    origins: list[str]
    applied: bool
    detail: str


def object_storage_configured() -> bool:
    """True when ``AWS_STORAGE_BUCKET_NAME`` selects the S3 backend.

    The bucket name is the single switch, in settings and in ``.env.example``.
    Reading the storage backend class instead would make this answer depend on
    import order.
    """
    return bool(getattr(settings, "AWS_STORAGE_BUCKET_NAME", ""))


def bucket_name() -> str:
    """Return the configured bucket name or raise.

    ``env()`` treats an empty value as unset, so an empty bucket name can never
    reach here through normal configuration. It is checked anyway because a
    bucket of ``""`` would make boto3 sign a request for a path with no bucket
    and produce an error that does not mention configuration at all.
    """
    name = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "")
    if not name:
        raise StorageError(
            "AWS_STORAGE_BUCKET_NAME is not set. Configure object storage or "
            "use the local filesystem backend."
        )
    return name


def s3_client() -> Any:
    """Return the boto3 client django-storages is already using.

    Reusing ``default_storage.connection`` rather than building a second client
    means the probe and the application cannot disagree about the endpoint,
    region or signing style — the class of bug where a round-trip succeeds
    against one endpoint while uploads go to another.
    """
    if not object_storage_configured():
        raise StorageError(
            "Object storage is not configured. Set AWS_STORAGE_BUCKET_NAME (and "
            "AWS_S3_ENDPOINT_URL for MinIO/R2) or use the local filesystem."
        )
    connection = getattr(default_storage, "connection", None)
    if connection is None:
        raise StorageError(
            "The configured default storage is not S3-compatible "
            f"({default_storage.__class__.__name__})."
        )
    try:
        return connection.meta.client
    except BotoCoreError as exc:
        raise _translate(exc, "connecting to object storage") from exc


def presign_client() -> Any:
    """The client used to sign upload URLs, pointed at the browser-facing host.

    ``generate_presigned_url`` is local computation: it signs a request and
    never opens a connection. A second client with ``S3_PUBLIC_ENDPOINT_URL``
    therefore costs nothing and produces a URL a browser can actually reach,
    while server-side reads keep using ``AWS_S3_ENDPOINT_URL``.

    Rewriting the host of a signed URL afterwards is not an option: the host is
    part of the SigV4 canonical request, so the object store rejects the result
    with ``SignatureDoesNotMatch``. That is why this exists at all, and why the
    setting is read here and not in the view.

    Empty ``S3_PUBLIC_ENDPOINT_URL`` (or one equal to the internal endpoint)
    returns the storage client unchanged, so a single-host deployment gains no
    second client and no new failure mode.
    """
    public = getattr(settings, "S3_PUBLIC_ENDPOINT_URL", "")
    internal = s3_client()
    if not public:
        return internal

    if str(getattr(internal.meta, "endpoint_url", "")).rstrip("/") == public.rstrip(
        "/"
    ):
        return internal

    try:
        return boto3.client(
            "s3",
            endpoint_url=public,
            region_name=settings.AWS_S3_REGION_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )
    except BotoCoreError as exc:
        raise _translate(exc, "preparing the browser upload client") from exc


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", "Unknown"))


def _translate(exc: Exception, action: str) -> StorageError:
    """Turn a botocore failure into an actionable message.

    Only the S3 error code and the operation are included. The message from
    botocore is not interpolated because a ClientError can carry request
    metadata, and this string is logged.
    """
    if isinstance(exc, ClientError):
        code = _error_code(exc)
        hint = ""
        if code in {
            "InvalidAccessKeyId",
            "SignatureDoesNotMatch",
            "403",
            "AccessDenied",
        }:
            hint = " Check AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY."
        return StorageError(f"{action} failed: S3 error {code}.{hint}")
    if isinstance(exc, BotoCoreError):
        return StorageError(f"{action} failed: {exc.__class__.__name__}.")
    if isinstance(exc, ImproperlyConfigured):
        return StorageError(f"{action} failed: {exc}")
    return StorageError(f"{action} failed: {exc.__class__.__name__}.")


def cors_configuration(origins: list[str]) -> dict[str, Any]:
    """Build an S3 ``CORSConfiguration`` from a list of origins.

    An empty list raises instead of producing a policy with no origins: that
    would be a bucket the application can write to and a browser cannot, and the
    failure would appear as a preflight error in devtools with no server-side
    trace. A wildcard is allowed only because the caller configured it
    explicitly — this function does not add one.
    """
    cleaned = [origin.strip() for origin in origins if origin and origin.strip()]
    if not cleaned:
        raise StorageError(
            "S3_CORS_ALLOWED_ORIGINS is empty. Set at least the origin the "
            "browser loads the application from."
        )
    return {
        "CORSRules": [
            {
                "AllowedOrigins": cleaned,
                "AllowedMethods": CORS_METHODS,
                "AllowedHeaders": ["*"],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": CORS_MAX_AGE_SECONDS,
            }
        ]
    }


def ensure_bucket() -> bool:
    """Create the bucket if it does not exist. Return True when it was created.

    Idempotent on purpose: the Compose entrypoint calls it on every start. A
    403 from ``head_bucket`` means the bucket exists but belongs to someone
    else, which is a configuration error rather than "create it", so it is not
    treated as missing.
    """
    client = s3_client()
    name = bucket_name()

    try:
        client.head_bucket(Bucket=name)
        return False
    except BotoCoreError as exc:
        # A connection failure, a DNS failure or a signing failure. Translated
        # rather than propagated: the entrypoint calls this, and a stack trace
        # through urllib3 does not tell an operator which endpoint was wrong.
        raise _translate(exc, f"head_bucket({name})") from exc
    except ClientError as exc:
        if _error_code(exc) not in _MISSING_BUCKET_CODES:
            raise _translate(exc, f"head_bucket({name})") from exc

    kwargs: dict[str, Any] = {"Bucket": name}
    region = getattr(settings, "AWS_S3_REGION_NAME", None)
    # Every region except us-east-1 requires an explicit LocationConstraint;
    # MinIO defaults to us-east-1 and rejects the element when it is sent.
    if region and region != "us-east-1":
        kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}

    try:
        client.create_bucket(**kwargs)
    except BotoCoreError as exc:
        raise _translate(exc, f"create_bucket({name})") from exc
    except ClientError as exc:
        if _error_code(exc) in _ALREADY_OWNED_CODES:
            return False
        raise _translate(exc, f"create_bucket({name})") from exc
    return True


def apply_cors() -> CorsPolicy:
    """Install the bucket CORS policy, or report that the backend has none.

    Returns a :class:`CorsPolicy` rather than a plain list because MinIO answers
    ``NotImplemented`` to ``PutBucketCors``: it configures CORS at the server
    level (``MINIO_API_CORS_ALLOW_ORIGIN``) instead. That is not a failure of the
    stack, so it must not fail the entrypoint — but it must not be reported as
    success either, because the origins then live in the MinIO service, not in
    the bucket.
    """
    client = s3_client()
    name = bucket_name()
    origins = list(getattr(settings, "S3_CORS_ALLOWED_ORIGINS", []))
    configuration = cors_configuration(origins)
    try:
        client.put_bucket_cors(Bucket=name, CORSConfiguration=configuration)
    except BotoCoreError as exc:
        raise _translate(exc, f"put_bucket_cors({name})") from exc
    except ClientError as exc:
        if _error_code(exc) in _CORS_UNSUPPORTED_CODES:
            return CorsPolicy(
                origins=origins,
                applied=False,
                detail=(
                    f"bucket CORS is not supported by this endpoint "
                    f"(S3 error {_error_code(exc)}); use the server-level CORS "
                    f"allow-list (MINIO_API_CORS_ALLOW_ORIGIN)"
                ),
            )
        raise _translate(exc, f"put_bucket_cors({name})") from exc
    return CorsPolicy(origins=origins, applied=True, detail="bucket CORS applied")


@dataclass(frozen=True)
class RoundTrip:
    """What :func:`round_trip` wrote and read back. No PII: the key is a UUID."""

    backend: str
    bucket: str
    key: str
    size: int


def round_trip() -> RoundTrip:
    """Write a probe object through Django's storage API, read it, delete it.

    The write goes through ``default_storage`` rather than boto3 directly, so
    the probe exercises the same configuration the application uses. Deleting in
    a ``finally`` matters: a failed *read* must not leave probe objects behind
    on every retry.
    """
    key = f"{PROBE_PREFIX}/{uuid.uuid4().hex}.txt"
    try:
        saved_key = default_storage.save(key, ContentFile(PROBE_BYTES))
        try:
            with default_storage.open(saved_key, "rb") as handle:
                data = handle.read()
        finally:
            default_storage.delete(saved_key)
    except (ClientError, BotoCoreError, ImproperlyConfigured) as exc:
        raise _translate(exc, "storage round-trip") from exc

    if data != PROBE_BYTES:
        raise StorageError(
            f"storage round-trip failed: wrote {len(PROBE_BYTES)} bytes and read "
            f"back {len(data)}."
        )

    storage = default_storage.__class__
    return RoundTrip(
        backend=f"{storage.__module__}.{storage.__qualname__}",
        bucket=getattr(settings, "AWS_STORAGE_BUCKET_NAME", "") or "-",
        key=saved_key,
        size=len(data),
    )
