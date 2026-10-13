from django.urls import path

from board.presentation.views import (
    CommentDetailView,
    CommentListCreateView,
    EligibleNoticeCategoriesView,
    PostDetailView,
    PostListCreateView,
)

app_name = "board"

urlpatterns = [
    path("posts/", PostListCreateView.as_view(), name="post-list-create"),
    path("posts/<int:post_id>/", PostDetailView.as_view(), name="post-detail"),
    path(
        "posts/<int:post_id>/comments/",
        CommentListCreateView.as_view(),
        name="comment-list-create",
    ),
    path("comments/<int:comment_id>/", CommentDetailView.as_view(), name="comment-detail"),
    path(
        "notice-categories/eligible/",
        EligibleNoticeCategoriesView.as_view(),
        name="eligible-notice-categories",
    ),
]
