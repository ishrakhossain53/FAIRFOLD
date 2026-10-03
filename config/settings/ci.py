"""CI settings.

Runs against the `pgvector/pgvector:pg17`, `redis:7-alpine` and
`clamav/clamav:1.4` services defined in Arch Doc §6.5. **Every test uses this
module** — there is no `config.settings.test`, because a SQLite-based test
settings module would let the embedding, ranking and screening tests pass on a
database that cannot represent a vector, and fail in production.

The design goal is that a test failure means the code is wrong. Settings that
differ from production are therefore limited to two, both performance:

- ``MD5PasswordHasher`` — a PBKDF2 hash costs ~100 ms per login test.
- ``CELERY_TASK_ALWAYS_EAGER`` is deliberately **not** set. Eager Celery hides
  exactly the serialisation and connection bugs these tests exist to catch, so
  tasks run against the real broker.

Security settings match production: ``SESSION_COOKIE_SECURE`` and
``CSRF_COOKIE_SECURE`` are on, so a test that forgets them fails here rather
than in production.
"""

# DATABASES is imported explicitly as well as by the star import above: flake8
# cannot see through a star import, so mutating DATABASES["default"] here reads
# as F405 and would mask a real NameError if the star import were dropped.
from config.settings.base import *  # noqa: F401,F403
from config.settings.base import DATABASES, env

# Django refuses to start with DEBUG=True unless the host is localhost. The CI
# host *is* localhost, but leaving DEBUG off keeps the failure mode identical to
# production.
DEBUG = False

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# `testserver` is the host Django's test client uses. Without it, every test
# that builds an absolute URL raises DisallowedHost.
CSRF_TRUSTED_ORIGINS = ["http://testserver"]

SECURE_SSL_REDIRECT = False
# On in CI, matching production: a view that only sets its cookie over HTTPS
# should fail here rather than in a browser.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# `manage.py check --deploy` runs in CI (Arch Doc §6.5) with --fail-level
# WARNING, and Django's security checks read these two regardless of
# environment. Both are **on here on purpose**, for a specific reason:
#
# HSTS is a browser-side pin, so it is inert against the test client and cannot
# lock anyone out. Setting it in CI means a settings change that turns it off in
# production is caught here rather than in a browser.
#
# SECURE_SSL_REDIRECT is the one that *does* matter. Django's test client
# follows no redirects by default and does not assert on them, so this does not
# break the suite -- but it is left **False** rather than True deliberately,
# because a developer running pytest against `config.settings.ci` locally over
# plain http:// would otherwise get a redirect loop on every request. The
# production value is asserted in production.py, which is the module that
# matters for it.
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    # A fixed non-secret key. CI settings must be importable before any .env is
    # loaded, and a *random* key per run would invalidate every session cache
    # between steps. This value is public and is only ever used by tests.
    #
    # Long and varied on purpose: `check --deploy` (security.W009) rejects a key
    # under 50 characters or with fewer than 5 unique ones, so a short readable
    # placeholder fails the very check meant to catch a weak key. It must be
    # strong enough to satisfy the check and obviously fake enough that nobody
    # copies it anywhere.
    "ci-only-not-a-real-secret-key-0000000000000000000000000000000000",
)

# The base module requires these; CI has no .env file. They are placeholders
# that no CI code path can use — there is no ClamAV daemon in the worker job
# beyond the service container, and no field encryption round-trip in CI.
ENCRYPTION_KEY = env("ENCRYPTION_KEY", "ci-only-fernet-placeholder-0000000000=")

DATABASES["default"]["NAME"] = env("POSTGRES_DB", "fairfold_test")  # noqa: F405
DATABASES["default"]["TEST"] = {
    "NAME": env("POSTGRES_TEST_DB", "fairfold_test")
}  # noqa: F405

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

LOG_LEVEL = env("LOG_LEVEL", "WARNING").upper()

# Celery talks to the real Redis broker. Tasks are not run eagerly.
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = True

# ClamAV's definitions download on first boot, so the first scan of a run can be
# slow. Waiting for the container healthcheck (Arch Doc §6.5) handles the daemon;
# this covers the scan itself.
CLAMD_TIMEOUT = 60
