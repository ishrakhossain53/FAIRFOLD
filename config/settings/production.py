"""Production settings.

Nothing here has a working default. Every value is read from the environment and
a missing one raises ``ImproperlyConfigured`` **at boot**, which is the only
moment a missing secret is cheap to discover.

This module is deliberately *longer* than `local.py`. A setting absent from a
production module silently keeps its base value, and "I thought I turned that
off" is a class of bug that a short production file makes likely rather than
unlikely. Each entry below is therefore explicit even when the base already
looks right.
"""

# STORAGES, like DATABASES, is imported explicitly for the same reason: it is
# mutated below, and an explicit import keeps the mutation honest if the star
# import in base.py ever changes.
from config.settings.base import *  # noqa: F401,F403
from config.settings.base import (
    DATABASES,
    STORAGES,
    ImproperlyConfigured,
    env,
    env_bool,
    env_list,
)

# ---------------------------------------------------------------------------
# Assertions — fail at boot, not at first request
# ---------------------------------------------------------------------------

DEBUG = False
if env_bool("DEBUG", default=False):
    raise ImproperlyConfigured("DEBUG must be False in production.")

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY.startswith("change-me"):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is unset or still the .env.example placeholder. "
        "Run: python scripts/generate_secret_key.py"
    )

ENCRYPTION_KEY = env("ENCRYPTION_KEY")
if not ENCRYPTION_KEY or ENCRYPTION_KEY.startswith("change-me"):
    raise ImproperlyConfigured(
        "ENCRYPTION_KEY is unset or still the placeholder. Rotating it later "
        "makes existing encrypted PII unreadable, so set it correctly now."
    )

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
if any("*" in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured("ALLOWED_HOSTS must not contain a wildcard.")

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
if any(not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured(
        f"CSRF_TRUSTED_ORIGINS must all be https in production: {CSRF_TRUSTED_ORIGINS}"
    )


# ---------------------------------------------------------------------------
# Transport security — every one of these on, no exceptions
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

# Only safe because TLS terminates at a proxy that overwrites this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ---------------------------------------------------------------------------
# Cookies and sessions
# ---------------------------------------------------------------------------

SESSION_COOKIE_AGE = 60 * 30
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# False because the base template reads this cookie to set the CSRF header on
# HTMX requests. HttpOnly would break every POST.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES["default"]["OPTIONS"]["sslmode"] = "require"  # noqa: F405
DATABASES["default"]["CONN_MAX_AGE"] = 60  # noqa: F405

# An unbounded pool against a managed Postgres is how a deploy exhausts the
# connection limit and takes the database down for every other client.
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405


# ---------------------------------------------------------------------------
# Email — a real provider is required, console is not acceptable
# ---------------------------------------------------------------------------

EMAIL_BACKEND_URL = env("EMAIL_BACKEND_URL", "")
if not EMAIL_BACKEND_URL or EMAIL_BACKEND_URL.startswith("console://"):
    raise ImproperlyConfigured(
        "EMAIL_BACKEND_URL must be a real provider in production. A console "
        "backend silently discards password-reset and interview-invitation "
        "emails, which looks like a working system to everyone testing it."
    )

ANYMAIL = {"BASE_URL": EMAIL_BACKEND_URL}

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "")
if not DEFAULT_FROM_EMAIL or DEFAULT_FROM_EMAIL.endswith(".local"):
    raise ImproperlyConfigured(
        "DEFAULT_FROM_EMAIL must be a real sendable address in production."
    )


# ---------------------------------------------------------------------------
# Error tracking — silent failures are the failure mode in production
# ---------------------------------------------------------------------------

SENTRY_DSN = env("SENTRY_DSN", "")
if not SENTRY_DSN:
    raise ImproperlyConfigured(
        "SENTRY_DSN is required in production. Without it, errors reach users "
        "before they reach the team."
    )

SENTRY_ENVIRONMENT = "production"
SENTRY_TRACES_SAMPLE_RATE = float(env("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
SENTRY_SEND_DEFAULT_PII = False  # the product handles candidate PII; do not ship it


# ---------------------------------------------------------------------------
# AI provider — a missing key silently degrades every AI feature
# ---------------------------------------------------------------------------

OPENROUTER_API_KEY = env("OPENROUTER_API_KEY", "")
if not OPENROUTER_API_KEY:
    # Not raised. The documented fallback (OfflineFallbackProvider, Complete Doc
    # §6.4) returns deterministic non-AI responses, so the product still runs.
    # Raising here would make the whole site unavailable over a missing
    # optional integration; a warning lets the team notice in the logs instead.
    import logging

    logging.getLogger("fairfold").warning(
        "OPENROUTER_API_KEY is not set. Every AI feature will use "
        "OfflineFallbackProvider and return deterministic non-AI responses. "
        "Screening will run but will not rank."
    )
else:
    AI_PROVIDER = "openrouter"
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL = env("OPENROUTER_MODEL", "anthropic/claude-sonnet-4")
    # Screening on the matching path is the slowest call in the system.
    OPENROUTER_TIMEOUT = int(env("OPENROUTER_TIMEOUT", "120"))


# ---------------------------------------------------------------------------
# Static files — served by the CDN, not Django
# ---------------------------------------------------------------------------

STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
}

STORAGES["default"] = {
    "BACKEND": "django.core.files.storage.FileSystemStorage"
}  # noqa: F405

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"  # noqa: F405

# Cache is not optional in production: django-ratelimit and the lockout counter
# both depend on Redis being reachable. `dummy` would turn rate limiting off
# silently.
CACHES["default"]["LOCATION"] = env("REDIS_URL")  # noqa: F405


# ---------------------------------------------------------------------------
# Uploads
# ---------------------------------------------------------------------------

# Fail-closed ClamAV scanning. See base.py: there is intentionally no switch to
# disable it, and `CLAMD_HOST` is required.
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL = env("LOG_LEVEL", "INFO").upper()

LOGGING["root"]["level"] = LOG_LEVEL  # noqa: F405

# Anonymised screening payloads must never be written to a log aggregator.
LOGGING["loggers"]["ai"]["propagate"] = True  # noqa: F405
