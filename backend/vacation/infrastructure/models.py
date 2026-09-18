from django.db import models
from django.db.models import F, Q


class LeaveTypeModel(models.Model):
    type_id = models.CharField(primary_key=True, max_length=20)
    type_name = models.CharField(max_length=50, unique=True)
    is_paid = models.BooleanField(default=True)
    deduct_days = models.DecimalField(max_digits=3, decimal_places=2, default=1)

    class Meta:
        db_table = "leave_types"
        constraints = [
            models.CheckConstraint(
                condition=Q(deduct_days__gte=0), name="leave_type_deduct_days_nonnegative"
            )
        ]


class LeaveRequestModel(models.Model):
    class Status(models.TextChoices):
        PENDING = "대기", "대기"
        APPROVED = "승인", "승인"
        REJECTED = "반려", "반려"
        CANCELLED = "취소", "취소"
        RECALLED = "회수", "회수"

    request_id = models.BigAutoField(primary_key=True)
    employee_no = models.IntegerField(db_column="emp_no")
    vacation_type = models.ForeignKey(
        LeaveTypeModel,
        db_column="type_id",
        db_constraint=True,
        on_delete=models.RESTRICT,
        related_name="requests",
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    use_days = models.DecimalField(max_digits=3, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approver_no = models.IntegerField()
    approved_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.CharField(max_length=255, null=True, blank=True)
    request_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "leave_requests"
        ordering = ["-request_id"]
        indexes = [
            models.Index(fields=["employee_no", "status"], name="leave_req_emp_status_idx"),
            models.Index(fields=["approver_no", "status"], name="leave_req_appr_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(use_days__gt=0), name="leave_request_days_positive"),
            models.CheckConstraint(
                condition=Q(end_datetime__gte=F("start_datetime")),
                name="leave_request_period_valid",
            ),
        ]


class LeaveRequestHistoryModel(models.Model):
    history_id = models.BigAutoField(primary_key=True)
    request = models.ForeignKey(
        LeaveRequestModel,
        db_column="request_id",
        on_delete=models.RESTRICT,
        related_name="history_entries",
    )
    from_status = models.CharField(
        max_length=20, choices=LeaveRequestModel.Status.choices, null=True, blank=True
    )
    to_status = models.CharField(max_length=20, choices=LeaveRequestModel.Status.choices)
    actor_employee_no = models.IntegerField(db_column="actor_emp_no")
    reason = models.CharField(max_length=255, null=True, blank=True)
    changed_at = models.DateTimeField()

    class Meta:
        db_table = "leave_request_history"
        ordering = ["changed_at", "history_id"]
        indexes = [models.Index(fields=["request", "changed_at"], name="leave_hist_req_time_idx")]
