from django.contrib import admin

from evaluation.infrastructure.models import EvaluationModel


@admin.register(EvaluationModel)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ("eval_id", "employee", "eval_year", "score", "grade", "eval_status")
    list_filter = ("eval_year", "eval_status", "grade")
