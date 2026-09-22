from rest_framework import serializers

from board.domain.entities import NoticeCategory, PostType


class PostCreateSerializer(serializers.Serializer):
    post_type = serializers.ChoiceField(choices=[item.value for item in PostType])
    notice_category = serializers.ChoiceField(
        choices=[item.value for item in NoticeCategory], required=False, allow_null=True
    )
    title = serializers.CharField(max_length=100)
    content = serializers.CharField()


class PostUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    content = serializers.CharField()
