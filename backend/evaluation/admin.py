from django.contrib import admin
from django.http import HttpRequest

from evaluation.infrastructure.models import EvaluationHistoryModel, EvaluationModel


class ReadOnlyAdmin(admin.ModelAdmin):
    """Writes must go through the API so grade, state and history rules hold."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


@admin.register(EvaluationModel)
class EvaluationAdmin(ReadOnlyAdmin):
    list_display = (
        "eval_id",
        "employee",
        "eval_year",
        "evaluator",
        "score",
        "grade",
        "eval_status",
    )
    list_filter = ("eval_year", "eval_status", "grade")


@admin.register(EvaluationHistoryModel)
class EvaluationHistoryAdmin(ReadOnlyAdmin):
    list_display = ("history_id", "evaluation", "action", "from_status", "to_status", "actor")
    list_filter = ("action",)
