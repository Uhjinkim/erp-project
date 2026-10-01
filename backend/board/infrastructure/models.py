from django.db import models

from workforce.infrastructure.models import Employee


class NoticeCategoryModel(models.Model):
    notice_category_code = models.CharField(primary_key=True, max_length=20)
    category_name = models.CharField(max_length=50)

    class Meta:
        db_table = "board_notice_categories"


class PostModel(models.Model):
    class PostType(models.TextChoices):
        GENERAL = "일반", "일반"
        NOTICE = "공지", "공지"

    post_id = models.BigAutoField(primary_key=True)
    writer = models.ForeignKey(
        Employee,
        db_column="writer_emp_no",
        on_delete=models.RESTRICT,
        related_name="board_posts",
    )
    post_type = models.CharField(max_length=10, choices=PostType.choices, default=PostType.GENERAL)
    notice_category = models.ForeignKey(
        NoticeCategoryModel,
        db_column="notice_category_code",
        on_delete=models.RESTRICT,
        related_name="posts",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "board_posts"
        ordering = ["-post_id"]


class CommentModel(models.Model):
    comment_id = models.BigAutoField(primary_key=True)
    post = models.ForeignKey(
        PostModel,
        db_column="post_id",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    writer = models.ForeignKey(
        Employee,
        db_column="writer_emp_no",
        on_delete=models.RESTRICT,
        related_name="board_comments",
    )
    parent = models.ForeignKey(
        "self",
        db_column="parent_comment_id",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
    )
    content = models.TextField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "board_comments"
        ordering = ["created_at", "comment_id"]
