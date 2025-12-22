from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True, allow_null=True)
    post_title = serializers.CharField(source='post.title', read_only=True)

    class Meta:
        model = Notification
        fields = (
            'id',
            'type',
            'is_read',
            'created_at',
            'actor_username',
            'post',
            'post_title',
            'comment',
        )


class MarkReadSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
