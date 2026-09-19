from django.conf import settings

from vacation.application.ports import LeaveBalanceGateway, WorkforceGateway


def build_vacation_gateways() -> tuple[WorkforceGateway, LeaveBalanceGateway]:
    if settings.VACATION_INTEGRATION_MODE == "development":
        from vacation.infrastructure.development_gateways import (
            SettingsLeaveBalanceGateway,
            SettingsWorkforceGateway,
        )

        return SettingsWorkforceGateway(), SettingsLeaveBalanceGateway()

    from vacation.infrastructure.workforce_gateways import (
        DjangoLeaveBalanceGateway,
        DjangoWorkforceGateway,
    )

    return DjangoWorkforceGateway(), DjangoLeaveBalanceGateway()
