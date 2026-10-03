"""Logging helpers.

The filter exists because ``LOGGING["formatters"]["verbose"]`` in
``config/settings/base.py`` interpolates ``[%(request_id)s]``. Without this
filter, **every** log record fails to format and raises ``KeyError`` -- logging
errors are swallowed by default, so the symptom is not an exception but a log
full of the message "--- Logging error ---". That is a silent failure that looks
like a broken log format and costs hours.
"""

from __future__ import annotations

import logging


class RequestIDFilter(logging.Filter):
    """Inject ``request_id`` into every record.

    Reads from the thread-local set by :mod:`core.middleware`, and falls back to
    ``"-"`` rather than raising. A record emitted outside a request -- a Celery
    task, a management command, a startup check -- must still format.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = self._current() or "-"
        return True

    @staticmethod
    def _current() -> str | None:
        try:
            from core.middleware import current_request_id

            return current_request_id()
        except Exception:  # pragma: no cover - never break logging
            return None