"""API v1 routes for jobs (REQ-FR-025-027, Complete Doc §C.12).

Mounted at `/api/v1/jobs/`, not under `/api/v1/employers/`: §C.12 puts the job
resource at that prefix, and the public board (batch 1.31) will read the same
collection. The ownership rule is not in the path -- it is `request.user`'s
profile -- so one prefix serves both surfaces without leaking another employer's
row.

`app_name = "jobs"` keeps `reverse()` distinct from `employer_portal` (the pages)
and `employers` (the company-profile API). The collection answers `POST` and the
detail route answers `GET`/`PATCH`/`DELETE`; the collection's `GET` (the jobs
list, page #35) is a later batch, and an absent row is a 405 rather than a stub
that returns an empty list. The three state actions are separate paths because
Arch Doc §4.3 makes each one an audited transition, not a field update.
"""

from __future__ import annotations

from django.urls import path

from employers.api_views import (
    JobActivateView,
    JobCloseView,
    JobCreateView,
    JobDetailView,
    JobPauseView,
)

app_name = "jobs"

urlpatterns = [
    path("", JobCreateView.as_view(), name="job-create"),
    path("<uuid:job_id>/", JobDetailView.as_view(), name="job-detail"),
    path("<uuid:job_id>/activate/", JobActivateView.as_view(), name="job-activate"),
    path("<uuid:job_id>/pause/", JobPauseView.as_view(), name="job-pause"),
    path("<uuid:job_id>/close/", JobCloseView.as_view(), name="job-close"),
]
