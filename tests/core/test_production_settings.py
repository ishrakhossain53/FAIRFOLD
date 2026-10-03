"""Tests for `config.settings.production.py` and the health-check endpoints.

The production settings module is **mostly assertions**, and assertions nobody
exercises are comments. Every one of these was written to stop a deploy, and
every one is now verified to actually stop it:

- a `.env.example` placeholder reaching production would be a public secret key;
- a missing SENTRY_DSN means errors reach users before they reach the team;
- a console email backend silently discards password-reset and interview emails,
  which looks like a working system to everyone testing it.

The module is reloaded per test with a patched environment. That is deliberate:
a single import would evaluate every assertion once and then the remaining tests
would assert against whatever happened to be true at import time.
"""

from __future__ import annotations

import copy
import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import Client

# A complete, valid environment. Each test overrides exactly the variable it is
# about, so a failure names the one variable that broke it rather than a list.
VALID_ENV = {
    "DJANGO_SECRET_KEY": "a" * 60,
    "ENCRYPTION_KEY": "b" * 44,
    "ALLOWED_HOSTS": "app.example.com",
    "CSRF_TRUSTED_ORIGINS": "https://app.example.com",
    "EMAIL_BACKEND_URL": "https://key@api.resend.com",
    "DEFAULT_FROM_EMAIL": "noreply@example.com",
    "SENTRY_DSN": "https://key@o0.ingest.sentry.io/1",
    "CLAMD_HOST": "clamav",
    "SECURE_SSL_REDIRECT": "True",
    "SESSION_COOKIE_SECURE": "True",
    "CSRF_COOKIE_SECURE": "True",
    "SECURE_HSTS_SECONDS": "31536000",
    "SECURE_HSTS_INCLUDE_SUBDOMAINS": "True",
    "SECURE_HSTS_PRELOAD": "True",
}


def _restore_in_place(live, snapshot):
    """Restore `live` to `snapshot` without replacing any dict object.

    A plain ``live.clear(); live.update(snapshot)`` is not enough. Django's
    connection caches ``settings_dict["OPTIONS"]`` as a *reference to the nested
    dict*, so substituting a fresh copy at ``DATABASES["default"]`` leaves the
    connection still holding production's ``sslmode="require"`` -- and test
    database teardown then fails with "server does not support SSL, but SSL was
    required". Only mutating the innermost dicts in place clears every reference
    at once.
    """
    # Recurse *before* removing surplus keys. Clearing first would make
    # ``live.get(key)`` return None for every key, so every nested dict would be
    # replaced by a fresh copy -- which is the exact thing this function exists
    # to avoid. It is a subtle order dependency because both halves look correct.
    for key in [k for k in live if k not in snapshot]:
        del live[key]
    for key, value in snapshot.items():
        if isinstance(value, dict) and isinstance(live.get(key), dict):
            _restore_in_place(live[key], value)
        else:
            live[key] = value


@pytest.fixture
def production_settings(monkeypatch):
    """Import `config.settings.production` afresh with a patched environment.

    Importing this module *mutates the live settings*, and the reason is
    non-obvious enough to be worth stating. ``production.py`` does
    ``from config.settings.base import *``, which copies references, not values.
    ``DATABASES`` is therefore the same dict object the running test session uses,
    so production's ``sslmode = "require"`` reaches every test that follows.

    The symptom is a pytest-django teardown failure -- "server does not support
    SSL, but SSL was required" -- which reads like an environment problem and is
    actually this import. So the real ``settings.DATABASES`` is restored
    afterwards.
    """

    def load(**overrides):
        env = {**VALID_ENV, **overrides}
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        # A missing AI key must not raise, but it must warn. Cleared here so each
        # test starts from a known state.
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        sys.modules.pop("config.settings.production", None)
        return importlib.import_module("config.settings.production")

    from django.conf import settings as django_settings

    snapshot = copy.deepcopy(django_settings.DATABASES)
    yield load
    sys.modules.pop("config.settings.production", None)
    # Restored *in place*, not by rebinding ``settings.DATABASES``. By this point
    # pytest-django has already built a connection whose ``settings_dict`` holds a
    # reference to this same nested dict, so rebinding the top-level name leaves
    # the connection pointing at production's mutated ``sslmode`` -- and test
    # database teardown then fails with "server does not support SSL, but SSL was
    # required". Updating the existing object clears every reference at once.
    _restore_in_place(django_settings.DATABASES, snapshot)


class TestProductionAssertions:
    def test_loads_with_a_complete_environment(self, production_settings):
        module = production_settings()
        assert module.DEBUG is False

    @pytest.mark.parametrize(
        ("overrides", "expected"),
        [
            (
                {"DJANGO_SECRET_KEY": "change-me-generate-a-real-key"},
                "DJANGO_SECRET_KEY",
            ),
            ({"ENCRYPTION_KEY": "change-me-generate-a-real-key"}, "ENCRYPTION_KEY"),
            ({"ALLOWED_HOSTS": "*"}, "wildcard"),
            ({"CSRF_TRUSTED_ORIGINS": "http://app.example.com"}, "https"),
            ({"EMAIL_BACKEND_URL": "console://"}, "EMAIL_BACKEND_URL"),
            ({"DEFAULT_FROM_EMAIL": "noreply@fairfold.local"}, "DEFAULT_FROM_EMAIL"),
            ({"SENTRY_DSN": ""}, "SENTRY_DSN"),
        ],
    )
    def test_rejects_an_unsafe_configuration(
        self, production_settings, overrides, expected
    ):
        # Each of these is a documented footgun that reaches production only when
        # nobody is looking, which is why each is a boot failure rather than a
        # log line.
        with pytest.raises(ImproperlyConfigured) as excinfo:
            production_settings(**overrides)
        assert expected in str(excinfo.value)

    def test_rejects_debug_true(self, production_settings):
        with pytest.raises(ImproperlyConfigured, match="DEBUG must be False"):
            production_settings(DEBUG="True")

    def test_a_console_email_backend_is_refused(self, production_settings):
        # Not a warning. A console backend means password resets and interview
        # invitations are written to a log and never sent, and nothing about that
        # looks broken from inside the system.
        with pytest.raises(ImproperlyConfigured, match="EMAIL_BACKEND_URL"):
            production_settings(EMAIL_BACKEND_URL="console://")

    def test_sentry_is_required(self, production_settings):
        # Without it, errors reach users before they reach the team -- which is
        # the failure mode where nobody finds out until a customer complains.
        with pytest.raises(ImproperlyConfigured, match="SENTRY_DSN"):
            production_settings(SENTRY_DSN="")

    def test_transport_security_is_on(self, production_settings):
        module = production_settings()
        assert module.SECURE_SSL_REDIRECT is True
        assert module.SESSION_COOKIE_SECURE is True
        assert module.CSRF_COOKIE_SECURE is True
        assert module.SECURE_HSTS_SECONDS == 31536000
        assert module.SECURE_HSTS_PRELOAD is True

    def test_sentry_is_configured_not_to_send_pii(self, production_settings):
        # The product handles candidate PII. A crash report carrying it would put
        # a resume fragment in a third party's storage.
        assert production_settings().SENTRY_SEND_DEFAULT_PII is False

    def test_csrf_cookie_is_readable_by_the_frontend(self, production_settings):
        # False, deliberately: the base template reads this cookie to set the
        # CSRF header on every HTMX request. HttpOnly would break every POST.
        module = production_settings()
        assert module.CSRF_COOKIE_HTTPONLY is False
        assert module.SESSION_COOKIE_HTTPONLY is True

    def test_a_missing_ai_key_does_not_stop_the_boot(self, production_settings, caplog):
        # Not an assertion: the documented fallback (OfflineFallbackProvider)
        # returns deterministic non-AI responses, so raising would take the whole
        # site down over an optional integration. It warns instead -- and the
        # warning is the only signal that screening will not rank.
        import logging

        with caplog.at_level(logging.WARNING, logger="fairfold"):
            module = production_settings()
        assert module.OPENROUTER_API_KEY == ""
        assert any("OfflineFallbackProvider" in r.message for r in caplog.records)


@pytest.mark.django_db
class TestHealthEndpoints:
    """The probes the deploy jobs curl (Arch Doc §6.5)."""

    def test_health_returns_ok(self, client: Client):
        response = client.get("/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_does_not_touch_a_dependency(self, client: Client):
        # Liveness must stay up during a database blip. A probe that verifies the
        # database restarts every container in the stack at the same moment.
        response = client.get("/health/")
        assert "checks" not in response.json()

    def test_health_is_never_cached(self, client: Client):
        response = client.get("/health/")
        assert "no-cache" in response.get("Cache-Control", "")

    def test_ready_reports_dependencies_without_failing(self, client: Client):
        # Readiness reports state; it does not 503 during a rolling restart,
        # because that would pull every instance out of the load balancer at once.
        response = client.get("/health/ready/")
        assert response.status_code == 200
        body = response.json()
        assert set(body["checks"]) == {"database", "cache"}
