from django.db import models
from django.db.models import Q

from workforce.infrastructure.models import Employee


class PayrollComponentTypeModel(models.Model):
    class Category(models.TextChoices):
        EARNING = "지급", "지급"
        DEDUCTION = "공제", "공제"

    code = models.CharField(primary_key=True, max_length=30)
    name = models.CharField(max_length=50)
    category = models.CharField(max_length=10, choices=Category.choices)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "payroll_component_types"
        ordering = ["sort_order", "code"]


class PayrollStatementModel(models.Model):
    class Status(models.TextChoices):
        DRAFT = "작성중", "작성중"
        CONFIRMED = "확정", "확정"

    statement_id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        Employee,
        db_column="emp_no",
        on_delete=models.RESTRICT,
        related_name="payroll_statements",
    )
    period = models.DateField()
    payment_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    total_earnings = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_by = models.IntegerField(db_column="created_by_emp_no")
    confirmed_by = models.IntegerField(db_column="confirmed_by_emp_no", null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payroll_statements"
        ordering = ["-period", "employee_id"]
        indexes = [
            models.Index(fields=["employee", "status"], name="payroll_stmt_emp_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "period"], name="payroll_statement_employee_period_unique"
            ),
        ]


class PayrollItemModel(models.Model):
    item_id = models.BigAutoField(primary_key=True)
    statement = models.ForeignKey(
        PayrollStatementModel,
        db_column="statement_id",
        on_delete=models.RESTRICT,
        related_name="items",
    )
    component = models.ForeignKey(
        PayrollComponentTypeModel,
        db_column="component_code",
        on_delete=models.RESTRICT,
        related_name="items",
    )
    category = models.CharField(max_length=10, choices=PayrollComponentTypeModel.Category.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        db_table = "payroll_items"
        ordering = ["statement_id", "component_id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=0), name="payroll_item_amount_nonnegative"
            ),
        ]


class PayrollHistoryModel(models.Model):
    history_id = models.BigAutoField(primary_key=True)
    statement = models.ForeignKey(
        PayrollStatementModel,
        db_column="statement_id",
        on_delete=models.RESTRICT,
        related_name="history_entries",
    )
    action = models.CharField(max_length=20)
    actor_employee_no = models.IntegerField(db_column="actor_emp_no")
    reason = models.CharField(max_length=255, null=True, blank=True)
    change_summary = models.TextField(null=True, blank=True)
    changed_at = models.DateTimeField()

    class Meta:
        db_table = "payroll_history"
        ordering = ["changed_at", "history_id"]
        indexes = [
            models.Index(fields=["statement", "changed_at"], name="payroll_hist_stmt_time_idx"),
        ]


class PublicHolidayModel(models.Model):
    holiday_date = models.DateField(primary_key=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "payroll_public_holidays"
        ordering = ["holiday_date"]
