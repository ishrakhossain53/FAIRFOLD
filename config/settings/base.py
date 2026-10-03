"""Base settings shared by local, ci and production.

Two rules hold throughout:

1. **No secret is written here.** Every sensitive value comes from the
   environment via :func:`env`, and :func:`env_required` raises rather than
   falling back to a default. A development convenience that silently becomes a
   production default is how a real key ends up in a public repository.
2. **Security settings are asserted, not defaulted.** A missing
   ``SECRET_KEY`` in production is a crash on boot, not a warning.

Committed 2026-10-04. Every setting here traces to Complete Doc §4.3, §C.7 or
Arch Doc §3.4; nothing is included speculatively.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

__all__ = [
    "ImproperlyConfigured",
    "env",
    "env_bool",
    "env_list",
    "env_required",
]

BASE_DIR = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Environment reading
# ---------------------------------------------------------------------------


def env(name: str, default: str | None = None) -> str | None:
    """Return an environment variable, or ``default`` if it is unset or empty.

    An empty string counts as unset. ``FOO=`` in a ``.env`` file is almost
    always a mistake, and treating it as a real value produces settings that
    look configured and are not.
    """
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def env_required(name: str) -> str:
    """Return an environment variable or raise ``ImproperlyConfigured``."""
    value = env(name)
    if value is None:
        raise ImproperlyConfigured(
            f"{name} is required but not set. Copy .env.example to .env and "
            f"generate the keys with: python scripts/generate_secret_key.py"
        )
    return value


def env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable. Only a small set of literals count.

    Anything unrecognised raises instead of guessing. ``bool("False")`` is True
    in Python, so a permissive parser would turn a disabled security flag on.
    """
    raw = env(name)
    if raw is None:
        return default
    lowered = raw.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(f"{name} must be a boolean, got {raw!r}")


def env_list(name: str, default: str = "") -> list[str]:
    """Parse a comma-separated environment variable into a list.

    Malformed entries raise rather than being dropped. A silently absent
    ``ALLOWED_HOSTS`` entry in production is a site that serves nobody.
    """
    raw = env(name, default)
    if raw is None:
        return []
    items = [item.strip() for item in raw.split(",") if item.strip()]
    if not items:
        raise ImproperlyConfigured(
            f"{name} was set but contains no usable entries: {raw!r}"
        )
    return items


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

# No default. A committed placeholder key is a production key one careless
# deploy away.
SECRET_KEY = env_required("DJANGO_SECRET_KEY")

DEBUG = env_bool("DEBUG", default=False)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default="localhost,127.0.0.1")

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", default="http://localhost:8000")

SITE_ID = int(env("SITE_ID", "1"))

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

# `core` first so its `AppConfig.ready()` registrations happen before any app
# that might depend on them.
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    # Third party
    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",
    # FairFold — project first, then apps in dependency order.
    "core",
    "accounts",
    "candidates",
    "employers",
    "matching",
    "assessments",
    "interviews",
    "notifications",
    "journey",
    "ai",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.RequestIDMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Database — PostgreSQL 17 + pgvector
# ---------------------------------------------------------------------------

# There is deliberately no SQLite fallback (Complete Doc §4.2). SQLite has no
# pgvector, so a fallback "just works" branch would pass tests and then fail on
# every embedding query in production.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "fairfold_dev"),
        "USER": env("POSTGRES_USER", "fairfold"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": int(env("DB_CONN_MAX_AGE", "60")),
        "OPTIONS": {"sslmode": env("DB_SSLMODE", "prefer")},
    }
}

# The `vector` extension must exist before any migration that adds a VectorField.
# This runs on `migrate`, not on app start, because connecting at import time
# makes every management command — including `makemigrations` on a fresh
# checkout with no database — fail.
PGVECTOR_EXTENSION = env_bool("PGVECTOR_EXTENSION", default=True)


# ---------------------------------------------------------------------------
# Cache and Celery
# ---------------------------------------------------------------------------

REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        # Rate limiting (django-ratelimit) depends on the cache, not the
        # database, because a lockout check on every login attempt must not be
        # able to take the login table down with it.
        "KEY_PREFIX": "fairfold",
    }
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL)
# Separate Redis DB from the broker: a FLUSHDB on the result backend must not
# discard queued tasks.
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Dhaka"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 270

# Async AI calls and pgvector queries both wait on the network or the database.
# The default 60s socket timeout is shorter than a cold embedding model, which
# produces a timeout that looks like a model failure in the logs.
DATABASES["default"]["OPTIONS"]["connect_timeout"] = 10

AI_REQUEST_TIMEOUT_SECONDS = int(env("AI_REQUEST_TIMEOUT_SECONDS", "120"))


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

# Field-level encryption key for PII columns. Rotating it makes existing
# ciphertext unreadable — see the data-migration strategy in Complete Doc §C.8.
ENCRYPTION_KEY = env_required("ENCRYPTION_KEY")

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", default=False)

SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", default=False)

SECURE_CONTENT_TYPE_NOSNIFF = True
# Django 5 removed SECURE_BROWSER_XSS_FILTER, which Complete Doc §4.3 still
# listed. The header it set (`X-XSS-Protection: 0`) is deprecated and ignored by
# every current browser, so the setting is omitted rather than reinstated — see
# the correction note in Arch Doc §4.3.
X_FRAME_OPTIONS = "DENY"

# Only honoured behind a proxy that sets the header. Trusting it without TLS
# termination lets a client claim https:// and bypass the redirect.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_REFERRER_POLICY = "same-origin"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# 30 minutes idle, 8 hours absolute. Shorter than the default because a
# recruitment session holds PII and a shared or borrowed machine is a real risk
# in the target market.
SESSION_COOKIE_AGE = int(env("SESSION_COOKIE_AGE", str(60 * 30)))
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Logout must invalidate server-side state, not just clear the cookie.
SESSION_ENGINE = "django.contrib.sessions.backends.db"

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"


# ---------------------------------------------------------------------------
# ClamAV — fails closed
# ---------------------------------------------------------------------------

# Required, not optional: an upload is REJECTED when the daemon is unreachable,
# rather than passed through unscanned. docker-compose and CI both run a
# `clamav` service. There is intentionally no switch to disable the scan.
CLAMD_HOST = env_required("CLAMD_HOST")
CLAMD_PORT = int(env("CLAMD_PORT", "3310"))
CLAMD_TIMEOUT = int(env("CLAMD_TIMEOUT", "30"))

MAX_UPLOAD_SIZE_BYTES = int(env("MAX_UPLOAD_SIZE_BYTES", str(5 * 1024 * 1024)))


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "noreply@fairfold.local")
DEFAULT_FROM_EMAIL_NAME = "FairFold"


# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

# Bengali is deferred to Phase 5 (design.md, open decision 4). Enabling it here
# would change date and number formatting for every template on day one.
LANGUAGES = [("en", "English")]


# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # AI actions cost money per call, so the quota is enforced at the API
        # boundary and not only in the UI.
        "ai_action": env("THROTTLE_AI_ACTION", "20/hour"),
        "login": env("THROTTLE_LOGIN", "10/minute"),
        "screening": env("THROTTLE_SCREENING", "30/hour"),
    },
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FairFold API",
    "DESCRIPTION": "AI-Powered, Explainable Recruitment Platform",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

# Request IDs are attached by core.middleware.RequestIDMiddleware so a single
# screening failure can be traced across the web request, the Celery task and
# the AI provider call.
LOG_LEVEL = env("LOG_LEVEL", "INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
        },
    },
    "filters": {
        "request_id": {"()": "core.logging.RequestIDFilter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["request_id"],
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.db.backends": {"level": "WARNING", "propagate": True},
        # Anonymised payloads must never reach the log: the whole screening
        # design depends on the employer not seeing them.
        "ai": {"level": LOG_LEVEL, "propagate": True},
    },
}