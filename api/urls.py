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
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView

app_name = "api"


class ApiRootSerializer(serializers.Serializer):
    """The shape of the API index response.

    Exists so the endpoint appears in the OpenAPI schema. drf-spectacular cannot
    infer a body for a bare `APIView` and omits the view entirely
    (spectacular.W002) -- so without this the endpoint is in no client
    generation and no contract test, which is the same failure shape as the
    absent package-lock.json: a thing invisible because the tool that should
    have reported it had nothing to report.

    `domains` is a `DictField` rather than fixed fields because its keys are the
    mounted app names. Fixed fields would need editing every time an app is
    mounted, and would then quietly under-report instead of failing.
    """

    version = serializers.CharField()
    documentation = serializers.CharField()
    domains = serializers.DictField(child=serializers.CharField())


# never_cache is applied to `dispatch`, not to `get`. On a class-based view a
# bare @never_cache on the method wraps the unbound function, so DRF's call
# `handler(request, ...)` passes the view instance where the decorator expects
# the HttpRequest and every request to /api/v1/ raises TypeError ("never_cache
# didn't receive an HttpRequest"). Decorating at the class also covers the
# `router.APIRootView` use below, which a URL-level decorator would miss.
@method_decorator(never_cache, name="dispatch")
class ApiRootView(APIView):
    """Unauthenticated API index listing the mounted domains.

    Public on purpose: an integrator needs to discover what exists without
    holding a key. It lists **URL prefixes only** -- no schema, no model names,
    no field-level detail -- so it discloses the shape of the API without
    describing the data model.
    """

    permission_classes: list = []
    authentication_classes: list = []

    @extend_schema(
        responses={200: ApiRootSerializer},
        summary="API index",
        description=(
            "Public. Lists the mounted domain prefixes only -- no schema, no "
            "model names, no field-level detail."
        ),
    )
    def get(self, request) -> Response:
        return Response(
            {
                "version": "v1",
                "documentation": "/api/docs/",
                "domains": {
                    # §C.12 puts the auth routes under `auth/`, not under the
                    # accounts app's own prefix; both are owned by accounts.
                    "auth": "/api/v1/auth/",
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
    # §C.12 puts registration and email verification under `/api/v1/auth/`.
    # `accounts.api_urls` stays mounted at `accounts/` for the profile routes
    # that land later; the two prefixes must not share one module.
    path("auth/", include("accounts.auth_urls")),
    # Mounted app by app as each app's viewsets land. An empty include() mounts a
    # prefix with nothing beneath it, which 404s every URL the frontend calls.
    path("accounts/", include("accounts.api_urls")),
    path("candidates/", include("candidates.api_urls")),
    path("employers/", include("employers.api_urls")),
    path("jobs/", include("employers.job_urls")),
    path("assessments/", include("assessments.api_urls")),
    path("interviews/", include("interviews.api_urls")),
    path("notifications/", include("notifications.api_urls")),
]
