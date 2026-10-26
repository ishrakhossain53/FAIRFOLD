"""Candidate portal routes (design.md pages #14 and #16).

Mounted at `/candidate/` by `config.urls`. The namespace is `candidate_portal`,
not `candidates`: `candidates.api_urls` already owns the `candidates` namespace
under `/api/v1/candidates/`, and Django's resolver keeps one entry per namespace
name. Giving the template pages their own namespace keeps `reverse()` unambiguous
for both the API and the HTML.

`profile/edit/` is one route with the section in the POST body, not a
`<str:section>` segment. The authorization matrix refuses to guess a sample value
for a parameterised route, and a fixed path keeps this page covered by one
matrix row.
"""

from __future__ import annotations

from django.urls import path

from candidates import views

app_name = "candidate_portal"

urlpatterns = [
    path("onboarding/", views.onboarding, name="onboarding"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile-edit"),
    path("resumes/", views.resumes, name="resumes"),
    # One fixed path for the confirmation page and the POST that performs it.
    # `/resumes/<uuid:pk>/delete/` would be a parameterised page route, and the
    # authorization matrix refuses to guess a sample value for one.
    path("resumes/delete/", views.resume_delete, name="resume-delete"),
    # Pages #28 and #29 (REQ-FR-023, batch 1.39). The detail id is in the path
    # because the page is about one application; ownership is still decided by
    # `request.user` inside the view, so the id never grants access.
    path("applications/", views.applications, name="applications"),
    path(
        "applications/<uuid:application_id>/",
        views.application_detail,
        name="application-detail",
    ),
]
