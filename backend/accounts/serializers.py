from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.validators import validate_email
from rest_framework import serializers

import re
from django.utils import timezone

from .services import get_login_days_count, get_or_create_today_point_stat, get_or_create_today_stat

User = get_user_model()

_HANDLE_RE = re.compile(r'^@[A-Za-z0-9_]+$')


def _reject_angle_brackets(s: str) -> str:
    if '<' in s or '>' in s:
        raise serializers.ValidationError('不允许包含 < 或 >。')
    return s


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    nickname = serializers.CharField(max_length=20, allow_blank=False, trim_whitespace=False)
    email_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('nickname', 'username', 'email', 'email_code', 'password')

    def validate_nickname(self, value: str) -> str:
        v = (value or '').strip()
        if not v:
            raise serializers.ValidationError('必填。')
        if len(v) > 20:
            raise serializers.ValidationError('长度不能超过 20。')
        return _reject_angle_brackets(v)

    def validate_username(self, value: str) -> str:
        v = (value or '').strip()
        if not v:
            raise serializers.ValidationError('必填。')
        if len(v) > 20:
            raise serializers.ValidationError('长度不能超过 20。')
        v = v.lower()
        if not _HANDLE_RE.match(v):
            raise serializers.ValidationError('必须以 @ 开头，且仅包含字母/数字/下划线。')

        # Case-insensitive uniqueness.
        if User.objects.filter(username__iexact=v).exists():
            raise serializers.ValidationError('已被占用。')
        return v

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate_email(self, value: str) -> str:
        v = (value or '').strip()
        if not v:
            return ''
        try:
            validate_email(v)
        except Exception:
            raise serializers.ValidationError('邮箱格式不正确。')

        # Required for email login to be unambiguous.
        if User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError('该邮箱已被占用。')
        return v

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        code = (attrs.get('email_code') or '').strip()
        self._email_code_verified = False

        # Optional: only verify when both email and code are provided.
        if code and (not email):
            raise serializers.ValidationError({'email': ['请先填写邮箱。']})

        if email and code:
            key = f"email_code:register:{email.lower()}"
            expected = cache.get(key)
            if not expected:
                raise serializers.ValidationError({'email_code': ['验证码已过期或不存在。']})
            import secrets

            if not secrets.compare_digest(str(expected), code):
                raise serializers.ValidationError({'email_code': ['验证码错误。']})
            cache.delete(key)
            self._email_code_verified = True

        return attrs

    def create(self, validated_data):
        validated_data.pop('email_code', None)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        # PID is a system-generated 8-digit numeric identifier.
        try:
            if not getattr(user, 'pid', None):
                user.pid = str(int(user.id)).zfill(8)
                user.save(update_fields=['pid'])
        except Exception:
            pass
        return user


class MeSerializer(serializers.ModelSerializer):
    level = serializers.IntegerField(read_only=True)
    daily_download_limit = serializers.IntegerField(read_only=True)
    downloads_today = serializers.SerializerMethodField()
    downloads_remaining_today = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    pid = serializers.CharField(read_only=True)
    nickname = serializers.CharField(read_only=True)
    bio = serializers.CharField(read_only=True)
    plcoin = serializers.IntegerField(source='activity_score', read_only=True)
    login_days = serializers.SerializerMethodField()
    checked_in_today = serializers.SerializerMethodField()
    post_points_earned_today = serializers.SerializerMethodField()
    post_points_daily_cap = serializers.IntegerField(read_only=True, default=6)
    nickname_change_cost = serializers.IntegerField(read_only=True, default=3)
    nickname_changes_used = serializers.SerializerMethodField()
    nickname_changes_limit = serializers.IntegerField(read_only=True, default=12)
    username_change_cost = serializers.IntegerField(read_only=True, default=10)
    username_changes_used = serializers.SerializerMethodField()
    username_changes_limit = serializers.IntegerField(read_only=True, default=4)
    is_banned = serializers.BooleanField(read_only=True)
    banned_until = serializers.DateTimeField(read_only=True)
    ban_reason = serializers.CharField(read_only=True)
    is_muted = serializers.BooleanField(read_only=True)
    muted_until = serializers.DateTimeField(read_only=True)
    mute_reason = serializers.CharField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'pid',
            'nickname',
            'username',
            'email',
            'bio',
            'date_joined',
            'last_login',
            'activity_score',
            'plcoin',
            'level',
            'daily_download_limit',
            'downloads_today',
            'downloads_remaining_today',
            'login_days',
            'checked_in_today',
            'post_points_earned_today',
            'post_points_daily_cap',
            'nickname_change_cost',
            'nickname_changes_used',
            'nickname_changes_limit',
            'username_change_cost',
            'username_changes_used',
            'username_changes_limit',
            'avatar_url',
            'is_banned',
            'banned_until',
            'ban_reason',
            'is_muted',
            'muted_until',
            'mute_reason',
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

    def get_login_days(self, obj) -> int:
        return int(get_login_days_count(obj))

    def _year_window(self):
        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        start = timezone.datetime(today.year, 1, 1)
        end = timezone.datetime(today.year + 1, 1, 1)
        if timezone.is_naive(start):
            start = timezone.make_aware(start, tz)
        if timezone.is_naive(end):
            end = timezone.make_aware(end, tz)
        return start, end

    def _count_actions(self, obj, action: str) -> int:
        from .models import AuditLog

        start, end = self._year_window()
        return AuditLog.objects.filter(actor=obj, action=action, created_at__gte=start, created_at__lt=end).count()

    def get_nickname_changes_used(self, obj) -> int:
        return int(self._count_actions(obj, 'user.nickname.update'))

    def get_username_changes_used(self, obj) -> int:
        return int(self._count_actions(obj, 'user.username.update'))

    def get_checked_in_today(self, obj) -> bool:
        stat = get_or_create_today_point_stat(obj)
        return bool(getattr(stat, 'checked_in', False))

    def get_post_points_earned_today(self, obj) -> int:
        stat = get_or_create_today_point_stat(obj)
        return int(getattr(stat, 'post_points_earned', 0) or 0)


def _build_abs_media_url(request, file_field) -> str:
    if not file_field:
        return ''
    try:
        url = file_field.url
    except Exception:
        return ''
    if request is None:
        return url
    return request.build_absolute_uri(url)


class PublicUserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    is_following = serializers.BooleanField(read_only=True, required=False, default=False)

    class Meta:
        model = User
        fields = (
            'pid',
            'username',
            'nickname',
            'bio',
            'avatar_url',
            'banner_url',
            'followers_count',
            'following_count',
            'is_following',
        )

    def get_avatar_url(self, obj) -> str:
        return _build_abs_media_url(self.context.get('request'), getattr(obj, 'avatar', None))

    def get_banner_url(self, obj) -> str:
        return _build_abs_media_url(self.context.get('request'), getattr(obj, 'banner', None))


class UserSelfSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)

    # Allow updating avatar/banner via multipart/form-data.
    avatar = serializers.ImageField(write_only=True, required=False, allow_null=True)
    banner = serializers.ImageField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'pid',
            'username',
            'nickname',
            'email',
            'bio',
            'avatar',
            'avatar_url',
            'banner',
            'banner_url',
            'followers_count',
            'following_count',
        )
        read_only_fields = (
            'pid',
            'username',
            'avatar_url',
            'banner_url',
            'followers_count',
            'following_count',
        )

    def get_avatar_url(self, obj) -> str:
        return _build_abs_media_url(self.context.get('request'), getattr(obj, 'avatar', None))

    def get_banner_url(self, obj) -> str:
        return _build_abs_media_url(self.context.get('request'), getattr(obj, 'banner', None))


class AdminUserSerializer(serializers.ModelSerializer):
    level = serializers.IntegerField(read_only=True)
    daily_download_limit = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'pid',
            'nickname',
            'username',
            'email',
            'is_active',
            'is_staff',
            'is_superuser',
            'staff_board_scoped',
            'activity_score',
            'level',
            'daily_download_limit',
            'is_banned',
            'banned_until',
            'ban_reason',
            'is_muted',
            'muted_until',
            'mute_reason',
            'date_joined',
            'last_login',
        )
