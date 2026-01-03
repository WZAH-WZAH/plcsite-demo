from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True, allow_null=True)
    actor_nickname = serializers.CharField(source='actor.nickname', read_only=True, allow_null=True)
    actor_pid = serializers.CharField(source='actor.pid', read_only=True, allow_null=True)
    actor_avatar_url = serializers.SerializerMethodField()
    post_title = serializers.CharField(source='post.title', read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = (
            'id',
            'type',
            'is_read',
            'created_at',
            'actor_username',
            'actor_nickname',
            'actor_pid',
            'actor_avatar_url',
            'post',
            'post_title',
            'comment',
        )

    def get_actor_avatar_url(self, obj) -> str:
        actor = getattr(obj, 'actor', None)
        if actor is None:
            return ''
        avatar = getattr(actor, 'avatar', None)
        if not avatar:
            return ''
        try:
            url = avatar.url
        except Exception:
            return ''
        request = self.context.get('request')
        if request is None:
            return url
        try:
            return request.build_absolute_uri(url)
        except Exception:
            return url


class MarkReadSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
