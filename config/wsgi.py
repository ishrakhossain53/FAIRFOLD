"""WSGI entrypoint.

Uses gunicorn in the Docker image (`docker-compose.yml`). Django's own
``runserver`` is development-only and refuses to serve on a public interface
with ``DEBUG=True``.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_wsgi_application()
