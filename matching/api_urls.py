"""API v1 routes for application decisions (REQ-FR-052, batch 1.41).

Mounted at `/api/v1/applications/`, the prefix Complete Doc §C.12 uses for the
screening-integrity actions. Two named verbs, no collection route: the list of
applications belongs to a job (`/api/v1/jobs/{id}/applications/`, batch 1.40),
and there is no documented `GET /api/v1/applications/` or `PATCH` on one
application. An absent verb is a `405`, not a stub that pretends to exist.

`<uuid:application_id>` rather than `<uuid:pk>` so the view signature reads the
same as the URL an error message would quote, and so the authz matrix sample
names the same thing.
"""

from __future__ import annotations

from django.urls import path

from matching.api_views import ApplicationRejectView, ApplicationShortlistView

app_name = "applications"

urlpatterns = [
    path(
        "<uuid:application_id>/shortlist/",
        ApplicationShortlistView.as_view(),
        name="application-shortlist",
    ),
    path(
        "<uuid:application_id>/reject/",
        ApplicationRejectView.as_view(),
        name="application-reject",
    ),
]
