"""API v1 routes under `/api/v1/auth/` (Complete Doc §C.12).

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
]
