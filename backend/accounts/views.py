from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import write_audit_log

from .models import UserFollow
from .serializers import MeSerializer, RegisterSerializer


User = get_user_model()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    @method_decorator(ratelimit(key='ip', rate='10/m', block=True))
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({'id': user.id, 'username': user.username}, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user, context={'request': request}).data)


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
