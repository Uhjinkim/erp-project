from django.contrib import admin

from payroll.infrastructure.models import (
    PayrollComponentTypeModel,
    PayrollDetailModel,
    PayrollHistoryModel,
    PayrollStatementModel,
    PublicHolidayModel,
)

admin.site.register(
    [
        PayrollComponentTypeModel,
        PayrollStatementModel,
        PayrollDetailModel,
        PayrollHistoryModel,
        PublicHolidayModel,
    ]
)
