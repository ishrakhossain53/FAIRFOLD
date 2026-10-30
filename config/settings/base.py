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
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

# ⚠️ DO NOT ADD AN `__all__` HERE.
#
# An earlier revision of this file defined `__all__ = ["ImproperlyConfigured", "env", ...]`
# so that `production.py` could import `ImproperlyConfigured` by name. That broke every
# setting: `__all__` restricts what `from .base import *` exports, so `ci.py` and
# `production.py` received only those five names and NONE of the Django settings.
# `INSTALLED_APPS` became `[]`, `DATABASES` became empty, and `manage.py check`
# reported **"System check identified no issues"** — a pass produced by checking
# nothing at all.
#
# The lesson is recorded here rather than in HISTORY because the next person to
# tidy this file will reach for `__all__` too: it is the idiomatic way to export a
# helper, and here it silently empties a Django settings module.
#
# To import a name explicitly, just import it -- see `production.py`, which does
# `from config.settings.base import ImproperlyConfigured, ...`.

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
    # D-7: SimpleJWT's blacklist app is what makes BLACKLIST_AFTER_ROTATION and
    # logout revocation (REQ-FR-008) do anything. Without it both are inert.
    "rest_framework_simplejwt.token_blacklist",
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
    # Batch 1.13: Django 5.2 has no CSP support, and the documented policy lived
    # only in the Nginx config. Setting it here makes it part of the tested
    # response surface.
    "core.middleware.ContentSecurityPolicyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Exposes `request.htmx` for the registration/verification pages (batch 1.6).
    # It is what turns "is this an HTMX request" into a typed answer instead of a
    # header comparison in every view.
    "django_htmx.middleware.HtmxMiddleware",
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
                # The header bell's unread count (design.md §5.4, W19, batch
                # 1.44). It returns 0 for anonymous requests without querying,
                # so the public pages pay nothing for it.
                "notifications.context_processors.unread_notification_count",
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
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False
)
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

# Content-Security-Policy (REQ-SEC-010, batch 1.13). Set by
# `core.middleware.ContentSecurityPolicyMiddleware`, not only by the edge: the
# canonical docs configured it in Nginx, and a deployment without that proxy
# shipped no CSP at all.
#
# Self-hosted only. `base.html` loads the compiled Tailwind file and the vendored
# htmx from /static/, and design.md §11.2 says the CDN is not a production
# fallback, so no third-party script host appears here. `'unsafe-inline'` is
# still required by the two inline <script> blocks (base.html and home.html) and
# by inline style attributes; replacing it with a per-response nonce is a
# separate change with its own template edits.
#
# `connect-src` is built after the storage block below: REQ-FR-010 uploads
# straight from the browser to the bucket, so the bucket's origin has to be
# named or the browser blocks the PUT while every server-side test still passes.
# See the assignment under "Object storage".

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# REQ-SEC-001 requires Argon2id, not "whatever Django defaults to". Django has
# listed Argon2 first since 4.0, but a security contract that a framework default
# can silently change is not a contract. `Argon2PasswordHasher` is Argon2**id**
# (`argon2.low_level.Type.ID`), not Argon2i or Argon2d.
#
# The tests do not hash with this list: `ci.py` overrides it with MD5 so a login
# test does not spend 100 ms on a KDF, and `local.py` does the same. The pin is
# asserted directly against this module in
# `tests/accounts/test_password_hashing.py`.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
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

MAX_UPLOAD_SIZE_BYTES = int(env("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024)))

# The one file type a resume may be declared as, mapped to the extension used in
# the object key. REQ-SEC-012 says "MIME validation + virus scan"; REQ-FR-012
# names PDF as the input the extraction pipeline reads. DOCX is deliberately
# absent: accepting a type nothing can extract yet is a dead end, not a feature.
# The extension comes from this map, never from the client's filename.
RESUME_ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
}

# How long a presigned PUT stays valid. Short on purpose: the URL is a bearer
# credential for exactly one object and it is handed to a browser.
RESUME_PRESIGN_EXPIRES_SECONDS = int(env("RESUME_PRESIGN_EXPIRES_SECONDS", "300"))


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "noreply@fairfold.local")
DEFAULT_FROM_EMAIL_NAME = "FairFold"

# Where the verification link points (design.md page #11). The template route is
# built in batch 1.6, so this default is a placeholder until that route exists;
# it is a setting because a Celery task has no request to build an absolute URI
# from and because the host differs per environment.
EMAIL_VERIFICATION_URL = env(
    "EMAIL_VERIFICATION_URL", "http://localhost:8000/verify-email/"
)

# design.md X02 shows the resend button as "available in 0:45", so the cooldown
# is 45 seconds. It lives in the cache, not the database: a resend check must
# not be able to take the users table down.
EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS = int(
    env("EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS", "45")
)

# REQ-FR-001 requires an expiring link but does not state a lifetime. 24 hours is
# the default; it is a setting so the policy can be changed without editing the
# signing code, and short enough that a leaked mailbox does not stay useful.
EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS = int(
    env("EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS", "86400")
)

# Where the password-reset link points (design.md page #10). The task builds the
# absolute URL from this setting for the same reason as the verification link:
# a Celery worker has no request.
PASSWORD_RESET_URL = env("PASSWORD_RESET_URL", "http://localhost:8000/reset-password/")

# REQ-FR-004 states one hour. Django's `default_token_generator` reads this
# setting, so the lifetime is a policy value rather than a number in the signing
# code. It also expires a link that is never used.
PASSWORD_RESET_TIMEOUT = int(env("PASSWORD_RESET_TIMEOUT", "3600"))

# Origin of the application's own links, used to turn a stored notification path
# into an absolute URL in the email that mirrors it (REQ-FR-022, batch 1.43).
# `notifications.url` holds a path -- the DDL's VARCHAR(500) is a link to a page,
# not a per-environment absolute URL -- and the Celery task that sends the email
# has no request to build one from. Same reasoning as `EMAIL_VERIFICATION_URL`,
# and the host differs per environment, so it is a setting rather than a
# constant.
SITE_URL = env("SITE_URL", "http://localhost:8000")


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


# ---------------------------------------------------------------------------
# Object storage — S3-compatible (REQ-FR-010, Arch Doc §6.1)
# ---------------------------------------------------------------------------
# The *presence of a bucket name* is the switch, exactly as .env.example
# promises ("leave unset to store files on the local filesystem"). A filesystem
# default that silently becomes S3, or the reverse, is how a resume ends up
# somewhere nobody backs up.
#
# `endpoint_url` is what points this at MinIO instead of AWS; it is passed
# through unmodified because MinIO needs path-style addressing (a bucket
# subdomain does not exist in a local stack) and SigV4.
#
# Credentials stay optional: on real AWS an instance role is a legitimate
# source, and boto3 resolves it when neither key is set. Requiring them here
# would make the IAM path impossible.
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", "us-east-1")

# The same store as the browser reaches it (batch 1.22, REQ-FR-010). Compose
# speaks to MinIO at `minio:9000`, which no browser can resolve; the browser
# uses `localhost:9000`. The host is part of the SigV4 signature, so a URL
# signed for the internal host cannot be rewritten afterwards -- it is signed
# against this endpoint instead. Empty means "same host as the server".


def public_endpoint(value: str) -> str:
    """`S3_PUBLIC_ENDPOINT_URL`, refusing anything that is not an http(s) URL.

    A scheme-less value (`minio:9000`) parses as scheme `minio` and would reach
    boto3 as a nonsense endpoint; the failure would then appear when a candidate
    clicks Upload, not at boot. A function so the guard itself is testable.
    """
    if value and urlsplit(value).scheme not in {"http", "https"}:
        raise ImproperlyConfigured(
            "S3_PUBLIC_ENDPOINT_URL must be an http(s) URL, e.g. "
            "http://localhost:9000."
        )
    return value


S3_PUBLIC_ENDPOINT_URL = public_endpoint(env("S3_PUBLIC_ENDPOINT_URL"))

# Browser CORS for presigned PUT/POST (batch 1.19). Comma-separated origins, the
# same shape as CSRF_TRUSTED_ORIGINS, because both answer the same question:
# which origin is allowed to act on this deployment.
S3_CORS_ALLOWED_ORIGINS = env_list(
    "S3_CORS_ALLOWED_ORIGINS",
    default="http://localhost:8000,http://127.0.0.1:8000",
)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

if AWS_STORAGE_BUCKET_NAME:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": AWS_ACCESS_KEY_ID,
            "secret_key": AWS_SECRET_ACCESS_KEY,
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "endpoint_url": AWS_S3_ENDPOINT_URL,
            "region_name": AWS_S3_REGION_NAME,
            # MinIO serves buckets as paths, not subdomains.
            "addressing_style": "path",
            "signature_version": "s3v4",
            # Files are private. Every read goes through an authenticated,
            # rate-limited Django view with a signed URL (Complete Doc §C.6),
            # never a public object URL.
            "default_acl": None,
            "querystring_auth": True,
            # Two uploads of the same name must not overwrite each other.
            "file_overwrite": False,
        },
    }


# ---------------------------------------------------------------------------
# Content Security Policy
# ---------------------------------------------------------------------------

# Derived, never hand-written. With `AWS_S3_ENDPOINT_URL` set the browser talks
# to that endpoint (MinIO locally, a gateway in a real deployment); with only a
# bucket configured it talks to the regional virtual-host address boto3 signs
# for. Reading the origin off the same values the storage backend uses is what
# keeps the policy and the presigned URL pointing at the same host.


def storage_origin(
    endpoint_url: str,
    bucket: str,
    region: str,
    public_endpoint_url: str = "",
) -> str:
    """The origin a browser uploads to, or "" when no bucket is configured.

    A function, not three module-level lines, so `tests/core/test_security_headers.py`
    can prove every case without reloading the settings module. The empty string
    is the "no storage" case: the policy then stays `connect-src 'self'` rather
    than gaining a wildcard.

    `public_endpoint_url` wins because it is the host the browser actually talks
    to; the internal endpoint is the fallback for a deployment where one host
    serves both roles.
    """
    if not bucket:
        return ""

    for url in (public_endpoint_url, endpoint_url):
        if url:
            parsed = urlsplit(url)
            return f"{parsed.scheme}://{parsed.netloc}"

    return f"https://{bucket}.s3.{region}.amazonaws.com"


_STORAGE_ORIGIN = storage_origin(
    AWS_S3_ENDPOINT_URL,
    AWS_STORAGE_BUCKET_NAME,
    AWS_S3_REGION_NAME,
    public_endpoint_url=S3_PUBLIC_ENDPOINT_URL,
)

# `'self'` first: the API calls the page makes are same-origin. The storage
# origin is appended only when one is configured, so a deployment without a
# bucket keeps the stricter policy instead of gaining a bare `https:` wildcard.
CONNECT_SRC = "'self'" + (f" {_STORAGE_ORIGIN}" if _STORAGE_ORIGIN else "")

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    f"connect-src {CONNECT_SRC}; "
    "font-src 'self'"
)


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
        # Batch 1.5. Complete Doc §5.5 gives one rate for unauthenticated
        # traffic -- 100 requests/hour -- and does not name a separate one for
        # signup. Using that documented figure avoids inventing a number; the
        # per-account resend cooldown (45 s) is the finer limit that actually
        # stops a verification-email flood. Verification and resend share a
        # scope because both are anonymous and both are the same attack surface.
        "register": env("THROTTLE_REGISTER", "100/hour"),
        "verify_email": env("THROTTLE_VERIFY_EMAIL", "100/hour"),
        # Batch 1.10. Reset requests are anonymous and send mail, so they share
        # the documented unauthenticated ceiling (Complete Doc §5.5) rather than
        # a number invented here.
        "password_reset": env("THROTTLE_PASSWORD_RESET", "100/hour"),
    },
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    # D-7: REQ-FR-002/007 and prd.md §10.1 pin the access token at 15 minutes and
    # the refresh token at 7 days, with rotation invalidating the previous token.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
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
    # Swagger UI's default template loads its CSS, JS and favicon from
    # cdn.jsdelivr.net. CONTENT_SECURITY_POLICY allows only 'self', so every one
    # of those requests was blocked and /api/docs/ rendered an empty page. The
    # assets are vendored from the pinned swagger-ui-dist devDependency by
    # `npm run vendor`, the same way htmx and Chart.js are.
    "SWAGGER_UI_DIST": f"{STATIC_URL}vendor/swagger-ui",
    "SWAGGER_UI_FAVICON_HREF": f"{STATIC_URL}vendor/swagger-ui/favicon-32x32.png",
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
