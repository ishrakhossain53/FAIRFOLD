"""Candidate onboarding and profile pages (REQ-FR-009, design.md pages #14/#16).

Two guards, in this order:

1. `login_required` sends an anonymous visitor to `/login/` with a `next` that
   comes back here. A 403 for an anonymous user would be a dead end.
2. The `candidate` group check returns 403 for an employer, an interviewer or a
   platform admin. Those accounts are authenticated but are not candidates; the
   page must not create a candidate profile for them.

The target is always `request.user`. There is no id in any URL and no id in the
edit body, so "another candidate cannot edit this profile" is structural rather
than a comparison a later edit could drop.

The edit endpoint takes the section name in a POST field rather than in the URL.
A `<str:section>` path segment would be a parameterised route, and the
authorization matrix deliberately refuses to guess sample values for those
(`tests/core/test_authz_matrix.py`). The field is validated against
`SECTION_FORMS`, so an unknown value is a 400 and never a `setattr` on an
arbitrary column.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from candidates.forms import SECTION_FORMS, SECTION_LABELS, CandidateProfileForm
from candidates.models import CandidateProfile


def candidate_required(view: Callable) -> Callable:
    """Require a signed-in user in the `candidate` group.

    `login_required` is applied first so an anonymous request gets the login
    redirect rather than a 403. Once authenticated, the account must be active
    and in the seeded `candidate` group (D-2); there is no `role` column. The
    `is_active` check is a guard for a hand-built request: Django's
    `ModelBackend` already rebuilds an inactive session as `AnonymousUser`.

    `PermissionDenied` is Django's, not DRF's, because these are template views.
    `config.urls.handler403` renders the documented error page.
    """

    @login_required
    @wraps(view)
    def wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not request.user.is_active or not request.user.is_candidate:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def profile_completeness(profile: CandidateProfile) -> int:
    """Percentage of the profile that has an answer (0-100, in steps of 25).

    The three free-text fields count when they are non-empty. The remote
    preference counts once the profile exists: it is a boolean, so `False` is an
    answer ("not open to remote"), not a missing value. Counting it as missing
    when `False` would show a completed profile as incomplete.

    design.md S02's 70% is illustrative; the bar here is computed from the four
    fields this batch actually owns.
    """
    text_fields = ("title", "bio", "location")
    filled = sum(1 for field in text_fields if (getattr(profile, field) or "").strip())
    return round((filled + 1) * 100 / 4)


def _profile_context(
    profile: CandidateProfile,
    *,
    bound_section: str | None = None,
    bound_form=None,
) -> dict:
    """Build the four inline forms plus the completeness value for page #16.

    Each form starts from the stored value so a section the user did not touch
    keeps its current value. The section that failed validation replaces its
    initial form with the bound one, and `open_section` makes its `<details>`
    render open so the error is visible without JavaScript.
    """
    forms = {
        section: form_class(initial={section: getattr(profile, section)})
        for section, form_class in SECTION_FORMS.items()
    }
    if bound_section and bound_form is not None:
        forms[bound_section] = bound_form

    return {
        "profile": profile,
        "completeness": profile_completeness(profile),
        "title_form": forms["title"],
        "bio_form": forms["bio"],
        "location_form": forms["location"],
        "remote_ok_form": forms["remote_ok"],
        "open_section": bound_section or "",
    }


@never_cache
@candidate_required
@require_http_methods(["GET", "POST"])
def onboarding(request: HttpRequest) -> HttpResponse:
    """Page #14's manual profile step. GET renders; POST creates or updates.

    design.md S02's wizard has three steps. The resume-upload step (batch 1.17)
    and the skills step (1.18) are out of scope here and are not faked: this page
    is the "build manually" path, and it owns exactly the four REQ-FR-009 fields.

    A candidate who already has a profile is sent to page #16 on GET. A stale
    POST still updates the four fields rather than silently discarding the
    submission.
    """
    profile = CandidateProfile.objects.filter(user=request.user).first()

    if request.method == "GET" and profile is not None:
        return redirect("candidate_portal:profile")

    instance = profile or CandidateProfile(user=request.user)
    form = CandidateProfileForm(
        request.POST if request.method == "POST" else None,
        instance=instance,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile is saved.")
        return redirect("candidate_portal:profile")

    return render(request, "candidates/onboarding.html", {"form": form})


@never_cache
@candidate_required
@require_http_methods(["GET"])
def profile(request: HttpRequest) -> HttpResponse:
    """Page #16: read-only profile plus one inline form per section."""
    candidate_profile = CandidateProfile.objects.filter(user=request.user).first()
    if candidate_profile is None:
        return redirect("candidate_portal:onboarding")

    return render(
        request,
        "candidates/profile.html",
        _profile_context(candidate_profile),
    )


@never_cache
@candidate_required
@require_POST
def profile_edit(request: HttpRequest) -> HttpResponse:
    """Update exactly one section of page #16 (design.md S02's inline edit).

    The section is a POST field, validated against `SECTION_FORMS`. Only the
    matching column is written, via `update_fields`, so a request cannot use this
    form to change the other three sections or any column outside the profile.
    """
    candidate_profile = CandidateProfile.objects.filter(user=request.user).first()
    if candidate_profile is None:
        # Nothing to edit yet. Send the candidate to onboarding rather than
        # rendering a form that would fail on every submit.
        return redirect("candidate_portal:onboarding")

    section = request.POST.get("section", "")
    form_class = SECTION_FORMS.get(section)
    if form_class is None:
        return HttpResponseBadRequest("Unknown profile section.")

    form = form_class(request.POST)
    if form.is_valid():
        setattr(candidate_profile, section, form.cleaned_data[section])
        candidate_profile.save(update_fields=[section, "updated_at"])
        messages.success(request, f"{SECTION_LABELS[section]} updated.")
        return redirect("candidate_portal:profile")

    # Re-render page #16 with the failed form bound and its section open. The
    # other sections keep their stored values.
    return render(
        request,
        "candidates/profile.html",
        _profile_context(
            candidate_profile,
            bound_section=section,
            bound_form=form,
        ),
    )
