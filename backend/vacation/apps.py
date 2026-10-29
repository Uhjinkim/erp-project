from django.apps import AppConfig


class VacationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vacation"

    def ready(self) -> None:
        from vacation.infrastructure import signals  # noqa: F401
