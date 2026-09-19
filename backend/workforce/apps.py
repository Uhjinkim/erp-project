from django.apps import AppConfig


class WorkforceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "workforce"

    def ready(self) -> None:
        from workforce.infrastructure import signals  # noqa: F401
