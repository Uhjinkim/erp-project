from django.contrib import admin

from board.infrastructure.models import PostModel


@admin.register(PostModel)
class PostAdmin(admin.ModelAdmin):
    list_display = ("post_id", "post_type", "notice_category", "title", "author_employee_no")
    list_filter = ("post_type", "notice_category")
    search_fields = ("title",)
