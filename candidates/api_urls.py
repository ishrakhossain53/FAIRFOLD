"""API v1 routes for the candidates app.

`/api/v1/candidates/me/` and `/api/v1/candidates/resumes/` are plain `path()`
entries before the router: both have fixed paths and no object id, and a router
entry would add a `{pk}` lookup that the contract does not have. The API
app_name stays `candidates` (it is nested under the `api` namespace); the
server-rendered pages use `candidate_portal` so the two URLconfs do not collide
(Django keeps one resolver per namespace name).
"""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from candidates.api_views import (
    CandidateMeView,
    CandidateResumeCompleteView,
    CandidateResumeUploadView,
)

app_name = "candidates"

router = DefaultRouter()

# Registered per viewset as the viewset lands, e.g.:
#   router.register("profile", ProfileViewSet, basename="profile")

urlpatterns = [
    path("me/", CandidateMeView.as_view(), name="me"),
    # Batch 1.19 owns only the upload start. The list/detail routes in §C.12 are
    # batch 1.21, so this path deliberately has no GET yet.
    path("resumes/", CandidateResumeUploadView.as_view(), name="resume-upload"),
    path(
        "resumes/<uuid:pk>/complete/",
        CandidateResumeCompleteView.as_view(),
        name="resume-complete",
    ),
    path("", include(router.urls)),
]
