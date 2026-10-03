"""Error handlers for `handler404` / `handler403` / `handler500`.

These render a template rather than letting Django's default page appear,
because Django's debug error page leaks the URL pattern, the settings module
name and a traceback with local variable values -- candidate PII among them.

Every handler must **not** echo the requested path into the response body without
escaping. A 404 for a URL containing ``<script>`` is a reflected-XSS vector if
the path is rendered unescaped, and the path is attacker-controlled by
definition.
"""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def _render(request: HttpRequest, template: str, status: int) -> HttpResponse:
    """Render an error page.

    `path` is passed through Django's autoescaping in the template. The 500
    handler passes no request-derived detail at all.
    """
    return render(request, template, {"path": request.path}, status=status)


def error_404(request: HttpRequest, exception=None) -> HttpResponse:
    return _render(request, "errors/404.html", 404)


def error_403(request: HttpRequest, exception=None) -> HttpResponse:
    return _render(request, "errors/403.html", 403)


def error_500(request: HttpRequest) -> HttpResponse:
    """Server error.

    `request` is deliberately not passed to the template. At this point the
    exception may have included a resume filename, an email address or an AI
    provider response body in its local variables, and the page must not become a
    mirror of it.
    """
    request_id = getattr(request, "request_id", "")
    logger.error("Unhandled server error", extra={"request_id": request_id})
    return render(request, "errors/500.html", {"reference": request_id}, status=500)
