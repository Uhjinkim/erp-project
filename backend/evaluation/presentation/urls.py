from django.urls import path

from evaluation.presentation.views import (
    EvaluationCancelConfirmationView,
    EvaluationCancelExclusionView,
    EvaluationConfirmView,
    EvaluationDetailView,
    EvaluationExcludeView,
    EvaluationHistoryView,
    EvaluationListCreateView,
    EvaluationReassignView,
    EvaluationReturnView,
    EvaluationSubmitView,
)

app_name = "evaluation"

urlpatterns = [
    path("", EvaluationListCreateView.as_view(), name="evaluation-list-create"),
    path("<int:eval_id>/", EvaluationDetailView.as_view(), name="evaluation-detail"),
    path("<int:eval_id>/history/", EvaluationHistoryView.as_view(), name="evaluation-history"),
    path("<int:eval_id>/submit/", EvaluationSubmitView.as_view(), name="evaluation-submit"),
    path("<int:eval_id>/return/", EvaluationReturnView.as_view(), name="evaluation-return"),
    path(
        "<int:eval_id>/reassign/",
        EvaluationReassignView.as_view(),
        name="evaluation-reassign",
    ),
    path("<int:eval_id>/confirm/", EvaluationConfirmView.as_view(), name="evaluation-confirm"),
    path(
        "<int:eval_id>/cancel-confirmation/",
        EvaluationCancelConfirmationView.as_view(),
        name="evaluation-cancel-confirmation",
    ),
    path("<int:eval_id>/exclude/", EvaluationExcludeView.as_view(), name="evaluation-exclude"),
    path(
        "<int:eval_id>/cancel-exclusion/",
        EvaluationCancelExclusionView.as_view(),
        name="evaluation-cancel-exclusion",
    ),
]
