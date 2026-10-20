"""Public auth pages, mounted at the site root (design.md pages #6, #7, #9-#11).

Separate from `accounts.urls` (mounted at `/accounts/` for the signed-in account
area) and from `accounts.auth_urls` (the JSON API under `/api/v1/auth/`). The
three surfaces are owned by the same app but have three different prefixes, and
one module mounted three times would expose every route three times.

`/verify-email/` is not a free choice: `EMAIL_VERIFICATION_URL` in
`config/settings/base.py` already points at it, and that setting is what
`accounts.tasks.verification_link` puts in the email. `/login/` and
`/reset-password/` are fixed the same way, by `LOGIN_URL` and `PASSWORD_RESET_URL`.
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
    # Batch 1.9: page #7's login and its POST-only logout. LOGIN_URL is
    # "/login/" in base.py, so the path is fixed by that setting.
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Batch 1.11: pages #9 and #10. `PASSWORD_RESET_URL` points at
    # "/reset-password/", so that path is fixed by the setting too.
    path("forgot-password/", views.forgot_password, name="forgot-password"),
    path("reset-password/", views.reset_password_page, name="reset-password"),
]
