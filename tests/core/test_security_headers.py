"""Response-level security headers under production-like settings (REQ-SEC-010).

`tests/core/test_production_settings.py` proves the settings module holds the
documented values. This file proves those values reach an actual response: a
setting that no middleware reads is a comment, and the failure mode is a header
that is present in staging and absent on the one deployment path nobody tested.

HSTS is only emitted on a request Django considers secure (`request.is_secure()`
or a trusted `X-Forwarded-Proto`), so every request here uses `secure=True`.
That is the production shape: TLS terminates at the proxy, `SECURE_PROXY_SSL_HEADER`
trusts the forwarded scheme, and Django sees HTTPS.

The CSP header is set by `core.middleware.ContentSecurityPolicyMiddleware`
because Django 5.2 has no CSP support and the docs placed the policy at the
Nginx edge only. The policy is deliberately self-hosted: the compiled Tailwind
file and vendored htmx are served from `/static/`, and design.md §11.2 says the
CDN is not a production fallback.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.http import HttpResponse
from django.test import Client, RequestFactory

from core.middleware import ContentSecurityPolicyMiddleware

pytestmark = pytest.mark.django_db

HSTS = "max-age=31536000; includeSubDomains; preload"

# A public page, a probe, the API index and an unauthenticated API response. The
# last one matters: an error path is exactly where a middleware that only decorates
# success responses stops adding the header.
PATHS = ("/", "/health/", "/api/v1/", "/api/v1/auth/me/")


@pytest.fixture
def production_like(settings):
    """The production values, applied to the live settings for one test.

    `override_settings` semantics (the pytest-django `settings` fixture restores
    afterwards) rather than importing `config.settings.production`: that module
    does `from base import *` and would mutate the session's DATABASES dict -- the
    failure `tests/core/test_production_settings.py` documents at length.
    """
    settings.DEBUG = False
    settings.SECURE_SSL_REDIRECT = True
    settings.SECURE_HSTS_SECONDS = 31536000
    settings.SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    settings.SECURE_HSTS_PRELOAD = True
    settings.SECURE_CONTENT_TYPE_NOSNIFF = True
    settings.X_FRAME_OPTIONS = "DENY"
    settings.SECURE_REFERRER_POLICY = "same-origin"
    settings.SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    return settings


@pytest.mark.parametrize("path", PATHS)
def test_production_security_headers_are_on_every_response(path, production_like):
    response = Client().get(path, secure=True)

    assert response["Strict-Transport-Security"] == HSTS
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert response["Referrer-Policy"] == "same-origin"


@pytest.mark.parametrize("path", PATHS)
def test_content_security_policy_is_self_hosted(path, production_like):
    response = Client().get(path, secure=True)

    policy = response["Content-Security-Policy"]
    assert policy == settings.CONTENT_SECURITY_POLICY
    assert "default-src 'self'" in policy
    assert "script-src 'self' 'unsafe-inline'" in policy
    # The templates serve Tailwind and htmx from /static/. A CDN source here
    # would let an injected script load from a host nobody reviewed.
    for third_party in ("cdn.tailwindcss.com", "cdn.jsdelivr.net", "openrouter.ai"):
        assert third_party not in policy


def test_connect_src_names_the_storage_origin(production_like):
    """REQ-FR-010 uploads from the browser to the bucket, so `connect-src 'self'`
    alone blocks the PUT while every server-side test still passes (batch 1.22).

    The cases are asserted on the pure function rather than by reloading the
    settings module: the policy is computed once at import, and a test that
    mutated `AWS_S3_ENDPOINT_URL` afterwards would be testing nothing.

    The public endpoint wins because it is the host the browser reaches; Compose
    serves the app at `localhost:8000` and the bucket at `localhost:9000` while
    the server itself talks to `minio:9000`.
    """
    from config.settings.base import storage_origin

    assert (
        storage_origin("http://127.0.0.1:9000", "fairfold-media", "us-east-1")
        == "http://127.0.0.1:9000"
    )
    assert (
        storage_origin("", "fairfold-media", "eu-west-1")
        == "https://fairfold-media.s3.eu-west-1.amazonaws.com"
    )
    assert storage_origin("", "", "us-east-1") == ""
    # An endpoint without a bucket is not storage: no S3 backend is selected, so
    # the policy must not name a host nothing uploads to.
    assert storage_origin("http://127.0.0.1:9000", "", "us-east-1") == ""
    # The browser-facing endpoint overrides the internal one.
    assert (
        storage_origin(
            "http://minio:9000",
            "fairfold-media",
            "us-east-1",
            public_endpoint_url="http://localhost:9000",
        )
        == "http://localhost:9000"
    )

    # And the live policy is 'self' plus at most that one origin: no wildcard.
    assert "connect-src 'self'" in settings.CONTENT_SECURITY_POLICY
    assert "connect-src 'self' *" not in settings.CONTENT_SECURITY_POLICY
    assert "connect-src 'self' https:;" not in settings.CONTENT_SECURITY_POLICY
    assert "connect-src 'self' http;" not in settings.CONTENT_SECURITY_POLICY


def test_a_view_specific_policy_is_not_overwritten():
    """Two CSP headers are enforced as their intersection, so overriding a
    stricter per-page policy silently weakens it in a way neither file shows."""

    def get_response(request):
        response = HttpResponse()
        response["Content-Security-Policy"] = "default-src 'none'"
        return response

    response = ContentSecurityPolicyMiddleware(get_response)(RequestFactory().get("/"))

    assert response["Content-Security-Policy"] == "default-src 'none'"


def test_hsts_is_not_sent_on_plain_http(production_like):
    """HSTS over plain HTTP is meaningless and leaks a directive to a client
    that is about to be redirected. Production redirects first; the header must
    only appear once the request is secure."""
    response = Client().get("/health/", secure=False)

    assert response.status_code == 301
    assert "Strict-Transport-Security" not in response
