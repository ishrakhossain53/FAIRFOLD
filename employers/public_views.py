"""Public job board pages #4 and #5 (REQ-FR-042, design.md S04/S05).

Both pages are anonymous. They render the same `public_job_queryset()` as
`GET /api/v1/jobs/public/`, so the page and the API cannot disagree about what
"active", "newest first" or any filter means.

**The template never sees `job.employer`.** The view resolves the one allowed
employer value through `public_employer_name()` and passes it as
`card.employer_name` / `employer_name`. A template that could write
`job.employer.company_name` would be one edit away from a leak; this shape makes
the hidden name unavailable in the first place.

**Filtering is a normal GET.** The filter state lives in the URL, so Back,
refresh and a pasted link all restore it without JavaScript. design.md S04
mentions `hx-push-url`; a full GET already has that property, and a server round
trip is what a board of this size needs.

**Errors are a page state, not a traceback.** An unknown level or a non-boolean
`remote` re-renders the board at 400 with a list of the offending fields, using
the same serializer the API uses. The alternative -- silently dropping the
parameter -- would show a board that does not match its URL.
"""

from __future__ import annotations

from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from candidates.models import CandidateProfile
from employers.serializers import JobPublicFilterSerializer, public_employer_name
from employers.services import public_job_queryset
from matching.models import Application, Job

#: Page #4's cards are denser than the API's default 20, but 20 is what the
#: existing `StandardPagination` uses and what a 360px viewport can scroll
#: without losing the filter controls. The API's 50-row cap is separate.
PAGE_SIZE = 20

FILTER_LABELS = {
    "q": "Search",
    "location": "Location",
    "remote": "Remote",
    "experience_level": "Experience level",
}


def _filter_values(request: HttpRequest) -> dict[str, str]:
    """The raw query values, for repopulating the form after an error.

    Deliberately raw rather than `validated_data`: a rejected value must stay in
    the input so the user can correct it, not disappear and leave an error about
    something no longer visible.
    """
    return {
        "q": request.GET.get("q", ""),
        "location": request.GET.get("location", ""),
        "remote": request.GET.get("remote", ""),
        "experience_level": request.GET.get("experience_level", ""),
    }


def _remove_filter_url(request: HttpRequest, *keys: str) -> str:
    """The current board URL with one filter removed.

    `page` goes too: after a filter changes, page 4 of the old result set is not
    page 4 of the new one, and keeping it would show an empty page.
    """
    params = request.GET.copy()
    for key in (*keys, "page"):
        params.pop(key, None)
    query = params.urlencode()
    target = reverse("job_board:list")
    return f"{target}?{query}" if query else target


def _active_filter_chips(request: HttpRequest) -> list[dict[str, str]]:
    chips: list[dict[str, str]] = []

    query = request.GET.get("q", "").strip()
    if query:
        chips.append(
            {
                "label": f'Search: "{query}"',
                "remove_url": _remove_filter_url(request, "q"),
            }
        )

    location = request.GET.get("location", "").strip()
    if location:
        chips.append(
            {
                "label": f"Location: {location}",
                "remove_url": _remove_filter_url(request, "location"),
            }
        )

    if request.GET.get("remote") == "true":
        chips.append(
            {"label": "Remote", "remove_url": _remove_filter_url(request, "remote")}
        )

    level = request.GET.get("experience_level", "")
    if level:
        label = dict(Job.ExperienceLevel.choices).get(level, level)
        chips.append(
            {
                "label": f"Level: {label}",
                "remove_url": _remove_filter_url(request, "experience_level"),
            }
        )

    return chips


def _querystring_without_page(request: HttpRequest) -> str:
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


def _error_messages(errors) -> list[str]:
    messages: list[str] = []
    for field, field_errors in errors.items():
        label = FILTER_LABELS.get(field, field)
        for error in field_errors:
            messages.append(f"{label}: {error}")
    return messages


def _cards(jobs) -> list[dict[str, object]]:
    """Flatten each job to the two values the public card may show.

    `skills` is sorted here rather than in the template so the order is
    deterministic. The queryset prefetches the join rows, so this is not a query
    per card.
    """
    return [
        {
            "job": job,
            "employer_name": public_employer_name(job.employer),
            "skills": sorted(
                link.skill.canonical_name for link in job.job_skills.all()
            ),
        }
        for job in jobs
    ]


def job_list(request: HttpRequest) -> HttpResponse:
    """Page #4: search, filters, newest first, paginated."""
    filters = JobPublicFilterSerializer(data=request.GET)
    filter_errors: list[str] = []

    if filters.is_valid():
        queryset = public_job_queryset(filters.validated_data)
        paginator = Paginator(queryset, PAGE_SIZE)
        # `get_page` clamps an out-of-range or non-numeric page instead of
        # letting a hand-edited URL 404 the whole board. The API can be strict
        # because a client sends the parameter; a browser link is not a client.
        page_obj = paginator.get_page(request.GET.get("page"))
        cards = _cards(page_obj)
        total = paginator.count
        page_range = list(page_obj.paginator.get_elided_page_range(page_obj.number))
        status = 200
    else:
        filter_errors = _error_messages(filters.errors)
        page_obj = None
        cards = []
        total = 0
        page_range = []
        status = 400

    context = {
        "page_obj": page_obj,
        "page_range": page_range,
        "cards": cards,
        "total": total,
        "filter_errors": filter_errors,
        "filter_chips": _active_filter_chips(request),
        "form_values": _filter_values(request),
        "querystring": _querystring_without_page(request),
        "level_choices": Job.ExperienceLevel.choices,
    }
    return render(request, "jobs/list.html", context, status=status)


def job_detail(request: HttpRequest, job_id) -> HttpResponse:
    """Page #5: one active job. A draft, paused or closed job is a 404.

    **The apply state is resolved here, not in the template.** The template gets
    `application` (the caller's own row, or `None`) and `candidate_has_profile`,
    so it cannot accidentally query the candidate table or show an Apply button
    to an account that cannot use it. An anonymous visitor triggers neither
    query: the page must stay free of candidate lookups for guests.
    """
    job = get_object_or_404(public_job_queryset({}), pk=job_id)

    application = None
    candidate_has_profile = False
    if request.user.is_authenticated and request.user.is_candidate:
        profile = CandidateProfile.objects.filter(user=request.user).first()
        candidate_has_profile = profile is not None
        if profile is not None:
            application = (
                Application.objects.filter(job=job, candidate=profile)
                .only("created_at")
                .first()
            )

    context = {
        "job": job,
        "employer_name": public_employer_name(job.employer),
        "skills": list(job.job_skills.all()),
        "application": application,
        "candidate_has_profile": candidate_has_profile,
    }
    return render(request, "jobs/detail.html", context)
