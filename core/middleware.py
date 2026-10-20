"""Request-scoped correlation IDs and the application-level CSP.

Every request gets an ID, and the same ID appears in the web log line, in the
Celery task that request schedules, and in the AI provider call. Without it, a
screening failure is three log lines in three files with nothing to join them on.

The second middleware here sets `Content-Security-Policy`. Django 5.2 has no CSP
support, and the canonical docs placed the header at the Nginx edge only, which
left a deployment without that proxy with no CSP at all. Keeping it in Django
makes the header testable by the same suite as the rest of REQ-SEC-010.

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

from django.conf import settings
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


class ContentSecurityPolicyMiddleware:
    """Attach `settings.CONTENT_SECURITY_POLICY` to every response.

    Django 5.2 has no CSP support, and the policy was documented only at the
    Nginx edge (Arch Doc §6.3). A deployment without that proxy therefore shipped
    no CSP at all, and `test_security_headers.py` had nothing to assert. Setting
    it here makes the header part of the application's tested surface; the edge
    may still add its own copy, but the browser intersects multiple CSP headers,
    so the strictest one wins.

    A response that already carries a policy is left alone. Two headers from two
    layers that disagree are enforced as their intersection, and the effective
    policy then cannot be read from either file.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        policy = getattr(settings, "CONTENT_SECURITY_POLICY", "")
        if policy and "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = policy
        return response
