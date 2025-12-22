from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .services import get_or_create_today_stat

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MeSerializer(serializers.ModelSerializer):
    level = serializers.IntegerField(read_only=True)
    daily_download_limit = serializers.IntegerField(read_only=True)
    downloads_today = serializers.SerializerMethodField()
    downloads_remaining_today = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    is_banned = serializers.BooleanField(read_only=True)
    banned_until = serializers.DateTimeField(read_only=True)
    ban_reason = serializers.CharField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'date_joined',
            'last_login',
            'activity_score',
            'level',
            'daily_download_limit',
            'downloads_today',
            'downloads_remaining_today',
            'avatar_url',
            'is_banned',
            'banned_until',
            'ban_reason',
            'is_staff',
            'is_superuser',
        )

    def get_avatar_url(self, obj) -> str:
        # 备注：
        # - 尽量返回绝对 URL，方便前端在不同域名/端口下直接使用。
        # - DEBUG 下由 Django 直接 serve MEDIA_URL；生产环境应由对象存储/CDN 处理。
        avatar = getattr(obj, 'avatar', None)
        if not avatar:
            return ''
        try:
            url = avatar.url
        except Exception:
            return ''
        request = self.context.get('request')
        if request is None:
            return url
        return request.build_absolute_uri(url)

    def get_downloads_today(self, obj) -> int:
        stat = get_or_create_today_stat(obj)
        return int(stat.count)

    def get_downloads_remaining_today(self, obj) -> int:
        stat = get_or_create_today_stat(obj)
        remaining = int(obj.daily_download_limit) - int(stat.count)
        return max(0, remaining)


class AdminUserSerializer(serializers.ModelSerializer):
    level = serializers.IntegerField(read_only=True)
    daily_download_limit = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'is_active',
            'is_staff',
            'is_superuser',
            'activity_score',
            'level',
            'daily_download_limit',
            'is_banned',
            'banned_until',
            'ban_reason',
            'date_joined',
            'last_login',
        )
