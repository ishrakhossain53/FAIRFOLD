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

import uuid
from functools import wraps
from typing import Callable

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from candidates.forms import SECTION_FORMS, SECTION_LABELS, CandidateProfileForm
from candidates.models import CandidateProfile, CandidateResume
from candidates.services import delete_resume


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


# Display text for page #17. The pipeline states are the model's, not a second
# vocabulary: `candidate_resumes.status` is the only place a state is defined
# (D-6(a)), and this dict only decides how each one reads to a candidate.
RESUME_STATUS_LABELS = {
    CandidateResume.Status.PENDING: "Not uploaded",
    CandidateResume.Status.UPLOADED: "Uploaded",
    CandidateResume.Status.SCANNING: "Checking for viruses",
    CandidateResume.Status.CLEAN: "Ready",
    CandidateResume.Status.REJECTED: "Rejected",
    CandidateResume.Status.PROCESSING: "Processing",
    CandidateResume.Status.EXTRACTED: "Processed",
    CandidateResume.Status.EMBEDDED: "Processed",
    CandidateResume.Status.FAILED: "Failed",
}

# Statuses that mean "this file is usable, or was and can be replaced". A
# `pending` row never received bytes, so "Replace" would be a second empty row;
# it gets "Delete" only.
RESUME_REPLACEABLE = {
    CandidateResume.Status.UPLOADED,
    CandidateResume.Status.SCANNING,
    CandidateResume.Status.CLEAN,
    CandidateResume.Status.REJECTED,
    CandidateResume.Status.PROCESSING,
    CandidateResume.Status.EXTRACTED,
    CandidateResume.Status.EMBEDDED,
    CandidateResume.Status.FAILED,
}


def _owned_resume(request: HttpRequest, raw_id: str | None) -> CandidateResume:
    """The caller's resume named by `raw_id`, or a 404.

    One answer for a malformed id, an id that exists nowhere and another
    candidate's id: a candidate has no business distinguishing them, and a
    distinguishable answer would enumerate ids.
    """
    try:
        resume_id = uuid.UUID(str(raw_id))
    except (TypeError, ValueError):
        raise Http404("Resume not found.")

    resume = CandidateResume.objects.filter(
        pk=resume_id, candidate__user=request.user
    ).first()
    if resume is None:
        raise Http404("Resume not found.")
    return resume


def _resume_api_urls() -> dict:
    """The three API addresses page #17's uploader calls.

    The two object routes are templated from the nil UUID rather than assembled
    by string concatenation in the template: the URLconf stays the only place a
    path is written, so a future route change cannot leave the page calling a
    stale address. `{id}` is substituted by `static/js/resume-upload.js`.
    """
    nil = uuid.UUID(int=0)
    return {
        "upload": reverse("api:candidates:resume-list"),
        "complete": reverse("api:candidates:resume-complete", args=[nil]).replace(
            str(nil), "{id}"
        ),
        "detail": reverse("api:candidates:resume-detail", args=[nil]).replace(
            str(nil), "{id}"
        ),
    }


def _resume_rows(candidate_profile: CandidateProfile) -> list[dict]:
    """The metadata list for page #17, newest first.

    Names, sizes and codes only. `file_key` never reaches the template: the page
    has no use for it, and a key rendered into HTML is a key in every screenshot
    and support ticket.
    """
    rows = []
    for resume in CandidateResume.objects.filter(candidate=candidate_profile):
        rows.append(
            {
                "id": resume.id,
                "filename": resume.original_filename or "Resume",
                "uploaded_at": resume.created_at,
                "status": resume.status,
                "status_label": RESUME_STATUS_LABELS.get(resume.status, resume.status),
                "status_reason": resume.status_reason,
                "rejected": resume.status == CandidateResume.Status.REJECTED,
                "can_replace": resume.status in RESUME_REPLACEABLE,
            }
        )
    return rows


def _replace_id(candidate_profile: CandidateProfile, raw_id: str) -> str:
    """The id the page is replacing, or "" — only for a resume this candidate owns.

    The page offers "Replace" as `?replace=<id>` so the intent survives a reload
    and works as a plain link. Validating it here means a hand-edited query
    string cannot make the page claim it is replacing somebody else's resume,
    and the JavaScript that deletes the old row is only ever handed an id the
    server confirmed belongs to this candidate.
    """
    if not raw_id:
        return ""
    try:
        resume_id = uuid.UUID(raw_id)
    except (TypeError, ValueError):
        return ""

    owned = CandidateResume.objects.filter(
        pk=resume_id, candidate=candidate_profile
    ).exists()
    return str(resume_id) if owned else ""


@never_cache
@candidate_required
@require_http_methods(["GET"])
def resumes(request: HttpRequest) -> HttpResponse:
    """Page #17: the Resume manager (design.md S03, REQ-FR-010).

    The page renders the list server-side and hands the upload flow the three
    API addresses it needs. It deliberately does not call the API itself: a
    template that fetches its own list would show an empty page whenever the
    JSON call failed, and the list is the part that must survive a broken
    uploader.

    A candidate with no profile is sent to onboarding, like page #16: resumes
    hang off the profile (REQ-FR-009 precedes REQ-FR-010).
    """
    candidate_profile = CandidateProfile.objects.filter(user=request.user).first()
    if candidate_profile is None:
        return redirect("candidate_portal:onboarding")

    return render(
        request,
        "candidates/resumes.html",
        {
            "resumes": _resume_rows(candidate_profile),
            "status_labels": RESUME_STATUS_LABELS,
            "max_upload_bytes": settings.MAX_UPLOAD_SIZE_BYTES,
            "max_upload_mb": settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024),
            "replace_id": _replace_id(
                candidate_profile, request.GET.get("replace", "")
            ),
            "api": _resume_api_urls(),
        },
    )


@never_cache
@candidate_required
@require_http_methods(["GET", "POST"])
def resume_delete(request: HttpRequest) -> HttpResponse:
    """Page #17's Delete action: a confirmation page, then a POST that deletes.

    The confirmation is a page rather than a `<dialog>` so the destructive action
    works without JavaScript, which is the batch's degradation rule. It is a
    fixed path with the id in the query string or the body, not a
    `<uuid:pk>` segment, for the same reason as `profile/edit/`: the
    authorization matrix refuses to guess a sample for a parameterised page
    route.

    The mutation is a POST. A GET never deletes anything: a link that does is
    triggered by prefetchers, crawlers and a mis-click on "reload".
    """
    raw_id = request.POST.get("resume") if request.method == "POST" else None
    if raw_id is None:
        raw_id = request.GET.get("resume")

    resume = _owned_resume(request, raw_id)

    if request.method == "POST":
        delete_resume(resume, actor=request.user)
        messages.success(request, "Resume deleted.")
        return redirect("candidate_portal:resumes")

    return render(
        request,
        "candidates/resume_confirm_delete.html",
        {"resume": resume},
    )
