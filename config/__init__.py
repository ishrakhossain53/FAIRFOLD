"""Django project package for FairFold.

This is the *project* package (``config/``), not an app. Application packages
sit at the repository root — see Complete Doc §4.2.

Importing the Celery app here means ``@shared_task`` works in any app without
each app having to import it, and it is the documented way to avoid the
"Celery worker starts but never sees any tasks" failure.
"""

from config.celery import app as celery_app

__all__ = ("celery_app",)
