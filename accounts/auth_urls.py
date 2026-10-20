"""API v1 routes under `/api/v1/auth/` (Complete Doc §C.12).

Registration and verification (batch 1.5), login/refresh/logout (1.8) and
password reset/change (1.10), plus the authenticated current-user route (1.12).

Separate from `accounts.api_urls` on purpose. That module is mounted at
`/api/v1/accounts/` (the app's own domain); §C.12 puts the auth routes under
`/api/v1/auth/`. Mounting one module at both prefixes would expose every route in
it twice and break `reverse()` ambiguity checks, so the two prefixes get two
modules.

The routes are plain `path()`s rather than a router: they are function-per-action
endpoints with fixed, documented paths, and a router would add a trailing
`{pk}` lookup none of them has.
"""

from __future__ import annotations

from django.urls import path

from accounts.api_views import (
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshView,
    RegisterView,
    ResendVerificationEmailView,
    VerifyEmailView,
)

app_name = "accounts_auth"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path(
        "verify-email/resend/",
        ResendVerificationEmailView.as_view(),
        name="verify-email-resend",
    ),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path(
        "password/reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "password/change/",
        PasswordChangeView.as_view(),
        name="password-change",
    ),
    # §C.12: GET/PUT of the caller's own account. Authenticated, unlike every
    # route above it in this module.
    path("me/", MeView.as_view(), name="me"),
]
