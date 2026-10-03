"""API error handling.

DRF's default handler returns ``{"detail": "..."}``. That is a poor contract for
a frontend that has to render a field-level form error, and it leaks internal
exception text on an unhandled 500 -- which in this product means it can leak
candidate PII or an AI provider's raw response into a response body.

This handler therefore enforces two rules:

- **A 500 never carries the exception message.** The detail becomes a generic
  string plus the request ID, and the traceback goes to Sentry. The user is given
  the ID because it is the only thing that lets support find the traceback.
- **A validation error is keyed by field**, so the template can attach each
  message to the input that caused it instead of printing a blob at the top.
"""

from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

# Returned to the client instead of the real message. Wording is deliberately
# free of internal nouns: "configuration" or "database" tells an attacker what
# is running behind the app.
GENERIC_500 = "Something went wrong on our side. Please quote the reference code."


def api_exception_handler(exc, context):
    """Wrap DRF's handler, then replace any unhandled 500 body."""
    response = drf_exception_handler(exc, context)

    if response is None:
        # Unhandled. DRF returns None for anything it does not recognise, which
        # Django would turn into a 500 whose body may contain the exception text.
        request = context.get("request")
        request_id = getattr(request, "request_id", None)
        logger.exception("Unhandled API exception", extra={"request_id": request_id})
        return Response(
            {"detail": GENERIC_500, "reference": request_id or ""},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, Http404):
        # A missing row and a row the user may not see must be indistinguishable,
        # or the 403/404 difference becomes an enumeration oracle for candidate
        # IDs. See Complete Doc §C.12 on `jobs/public/`.
        return Response(
            {"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND
        )

    if isinstance(exc, PermissionDenied):
        return Response(
            {"detail": "You do not have permission to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if isinstance(response.data, dict) and "detail" in response.data:
        response.data["reference"] = getattr(
            context.get("request"), "request_id", ""
        )

    return response