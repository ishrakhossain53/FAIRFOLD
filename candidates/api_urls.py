"""API v1 routes for the candidates app.

`/api/v1/candidates/me/` and `/api/v1/candidates/resumes/` are plain `path()`
entries before the router: both have fixed paths and no object id, and a router
entry would add a `{pk}` lookup that the contract does not have. The resume
detail route is a `path()` for the same reason -- Complete Doc §C.12 addresses
resumes by `<uuid:pk>` and the router would register a full CRUD viewset whose
`PUT`/`PATCH`/`DELETE` verbs the contract does not declare. The API app_name
stays `candidates` (it is nested under the `api` namespace); the server-rendered
pages use `candidate_portal` so the two URLconfs do not collide (Django keeps one
resolver per namespace name).
"""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from candidates.api_views import (
    CandidateApplicationDetailView,
    CandidateApplicationListView,
    CandidateMeView,
    CandidateResumeCompleteView,
    CandidateResumeDetailView,
    CandidateResumeListView,
)

app_name = "candidates"

router = DefaultRouter()

# Registered per viewset as the viewset lands, e.g.:
#   router.register("profile", ProfileViewSet, basename="profile")

urlpatterns = [
    path("me/", CandidateMeView.as_view(), name="me"),
    # Batch 1.19 owns the upload start, batch 1.21 the list; both live on this
    # path because §C.12 puts `GET` and `POST` on the same resource.
    path("resumes/", CandidateResumeListView.as_view(), name="resume-list"),
    path(
        "resumes/<uuid:pk>/complete/",
        CandidateResumeCompleteView.as_view(),
        name="resume-complete",
    ),
    # Declared after `complete/` so the literal suffix is matched before the bare
    # detail pattern; `<uuid:pk>` would not match `.../complete/` anyway, but the
    # order documents which route owns the nested path.
    path(
        "resumes/<uuid:pk>/",
        CandidateResumeDetailView.as_view(),
        name="resume-detail",
    ),
    # Candidate application history (REQ-FR-023, batch 1.38). §C.12 puts both
    # reads under `candidates/applications/`; the model lives in `matching`
    # because Complete Doc §C.4 assigns `applications` there, and the view lives
    # here because the owner is always `request.user`.
    path(
        "applications/",
        CandidateApplicationListView.as_view(),
        name="application-list",
    ),
    path(
        "applications/<uuid:pk>/",
        CandidateApplicationDetailView.as_view(),
        name="application-detail",
    ),
    path("", include(router.urls)),
]
