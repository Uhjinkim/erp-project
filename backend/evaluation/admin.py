from django.contrib import admin
from django.http import HttpRequest

from evaluation.infrastructure.models import EvaluationModel


@admin.register(EvaluationModel)
class EvaluationAdmin(admin.ModelAdmin):
    """Read-only: writes must go through the API so grade and state rules hold."""

    list_display = ("eval_id", "employee", "eval_year", "score", "grade", "eval_status")
    list_filter = ("eval_year", "eval_status", "grade")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
