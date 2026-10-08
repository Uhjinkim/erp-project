from django.db import models

from evaluation.infrastructure.fields import TimestampField
from workforce.infrastructure.models import Department, Employee, Position


class EvaluationModel(models.Model):
    class Status(models.TextChoices):
        DRAFT = "작성중", "작성중"
        SUBMITTED = "제출", "제출"
        RETURNED = "반려", "반려"
        CONFIRMED = "확정", "확정"
        EXCLUDED = "제외", "제외"

    eval_id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        Employee,
        db_column="emp_no",
        on_delete=models.RESTRICT,
        related_name="evaluations",
    )
    eval_year = models.CharField(max_length=4)
    snapshot_department = models.ForeignKey(
        Department,
        db_column="snapshot_dept_no",
        on_delete=models.RESTRICT,
        related_name="evaluation_snapshots",
        null=True,
        blank=True,
    )
    snapshot_position = models.ForeignKey(
        Position,
        db_column="snapshot_pos_code",
        on_delete=models.RESTRICT,
        related_name="evaluation_snapshots",
        null=True,
        blank=True,
    )
    # Current evaluator. Changes only through an HR reassignment.
    evaluator = models.ForeignKey(
        Employee,
        db_column="evaluator_no",
        on_delete=models.RESTRICT,
        related_name="authored_evaluations",
    )
    # First author. Nullable because rows created before this column existed have none.
    created_by = models.ForeignKey(
        Employee,
        db_column="created_by",
        on_delete=models.RESTRICT,
        related_name="created_evaluations",
        null=True,
        blank=True,
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=10)
    comments = models.TextField(null=True, blank=True)
    eval_status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    confirmed_by = models.ForeignKey(
        Employee,
        db_column="confirmed_by",
        on_delete=models.RESTRICT,
        related_name="confirmed_evaluations",
        null=True,
        blank=True,
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "evaluations"
        ordering = ["-eval_year", "-eval_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "eval_year"],
                name="uq_evaluations_emp_no_eval_year",
            ),
        ]


class EvaluationHistoryModel(models.Model):
    history_id = models.BigAutoField(primary_key=True)
    evaluation = models.ForeignKey(
        EvaluationModel,
        db_column="eval_id",
        on_delete=models.RESTRICT,
        related_name="history_entries",
    )
    action = models.CharField(max_length=20)
    from_status = models.CharField(max_length=20, null=True, blank=True)
    to_status = models.CharField(max_length=20)
    actor = models.ForeignKey(
        Employee,
        db_column="actor_emp_no",
        on_delete=models.RESTRICT,
        related_name="evaluation_actions",
    )
    from_evaluator = models.ForeignKey(
        Employee,
        db_column="from_evaluator_no",
        on_delete=models.RESTRICT,
        related_name="+",
        null=True,
        blank=True,
    )
    to_evaluator = models.ForeignKey(
        Employee,
        db_column="to_evaluator_no",
        on_delete=models.RESTRICT,
        related_name="+",
        null=True,
        blank=True,
    )
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True, default="")
    # README: changed_at timestamp (without time zone), like the other ERP tables.
    changed_at = TimestampField()

    class Meta:
        db_table = "evaluation_history"
        ordering = ["changed_at", "history_id"]
