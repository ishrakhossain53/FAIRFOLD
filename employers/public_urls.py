"""Public job-board pages (design.md pages #4 and #5, batch 1.33).

Mounted at `/jobs/` by `config.urls`. The namespace is `job_board`, separate
from `employer_portal`, because these pages are anonymous and must never inherit
an employer-only decorator by proximity.

The id is a UUID, not the `/jobs/backend` slug design.md S05 sketches for the
share link: `jobs` has no slug column (Arch Doc §5.1), and inventing one would
be a schema change outside this batch. A UUID is stable across edits and is the
same id the public API returns.
"""

from __future__ import annotations

from django.urls import path

from employers import public_views

app_name = "job_board"

urlpatterns = [
    path("", public_views.job_list, name="list"),
    path("<uuid:job_id>/", public_views.job_detail, name="detail"),
]
