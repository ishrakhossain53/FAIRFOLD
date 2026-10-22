"""API v1 routes for the employers app.

`/api/v1/employers/me/` is a plain `path()` before the router: it has a fixed
path and no object id, and a router entry would add a `{pk}` lookup that the
contract does not have. Complete Doc §C.12 lists exactly `GET` and `PATCH` on
this resource, so a viewset would also expose verbs the contract does not
declare.

The router stays mounted for the team, job and billing viewsets that land in
later batches. The API `app_name` is `employers`; the server-rendered pages use
`employer_portal` so the two URLconfs do not collide (Django keeps one resolver
per namespace name).
"""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from employers.api_views import EmployerMeView

app_name = "employers"

router = DefaultRouter()

# Registered per viewset as the viewset lands, e.g.:
#   router.register("team", TeamViewSet, basename="team")

urlpatterns = [
    path("me/", EmployerMeView.as_view(), name="me"),
    path("", include(router.urls)),
]
