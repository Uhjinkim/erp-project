from django.db import models
from django.db.models import Q


class PostModel(models.Model):
    class PostType(models.TextChoices):
        GENERAL = "일반", "일반"
        NOTICE = "공지", "공지"

    class NoticeCategory(models.TextChoices):
        MANAGEMENT = "경영", "경영"
        HR = "인사", "인사"
        PAYROLL = "급여", "급여"
        DEPARTMENT = "부서", "부서"

    post_id = models.BigAutoField(primary_key=True)
    author_employee_no = models.IntegerField(db_column="author_emp_no")
    post_type = models.CharField(max_length=10, choices=PostType.choices)
    notice_category = models.CharField(
        max_length=10, choices=NoticeCategory.choices, null=True, blank=True
    )
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "board_posts"
        ordering = ["-post_id"]
        indexes = [
            models.Index(fields=["post_type", "deleted_at"], name="board_post_type_del_idx"),
            models.Index(fields=["notice_category"], name="board_post_category_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(post_type="일반", notice_category__isnull=True)
                    | Q(post_type="공지", notice_category__isnull=False)
                ),
                name="board_post_notice_category_matches_type",
            ),
        ]
