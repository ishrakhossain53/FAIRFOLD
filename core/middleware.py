"""Request-scoped correlation IDs.

Every request gets an ID, and the same ID appears in the web log line, in the
Celery task that request schedules, and in the AI provider call. Without it, a
screening failure is three log lines in three files with nothing to join them on.

A ``contextvars.ContextVar`` is used rather than an attribute on the request so
that :class:`core.logging.RequestIDFilter` and Celery tasks can read the current
value without holding the request object, and so the value is copied correctly
into a task's context instead of leaking between concurrent requests.

The ID is validated before being accepted from an upstream proxy. It is echoed
in an ``X-Request-ID`` response header and sent through an HTMX header, so an
unvalidated one is attacker-controlled text landing in every log line for the
request.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"

_request_id: ContextVar[str] = ContextVar("fairfold_request_id", default="")


def current_request_id() -> str:
    """Return the request ID in scope, or an empty string outside a request."""
    return _request_id.get()


def set_request_id(value: str) -> None:
    """Set the request ID for the current context.

    Public because a Celery task inherits the value from the caller and may need
    to reset it: a worker process is reused across tasks, and a stale ID from the
    previous task would make two unrelated failures look like one.
    """
    _request_id.set(value)


class RequestIDMiddleware:
    """Attach a request ID to every request and response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = self._resolve_id(request)
        request.request_id = request_id
        set_request_id(request_id)

        try:
            response = self.get_response(request)
        finally:
            # Reset even on an exception, so the next request on this thread does
            # not inherit this request's ID.
            set_request_id("")

        # Echoed so a user can quote it in a support request without us having to
        # guess which of their requests failed.
        response["X-Request-ID"] = request_id
        return response

    @staticmethod
    def _resolve_id(request: HttpRequest) -> str:
        supplied = request.META.get(REQUEST_ID_HEADER, "")
        if supplied and 8 <= len(supplied) <= 64 and supplied.isalnum():
            return supplied
        return uuid.uuid4().hex[:16]