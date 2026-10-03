#!/usr/bin/env python
"""Django's command-line utility for administrative tasks.

The settings module is ``config.settings`` (Complete Doc §4.2) — the project
package is ``config/``, not ``fairfold/``. Overriding ``DJANGO_SETTINGS_MODULE``
on the command line is intentional and common:

    python manage.py migrate --settings=config.settings.ci
"""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - import guard
        raise ImportError(
            "Couldn't import Django. Is it installed and is your virtual "
            "environment active? Try: pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()