"""API v1 routes for the candidates app.

Empty on purpose until this app's endpoints land. `config/urls.py` and
`api/urls.py` include this module, so it must exist as an importable module from
the first commit -- a missing module is a boot-time `ImportError` that takes down
every URL in the project, not just this app's.

The routers below are declared with `register()` calls added per viewset. An
unregistered router renders a browsable API listing nothing, which is worse than
404 because it looks wired up.
"""

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

app_name = "candidates"

router = DefaultRouter()

# Registered per viewset as the viewset lands, e.g.:
#   router.register("profile", ProfileViewSet, basename="profile")

urlpatterns = [
    path("", include(router.urls)),
]
