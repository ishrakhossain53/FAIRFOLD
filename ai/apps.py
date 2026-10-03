"""AI provider abstraction, bias auditing and the rationale path."""

from django.apps import AppConfig


class AiConfig(AppConfig):
    """AI provider abstraction, bias auditing and the rationale path."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ai"

    def ready(self) -> None:
        """Import-time registration hook.

        Called once when the app registry is populated -- before any request is
        served and before `manage.py migrate`. Signal receivers belong here so a
        missed import is a boot error rather than a silently absent handler.
        """
        # No signal imports yet. Uncomment when the first receiver exists:
        # from . import signals  # noqa: F401
        pass
