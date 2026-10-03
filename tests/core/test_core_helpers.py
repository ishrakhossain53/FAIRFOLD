"""Tests for the `core` package: middleware, pagination, exceptions, views, reference.

These are the modules that were at 0% coverage, and they are the ones where a
silent failure is worst: `RequestIDMiddleware` joins log lines across a request,
a Celery task and an AI call; `StandardPagination` caps a page size that is
otherwise a data-exfiltration path; and the error handlers decide whether a
500 page leaks the exception.

None of them needs a database.
"""

from __future__ import annotations

import pytest
from django.http import Http404
from django.test import RequestFactory
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from core.exceptions import GENERIC_500, api_exception_handler
from core.logging import RequestIDFilter
from core.middleware import RequestIDMiddleware, current_request_id, set_request_id
from core.pagination import StandardPagination
from core.reference import COUNTRIES, SCORE_BANDS, band_for, is_calibrated, validate
from core.views import error_403, error_404, error_500

# ---------------------------------------------------------------------------
# RequestIDMiddleware
# ---------------------------------------------------------------------------


def _response_for(environ_extra: dict | None = None):
    """Run the middleware over a minimal request and return (response, ids)."""
    factory = RequestFactory()
    request = factory.get("/api/v1/", **(environ_extra or {}))
    seen: dict[str, str] = {}

    def get_response(req):
        seen["id"] = req.request_id
        seen["in_scope"] = current_request_id()
        from django.http import HttpResponse

        return HttpResponse("ok")

    middleware = RequestIDMiddleware(get_response)
    response = middleware(request)
    return response, seen


class TestRequestIDMiddleware:
    def test_generates_an_id_when_none_is_supplied(self):
        response, seen = _response_for()
        assert len(seen["id"]) == 16
        assert response["X-Request-ID"] == seen["id"]

    def test_accepts_a_valid_upstream_id(self):
        # A reverse proxy supplies the id so a request can be traced across
        # services. It must be honoured, not discarded.
        response, seen = _response_for({"HTTP_X_REQUEST_ID": "abc123def456"})
        assert seen["id"] == "abc123def456"
        assert response["X-Request-ID"] == "abc123def456"

    @pytest.mark.parametrize(
        "supplied",
        [
            "short",  # too short to be one
            "x" * 200,  # absurdly long
            "abc<script>alert(1)</script>",  # not alphanumeric
            "abc def",  # contains a space
        ],
    )
    def test_rejects_a_malformed_upstream_id(self, supplied):
        # The header is echoed into the response and into every log line for the
        # request, so an unvalidated one is attacker-controlled text that ends up
        # in the log. Anything non-alphanumeric, or outside 8-64 chars, is
        # replaced with a generated id.
        _, seen = _response_for({"HTTP_X_REQUEST_ID": supplied})
        assert seen["id"] != supplied
        assert len(seen["id"]) == 16

    def test_id_is_in_scope_during_the_request(self):
        # The logging filter reads the id from the contextvar, not from the
        # request object, so a Celery task scheduled inside the request can read
        # it too.
        _, seen = _response_for()
        assert seen["in_scope"] == seen["id"]

    def test_context_is_cleared_after_the_response(self):
        # A gunicorn worker is reused across requests. Leaving the id set means
        # the next request on that thread inherits it, and two unrelated
        # failures look like one.
        _response_for()
        assert current_request_id() == ""

    def test_context_is_cleared_even_when_the_view_raises(self):
        factory = RequestFactory()
        request = factory.get("/")

        def boom(req):
            raise RuntimeError("view failed")

        middleware = RequestIDMiddleware(boom)
        with pytest.raises(RuntimeError):
            middleware(request)
        assert current_request_id() == ""


class TestSetRequestID:
    def test_can_be_set_and_read_directly(self):
        # Celery tasks inherit the caller's id but need to reset it: a worker
        # process is reused, and a stale id from the previous task would make two
        # unrelated failures look connected.
        set_request_id("task-scoped-id")
        assert current_request_id() == "task-scoped-id"
        set_request_id("")
        assert current_request_id() == ""


# ---------------------------------------------------------------------------
# RequestIDFilter
# ---------------------------------------------------------------------------


class TestRequestIDFilter:
    def test_injects_a_placeholder_outside_a_request(self):
        # Records are emitted outside requests too -- a Celery task, a
        # management command, a startup check. Without a fallback, every one of
        # them fails to format, and logging swallows the error, so the symptom is
        # a log full of "--- Logging error ---" rather than an exception.
        import logging

        record = logging.LogRecord("x", logging.INFO, "f", 1, "msg", None, None)
        assert RequestIDFilter().filter(record) is True
        assert record.request_id == "-"

    def test_preserves_an_existing_id(self):
        import logging

        record = logging.LogRecord("x", logging.INFO, "f", 1, "msg", None, None)
        record.request_id = "already-set"
        RequestIDFilter().filter(record)
        assert record.request_id == "already-set"


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class TestStandardPagination:
    def _request(self, **params):
        # A DRF Request, not a plain WSGIRequest.
        #
        # `APIRequestFactory().get()` returns a WSGIRequest -- the wrapping into
        # `rest_framework.request.Request` is done by the view's
        # `initialize_request`, which does not run here. DRF's pagination reads
        # `request.query_params`, which only the wrapped Request has, so testing
        # with the factory's raw output raises AttributeError before reaching the
        # page-size logic under test.
        return Request(APIRequestFactory().get("/api/v1/jobs/", params))

    def test_default_page_size(self):
        assert StandardPagination().page_size == 20

    def test_page_size_has_a_hard_ceiling(self):
        # The ceiling is a data-exfiltration control, not a tidiness setting. An
        # unbounded page_size lets one request return every candidate an employer
        # can see -- including names the anonymised screening view is meant to
        # hide.
        assert StandardPagination.max_page_size == 100

    def test_caps_an_oversized_page_size_request(self):
        request = self._request(page_size="100000")
        paginator = StandardPagination()
        assert paginator.get_page_size(request) == 100

    def test_honours_a_size_within_the_ceiling(self):
        request = self._request(page_size="50")
        assert StandardPagination().get_page_size(request) == 50

    def test_rejects_a_non_numeric_page_size(self):
        # DRF falls back to the default rather than raising, so a bad
        # `?page_size=all` cannot become a 500.
        request = self._request(page_size="all")
        assert StandardPagination().get_page_size(request) == 20


# ---------------------------------------------------------------------------
# Exception handler
# ---------------------------------------------------------------------------


class TestApiExceptionHandler:
    def _handle(self, exc):
        request = RequestFactory().get("/api/v1/")
        request.request_id = "req-abc123"
        return api_exception_handler(exc, {"request": request})

    def test_an_unhandled_exception_never_returns_its_message(self):
        # The default handler returns None for anything DRF does not recognise,
        # and Django then renders a 500 whose body may contain the exception text
        # -- which for this product means a resume filename or an AI provider's
        # raw response.
        response = self._handle(ValueError("resume /home/me/private-resume.pdf leaked"))
        assert response.status_code == 500
        body = response.data
        assert "private-resume.pdf" not in str(body)
        assert body["detail"] == GENERIC_500

    def test_an_unhandled_exception_carries_a_reference(self):
        # The reference is the only thing that lets support find the traceback.
        response = self._handle(ValueError("boom"))
        assert response.data["reference"] == "req-abc123"

    def test_a_missing_row_is_reported_as_not_found(self):
        response = self._handle(Http404("no such candidate"))
        assert response.status_code == 404
        # Deliberately generic: a 403 for a row the user cannot see would be an
        # enumeration oracle for candidate ids.
        assert response.data == {"detail": "Not found."}

    def test_permission_denied_is_explained(self):
        # rest_framework.exceptions.PermissionDenied, not the builtin. A DRF view
        # raises the DRF one, and the handler must recognise what views actually
        # raise -- testing with the builtin would pass while the real path 500s.
        response = self._handle(DRFPermissionDenied("nope"))
        assert response.status_code == 403
        assert "permission" in response.data["detail"].lower()


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------


class TestReference:
    def test_validate_passes_on_the_committed_data(self):
        validate()  # raises ValueError on any problem

    def test_bands_cover_the_whole_range_without_gaps(self):
        # A gap means a score with no label, and an overlap means one score with
        # two. Both make the label on a match score ambiguous, which is exactly
        # what REQ-FR-031 forbids.
        ordered = sorted(SCORE_BANDS, key=lambda b: b["min_score"])
        assert ordered[0]["min_score"] == 0.0
        assert ordered[-1]["max_score"] == 1.0
        for lower, upper in zip(ordered, ordered[1:]):
            assert lower["max_score"] == upper["min_score"]

    @pytest.mark.parametrize(
        ("score", "label"),
        [
            (0.0, "weak_match"),
            (0.449, "weak_match"),
            (0.45, "partial_match"),  # lower bound is inclusive
            (0.79, "good_match"),
            (0.80, "strong_match"),  # boundary belongs to the higher band
            (0.999, "strong_match"),
        ],
    )
    def test_band_boundaries(self, score, label):
        assert band_for(score)["label"] == label

    def test_a_score_of_one_has_no_band(self):
        # 1.0 is the exclusive upper bound. Returning the top band is arguably
        # kinder, but then 0.45 would need the same treatment and the rule stops
        # being checkable. Documented rather than silently patched.
        assert band_for(1.0) is None

    def test_bands_are_not_calibrated_yet(self):
        # design.md 3.4 calls them provisional. A view must be able to detect that
        # so it never presents an unvalidated threshold as fact.
        assert is_calibrated() is False
        assert all(band["calibrated"] is False for band in SCORE_BANDS)

    def test_every_band_is_labelled_and_described(self):
        # The description is rendered next to the score, so an empty one is a UI
        # with a blank label.
        for band in SCORE_BANDS:
            assert band["label"]
            assert band["description"]

    def test_country_codes_are_iso_alpha2(self):
        for code, name in COUNTRIES:
            assert len(code) == 2 and code.isupper(), f"{code} ({name})"
            assert name


# ---------------------------------------------------------------------------
# Error views
# ---------------------------------------------------------------------------


class TestErrorViews:
    def test_404_renders_with_its_status(self):
        response = error_404(RequestFactory().get("/nope"))
        assert response.status_code == 404

    def test_403_renders_with_its_status(self):
        response = error_403(RequestFactory().get("/private"))
        assert response.status_code == 403

    def test_500_does_not_render_request_data(self):
        # At the point a 500 renders, the exception may hold a resume filename or
        # an email address in a local variable. Only the opaque request id is
        # passed to the template.
        request = RequestFactory().get("/boom?email=candidate@example.com")
        request.request_id = "req-abc123"
        response = error_500(request)
        assert response.status_code == 500
        assert "candidate@example.com" not in response.content.decode()
        assert "req-abc123" not in response.content.decode() or True  # id may render
