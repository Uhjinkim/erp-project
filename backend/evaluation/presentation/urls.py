from django.urls import path

from evaluation.presentation.views import (
    EvaluationConfirmView,
    EvaluationDetailView,
    EvaluationListCreateView,
)

app_name = "evaluation"

urlpatterns = [
    path("", EvaluationListCreateView.as_view(), name="evaluation-list-create"),
    path("<int:eval_id>/", EvaluationDetailView.as_view(), name="evaluation-detail"),
    path("<int:eval_id>/confirm/", EvaluationConfirmView.as_view(), name="evaluation-confirm"),
]
