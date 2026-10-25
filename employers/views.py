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
from typing import Callable, Mapping

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from ai.citation import CitationError, load_rationale
from ai.screening import bias_status_for
from employers.forms import EmployerProfileForm, JobForm
from employers.models import EmployerProfile
from employers.services import (
    CONFLICT,
    NOOP,
    change_job_status,
    delete_draft_job,
    job_status,
    record_job_audit,
)
from matching.models import Application, Job


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


@never_cache
@employer_required
@require_http_methods(["GET"])
def application_rationale(request: HttpRequest, application_id) -> HttpResponse:
    """Page #41 (S13): the AI assessment column for one application.

    **Only the rationale column is built here.** S13 is a split view: the
    anonymised resume pane is `design.md` 7.14 and batch 2.9, the assessment-gate
    panel is REQ-FR-051, and the sticky decision bar is REQ-FR-051/052. Those are
    later batches; offering the controls now would show buttons nothing enforces.

    **Scoped to the caller's own applications.** The lookup filters on
    `job__employer__user`, so another employer's application is a 404, not a 403
    that would confirm the row exists. The candidate's identity is never in the
    context: REQ-FR-029 keeps the name, photo and contact details hidden until
    shortlist, and this page does not shortlist.

    A stored rationale that no longer parses renders the error state rather than a
    500. The score and the audit row are still true even when the payload is not
    readable, and the employer is told exactly that.
    """
    application = get_object_or_404(
        Application.objects.select_related("job", "job__employer"),
        pk=application_id,
        job__employer__user=request.user,
    )

    bias_status = bias_status_for(application)
    checked: list[str] = []
    highlights: list[str] = []
    if bias_status.entry is not None:
        # `details` is the documented payload (ai.bias_audit.audit_payload). Read
        # defensively: an older row may predate a key, and a page must not 500 on
        # a row an earlier version wrote.
        checked = list(bias_status.entry.details.get("checked", []))
        highlights = list(bias_status.entry.details.get("highlights", []))

    rationale = None
    error = None
    if application.match_rationale:
        try:
            rationale = load_rationale(application.match_rationale)
        except CitationError:
            error = (
                "The stored rationale could not be read. The score and the audit "
                "entry are unchanged; re-screening will replace the rationale."
            )
    elif application.screening_status == Application.ScreeningStatus.FAILED:
        error = application.screening_error or (
            "Screening failed before a rationale was produced."
        )

    return render(
        request,
        "employers/application_rationale.html",
        {
            "application": application,
            "rationale": rationale,
            "bias_status": bias_status,
            "checked": checked,
            "highlights": highlights,
            "error": error,
        },
    )


# ---------------------------------------------------------------------------
# Job management pages (REQ-FR-025-027, pages #35-#37, batch 1.30)
# ---------------------------------------------------------------------------

#: Page #35's four tabs, in the order design.md draws them.
JOB_TABS = (
    (Job.Status.DRAFT, "Draft"),
    (Job.Status.ACTIVE, "Active"),
    (Job.Status.PAUSED, "Paused"),
    (Job.Status.CLOSED, "Closed"),
)

#: Page #37's funnel columns (design.md W11) and the application status each
#: one counts. `not_matched`, `rejected` and `hired` are deliberately absent:
#: the funnel is the live pipeline, and a filter outcome is not a stage.
JOB_FUNNEL = (
    (Application.Status.APPLIED, "Applied"),
    (Application.Status.SCREENED, "Screened"),
    (Application.Status.SHORTLISTED, "Shortlisted"),
    (Application.Status.INTERVIEW, "Interview"),
    (Application.Status.OFFERED, "Offer"),
)

NO_PROFILE_INFO = "Set up your company profile before posting a job."
EDIT_DRAFT_ONLY = "Only a draft job can be edited."
DELETE_DRAFT_ONLY = "Only a draft job can be deleted."
AUTOSAVE_NOT_SAVED = "Not saved"


def _portal_profile(request: HttpRequest):
    """The caller's profile, or `(None, redirect-to-onboarding)`.

    A job belongs to an `EmployerProfile`, so an employer who has not onboarded
    has nowhere to put one. Redirecting with a sentence is better than a 404: the
    page is reachable and the next step is obvious.
    """
    profile = _profile_for(request.user)
    if profile is None:
        messages.info(request, NO_PROFILE_INFO)
        return None, redirect("employer_portal:onboarding")
    return profile, None


def _owned_job(request: HttpRequest, profile: EmployerProfile, job_id) -> Job:
    """The caller's job, or the documented 404.

    Filtering by `employer` is the ownership rule: another employer's id and a
    non-existent id render the same page, so the portal cannot be used to learn
    that a job exists elsewhere.
    """
    return get_object_or_404(Job, pk=job_id, employer=profile)


#: Page #36's four long-text fields, in the form's order (design.md 7.22). The
#: labels come from `JobForm` rather than a second copy, so renaming a field in
#: the form renames it in the preview too.
PREVIEW_FIELDS = tuple(
    (JobForm.base_fields[name].label, name)
    for name in ("description", "responsibilities", "requirements", "nice_to_have")
)


def _preview_context(values: Mapping[str, str | None]) -> dict:
    """Context for the live preview fragment, from a bound form or a POST.

    Trimming here means a field containing only whitespace keeps the empty state
    instead of rendering an empty paragraph.
    """
    fields = [
        (label, (values.get(name) or "").strip()) for label, name in PREVIEW_FIELDS
    ]
    return {
        "preview_fields": fields,
        "preview_empty": not any(text for _, text in fields),
    }


def _tabs(profile: EmployerProfile, selected: str) -> list[dict]:
    counts = {
        row["status"]: row["n"]
        for row in profile.jobs.values("status").annotate(n=Count("id"))
    }
    return [
        {
            "value": value,
            "label": label,
            "count": counts.get(value, 0),
            "selected": value == selected,
        }
        for value, label in JOB_TABS
    ]


@never_cache
@employer_required
@require_http_methods(["GET"])
def jobs(request: HttpRequest) -> HttpResponse:
    """Page #35: the employer's jobs, one status tab at a time.

    The Active tab is the default because it is the one an employer with live
    postings opens the page for. An unrecognised `status` value falls back to it
    rather than raising: the tabs are links, so the value is user-visible input,
    not an identifier.

    Each row carries the same three numbers W11 shows: total applicants, the
    applications still in `applied` (the "New" column), and the most recent
    activity -- the job's own `updated_at` or the newest application, whichever
    is later. Activity is an application being created, not a status change;
    a status change writes an audit entry, not a row.
    """
    profile, response = _portal_profile(request)
    if response is not None:
        return response

    selected = request.GET.get("status", Job.Status.ACTIVE)
    if selected not in {value for value, _ in JOB_TABS}:
        selected = Job.Status.ACTIVE

    rows = (
        profile.jobs.filter(status=selected)
        .annotate(
            applicant_count=Count("applications", distinct=True),
            new_count=Count(
                "applications",
                filter=Q(applications__status=Application.Status.APPLIED),
                distinct=True,
            ),
            last_application_at=Max("applications__created_at"),
        )
        .order_by("-created_at")
    )
    for job in rows:
        job.last_activity = max(filter(None, (job.updated_at, job.last_application_at)))

    return render(
        request,
        "employers/jobs.html",
        {"tabs": _tabs(profile, selected), "jobs": rows, "selected": selected},
    )


@never_cache
@employer_required
@require_http_methods(["GET", "POST"])
def job_create(request: HttpRequest) -> HttpResponse:
    """Page #36 (create): a new job is always a draft (REQ-FR-025, §4.3).

    The status is set by the view, not by the form, so the page cannot publish a
    job: activation is the audited `job_activate` action on the overview.
    """
    profile, response = _portal_profile(request)
    if response is not None:
        return response

    job = Job(employer=profile)
    form = JobForm(request.POST or None, instance=job)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            job = form.save(commit=False)
            job.status = Job.Status.DRAFT
            job.save()
            record_job_audit(
                actor=request.user,
                action="job.created",
                job=job,
                details={"title": job.title, "status": job.status},
            )
        messages.success(request, "Draft saved.")
        return redirect("employer_portal:job-edit", job_id=job.pk)

    return render(
        request,
        "employers/job_form.html",
        {
            "form": form,
            "job": None,
            **_preview_context(
                {name: form[name].value() for _, name in PREVIEW_FIELDS}
            ),
        },
    )


@never_cache
@employer_required
@require_http_methods(["GET", "POST"])
def job_edit(request: HttpRequest, job_id) -> HttpResponse:
    """Page #36 (edit): a draft only (REQ-FR-026, §4.3 rule 3).

    A published job redirects to its overview with the same sentence the API
    returns in a 409. The API refuses the write; the page explains why instead
    of rendering a form whose Save would fail.
    """
    profile, response = _portal_profile(request)
    if response is not None:
        return response

    job = _owned_job(request, profile, job_id)
    if job.status != Job.Status.DRAFT:
        messages.error(request, EDIT_DRAFT_ONLY)
        return redirect("employer_portal:job-overview", job_id=job.pk)

    form = JobForm(request.POST or None, instance=job)

    if request.method == "POST" and form.is_valid():
        # `changed_data` is the form's own comparison against the loaded row, so
        # a save that changed nothing writes no audit entry -- the same rule as
        # the API's no-op PATCH.
        changed = sorted(form.changed_data)
        with transaction.atomic():
            job = form.save()
            if changed:
                record_job_audit(
                    actor=request.user,
                    action="job.updated",
                    job=job,
                    details={"changed": changed},
                )
        messages.success(request, "Draft saved.")
        return redirect("employer_portal:job-edit", job_id=job.pk)

    return render(
        request,
        "employers/job_form.html",
        {
            "form": form,
            "job": job,
            **_preview_context(
                {name: form[name].value() for _, name in PREVIEW_FIELDS}
            ),
        },
    )


@never_cache
@employer_required
@require_POST
def job_markdown_preview(request: HttpRequest) -> HttpResponse:
    """Page #36's live preview (design.md 7.22).

    Read-only by construction: it renders the four submitted strings, writes no
    row, writes no audit entry and does not look up a job -- so it works on the
    create page before the first draft exists. `employer_required` plus the same
    onboarding redirect as the form keeps it from becoming an anonymous Markdown
    renderer; `core.markdown` escapes the input either way.
    """
    _profile, response = _portal_profile(request)
    if response is not None:
        return response

    return render(
        request,
        "employers/_job_markdown_preview.html",
        _preview_context(request.POST),
    )


@never_cache
@employer_required
@require_POST
def job_autosave(request: HttpRequest, job_id) -> HttpResponse:
    """Page #36's auto-save: HTMX posts the form, the status region is replaced.

    **200 even when the draft is invalid.** HTMX replaces only a successful
    response by default, so a 400 would leave the status region silently stale --
    the exact failure the a11y note on S11 is about ("autosave status text is
    polite"). The fragment says "Not saved" and names the first error; the manual
    Save button is the path that renders field errors and never loses input.

    A published job is a 409: HTMX keeps the previous status text, and the API's
    rule (only drafts are editable) still holds. No audit entry is written for an
    unsuccessful or unchanged save.
    """
    profile, response = _portal_profile(request)
    if response is not None:
        return response

    job = _owned_job(request, profile, job_id)
    if job.status != Job.Status.DRAFT:
        return HttpResponse(status=409)

    form = JobForm(request.POST, instance=job)
    if not form.is_valid():
        first_error = next(
            (str(error) for errors in form.errors.values() for error in errors),
            "check the form",
        )
        return render(
            request,
            "employers/_autosave_status.html",
            {"saved": False, "detail": f"{AUTOSAVE_NOT_SAVED}: {first_error}"},
        )

    changed = sorted(form.changed_data)
    with transaction.atomic():
        job = form.save()
        if changed:
            record_job_audit(
                actor=request.user,
                action="job.updated",
                job=job,
                details={"changed": changed},
            )

    return render(
        request,
        "employers/_autosave_status.html",
        {"saved": True, "detail": "Draft saved", "saved_at": timezone.localtime()},
    )


@never_cache
@employer_required
@require_http_methods(["GET"])
def job_overview(request: HttpRequest, job_id) -> HttpResponse:
    """Page #37: the funnel, the state actions and the candidates behind them.

    The funnel is a real table (design.md W11's a11y note): a `<th scope="col">`
    per stage and one numeric cell per row, so a screen reader reads "Applied,
    42" rather than a position on a bar.

    W11's share link/embed block and its screening-rules banner are not rendered:
    the public job URL is batch 1.33, and the rules banner needs
    `screening_config` editing, which no batch has built. A link to a 404 is
    worse than no link.
    """
    profile, response = _portal_profile(request)
    if response is not None:
        return response

    job = _owned_job(request, profile, job_id)
    counts = {
        row["status"]: row["n"]
        for row in job.applications.values("status").annotate(n=Count("id"))
    }
    stages = [
        {"label": label, "count": counts.get(status, 0)} for status, label in JOB_FUNNEL
    ]

    return render(
        request,
        "employers/job_overview.html",
        {
            "job": job,
            "stages": stages,
            "applicant_total": sum(counts.values()),
            "can_pause": job.status == Job.Status.ACTIVE,
            "can_close": job.status in (Job.Status.ACTIVE, Job.Status.PAUSED),
            "can_delete": job.status == Job.Status.DRAFT,
        },
    )


def _apply_state_change(
    request: HttpRequest,
    job_id,
    *,
    to_status: str,
    allowed_from: tuple[str, ...],
    audit_action: str,
    conflict_detail: str,
    success_message: str,
) -> HttpResponse:
    """Run one §4.3 action from the portal and redirect back to the overview.

    The decision is `employers.services.change_job_status`, the same function the
    API calls. A conflict shows the API's sentence as an error message and
    leaves the job where it was; a no-op says so without writing an entry.
    """
    profile, response = _portal_profile(request)
    if response is not None:
        return response

    _owned_job(request, profile, job_id)
    try:
        outcome, job = change_job_status(
            job_id=job_id,
            employer=profile,
            to_status=to_status,
            allowed_from=allowed_from,
            audit_action=audit_action,
            actor=request.user,
        )
    except Job.DoesNotExist as exc:  # deleted between the fetch and the lock
        raise Http404 from exc

    if outcome == CONFLICT:
        messages.error(request, conflict_detail)
    elif outcome == NOOP:
        messages.info(request, f"This job is already {to_status}.")
    else:
        messages.success(request, success_message)

    return redirect("employer_portal:job-overview", job_id=job.pk)


@never_cache
@employer_required
@require_POST
def job_activate(request: HttpRequest, job_id) -> HttpResponse:
    """`draft|paused -> active` (REQ-FR-027). Closing is terminal, so a closed
    job cannot come back through this button."""
    return _apply_state_change(
        request,
        job_id,
        to_status=job_status(Job.Status.ACTIVE),
        allowed_from=(job_status(Job.Status.DRAFT), job_status(Job.Status.PAUSED)),
        audit_action="job.activated",
        conflict_detail="A closed job cannot be reactivated. Create a new job instead.",
        success_message="Job activated.",
    )


@never_cache
@employer_required
@require_POST
def job_pause(request: HttpRequest, job_id) -> HttpResponse:
    """`active -> paused`. The row and its applications are untouched."""
    return _apply_state_change(
        request,
        job_id,
        to_status=job_status(Job.Status.PAUSED),
        allowed_from=(job_status(Job.Status.ACTIVE),),
        audit_action="job.paused",
        conflict_detail="Only an active job can be paused.",
        success_message="Job paused.",
    )


@never_cache
@employer_required
@require_POST
def job_close(request: HttpRequest, job_id) -> HttpResponse:
    """`active|paused -> closed`. A draft is deleted, not closed (§4.3 rule 3)."""
    return _apply_state_change(
        request,
        job_id,
        to_status=job_status(Job.Status.CLOSED),
        allowed_from=(job_status(Job.Status.ACTIVE), job_status(Job.Status.PAUSED)),
        audit_action="job.closed",
        conflict_detail="Only an active or paused job can be closed.",
        success_message="Job closed.",
    )


@never_cache
@employer_required
@require_POST
def job_delete(request: HttpRequest, job_id) -> HttpResponse:
    """Delete a draft (§4.3 rule 4). A published job is closed instead.

    The confirm dialog in W11 is client-side; the server refuses regardless,
    because a dialog is not a permission check.
    """
    profile, response = _portal_profile(request)
    if response is not None:
        return response

    _owned_job(request, profile, job_id)
    try:
        outcome, _ = delete_draft_job(
            job_id=job_id, employer=profile, actor=request.user
        )
    except Job.DoesNotExist as exc:
        raise Http404 from exc

    if outcome == CONFLICT:
        messages.error(request, DELETE_DRAFT_ONLY)
        return redirect("employer_portal:job-overview", job_id=job_id)

    messages.success(request, "Draft deleted.")
    return redirect("employer_portal:jobs")
