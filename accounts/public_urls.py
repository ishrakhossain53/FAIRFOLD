"""Public auth pages, mounted at the site root (design.md pages #6 and #11).

Separate from `accounts.urls` (mounted at `/accounts/` for the signed-in account
area) and from `accounts.auth_urls` (the JSON API under `/api/v1/auth/`). The
three surfaces are owned by the same app but have three different prefixes, and
one module mounted three times would expose every route three times.

`/verify-email/` is not a free choice: `EMAIL_VERIFICATION_URL` in
`config/settings/base.py` already points at it, and that setting is what
`accounts.tasks.verification_link` puts in the email.
"""

from __future__ import annotations

from django.urls import path

from accounts import views

app_name = "accounts_public"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("register/check-email/", views.check_email, name="check-email"),
    path("verify-email/", views.verify_email_page, name="verify-email"),
    path(
        "verify-email/resend/",
        views.resend_verification,
        name="verify-email-resend",
    ),
]
