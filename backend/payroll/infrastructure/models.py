from django.db import models
from django.db.models import Q

from workforce.infrastructure.models import Employee


class PayrollComponentTypeModel(models.Model):
    """Maps to the pre-existing legacy `payroll_items` table (component master data)."""

    class Category(models.TextChoices):
        EARNING = "지급", "지급"
        DEDUCTION = "공제", "공제"

    code = models.CharField(primary_key=True, max_length=20, db_column="item_code")
    name = models.CharField(max_length=50, db_column="item_name")
    category = models.CharField(max_length=10, choices=Category.choices, db_column="item_type")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "payroll_items"
        ordering = ["code"]


class PayrollStatementModel(models.Model):
    """Maps to the pre-existing legacy `payrolls` table."""

    class Status(models.TextChoices):
        DRAFT = "작성중", "작성중"
        CONFIRMED = "확정", "확정"

    statement_id = models.BigAutoField(primary_key=True, db_column="payroll_id")
    employee = models.ForeignKey(
        Employee,
        db_column="emp_no",
        on_delete=models.RESTRICT,
        related_name="payroll_statements",
    )
    period = models.CharField(max_length=6, db_column="pay_yyyymm")
    payment_date = models.DateField(db_column="pay_date")
    total_earnings = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, db_column="total_pay"
    )
    total_deductions = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, db_column="total_deduct"
    )
    net_pay = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    confirmed_by = models.ForeignKey(
        Employee,
        db_column="confirmed_by",
        null=True,
        blank=True,
        on_delete=models.RESTRICT,
        related_name="confirmed_payroll_statements",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payrolls"
        ordering = ["-period", "employee_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "period"], name="uq_payrolls_employee_month"
            ),
            models.CheckConstraint(
                condition=Q(total_earnings__gte=0), name="chk_payrolls_total_pay"
            ),
            models.CheckConstraint(
                condition=Q(total_deductions__gte=0), name="chk_payrolls_total_deduct"
            ),
            models.CheckConstraint(condition=Q(net_pay__gte=0), name="chk_payrolls_net_pay"),
        ]


class PayrollDetailModel(models.Model):
    """Maps to the pre-existing legacy `payroll_details` table (one row per line item)."""

    detail_id = models.BigAutoField(primary_key=True)
    statement = models.ForeignKey(
        PayrollStatementModel,
        db_column="payroll_id",
        on_delete=models.RESTRICT,
        related_name="details",
    )
    component = models.ForeignKey(
        PayrollComponentTypeModel,
        db_column="item_code",
        on_delete=models.RESTRICT,
        related_name="details",
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = "payroll_details"
        ordering = ["statement_id", "component_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["statement", "component"], name="uq_payroll_details_item"
            ),
            models.CheckConstraint(condition=Q(amount__gte=0), name="chk_payroll_details_amount"),
        ]


class PayrollHistoryModel(models.Model):
    """Maps to the pre-existing legacy `payroll_history` table."""

    history_id = models.BigAutoField(primary_key=True)
    statement = models.ForeignKey(
        PayrollStatementModel,
        db_column="payroll_id",
        on_delete=models.RESTRICT,
        related_name="history_entries",
    )
    action = models.CharField(max_length=20)
    actor_employee = models.ForeignKey(
        Employee,
        db_column="actor_emp_no",
        on_delete=models.RESTRICT,
        related_name="+",
    )
    reason = models.CharField(max_length=255, null=True, blank=True)
    changed_at = models.DateTimeField()

    class Meta:
        db_table = "payroll_history"
        ordering = ["changed_at", "history_id"]


class PublicHolidayModel(models.Model):
    """No legacy equivalent; a genuinely new table for settlement-date adjustment."""

    holiday_date = models.DateField(primary_key=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "payroll_public_holidays"
        ordering = ["holiday_date"]
