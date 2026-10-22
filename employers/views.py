"""Employer onboarding and company profile pages (REQ-FR-045, page #33).

Two guards, in this order:

1. `login_required` sends an anonymous visitor to `/login/` with a `next` that
   comes back here. A 403 for an anonymous user would be a dead end.
2. The employer group check returns 403 for a candidate, an interviewer or a
   platform admin. Those accounts are authenticated but are not employers; the
   page must not create an employer profile for them.

The target is always `request.user`. There is no id in any URL and no id in the
edit body, so "another employer cannot edit this profile" is structural rather
than a comparison a later edit could drop.

`onboarding` and `company` are separate routes on purpose. Page #33 is the
first-run form; the company page is the later edit surface. Keeping them apart
means "has the employer finished onboarding?" is answered by a redirect rather
than by a query parameter, and the authorization matrix can state both answers.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from employers.forms import EmployerProfileForm
from employers.models import EmployerProfile


def employer_required(view: Callable) -> Callable:
    """Require a signed-in user in `employer_hr` or `employer_manager`.

    `login_required` is applied first so an anonymous request gets the login
    redirect rather than a 403. Once authenticated, the account must be active
    and `is_employer` must be true (D-2). `is_employer` is the same property
    `accounts.permissions.IsEmployer` uses for the API, so the two surfaces
    cannot disagree about who counts as an employer.

    REQ-FR-045's candidate/employer mutual exclusion is enforced where a role is
    granted (`accounts.services.assign_role`), not here: this decorator answers
    "may this account use the employer portal", not "should this account hold an
    employer role".

    `PermissionDenied` is Django's, not DRF's, because these are template views.
    `config.urls.handler403` renders the documented error page.
    """

    @login_required
    @wraps(view)
    def wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not request.user.is_active or not request.user.is_employer:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def _profile_for(user) -> EmployerProfile | None:
    """The caller's company profile, or None before onboarding."""
    return EmployerProfile.objects.filter(user=user).first()


@never_cache
@employer_required
@require_http_methods(["GET", "POST"])
def onboarding(request: HttpRequest) -> HttpResponse:
    """Page #33: create the company profile. GET renders; POST creates.

    An employer who already has a profile is sent to the company page on GET. A
    stale POST still updates the four company fields rather than dropping the
    submission, matching the candidate onboarding page.

    There is no separate "skip" mutation: W10's "Skip for now" is a link back to
    the landing page. Skipping leaves no row, so the profile is still absent the
    next time the employer opens onboarding -- which is the correct state for
    "not finished" (and the state a future job-activation guard reads).
    """
    profile = _profile_for(request.user)

    if request.method == "GET" and profile is not None:
        return redirect("employer_portal:company")

    instance = profile or EmployerProfile(user=request.user)
    form = EmployerProfileForm(
        request.POST if request.method == "POST" else None,
        instance=instance,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your company profile is saved.")
        return redirect("employer_portal:company")

    return render(request, "employers/onboarding.html", {"form": form})


@never_cache
@employer_required
@require_http_methods(["GET"])
def company(request: HttpRequest) -> HttpResponse:
    """The company profile page: stored values plus the edit form.

    An employer without a profile is sent back to onboarding rather than shown an
    edit form that would create a row through a route the batch did not declare.
    """
    profile = _profile_for(request.user)
    if profile is None:
        return redirect("employer_portal:onboarding")

    return render(
        request,
        "employers/company.html",
        {
            "profile": profile,
            "form": EmployerProfileForm(instance=profile),
        },
    )


@never_cache
@employer_required
@require_POST
def company_edit(request: HttpRequest) -> HttpResponse:
    """Update the four company columns from the company page.

    `ModelForm(instance=profile)` writes only the fields declared in
    `EmployerProfileForm.Meta.fields`. Billing columns, the owner and timestamps
    are not in that list, so a request cannot reach them even if it posts their
    names.
    """
    profile = _profile_for(request.user)
    if profile is None:
        return redirect("employer_portal:onboarding")

    form = EmployerProfileForm(request.POST, instance=profile)
    if form.is_valid():
        form.save()
        messages.success(request, "Your company profile is updated.")
        return redirect("employer_portal:company")

    # An invalid ModelForm has already copied the submitted values onto
    # `form.instance` (the same object as `profile`). Re-read the row so the
    # read-only summary above the form shows what is actually stored, not the
    # rejected submission. The bound form still shows the user's attempt.
    profile.refresh_from_db()

    # Re-render the company page with the bound form so the error is visible.
    # The summary block uses `profile`'s stored values, which are unchanged
    # because an invalid ModelForm never saves.
    return render(
        request,
        "employers/company.html",
        {
            "profile": profile,
            "form": form,
        },
    )
