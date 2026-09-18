from django.urls import path

from vacation.presentation.views import (
    ApprovalListView,
    ApproveVacationView,
    CancelVacationView,
    RecallVacationView,
    RejectVacationView,
    ResubmitVacationView,
    VacationHistoryView,
    VacationRequestListCreateView,
    VacationTypeListView,
)

app_name = "vacation"

urlpatterns = [
    path("types/", VacationTypeListView.as_view(), name="type-list"),
    path("requests/", VacationRequestListCreateView.as_view(), name="request-list-create"),
    path("approvals/", ApprovalListView.as_view(), name="approval-list"),
    path("requests/<int:request_id>/cancel/", CancelVacationView.as_view(), name="cancel"),
    path("requests/<int:request_id>/approve/", ApproveVacationView.as_view(), name="approve"),
    path("requests/<int:request_id>/reject/", RejectVacationView.as_view(), name="reject"),
    path("requests/<int:request_id>/recall/", RecallVacationView.as_view(), name="recall"),
    path("requests/<int:request_id>/resubmit/", ResubmitVacationView.as_view(), name="resubmit"),
    path("requests/<int:request_id>/history/", VacationHistoryView.as_view(), name="history"),
]
