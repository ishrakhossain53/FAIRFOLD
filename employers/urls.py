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
]
