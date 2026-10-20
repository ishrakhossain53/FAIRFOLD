"""API v1 routes for the candidates app.

The profile route (`GET`/`PATCH /api/v1/candidates/me/`) is a plain `path()`
before the router: it has a fixed path and no object id, and a router entry
would add a `{pk}` lookup that the contract does not have. The API app_name
stays `candidates` (it is nested under the `api` namespace); the server-rendered
pages use `candidate_portal` so the two URLconfs do not collide (Django keeps
one resolver per namespace name).
"""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from candidates.api_views import CandidateMeView

app_name = "candidates"

router = DefaultRouter()

# Registered per viewset as the viewset lands, e.g.:
#   router.register("profile", ProfileViewSet, basename="profile")

urlpatterns = [
    path("me/", CandidateMeView.as_view(), name="me"),
    path("", include(router.urls)),
]
