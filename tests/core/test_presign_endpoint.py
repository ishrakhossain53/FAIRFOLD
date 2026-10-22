"""Presigning against a browser-reachable endpoint (batch 1.22, REQ-FR-010).

The browser PUTs a resume straight to object storage, so the URL it receives
must name a host *it* can resolve. Inside Compose the server talks to
`minio:9000` and the browser to `localhost:9000`. The host is part of the SigV4
canonical request, so the URL cannot be rewritten after signing -- it has to be
signed by a client pointed at the public endpoint.

`generate_presigned_url` is pure local computation (no connection is opened),
which is what makes a second client safe. `core.storage.s3_client` is replaced
with a stub: these tests are about endpoint selection, not about a live store.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings.base import public_endpoint
from core.storage import presign_client

BUCKET = "fairfold-media"


class StubClient:
    """A client that records what it signed instead of signing."""

    def __init__(self, endpoint_url: str) -> None:
        self.meta = SimpleNamespace(endpoint_url=endpoint_url)
        self.calls = []

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
        self.calls.append((ClientMethod, Params, ExpiresIn))
        return f"{self.meta.endpoint_url}/{Params['Bucket']}/{Params['Key']}?sig=stub"


@pytest.fixture
def internal(monkeypatch):
    client = StubClient("http://minio:9000")
    monkeypatch.setattr("core.storage.s3_client", lambda: client)
    return client


@pytest.fixture
def credentials(settings):
    settings.AWS_ACCESS_KEY_ID = "fairfold-minio"
    settings.AWS_SECRET_ACCESS_KEY = "devminio-password"
    settings.AWS_S3_REGION_NAME = "us-east-1"


def test_without_a_public_endpoint_the_storage_client_is_used(internal, settings):
    settings.S3_PUBLIC_ENDPOINT_URL = ""

    assert presign_client() is internal


def test_a_public_endpoint_equal_to_the_internal_one_reuses_it(internal, settings):
    """A single-host deployment must not gain a second client, and a trailing
    slash in the setting must not be mistaken for a different host."""
    settings.S3_PUBLIC_ENDPOINT_URL = "http://minio:9000/"

    assert presign_client() is internal


def test_a_public_endpoint_signs_for_the_browser_host(internal, settings, credentials):
    settings.S3_PUBLIC_ENDPOINT_URL = "http://localhost:9000"

    client = presign_client()

    assert client is not internal
    assert client.meta.endpoint_url == "http://localhost:9000"

    url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": BUCKET,
            "Key": "resumes/abc/def.pdf",
            "ContentType": "application/pdf",
        },
        ExpiresIn=300,
    )

    # The browser is handed the public host, with a real signature -- not the
    # internal `minio:9000` host, and not an unsigned URL.
    assert url.startswith(f"http://localhost:9000/{BUCKET}/resumes/abc/def.pdf?")
    assert "X-Amz-Signature=" in url
    assert "minio:9000" not in url


class TestPublicEndpointGuard:
    def test_empty_means_unset(self):
        assert public_endpoint("") == ""

    @pytest.mark.parametrize(
        "value", ["http://localhost:9000", "https://bucket.example"]
    )
    def test_http_and_https_are_accepted(self, value):
        assert public_endpoint(value) == value

    @pytest.mark.parametrize("value", ["minio:9000", "ftp://bucket.example"])
    def test_anything_else_fails_at_boot(self, value):
        # `minio:9000` parses as scheme `minio`; without the guard the failure
        # would appear as a dead Upload button, not as a startup error.
        with pytest.raises(ImproperlyConfigured):
            public_endpoint(value)
