from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.audit import write_audit_log

from .models import UserFollow
from .serializers import MeSerializer, RegisterSerializer
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
        return Response(
            {'id': user.id, 'pid': getattr(user, 'pid', ''), 'nickname': getattr(user, 'nickname', ''), 'username': user.username},
            status=status.HTTP_201_CREATED,
        )


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
            metadata={'cost': cost, 'username': username},
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
