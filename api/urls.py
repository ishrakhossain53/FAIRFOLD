"""API v1 routes.

Each app registers its own router under `api/v1/<domain>/`, so an endpoint's
URL states which app owns it and adding an endpoint never requires editing this
file beyond one `include`.

The path carries the version. A version in a header would be invisible in a
support ticket, in a browser bookmark, and in a log line -- and the Complete Doc
lists versioning as a requirement, so the version has to be somewhere a human can
read.
"""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

app_name = "api"


class ApiRootView(APIView):
    """Unauthenticated API index listing the mounted domains.

    Public on purpose: an integrator needs to discover what exists without
    holding a key. It lists **URL prefixes only** -- no schema, no model names,
    no field-level detail -- so it discloses the shape of the API without
    describing the data model.
    """

    permission_classes: list = []
    authentication_classes: list = []

    @never_cache
    def get(self, request) -> Response:
        return Response(
            {
                "version": "v1",
                "documentation": "/api/docs/",
                "domains": {
                    "accounts": "/api/v1/accounts/",
                    "candidates": "/api/v1/candidates/",
                    "employers": "/api/v1/employers/",
                    "jobs": "/api/v1/jobs/",
                    "assessments": "/api/v1/assessments/",
                    "interviews": "/api/v1/interviews/",
                    "gdpr": "/api/v1/gdpr/",
                    "notifications": "/api/v1/notifications/",
                },
            }
        )


router = DefaultRouter()
# The root view replaces the router's own API-root listing, which would render a
# DRF-browsable HTML page at /api/v1/ in production.
router.APIRootView = ApiRootView

urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
    # Mounted app by app as each app's viewsets land. An empty include() mounts a
    # prefix with nothing beneath it, which 404s every URL the frontend calls.
    path("accounts/", include("accounts.api_urls")),
    path("candidates/", include("candidates.api_urls")),
    path("employers/", include("employers.api_urls")),
    path("assessments/", include("assessments.api_urls")),
    path("interviews/", include("interviews.api_urls")),
    path("notifications/", include("notifications.api_urls")),
]