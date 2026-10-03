"""Root-level routes: health check, legal pages, and the unauthenticated landing page.

`/health/` is what the CI deploy jobs curl (Arch Doc §6.5). It deliberately
checks only that the process can serve a request. Making it verify the database
would mean a brief database blip fails a deploy and rolls back a healthy release.
The database has its own readiness check in `docker-compose.yml`.
"""

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import path
from django.views.decorators.cache import never_cache


@never_cache
def health(request: HttpRequest) -> HttpResponse:
    """Liveness probe. No database, no cache, no auth."""
    return JsonResponse({"status": "ok"})


@never_cache
def ready(request: HttpRequest) -> JsonResponse:
    """Readiness probe: reports dependency status without failing the deploy.

    Returns 200 even when a dependency is down, with the detail in the body. A
    probe that 503s takes the instance out of the load balancer, which is the
    right behaviour for a *liveness* check and the wrong one for readiness during
    a rolling restart.
    """
    from django.db import connection

    checks: dict[str, str] = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"

    try:
        from django.core.cache import cache

        cache.set("healthcheck", "1", timeout=5)
        checks["cache"] = "ok" if cache.get("healthcheck") == "1" else "error: no round-trip"
    except Exception as exc:
        checks["cache"] = f"error: {type(exc).__name__}"

    return JsonResponse({"status": "ok", "checks": checks})


app_name = "core"

urlpatterns = [
    path("health/", health, name="health"),
    path("health/ready/", ready, name="health-ready"),
]