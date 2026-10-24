"""Employer portal routes (design.md page #33).

Mounted at `/employer/` by `config.urls`. The namespace is `employer_portal`,
not `employers`: `employers.api_urls` already owns the `employers` namespace
under `/api/v1/employers/`, and Django's resolver keeps one entry per namespace
name. Giving the template pages their own namespace keeps `reverse()`
unambiguous for both the API and the HTML.

`company/edit/` is a fixed path rather than `/company/<uuid>/edit/`. The target
is always `request.user`, and the authorization matrix refuses to guess a
sample value for a parameterised route, so a fixed path keeps the edit route
covered by one matrix row.
"""

from __future__ import annotations

from django.urls import path

from employers import views

app_name = "employer_portal"

urlpatterns = [
    path("onboarding/", views.onboarding, name="onboarding"),
    path("company/", views.company, name="company"),
    path("company/edit/", views.company_edit, name="company-edit"),
    # Pages #35-#37 (REQ-FR-025-027, batch 1.30). The job id is in the path
    # because a page is about one row; ownership is still decided by
    # `request.user`'s profile inside the view, so the id never grants access.
    # `new/` comes before the UUID route for readability; the converter would
    # reject it either way.
    path("jobs/", views.jobs, name="jobs"),
    path("jobs/new/", views.job_create, name="job-create"),
    path("jobs/<uuid:job_id>/", views.job_overview, name="job-overview"),
    path("jobs/<uuid:job_id>/edit/", views.job_edit, name="job-edit"),
    path("jobs/<uuid:job_id>/autosave/", views.job_autosave, name="job-autosave"),
    path("jobs/<uuid:job_id>/activate/", views.job_activate, name="job-activate"),
    path("jobs/<uuid:job_id>/pause/", views.job_pause, name="job-pause"),
    path("jobs/<uuid:job_id>/close/", views.job_close, name="job-close"),
    path("jobs/<uuid:job_id>/delete/", views.job_delete, name="job-delete"),
    # design.md page #41 (S13). The path is keyed on the application, not the
    # candidate: the candidate's identifier must never appear in an employer
    # surface (REQ-FR-029).
    path(
        "applications/<uuid:application_id>/",
        views.application_rationale,
        name="application-rationale",
    ),
]
