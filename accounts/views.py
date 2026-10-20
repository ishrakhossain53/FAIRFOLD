"""Registration and email-verification pages (REQ-FR-001, pages #6 and #11).

These are the server-rendered half of the flow the API serves as JSON. The
domain work is in `accounts.services`; nothing here decides whether an account
may be created, only how the answer is shown.

Progressive enhancement is the rule: every form posts normally and every state is
a real page, so the flow works with JavaScript disabled. HTMX is an extra: the
form swaps its own panel on a validation error (`design.md §8.3`: "server-rendered
errors swapped in; focus moved to the error summary") and asks for a full
navigation on success with `HX-Redirect`, because swapping a whole page into a
form panel is not a navigation.

Two anti-enumeration rules are enforced in the templates:

* a duplicate address and a new one take the same redirect and show the same
  pending page, exactly as the API returns the same 201 body;
* the pending page shows the address masked ("a***@x.com", design.md X02), and
  the resend button answers identically whatever the address is.

The verification page verifies on GET, because the link in the email is a link.
The token is single-use by design (`verify_email` flips the flag once) and a
second visit renders the success state rather than an error.
"""

from __future__ import annotations

import math
import time

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from accounts.forms import RegistrationForm
from accounts.models import User
from accounts.services import (
    EmailAlreadyVerified,
    InvalidVerificationToken,
    VerificationTokenExpired,
    queue_verification_email,
    register_user,
    resend_verification_email,
    verify_email,
)

# Session keys, not URL parameters: the address is personal data and a URL ends
# up in the address bar, browser history, and the request log. The sessions table
# is server-side (SESSION_ENGINE = db) and is the right place for it.
PENDING_EMAIL_SESSION_KEY = "accounts.pending_verification_email"
PENDING_SENT_AT_SESSION_KEY = "accounts.pending_verification_sent_at"

# The same generic sentence the API returns (accounts.api_views.RESEND_DETAIL).
# It must not depend on whether the address exists, is verified, or is inside its
# cooldown.
RESEND_SENT_DETAIL = "If that address needs verification, we've sent a new link."


def mask_email(email: str) -> str:
    """'ada@example.com' -> 'a***@example.com' (design.md X02, page #11).

    The pending page has to show enough for the user to recognise the address
    without printing it in full on a screen someone else may be looking at. The
    local part is the identifying half; the domain is kept so a typo in the
    domain is still visible.
    """
    local, separator, domain = email.partition("@")
    if not separator or not local:
        # Defensive: the form validates first, so this is only reachable from a
        # corrupted session value. Revealing nothing is the safe answer.
        return "***"
    return f"{local[:1]}***@{domain}"


def _remember_pending(request: HttpRequest, email: str) -> None:
    """Record the address and the moment the page should treat as its last send.

    The timestamp is display only: the real cooldown is the cache key in
    `accounts.services`. It exists because Django's Redis cache backend has no
    `ttl()`, so an accurate "available in 0:45" after a page reload needs a
    value the page can read.
    """
    request.session[PENDING_EMAIL_SESSION_KEY] = email
    request.session[PENDING_SENT_AT_SESSION_KEY] = int(time.time())


def _cooldown_remaining(request: HttpRequest) -> int:
    """Seconds left on the resend cooldown, for the text beside the button."""
    sent_at = request.session.get(PENDING_SENT_AT_SESSION_KEY)
    if not sent_at:
        return 0
    elapsed = time.time() - float(sent_at)
    remaining = settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS - elapsed
    return max(0, math.ceil(remaining))


def _after_submit(request: HttpRequest, url_name: str) -> HttpResponse:
    """Redirect after a successful POST, or ask HTMX for a full navigation.

    A plain 302 is followed transparently by HTMX and the destination page would
    be swapped into the form panel. `HX-Redirect` is the documented way to say
    "navigate the browser instead".
    """
    url = reverse(url_name)
    if getattr(request, "htmx", False):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url)


@never_cache
def register(request: HttpRequest) -> HttpResponse:
    """Page #6. GET renders the form; POST creates the account.

    The response to a duplicate address is identical to the response to a new
    one -- same redirect, same pending page, no email. `register_user` returns
    `None` for the duplicate precisely so this view cannot accidentally tell the
    two apart.
    """
    if request.method != "POST":
        return render(request, "accounts/register.html", {"form": RegistrationForm()})

    form = RegistrationForm(request.POST)
    if form.is_valid():
        try:
            user = register_user(**form.service_kwargs())
        except DjangoValidationError as exc:
            # Unreachable after `clean()` ran the same validators; a guard so a
            # divergence is a form error rather than a 500.
            form.add_error(None, exc)
        else:
            if user is not None:
                queue_verification_email(user)
            # Set for a duplicate too, on purpose: "Available in 0:45" is part of
            # the pending page, and a page without the cooldown would tell a
            # stranger that the address was already registered.
            _remember_pending(request, form.cleaned_data["email"])
            return _after_submit(request, "accounts_public:check-email")

    if getattr(request, "htmx", False):
        # The swapped panel contains the summary and the field errors. 200 on
        # purpose: HTMX does not swap a 4xx response by default, and a validation
        # failure is a normal outcome of a normal form.
        return render(request, "accounts/_register_panel.html", {"form": form})
    return render(request, "accounts/register.html", {"form": form})


@never_cache
def check_email(request: HttpRequest) -> HttpResponse:
    """Page #11, pending state: "We sent a link to a***@x.com"."""
    email = request.session.get(PENDING_EMAIL_SESSION_KEY)
    if not email:
        # Reached by a bookmark or after the session expired. There is no address
        # to show and no button that could work, so start again rather than
        # render a dead page.
        return redirect("accounts_public:register")
    return render(
        request,
        "accounts/check_email.html",
        {
            "email": email,
            "masked_email": mask_email(email),
            "cooldown": _cooldown_remaining(request),
        },
    )


@never_cache
def verify_email_page(request: HttpRequest) -> HttpResponse:
    """Page #11, success and failure states, from the emailed GET link.

    `accounts.tasks.verification_link` points at this route
    (`EMAIL_VERIFICATION_URL?token=...`). The status code follows the state:
    200 for success (including an already-verified account, which is the success
    state and not an error) and 400 for an expired or invalid token, so a
    monitoring check can tell a dead link from a working one.

    The response must not be cached and must not leak the token in a `Referer`
    header to any third party; `no-store` and `no-referrer` are set explicitly on
    top of `never_cache`.
    """
    token = request.GET.get("token", "")
    state = "invalid"
    if token:
        try:
            verify_email(token)
        except VerificationTokenExpired:
            state = "expired"
        except InvalidVerificationToken:
            state = "invalid"
        except EmailAlreadyVerified:
            state = "success"
        else:
            state = "success"

    if state == "success":
        # Nothing left to resend, and the flag is what the pending page was
        # waiting for.
        request.session.pop(PENDING_EMAIL_SESSION_KEY, None)
        request.session.pop(PENDING_SENT_AT_SESSION_KEY, None)

    response = render(
        request,
        "accounts/verify_email.html",
        {
            "state": state,
            "email": request.session.get(PENDING_EMAIL_SESSION_KEY) or "",
            "cooldown": _cooldown_remaining(request),
        },
        status=200 if state == "success" else 400,
    )
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


@require_POST
@never_cache
def resend_verification(request: HttpRequest) -> HttpResponse:
    """Send another verification link, from the pending or the expired state.

    Always the same destination and the same sentence, whether the address exists,
    is already verified, or is inside its cooldown. That is the whole contract:
    this view is reachable without an account, so any difference in the answer
    is an account-enumeration oracle (the same reason `register_user` returns
    `None` for a duplicate).

    The address comes from the session, which is also where the pending page got
    it from. It is never a form field or a query parameter: the page must not
    print the full address in its own source when the visible copy is masked, and
    a field would let a stranger drive a resend for any address from this route
    instead of the throttled API.
    """
    email = request.session.get(PENDING_EMAIL_SESSION_KEY)
    if not email:
        # No address in this session: either the page was bookmarked after the
        # session was recycled, or the request did not come from our pages.
        return redirect("accounts_public:register")

    user = User.objects.filter(email=email).first()
    if user is not None and resend_verification_email(user):
        # Only restart the displayed countdown when something was actually queued.
        # A refused resend keeps the old timestamp, so the text beside the button
        # still shows the real window.
        _remember_pending(request, email)

    if getattr(request, "htmx", False):
        return render(
            request,
            "accounts/_resend_panel.html",
            {
                "email": email,
                "cooldown": _cooldown_remaining(request),
                "resent": True,
            },
        )

    messages.success(request, RESEND_SENT_DETAIL)
    return redirect("accounts_public:check-email")
