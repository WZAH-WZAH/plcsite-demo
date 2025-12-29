from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta

from django.db.models import BooleanField, Count, Exists, OuterRef, Q, Value
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.audit import write_audit_log

from .models import UserFollow
from .serializers import MeSerializer, PublicUserSerializer, RegisterSerializer, UserSelfSerializer
from .services import (
    record_login_day,
    try_award_checkin_points,
)


User = get_user_model()


def _year_window_aware() -> tuple[timezone.datetime, timezone.datetime]:
    """Return [start, end) for the current natural year in current TZ."""

    tz = timezone.get_current_timezone()
    today = timezone.localdate()
    start = timezone.datetime(today.year, 1, 1)
    end = timezone.datetime(today.year + 1, 1, 1)
    if timezone.is_naive(start):
        start = timezone.make_aware(start, tz)
    if timezone.is_naive(end):
        end = timezone.make_aware(end, tz)
    return start, end


def _count_audit_actions(user, action: str) -> int:
    from .models import AuditLog

    start, end = _year_window_aware()
    return AuditLog.objects.filter(actor=user, action=action, created_at__gte=start, created_at__lt=end).count()


def _reject_angle_brackets(s: str) -> str:
    if '<' in s or '>' in s:
        raise ValueError('不允许包含 < 或 >。')
    return s


class CustomTokenObtainPairView(TokenObtainPairView):
    """JWT login that also records daily login stats."""

    class Serializer(TokenObtainPairSerializer):
        """Allow login with email / pid / username (handle) + password.

        Client still posts { username, password } for backward compatibility.
        """

        def validate(self, attrs):
            identifier = str(attrs.get('username') or '').strip()
            password = attrs.get('password')

            if identifier and password:
                u = None
                if identifier.startswith('@'):
                    u = User.objects.filter(username__iexact=identifier.lower()).first()
                elif identifier.isdigit() and len(identifier) == 8:
                    u = User.objects.filter(pid=identifier).first()
                elif '@' in identifier:
                    u = User.objects.filter(email__iexact=identifier).first()

                if u is not None:
                    attrs['username'] = u.username

            return super().validate(attrs)

    serializer_class = Serializer

    @method_decorator(ratelimit(key='ip', rate='30/m', block=True))
    def post(self, request, *args, **kwargs):
        resp = super().post(request, *args, **kwargs)
        try:
            # TokenObtainPairView sets serializer on self.
            ser = self.get_serializer(data=request.data)
            ser.is_valid(raise_exception=True)
            user = getattr(ser, 'user', None)
            if user is not None:
                record_login_day(user)
        except Exception:
            # Do not break login if stats fail.
            pass
        return resp


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key='ip', rate='10/m', block=True))
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Ensure pid exists (8-digit numeric string).
        try:
            if not getattr(user, 'pid', None):
                user.pid = str(int(user.id)).zfill(8)
                user.save(update_fields=['pid'])
        except Exception:
            pass

        # Optional email verification marker (best-effort audit only).
        try:
            if bool(getattr(serializer, '_email_code_verified', False)):
                write_audit_log(
                    actor=user,
                    action='user.email.verify.register',
                    target_type='user',
                    target_id=str(user.id),
                    request=request,
                    metadata={'email': getattr(user, 'email', '')},
                )
        except Exception:
            pass

        return Response(
            {'id': user.id, 'pid': getattr(user, 'pid', ''), 'nickname': getattr(user, 'nickname', ''), 'username': user.username},
            status=status.HTTP_201_CREATED,
        )


def _email_code_cache_key(email: str, *, purpose: str) -> str:
    e = (email or '').strip().lower()
    p = (purpose or 'generic').strip().lower()[:32] or 'generic'
    return f"email_code:{p}:{e}"


class AuthEmailVerifyCodeSendView(APIView):
    """Send email verification code for unauth flows (e.g., registration).

    In DEBUG, if email sending is not configured, returns the code for dev use.
    """

    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key='ip', rate='10/m', block=True))
    def post(self, request):
        email = str(request.data.get('email') or '').strip()
        purpose = str(request.data.get('purpose') or 'register').strip()[:32] or 'register'

        if not email:
            return Response({'email': ['必填。']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from django.core.validators import validate_email

            validate_email(email)
        except Exception:
            return Response({'email': ['邮箱格式不正确。']}, status=status.HTTP_400_BAD_REQUEST)

        import secrets

        code = str(secrets.randbelow(1_000_000)).zfill(6)
        ttl_seconds = 10 * 60
        cache.set(_email_code_cache_key(email, purpose=purpose), code, timeout=ttl_seconds)

        sent = False
        try:
            from django.core.mail import send_mail

            subject = '验证码'
            message = f"你的验证码是：{code}（10分钟内有效）"
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', None) or ''
            send_mail(subject, message, from_email, [email], fail_silently=False)
            sent = True
        except Exception:
            sent = False

        if sent:
            return Response({'ok': True}, status=status.HTTP_200_OK)

        if getattr(settings, 'DEBUG', False):
            return Response({'ok': True, 'dev_code': code}, status=status.HTTP_200_OK)

        return Response({'detail': 'Email sending is not configured.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class AuthEmailVerifyCodeVerifyView(APIView):
    """Verify an email code previously sent (unauth flows)."""

    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key='ip', rate='30/m', block=True))
    def post(self, request):
        email = str(request.data.get('email') or '').strip()
        code = str(request.data.get('code') or '').strip()
        purpose = str(request.data.get('purpose') or 'register').strip()[:32] or 'register'

        if not email:
            return Response({'email': ['必填。']}, status=status.HTTP_400_BAD_REQUEST)
        if not code:
            return Response({'code': ['必填。']}, status=status.HTTP_400_BAD_REQUEST)

        key = _email_code_cache_key(email, purpose=purpose)
        expected = cache.get(key)
        if not expected:
            return Response({'detail': '验证码已过期或不存在。'}, status=status.HTTP_400_BAD_REQUEST)

        import secrets

        if not secrets.compare_digest(str(expected), code):
            return Response({'code': ['验证码错误。']}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete(key)
        return Response({'ok': True}, status=status.HTTP_200_OK)


class PasswordResetView(APIView):
    """
    允许未登录用户通过 邮箱 + 验证码 重置密码。
    """

    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key='ip', rate='5/m', block=True))
    def post(self, request):
        email = str(request.data.get('email') or '').strip()
        code = str(request.data.get('code') or '').strip()
        new_password = str(request.data.get('new_password') or '').strip()

        if not email or not code or not new_password:
            return Response({'detail': '缺少必要参数 (email, code, new_password)。'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. 校验验证码 (注意 purpose 要对应)
        # 客户端请求发验证码时，purpose 应该是 'reset_password'
        key = _email_code_cache_key(email, purpose='reset_password')
        expected = cache.get(key)
        if not expected:
            return Response({'detail': '验证码已过期或不存在。'}, status=status.HTTP_400_BAD_REQUEST)

        import secrets

        if not secrets.compare_digest(str(expected), code):
            return Response({'code': ['验证码错误。']}, status=status.HTTP_400_BAD_REQUEST)

        # 2. 查找用户
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            # 为了安全通常不提示“用户不存在”，但为了用户体验这里明确提示
            return Response({'email': ['该邮箱未注册。']}, status=status.HTTP_400_BAD_REQUEST)

        # 3. 校验新密码强度
        try:
            from django.contrib.auth.password_validation import validate_password

            validate_password(new_password, user=user)
        except Exception as exc:
            try:
                from django.core.exceptions import ValidationError

                if isinstance(exc, ValidationError):
                    return Response({'new_password': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                pass
            return Response({'new_password': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        # 4. 重置密码
        user.set_password(new_password)
        user.save(update_fields=['password'])

        # 销毁验证码，防止重放
        cache.delete(key)

        # 5. 记录审计日志
        try:
            write_audit_log(
                actor=user,
                action='user.password.reset',
                target_type='user',
                target_id=str(user.id),
                request=request,
            )
        except Exception:
            pass

        return Response({'ok': True}, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user, context={'request': request}).data)


class MeCheckinView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        awarded, new_balance = try_award_checkin_points(user, points=2)
        return Response({'awarded': bool(awarded), 'delta': 2 if awarded else 0, 'plcoin': int(new_balance)}, status=status.HTTP_200_OK)


class MeBioView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        bio = str(request.data.get('bio') or '')
        bio = bio.strip()
        if len(bio) > 200:
            return Response({'bio': ['长度不能超过 200。']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            bio = _reject_angle_brackets(bio)
        except ValueError as exc:
            return Response({'bio': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        user.bio = bio
        user.save(update_fields=['bio'])
        write_audit_log(actor=user, action='user.bio.update', target_type='user', target_id=str(user.id), request=request)
        return Response({'bio': user.bio}, status=status.HTTP_200_OK)


class MeNicknameView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    COST = 3
    LIMIT_PER_YEAR = 12

    def post(self, request):
        user = request.user
        nickname = str(request.data.get('nickname') or '').strip()
        if not nickname:
            return Response({'nickname': ['必填。']}, status=status.HTTP_400_BAD_REQUEST)
        if len(nickname) > 20:
            return Response({'nickname': ['长度不能超过 20。']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            nickname = _reject_angle_brackets(nickname)
        except ValueError as exc:
            return Response({'nickname': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        used = _count_audit_actions(user, 'user.nickname.update')
        if used >= self.LIMIT_PER_YEAR:
            return Response({'detail': '本年度昵称修改次数已用完。'}, status=status.HTTP_400_BAD_REQUEST)

        cost = int(self.COST)
        points = int(getattr(user, 'activity_score', 0) or 0)
        if points < cost:
            return Response({'detail': 'PLCoin 不足，无法修改昵称。'}, status=status.HTTP_400_BAD_REQUEST)

        if (getattr(user, 'nickname', '') or '').strip() == nickname:
            return Response({'nickname': nickname, 'plcoin': points, 'used': used, 'limit': self.LIMIT_PER_YEAR}, status=status.HTTP_200_OK)

        user.nickname = nickname
        user.activity_score = points - cost
        user.save(update_fields=['nickname', 'activity_score'])

        write_audit_log(
            actor=user,
            action='user.nickname.update',
            target_type='user',
            target_id=str(user.id),
            request=request,
            metadata={'cost': cost, 'nickname': nickname},
        )

        return Response(
            {
                'nickname': user.nickname,
                'plcoin': int(user.activity_score),
                'used': used + 1,
                'limit': self.LIMIT_PER_YEAR,
                'cost': cost,
            },
            status=status.HTTP_200_OK,
        )


class MeUsernameView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    COST = 10
    LIMIT_PER_YEAR = 4

    def post(self, request):
        user = request.user
        username_before = (getattr(user, 'username', '') or '')
        username = str(request.data.get('username') or '').strip().lower()
        if not username:
            return Response({'username': ['必填。']}, status=status.HTTP_400_BAD_REQUEST)
        if len(username) > 20:
            return Response({'username': ['长度不能超过 20。']}, status=status.HTTP_400_BAD_REQUEST)
        if not username.startswith('@'):
            return Response({'username': ['必须以 @ 开头。']}, status=status.HTTP_400_BAD_REQUEST)

        import re

        if not re.match(r'^@[A-Za-z0-9_]+$', username):
            return Response({'username': ['仅允许字母/数字/下划线。']}, status=status.HTTP_400_BAD_REQUEST)

        # No-op (case-insensitive)
        if (getattr(user, 'username', '') or '').lower() == username:
            return Response({'username': user.username, 'plcoin': int(getattr(user, 'activity_score', 0) or 0)}, status=status.HTTP_200_OK)

        # Uniqueness (case-insensitive)
        if User.objects.filter(username__iexact=username).exclude(id=user.id).exists():
            return Response({'username': ['已被占用。']}, status=status.HTTP_400_BAD_REQUEST)

        used = _count_audit_actions(user, 'user.username.update')
        if used >= self.LIMIT_PER_YEAR:
            return Response({'detail': '本年度用户名修改次数已用完。'}, status=status.HTTP_400_BAD_REQUEST)

        cost = int(self.COST)
        points = int(getattr(user, 'activity_score', 0) or 0)
        if points < cost:
            return Response({'detail': 'PLCoin 不足，无法修改用户名。'}, status=status.HTTP_400_BAD_REQUEST)

        user.username = username
        user.activity_score = points - cost
        user.save(update_fields=['username', 'activity_score'])

        write_audit_log(
            actor=user,
            action='user.username.update',
            target_type='user',
            target_id=str(user.id),
            request=request,
            metadata={
                'cost': cost,
                # Backward compatible
                'username': username,
                # New fields for admin audit UI
                'username_before': username_before,
                'username_after': username,
            },
        )

        return Response(
            {
                'username': user.username,
                'plcoin': int(user.activity_score),
                'used': used + 1,
                'limit': self.LIMIT_PER_YEAR,
                'cost': cost,
            },
            status=status.HTTP_200_OK,
        )


class MePasswordChangeView(APIView):
    """Change current user's primary password.

    This is a sensitive operation; the client should present a second confirmation.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = str(request.data.get('current_password') or '')
        new_password1 = str(request.data.get('new_password1') or '')
        new_password2 = str(request.data.get('new_password2') or '')

        if not current_password:
            return Response({'current_password': ['必填。']}, status=status.HTTP_400_BAD_REQUEST)
        if not user.check_password(current_password):
            return Response({'current_password': ['密码错误。']}, status=status.HTTP_400_BAD_REQUEST)

        if not new_password1:
            return Response({'new_password1': ['必填。']}, status=status.HTTP_400_BAD_REQUEST)
        if new_password1 != new_password2:
            return Response({'new_password2': ['两次输入不一致。']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from django.contrib.auth.password_validation import validate_password

            validate_password(new_password1, user=user)
        except Exception as exc:
            try:
                from django.core.exceptions import ValidationError

                if isinstance(exc, ValidationError):
                    return Response({'new_password1': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                pass
            return Response({'new_password1': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password1)
        user.save(update_fields=['password'])

        write_audit_log(
            actor=user,
            action='user.password.change',
            target_type='user',
            target_id=str(user.id),
            request=request,
        )

        return Response({'ok': True}, status=status.HTTP_200_OK)
class MeEmailVerifyCodeSendView(APIView):
    """Reserve API: send a verification code to an email.

    Notes:
    - In DEBUG, if email sending is not configured, returns the code for dev use.
    - In production, if email sending fails, returns 503.
    """

    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(ratelimit(key='ip', rate='10/m', block=True))
    def post(self, request):
        email = str(request.data.get('email') or '').strip()
        purpose = str(request.data.get('purpose') or 'generic').strip()[:32] or 'generic'

        if not email:
            return Response({'email': ['必填。']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from django.core.validators import validate_email

            validate_email(email)
        except Exception:
            return Response({'email': ['邮箱格式不正确。']}, status=status.HTTP_400_BAD_REQUEST)

        import secrets

        code = str(secrets.randbelow(1_000_000)).zfill(6)
        ttl_seconds = 10 * 60
        cache.set(_email_code_cache_key(email, purpose=purpose), code, timeout=ttl_seconds)

        # Best-effort sending. If not configured, dev can still proceed.
        sent = False
        try:
            from django.core.mail import send_mail

            subject = '验证码'
            message = f"你的验证码是：{code}（10分钟内有效）"
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', None) or ''
            send_mail(subject, message, from_email, [email], fail_silently=False)
            sent = True
        except Exception:
            sent = False

        write_audit_log(
            actor=request.user,
            action='user.email_code.send',
            target_type='user',
            target_id=str(getattr(request.user, 'id', '')),
            request=request,
            metadata={'purpose': purpose, 'email': email, 'sent': bool(sent)},
        )

        if sent:
            return Response({'ok': True}, status=status.HTTP_200_OK)

        if getattr(settings, 'DEBUG', False):
            return Response({'ok': True, 'dev_code': code}, status=status.HTTP_200_OK)

        return Response({'detail': 'Email sending is not configured.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class MeEmailVerifyCodeVerifyView(APIView):
    """Reserve API: verify an email code previously sent."""

    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(ratelimit(key='ip', rate='30/m', block=True))
    def post(self, request):
        email = str(request.data.get('email') or '').strip()
        code = str(request.data.get('code') or '').strip()
        purpose = str(request.data.get('purpose') or 'generic').strip()[:32] or 'generic'

        if not email:
            return Response({'email': ['必填。']}, status=status.HTTP_400_BAD_REQUEST)
        if not code:
            return Response({'code': ['必填。']}, status=status.HTTP_400_BAD_REQUEST)

        key = _email_code_cache_key(email, purpose=purpose)
        expected = cache.get(key)
        if not expected:
            return Response({'detail': '验证码已过期或不存在。'}, status=status.HTTP_400_BAD_REQUEST)

        import secrets

        if not secrets.compare_digest(str(expected), code):
            return Response({'code': ['验证码错误。']}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete(key)

        write_audit_log(
            actor=request.user,
            action='user.email_code.verify',
            target_type='user',
            target_id=str(getattr(request.user, 'id', '')),
            request=request,
            metadata={'purpose': purpose, 'email': email},
        )

        return Response({'ok': True}, status=status.HTTP_200_OK)


class MePostsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from forum.models import Post
        from forum.serializers import PostSerializer

        qs = (
            Post.objects.filter(author=request.user)
            .select_related('board', 'author', 'reviewed_by')
            .prefetch_related('resource__links')
            .order_by('-created_at', '-id')
        )
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        ser = PostSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(ser.data)


class MeAvatarView(APIView):
    """Avatar management for the current user.

    备注（为后续功能预留）：
    - 该接口专门用于“头像弹窗”。未来如果要做：预设头像、头像框、历史头像、审核、冷却时间等，
      建议继续扩展本接口的返回结构，而不是污染 /api/me/。
    - 积分字段目前复用 User.activity_score（站内积分/活跃值）。
    - 规则：首次设置头像免费；非首次更换头像按设置扣积分。
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def _avatar_url(self, request, user) -> str:
        avatar = getattr(user, 'avatar', None)
        if not avatar:
            return ''
        try:
            return request.build_absolute_uri(avatar.url)
        except Exception:
            return ''

    def _change_cost(self, user) -> int:
        # 首次设置头像免费；后续更换头像扣积分。
        if not getattr(user, 'avatar', None):
            return 0
        return int(getattr(settings, 'AVATAR_CHANGE_COST', 10))

    def get(self, request):
        user = request.user
        cost = self._change_cost(user)
        points = int(getattr(user, 'activity_score', 0) or 0)
        return Response(
            {
                'avatar_url': self._avatar_url(request, user),
                'points': points,
                'change_cost': cost,
                'can_change': points >= cost,
                'has_avatar': bool(getattr(user, 'avatar', None)),
            }
        )

    def post(self, request):
        user = request.user

        uploaded = request.FILES.get('avatar')
        if not uploaded:
            return Response({'avatar': ['请上传头像文件。']}, status=status.HTTP_400_BAD_REQUEST)

        # 复用论坛图片安全处理（限制 20MB、仅 JPEG/PNG/WEBP、重编码）。
        # 备注：后续如果要对头像做更严格的尺寸限制，可以在 image_utils 增加可选参数。
        from forum.image_utils import validate_and_process_uploaded_image

        processed = validate_and_process_uploaded_image(uploaded_file=uploaded, field_name='avatar')
        processed.content.name = f"avatar.{processed.ext}"

        cost = self._change_cost(user)
        points = int(getattr(user, 'activity_score', 0) or 0)
        if cost > 0 and points < cost:
            return Response({'detail': '积分不足，无法更换头像。'}, status=status.HTTP_400_BAD_REQUEST)

        # Save avatar + deduct points atomically-ish (single row update).
        user.avatar = processed.content
        if cost > 0:
            user.activity_score = max(0, points - cost)
        user.save(update_fields=['avatar', 'activity_score'])

        write_audit_log(
            actor=user,
            action='user.avatar.update',
            target_type='user',
            target_id=str(user.id),
            request=request,
            metadata={'cost': cost},
        )

        return Response(
            {
                'avatar_url': self._avatar_url(request, user),
                'points': int(getattr(user, 'activity_score', 0) or 0),
                'change_cost': self._change_cost(user),
                'has_avatar': bool(getattr(user, 'avatar', None)),
            },
            status=status.HTTP_200_OK,
        )


class PasswordCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key='ip', rate='30/m', block=True))
    def post(self, request):
        # Optional context: username/email helps Django's similarity validator.
        password = request.data.get('password')
        username = (request.data.get('username') or '')
        email = (request.data.get('email') or '')

        if not password:
            return Response({'password': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)

        # Provide a lightweight user object for validators that need it.
        user = User(username=username, email=email)

        try:
            # Reuse the same validation logic as registration.
            from django.contrib.auth.password_validation import validate_password

            validate_password(password, user=user)
        except Exception as exc:
            # Django raises ValidationError; keep response DRF-friendly.
            try:
                from django.core.exceptions import ValidationError

                if isinstance(exc, ValidationError):
                    return Response({'password': exc.messages}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                pass
            # Fallback
            return Response({'password': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'ok': True})


class UserFollowToggleView(APIView):
    """Toggle follow/unfollow for a user.

    Used by:
    - post detail: follow the author
    - following feed: show posts by followed authors

    Notes:
    - This intentionally does NOT create notifications.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id: int):
        follower = request.user
        if getattr(follower, 'is_currently_banned', False):
            return Response({'detail': 'User is banned.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            target_id = int(user_id)
        except Exception:
            return Response({'detail': 'Invalid user id.'}, status=status.HTTP_400_BAD_REQUEST)

        if follower.id == target_id:
            return Response({'detail': 'Cannot follow yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target = User.objects.get(id=target_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        obj = UserFollow.objects.filter(follower_id=follower.id, following_id=target.id).first()
        if obj is not None:
            obj.delete()
            following = False
            audit_action = 'user.unfollow'
        else:
            UserFollow.objects.create(follower_id=follower.id, following_id=target.id)
            following = True
            audit_action = 'user.follow'

        write_audit_log(
            actor=follower,
            action=audit_action,
            target_type='user',
            target_id=str(target.id),
            request=request,
        )

        followers_count = UserFollow.objects.filter(following_id=target.id).count()
        return Response({'following': following, 'followers_count': followers_count}, status=status.HTTP_200_OK)


class UserViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Public user profiles + self profile.

    Endpoints:
    - GET /api/users/<pid>/        (public)
    - GET/PATCH /api/users/me/     (auth)
    - POST /api/users/<pid>/follow/ (auth)
    """

    permission_classes = [permissions.AllowAny]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    lookup_field = 'pid'
    # PID is a system-generated numeric string (may include leading zeros).
    lookup_value_regex = r'\d{1,8}'

    def get_queryset(self):
        qs = (
            User.objects.all()
            .annotate(
                followers_count=Count('follower_users', distinct=True),
                following_count=Count('following_users', distinct=True),
            )
        )

        req_user = getattr(self.request, 'user', None)
        if req_user is not None and getattr(req_user, 'is_authenticated', False):
            qs = qs.annotate(
                is_following=Exists(
                    UserFollow.objects.filter(
                        follower_id=req_user.id,
                        following_id=OuterRef('id'),
                    )
                )
            )
        else:
            qs = qs.annotate(is_following=Value(False, output_field=BooleanField()))

        return qs.order_by('id')

    def get_serializer_class(self):
        if self.action == 'me':
            return UserSelfSerializer
        return PublicUserSerializer

    def get_permissions(self):
        if self.action in ('me', 'follow'):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_object(self):
        pid = str(self.kwargs.get(self.lookup_field) or '').strip()
        qs = self.filter_queryset(self.get_queryset())
        obj = get_object_or_404(qs, pid=pid)
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        # Ensure count annotations (followers_count/following_count) are present.
        user = self.get_queryset().filter(pk=request.user.pk).first() or request.user
        if request.method == 'GET':
            ser = self.get_serializer(user, context={'request': request})
            return Response(ser.data, status=status.HTTP_200_OK)

        ser = self.get_serializer(request.user, data=request.data, partial=True, context={'request': request})
        ser.is_valid(raise_exception=True)
        ser.save()

        user = self.get_queryset().filter(pk=request.user.pk).first() or request.user
        return Response(self.get_serializer(user, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='follow')
    def follow(self, request, pid=None):
        """Toggle follow/unfollow for a user by PID."""

        follower = request.user
        if getattr(follower, 'is_currently_banned', False):
            return Response({'detail': 'User is banned.'}, status=status.HTTP_403_FORBIDDEN)

        target = self.get_object()
        if follower.id == target.id:
            return Response({'detail': 'Cannot follow yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        obj = UserFollow.objects.filter(follower_id=follower.id, following_id=target.id).first()
        if obj is not None:
            obj.delete()
            following = False
            audit_action = 'user.unfollow'
        else:
            UserFollow.objects.create(follower_id=follower.id, following_id=target.id)
            following = True
            audit_action = 'user.follow'

        write_audit_log(
            actor=follower,
            action=audit_action,
            target_type='user',
            target_id=str(target.pid or ''),
            request=request,
        )

        followers_count = UserFollow.objects.filter(following_id=target.id).count()
        return Response({'following': following, 'followers_count': followers_count}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='recommended')
    def recommended(self, request):
        """Recommended users for sidebar.

        Rules:
        - If user is authenticated and follows >= 5 users:
          recommend users by common tags in followed users' posts.
        - Otherwise: simple + stable fallback: top users by followers_count.
        """

        base_qs = self.get_queryset().filter(is_active=True)
        me = request.user if (request.user and request.user.is_authenticated) else None
        if me is not None:
            base_qs = base_qs.exclude(id=me.id)

        # Default: top by followers_count.
        def fallback(exclude_ids=None):
            qs = base_qs
            if exclude_ids:
                qs = qs.exclude(id__in=list(exclude_ids))
            return qs.order_by('-followers_count', 'id')[:5]

        # Tag-based recommendation for users with a meaningful following graph.
        if me is not None:
            followed_ids_qs = UserFollow.objects.filter(follower_id=me.id).values_list('following_id', flat=True)
            followed_count = UserFollow.objects.filter(follower_id=me.id).count()

            if followed_count >= 5:
                try:
                    from forum.models import Post, Tag

                    since = timezone.now() - timedelta(days=180)
                    top_tag_names = list(
                        Tag.objects.filter(
                            posts__status=Post.Status.PUBLISHED,
                            posts__is_deleted=False,
                            posts__author_id__in=followed_ids_qs,
                            posts__created_at__gte=since,
                        )
                        .annotate(cnt=Count('posts', distinct=True))
                        .order_by('-cnt', 'name')
                        .values_list('name', flat=True)[:5]
                    )

                    if top_tag_names:
                        tag_post_filter = Q(
                            posts__status=Post.Status.PUBLISHED,
                            posts__is_deleted=False,
                            posts__created_at__gte=since,
                            posts__tags__name__in=top_tag_names,
                        )

                        cand = (
                            base_qs.exclude(id__in=followed_ids_qs)
                            .annotate(tag_score=Count('posts', filter=tag_post_filter, distinct=True))
                            .filter(tag_score__gt=0)
                            .order_by('-tag_score', '-followers_count', 'id')
                        )

                        items = list(cand[:5])
                        if len(items) < 5:
                            extra = list(fallback(exclude_ids=set([u.id for u in items]) | set(followed_ids_qs)))
                            items = (items + extra)[:5]
                        ser = self.get_serializer(items, many=True, context={'request': request})
                        return Response(ser.data, status=status.HTTP_200_OK)
                except Exception:
                    # Never break sidebar if recommendation logic fails.
                    pass

        ser = self.get_serializer(fallback(), many=True, context={'request': request})
        return Response(ser.data, status=status.HTTP_200_OK)
