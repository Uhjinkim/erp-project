from django.urls import path

from payroll.presentation.views import (
    CancelConfirmationView,
    ComponentListView,
    ConfirmView,
    HistoryView,
    ItemsUpdateView,
    StatementDetailView,
    StatementListCreateView,
)

app_name = "payroll"

urlpatterns = [
    path("components/", ComponentListView.as_view(), name="component-list"),
    path("statements/", StatementListCreateView.as_view(), name="statement-list-create"),
    path("statements/<int:statement_id>/", StatementDetailView.as_view(), name="statement-detail"),
    path("statements/<int:statement_id>/items/", ItemsUpdateView.as_view(), name="items-update"),
    path("statements/<int:statement_id>/confirm/", ConfirmView.as_view(), name="confirm"),
    path(
        "statements/<int:statement_id>/cancel-confirmation/",
        CancelConfirmationView.as_view(),
        name="cancel-confirmation",
    ),
    path("statements/<int:statement_id>/history/", HistoryView.as_view(), name="history"),
]
