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
]
