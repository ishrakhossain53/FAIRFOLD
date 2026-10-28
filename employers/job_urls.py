"""API v1 routes for jobs (REQ-FR-025-027, Complete Doc §C.12).

Mounted at `/api/v1/jobs/`, not under `/api/v1/employers/`: §C.12 puts the job
resource at that prefix, and the public board reads `/api/v1/jobs/public/`
(batch 1.31). The ownership rule is not in the path -- it is `request.user`'s
profile -- so one prefix serves both surfaces without leaking another employer's
row.

`app_name = "jobs"` keeps `reverse()` distinct from `employer_portal` (the pages)
and `employers` (the company-profile API). The collection answers `POST` and the
detail route answers `GET`/`PATCH`/`DELETE`; the collection's `GET` (the jobs
list, page #35) is a later batch, and an absent row is a 405 rather than a stub
that returns an empty list. The three state actions are separate paths because
Arch Doc §4.3 makes each one an audited transition, not a field update. The
candidate-facing `apply/` action is here too: it addresses a job, and the rule it
triggers lives in `matching.services.apply_to_job` (REQ-FR-022, batch 1.36).

`<job_id>/applications/` (batch 1.40) is the employer's inbox for one posting: a
read path under the job, because the list is always scoped to a posting, while
the per-application status changes are action endpoints on their own resource
(batch 1.41).
"""

from __future__ import annotations

from django.urls import path

from employers.api_views import (
    JobActivateView,
    JobApplicationListView,
    JobApplyView,
    JobCloseView,
    JobCreateView,
    JobDetailView,
    JobPauseView,
    JobPublicDetailView,
    JobPublicListView,
)

app_name = "jobs"

urlpatterns = [
    path("", JobCreateView.as_view(), name="job-create"),
    # Public routes before the private detail route: `public/` is a literal
    # segment and `uuid` cannot match it, but keeping the public pair first
    # makes the order explicit for anyone adding a route later.
    path("public/", JobPublicListView.as_view(), name="job-public-list"),
    path(
        "public/<uuid:job_id>/",
        JobPublicDetailView.as_view(),
        name="job-public-detail",
    ),
    path("<uuid:job_id>/", JobDetailView.as_view(), name="job-detail"),
    # The employer's inbox for one job (REQ-FR-029, batch 1.40). A read path on
    # the job, not an `applications/{id}/` resource: the list is always scoped to
    # a posting, and status changes are their own action endpoints (batch 1.41).
    path(
        "<uuid:job_id>/applications/",
        JobApplicationListView.as_view(),
        name="job-applications",
    ),
    # Candidate action on a job (REQ-FR-022, batch 1.36). Declared before the
    # state actions so the candidate-facing verb sits with the public routes;
    # `path()` anchors each pattern, so the order is documentation, not
    # disambiguation.
    path("<uuid:job_id>/apply/", JobApplyView.as_view(), name="job-apply"),
    path("<uuid:job_id>/activate/", JobActivateView.as_view(), name="job-activate"),
    path("<uuid:job_id>/pause/", JobPauseView.as_view(), name="job-pause"),
    path("<uuid:job_id>/close/", JobCloseView.as_view(), name="job-close"),
]
