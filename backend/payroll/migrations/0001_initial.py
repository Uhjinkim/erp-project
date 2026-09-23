# Hand-written state-only migration. `payrolls`, `payroll_details`, `payroll_items`, and
# `payroll_history` already exist in the shared ERP database (see erp_dev.md). This migration
# only registers their model state with Django and must not recreate them.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("workforce", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="PayrollComponentTypeModel",
                    fields=[
                        (
                            "code",
                            models.CharField(
                                db_column="item_code",
                                max_length=20,
                                primary_key=True,
                                serialize=False,
                            ),
                        ),
                        ("name", models.CharField(db_column="item_name", max_length=50)),
                        (
                            "category",
                            models.CharField(
                                choices=[("지급", "지급"), ("공제", "공제")],
                                db_column="item_type",
                                max_length=10,
                            ),
                        ),
                        ("is_active", models.BooleanField(default=True)),
                    ],
                    options={
                        "db_table": "payroll_items",
                        "ordering": ["code"],
                    },
                ),
                migrations.CreateModel(
                    name="PayrollStatementModel",
                    fields=[
                        (
                            "statement_id",
                            models.BigAutoField(
                                db_column="payroll_id", primary_key=True, serialize=False
                            ),
                        ),
                        ("period", models.CharField(db_column="pay_yyyymm", max_length=6)),
                        ("payment_date", models.DateField(db_column="pay_date")),
                        (
                            "total_earnings",
                            models.DecimalField(
                                db_column="total_pay", decimal_places=2, default=0, max_digits=15
                            ),
                        ),
                        (
                            "total_deductions",
                            models.DecimalField(
                                db_column="total_deduct",
                                decimal_places=2,
                                default=0,
                                max_digits=15,
                            ),
                        ),
                        (
                            "net_pay",
                            models.DecimalField(decimal_places=2, default=0, max_digits=15),
                        ),
                        (
                            "status",
                            models.CharField(
                                choices=[("작성중", "작성중"), ("확정", "확정")],
                                default="작성중",
                                max_length=20,
                            ),
                        ),
                        ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                        (
                            "confirmed_by",
                            models.ForeignKey(
                                blank=True,
                                db_column="confirmed_by",
                                null=True,
                                on_delete=django.db.models.deletion.RESTRICT,
                                related_name="confirmed_payroll_statements",
                                to="workforce.employee",
                            ),
                        ),
                        (
                            "employee",
                            models.ForeignKey(
                                db_column="emp_no",
                                on_delete=django.db.models.deletion.RESTRICT,
                                related_name="payroll_statements",
                                to="workforce.employee",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "payrolls",
                        "ordering": ["-period", "employee_id"],
                    },
                ),
                migrations.CreateModel(
                    name="PayrollHistoryModel",
                    fields=[
                        ("history_id", models.BigAutoField(primary_key=True, serialize=False)),
                        ("action", models.CharField(max_length=20)),
                        ("reason", models.CharField(blank=True, max_length=255, null=True)),
                        ("changed_at", models.DateTimeField()),
                        (
                            "actor_employee",
                            models.ForeignKey(
                                db_column="actor_emp_no",
                                on_delete=django.db.models.deletion.RESTRICT,
                                related_name="+",
                                to="workforce.employee",
                            ),
                        ),
                        (
                            "statement",
                            models.ForeignKey(
                                db_column="payroll_id",
                                on_delete=django.db.models.deletion.RESTRICT,
                                related_name="history_entries",
                                to="payroll.payrollstatementmodel",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "payroll_history",
                        "ordering": ["changed_at", "history_id"],
                    },
                ),
                migrations.CreateModel(
                    name="PayrollDetailModel",
                    fields=[
                        ("detail_id", models.BigAutoField(primary_key=True, serialize=False)),
                        (
                            "amount",
                            models.DecimalField(decimal_places=2, default=0, max_digits=15),
                        ),
                        (
                            "component",
                            models.ForeignKey(
                                db_column="item_code",
                                on_delete=django.db.models.deletion.RESTRICT,
                                related_name="details",
                                to="payroll.payrollcomponenttypemodel",
                            ),
                        ),
                        (
                            "statement",
                            models.ForeignKey(
                                db_column="payroll_id",
                                on_delete=django.db.models.deletion.RESTRICT,
                                related_name="details",
                                to="payroll.payrollstatementmodel",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "payroll_details",
                        "ordering": ["statement_id", "component_id"],
                    },
                ),
                migrations.AddConstraint(
                    model_name="payrollstatementmodel",
                    constraint=models.UniqueConstraint(
                        fields=("employee", "period"), name="uq_payrolls_employee_month"
                    ),
                ),
                migrations.AddConstraint(
                    model_name="payrollstatementmodel",
                    constraint=models.CheckConstraint(
                        condition=models.Q(("total_earnings__gte", 0)),
                        name="chk_payrolls_total_pay",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="payrollstatementmodel",
                    constraint=models.CheckConstraint(
                        condition=models.Q(("total_deductions__gte", 0)),
                        name="chk_payrolls_total_deduct",
                    ),
                ),
                migrations.AddConstraint(
                    model_name="payrollstatementmodel",
                    constraint=models.CheckConstraint(
                        condition=models.Q(("net_pay__gte", 0)), name="chk_payrolls_net_pay"
                    ),
                ),
                migrations.AddConstraint(
                    model_name="payrolldetailmodel",
                    constraint=models.UniqueConstraint(
                        fields=("statement", "component"), name="uq_payroll_details_item"
                    ),
                ),
                migrations.AddConstraint(
                    model_name="payrolldetailmodel",
                    constraint=models.CheckConstraint(
                        condition=models.Q(("amount__gte", 0)), name="chk_payroll_details_amount"
                    ),
                ),
            ],
        ),
    ]
