from django.contrib import admin

from payroll.infrastructure.models import (
    PayrollComponentTypeModel,
    PayrollHistoryModel,
    PayrollItemModel,
    PayrollStatementModel,
    PublicHolidayModel,
)

admin.site.register(
    [
        PayrollComponentTypeModel,
        PayrollStatementModel,
        PayrollItemModel,
        PayrollHistoryModel,
        PublicHolidayModel,
    ]
)
