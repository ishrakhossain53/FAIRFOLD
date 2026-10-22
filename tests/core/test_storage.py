"""Object storage configuration and probe tests (REQ-FR-010, Arch Doc §6.1).

The unit tests need no object store: they cover the settings switch, the CORS
policy and the error translation. The ``S3`` class runs against a real bucket —
MinIO from `docker compose up -d --wait` locally, or AWS/R2 — and **skips**
when ``AWS_STORAGE_BUCKET_NAME`` is unset, because CI has no MinIO service. A
skip here is honest: it says the integration was not exercised, not that it
passed.

What these tests deliberately do not do is assert that MinIO is healthy. A
container health check answers a different question from "can Django write an
object", and the gap between them is exactly what `check_storage` exists to
close.
"""

from __future__ import annotations

from io import BytesIO, StringIO
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from django.conf import settings as django_settings
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from core import storage

SECRET = "probe-secret-that-must-not-be-logged"


def _client_error(code: str, message: str = "denied") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": message}}, "HeadBucket")


class TestSettingsSwitch:
    def test_no_bucket_means_the_filesystem(self):
        """The documented default: unset bucket name keeps local files."""
        if storage.object_storage_configured():
            pytest.skip("AWS_STORAGE_BUCKET_NAME is set in this environment")

        assert isinstance(default_storage, FileSystemStorage)
        assert not storage.object_storage_configured()

    def test_bucket_name_raises_when_unset(self):
        with override_settings(AWS_STORAGE_BUCKET_NAME=""):
            with pytest.raises(storage.StorageError):
                storage.bucket_name()


class TestCorsConfiguration:
    def test_uses_every_configured_origin(self):
        configuration = storage.cors_configuration(
            ["http://localhost:8000", " https://app.example.test "]
        )

        rule = configuration["CORSRules"][0]
        # Trailing whitespace is stripped rather than signed into the policy: an
        # origin with a space never matches, and the failure is a CORS error in
        # the browser with no server-side trace.
        assert rule["AllowedOrigins"] == [
            "http://localhost:8000",
            "https://app.example.test",
        ]
        assert rule["AllowedMethods"] == storage.CORS_METHODS
        assert "PUT" in rule["AllowedMethods"]
        assert "POST" in rule["AllowedMethods"]

    def test_rejects_an_empty_origin_list(self):
        # A policy with no origins is a bucket Django can write to and a browser
        # cannot. Failing here turns that into a configuration error instead of
        # a preflight failure nobody can trace.
        with pytest.raises(storage.StorageError):
            storage.cors_configuration(["", "   "])

    def test_does_not_add_a_wildcard_by_itself(self):
        rule = storage.cors_configuration(["https://app.example.test"])["CORSRules"][0]

        assert "*" not in rule["AllowedOrigins"]

    def test_unsupported_bucket_cors_is_reported_not_raised(self):
        # MinIO returns NotImplemented for PutBucketCors and configures CORS on
        # the server instead. Failing here would stop the entrypoint on a
        # perfectly working stack; reporting success would hide where the policy
        # actually lives.
        with (
            override_settings(
                AWS_STORAGE_BUCKET_NAME="fairfold-probe",
                S3_CORS_ALLOWED_ORIGINS=["http://localhost:8000"],
            ),
            patch.object(storage, "s3_client") as client,
        ):
            client.return_value.put_bucket_cors.side_effect = _client_error(
                "NotImplemented"
            )

            policy = storage.apply_cors()

        assert policy.applied is False
        assert policy.origins == ["http://localhost:8000"]
        assert "NotImplemented" in policy.detail

    def test_supported_bucket_cors_is_applied(self):
        with (
            override_settings(
                AWS_STORAGE_BUCKET_NAME="fairfold-probe",
                S3_CORS_ALLOWED_ORIGINS=["https://app.example.test"],
            ),
            patch.object(storage, "s3_client") as client,
        ):
            policy = storage.apply_cors()

        assert policy.applied is True
        client.return_value.put_bucket_cors.assert_called_once()


class TestErrorTranslation:
    def test_client_error_reports_the_s3_code(self):
        error = storage._translate(_client_error("NoSuchBucket"), "head_bucket(b)")

        assert "NoSuchBucket" in str(error)

    def test_access_denied_points_at_the_credentials(self):
        error = storage._translate(
            _client_error("InvalidAccessKeyId"), "head_bucket(b)"
        )

        assert "AWS_ACCESS_KEY_ID" in str(error)

    def test_the_secret_never_reaches_the_message(self):
        # botocore's own message can echo request context; only the error code is
        # interpolated. This string is printed by a management command and lands
        # in a container log.
        error = storage._translate(
            _client_error("SignatureDoesNotMatch", message=SECRET),
            "head_bucket(b)",
        )

        assert SECRET not in str(error)

    def test_translation_accepts_a_connection_error(self):
        from botocore.exceptions import EndpointConnectionError

        error = storage._translate(
            EndpointConnectionError(endpoint_url="http://127.0.0.1:1"), "round-trip"
        )

        assert "EndpointConnectionError" in str(error)


class TestEnsureStorageCommand:
    def test_no_op_without_a_bucket(self):
        out = StringIO()

        with override_settings(AWS_STORAGE_BUCKET_NAME=""):
            call_command("ensure_storage", stdout=out)

        # A no-op, not an error: the local filesystem is a supported backend.
        assert "not configured" in out.getvalue()

    def test_unreachable_endpoint_is_a_command_error(self):
        out = StringIO()
        broken = {
            "default": {
                "BACKEND": "storages.backends.s3.S3Storage",
                "OPTIONS": {
                    "access_key": "probe-key",
                    "secret_key": SECRET,
                    # Port 1 is never listening, so this fails in milliseconds
                    # instead of waiting for a DNS timeout.
                    "endpoint_url": "http://127.0.0.1:1",
                    "bucket_name": "fairfold-probe",
                    "region_name": "us-east-1",
                    "addressing_style": "path",
                    "signature_version": "s3v4",
                },
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
            },
        }

        with override_settings(
            STORAGES=broken,
            AWS_STORAGE_BUCKET_NAME="fairfold-probe",
            AWS_S3_ENDPOINT_URL="http://127.0.0.1:1",
        ):
            with pytest.raises(CommandError) as excinfo:
                call_command("ensure_storage", stdout=out)

        # A CommandError, not a boto3 traceback: the entrypoint runs under
        # `set -e`, and the operator needs the operation that failed.
        assert "bucket" in str(excinfo.value).lower()
        assert SECRET not in str(excinfo.value)


class TestCheckStorageCommand:
    def test_round_trips_the_default_storage(self):
        out = StringIO()

        call_command("check_storage", stdout=out)

        output = out.getvalue()
        assert "storage round-trip verified" in output
        assert f"key={storage.PROBE_PREFIX}/" in output
        assert f"bytes={len(storage.PROBE_BYTES)}" in output

    def test_probe_object_is_deleted(self):
        result = storage.round_trip()

        assert not default_storage.exists(result.key)

    def test_write_failure_is_a_command_error(self):
        with patch.object(
            storage.default_storage, "save", side_effect=_client_error("AccessDenied")
        ):
            with pytest.raises(CommandError) as excinfo:
                call_command("check_storage", stdout=StringIO())

        assert "AccessDenied" in str(excinfo.value)

    def test_mismatched_read_back_is_a_failure(self):
        # A save that "succeeds" and a read that returns different bytes is the
        # one failure mode a status code cannot show: a truncated object, a
        # proxy that rewrote the body, or a backend pointed at two buckets.
        with (
            patch.object(
                storage.default_storage, "save", return_value="healthchecks/fake.txt"
            ),
            patch.object(
                storage.default_storage, "open", return_value=BytesIO(b"not the probe")
            ),
            patch.object(storage.default_storage, "delete"),
        ):
            with pytest.raises(storage.StorageError) as excinfo:
                storage.round_trip()

        assert "read back" in str(excinfo.value)


class TestS3Integration:
    """Runs only where a bucket is configured (Compose MinIO, AWS, R2)."""

    @pytest.fixture(autouse=True)
    def _require_bucket(self):
        if not storage.object_storage_configured():
            pytest.skip("AWS_STORAGE_BUCKET_NAME is unset; no S3 endpoint to test")

    def test_bucket_round_trip(self):
        result = storage.round_trip()

        assert result.bucket == django_settings.AWS_STORAGE_BUCKET_NAME
        assert "S3Storage" in result.backend
        assert result.size == len(storage.PROBE_BYTES)
        # And it is gone: a probe left behind on every start would accumulate.
        with pytest.raises(ClientError):
            storage.s3_client().head_object(Bucket=result.bucket, Key=result.key)

    def test_ensure_bucket_is_idempotent(self):
        # The entrypoint calls this on every start.
        first = storage.ensure_bucket()

        assert first is False
        assert storage.ensure_bucket() is False

    def test_cors_policy_matches_the_configured_origins(self):
        policy = storage.apply_cors()

        assert policy.origins == list(django_settings.S3_CORS_ALLOWED_ORIGINS)
        bucket = django_settings.AWS_STORAGE_BUCKET_NAME
        if policy.applied:
            applied = storage.s3_client().get_bucket_cors(Bucket=bucket)
            assert applied["CORSRules"][0]["AllowedOrigins"] == policy.origins
            assert "PUT" in applied["CORSRules"][0]["AllowedMethods"]
        else:
            # MinIO: no bucket CORS API at all. Assert that, so this test fails
            # loudly if an endpoint silently starts returning an empty policy.
            with pytest.raises(ClientError):
                storage.s3_client().get_bucket_cors(Bucket=bucket)

    def test_probe_failure_does_not_leave_an_object(self):
        # Deleting only on success would leak one probe object per failed run.
        before = (
            storage.s3_client()
            .list_objects_v2(
                Bucket=django_settings.AWS_STORAGE_BUCKET_NAME,
                Prefix=f"{storage.PROBE_PREFIX}/",
            )
            .get("KeyCount", 0)
        )

        with patch.object(
            storage.default_storage, "open", side_effect=IOError("read failed")
        ):
            with pytest.raises(IOError):
                storage.round_trip()

        after = (
            storage.s3_client()
            .list_objects_v2(
                Bucket=django_settings.AWS_STORAGE_BUCKET_NAME,
                Prefix=f"{storage.PROBE_PREFIX}/",
            )
            .get("KeyCount", 0)
        )
        assert after <= before
