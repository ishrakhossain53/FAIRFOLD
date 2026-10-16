"""Local development settings.

Differences from base, and why each one is safe to relax **only** here:

- ``DEBUG=True`` — required for tracebacks, and the reason the security
  settings below stay off. A development machine has no TLS to redirect to.
- Console email — nothing leaves the machine, so a password-reset email cannot
  reach a real inbox by accident.
- ``SECURE_*`` off — there is no HTTPS locally, so ``SECURE_SSL_REDIRECT=True``
  would produce a redirect loop against ``localhost``.

What is **not** relaxed: the database is still PostgreSQL with pgvector. There
is no SQLite path anywhere in this project (Complete Doc §4.2), because SQLite
would make every embedding query fail for a reason unrelated to the code under
test.
"""

# LOGGING is imported explicitly as well as by the star import. The star import
# supplies it at runtime, so the name IS defined -- but flake8 cannot see through
# a star import, and F405 here would otherwise mask a genuine NameError if the
# star import were ever removed.
from config.settings.base import *  # noqa: F401,F403
from config.settings.base import LOGGING, env, env_bool, env_list

DEBUG = env_bool("DEBUG", default=True)

# Read from the environment, with the previous hardcoded values as defaults.
# They used to be literal lists, which silently ignored the ALLOWED_HOSTS and
# CSRF_TRUSTED_ORIGINS .env.example documents for local access -- so reaching the
# stack by its LAN address returned 400 regardless of what .env said.
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default="localhost,127.0.0.1,[::1]")
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:8000,http://127.0.0.1:8000",
)

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Password hashing is slow by design. In local development it is fast enough to
# be irritating and slow enough to be representative.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Quiet the request log; keep warnings and errors.
LOG_LEVEL = env("LOG_LEVEL", "WARNING").upper()

# Show the SQL that a slow page generates. Never enabled in ci or production.
if env_bool("SHOW_SQL", default=False):  # pragma: no cover - developer aid
    LOGGING["loggers"]["django.db.backends"] = {"level": "SQL", "propagate": True}
