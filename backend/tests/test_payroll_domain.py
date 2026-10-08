from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from payroll.domain.entities import ComponentCategory, PayrollItem, PayrollStatement, PayrollStatus
from payroll.domain.exceptions import EmptyPayrollItemsError, InvalidPayrollTransitionError
from payroll.domain.policies import resolve_payment_date
from payroll.domain.value_objects import PayPeriod


def earning(amount: str) -> PayrollItem:
    return PayrollItem(
        component_code="BASE_PAY", category=ComponentCategory.EARNING, amount=Decimal(amount)
    )


def deduction(amount: str) -> PayrollItem:
    return PayrollItem(
        component_code="NATIONAL_PENSION",
        category=ComponentCategory.DEDUCTION,
        amount=Decimal(amount),
    )


def statement(
    status: PayrollStatus = PayrollStatus.DRAFT, items: list[PayrollItem] | None = None
) -> PayrollStatement:
    return PayrollStatement(
        statement_id=1,
        employee_no=1001,
        period=PayPeriod.of(2026, 9),
        payment_date=date(2026, 9, 25),
        status=status,
        items=items or [],
    )


def test_net_pay_is_the_exact_difference_between_earnings_and_deductions() -> None:
    # The shared `payrolls` table enforces net_pay = total_pay - total_deduct exactly
    # (chk_payrolls_net_pay), so this must never apply independent rounding.
    item = statement(items=[earning("3000000"), deduction("100000")])
    assert item.net_pay == Decimal("2900000")


def test_confirm_requires_at_least_one_item() -> None:
    with pytest.raises(EmptyPayrollItemsError):
        statement().confirm(9001, datetime.now(UTC))


def test_confirmed_statement_cannot_be_edited_directly() -> None:
    item = statement(PayrollStatus.CONFIRMED, items=[earning("3000000")])
    with pytest.raises(InvalidPayrollTransitionError):
        item.replace_items([earning("3200000")])


def test_cancel_confirmation_requires_a_reason() -> None:
    item = statement(PayrollStatus.CONFIRMED, items=[earning("3000000")])
    with pytest.raises(InvalidPayrollTransitionError):
        item.cancel_confirmation("   ")


def test_confirm_then_cancel_then_reconfirm_flow_is_tracked() -> None:
    item = statement(items=[earning("3000000")])

    is_first = item.confirm(9001, datetime.now(UTC))
    assert is_first is True
    assert item.status is PayrollStatus.CONFIRMED

    item.cancel_confirmation("금액 정정 필요")
    assert item.status is PayrollStatus.DRAFT

    item.replace_items([earning("3200000")])
    is_first_again = item.confirm(9001, datetime.now(UTC))
    assert is_first_again is False
    assert item.status is PayrollStatus.CONFIRMED
    assert item.net_pay == Decimal("3200000")


def test_resolve_payment_date_moves_weekend_settlement_back_to_the_previous_business_day() -> None:
    # 2026-09-25 falls on a Friday, so it should not move.
    assert resolve_payment_date(PayPeriod.of(2026, 9)) == date(2026, 9, 25)

    # 2026-10-25 falls on a Sunday, so it moves back through Saturday to Friday the 23rd.
    assert resolve_payment_date(PayPeriod.of(2026, 10)) == date(2026, 10, 23)


def test_resolve_payment_date_skips_registered_holidays_too() -> None:
    holidays = frozenset({date(2026, 9, 25)})
    assert resolve_payment_date(PayPeriod.of(2026, 9), holidays) == date(2026, 9, 24)
