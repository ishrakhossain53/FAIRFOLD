"""Celery application for FairFold.

Broker and result backend are deliberately **separate Redis databases**
(``.env.example``: ``CELERY_BROKER_URL`` db 0, ``CELERY_RESULT_BACKEND`` db 1).
A shared database means a ``FLUSHDB`` on one wipes the other's data — and
flushing the broker's DB mid-run silently discards queued tasks.

Tasks that are safe to run twice must carry their own idempotency. See
Complete Doc §C.8.2 for the three data operations that belong in Celery rather
than in a ``RunPython`` migration.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("fairfold")

# All Celery options live in Django settings under CELERY_*, so there is exactly
# one place to look. `namespace="CELERY"` means a Django setting named
# CELERY_TASK_TRACK_STARTED becomes `task_track_started` here.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load tasks.py from every installed app at startup.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> str:  # pragma: no cover - operational aid
    """Print the request. Used to confirm a worker is actually consuming."""
    return f"Request: {self.request!r}"
