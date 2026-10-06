from django.db import models

from workforce.infrastructure.models import Department, Employee, Position


class EvaluationModel(models.Model):
    class Status(models.TextChoices):
        DRAFT = "작성중", "작성중"
        CONFIRMED = "확정", "확정"

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
    evaluator = models.ForeignKey(
        Employee,
        db_column="evaluator_no",
        on_delete=models.RESTRICT,
        related_name="authored_evaluations",
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
