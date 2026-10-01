from django.contrib import admin

from board.infrastructure.models import CommentModel, NoticeCategoryModel, PostModel


@admin.register(PostModel)
class PostAdmin(admin.ModelAdmin):
    list_display = ("post_id", "post_type", "notice_category", "title", "writer", "deleted_at")
    list_filter = ("post_type", "notice_category")
    search_fields = ("title",)


@admin.register(NoticeCategoryModel)
class NoticeCategoryAdmin(admin.ModelAdmin):
    list_display = ("notice_category_code", "category_name")


@admin.register(CommentModel)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("comment_id", "post", "writer", "parent", "deleted_at")
    search_fields = ("content",)
