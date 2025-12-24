from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import write_audit_log
from .models import AuditLog
from .permissions import IsAdmin
from .serializers import AdminUserSerializer
from .models import StaffBoardPermission
from forum.models import Board
from .services import staff_allowed_board_ids

User = get_user_model()


def _rank(u) -> int:
    if not u:
        return 0
    if getattr(u, 'is_superuser', False):
        return 3
    if getattr(u, 'is_staff', False):
        return 2
    return 1


def _assert_can_manage(actor, target) -> None:
    """Actor can only manage strictly lower-ranked users."""

    from rest_framework.exceptions import PermissionDenied

    if _rank(actor) <= _rank(target):
        raise PermissionDenied('Not allowed.')


class AdminUserListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        qs = User.objects.order_by('-date_joined')
        # Normal staff can only view normal users.
        if request.user and request.user.is_authenticated and (not getattr(request.user, 'is_superuser', False)):
            qs = qs.filter(is_staff=False, is_superuser=False)
        qs = qs[:200]
        return Response(AdminUserSerializer(qs, many=True).data)


class AdminBanUserView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, user_id: int):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        _assert_can_manage(request.user, target)

        reason = (request.data.get('reason') or '')[:200]
        days = request.data.get('days')
        until = None
        if days is not None:
            try:
                days_int = int(days)
                until = timezone.now() + timedelta(days=max(0, days_int))
            except (TypeError, ValueError):
                return Response({'detail': 'Invalid days.'}, status=status.HTTP_400_BAD_REQUEST)

        target.is_banned = True
        target.banned_until = until
        target.ban_reason = reason
        target.save(update_fields=['is_banned', 'banned_until', 'ban_reason'])

        write_audit_log(
            actor=request.user,
            action='user.ban',
            target_type='user',
            target_id=str(target.id),
            request=request,
            metadata={'until': until.isoformat() if until else None, 'reason': reason},
        )

        return Response(AdminUserSerializer(target).data)


class AdminUnbanUserView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, user_id: int):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        _assert_can_manage(request.user, target)

        target.is_banned = False
        target.banned_until = None
        target.ban_reason = ''
        target.save(update_fields=['is_banned', 'banned_until', 'ban_reason'])

        write_audit_log(
            actor=request.user,
            action='user.unban',
            target_type='user',
            target_id=str(target.id),
            request=request,
        )

        return Response(AdminUserSerializer(target).data)


class AdminMuteUserView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, user_id: int):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        _assert_can_manage(request.user, target)

        reason = (request.data.get('reason') or '')[:200]
        days = request.data.get('days')
        until = None
        if days is not None:
            try:
                days_int = int(days)
                until = timezone.now() + timedelta(days=max(0, days_int))
            except (TypeError, ValueError):
                return Response({'detail': 'Invalid days.'}, status=status.HTTP_400_BAD_REQUEST)

        target.is_muted = True
        target.muted_until = until
        target.mute_reason = reason
        target.save(update_fields=['is_muted', 'muted_until', 'mute_reason'])

        write_audit_log(
            actor=request.user,
            action='user.mute',
            target_type='user',
            target_id=str(target.id),
            request=request,
            metadata={'until': until.isoformat() if until else None, 'reason': reason},
        )

        return Response(AdminUserSerializer(target).data)


class AdminUnmuteUserView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, user_id: int):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        _assert_can_manage(request.user, target)

        target.is_muted = False
        target.muted_until = None
        target.mute_reason = ''
        target.save(update_fields=['is_muted', 'muted_until', 'mute_reason'])

        write_audit_log(
            actor=request.user,
            action='user.unmute',
            target_type='user',
            target_id=str(target.id),
            request=request,
        )

        return Response(AdminUserSerializer(target).data)


class AdminAuditLogListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        include_archived = str(request.query_params.get('include_archived') or '').strip().lower() in ('1', 'true', 'yes')
        now = timezone.now()
        month_ago = now - timedelta(days=30)

        # Archived logs are only visible to superusers.
        if include_archived and (not getattr(request.user, 'is_superuser', False)):
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)

        qs = AuditLog.objects.select_related('actor').order_by('-created_at')
        if not include_archived:
            qs = qs.filter(created_at__gte=month_ago)

        # Server-side filtering (so the UI can fetch fewer rows).
        # Supported:
        # - actor: username (with or without leading '@') OR numeric user id
        # - actor_username: username (with or without leading '@')
        # - actor_id: numeric user id
        # - q: alias of actor
        actor_raw = (request.query_params.get('actor') or request.query_params.get('q') or '').strip()
        actor_username_raw = (request.query_params.get('actor_username') or '').strip()
        actor_id_raw = (request.query_params.get('actor_id') or '').strip()

        if actor_id_raw:
            try:
                qs = qs.filter(actor_id=int(actor_id_raw))
            except (TypeError, ValueError):
                qs = qs.none()
        elif actor_username_raw:
            u = actor_username_raw
            if u and not u.startswith('@'):
                u = '@' + u
            qs = qs.filter(actor__username__iexact=u)
        elif actor_raw:
            if actor_raw.isdigit():
                qs = qs.filter(actor_id=int(actor_raw))
            else:
                u = actor_raw
                if u and not u.startswith('@'):
                    u = '@' + u
                qs = qs.filter(actor__username__iexact=u)

        # Visibility for non-superuser staff.
        # Requirement: staff can only see:
        # - logs within boards they have permissions for, OR
        # - logs they acted on themselves (even if not tied to a board)
        allowed_board_ids: set[int] | None = None
        if request.user and request.user.is_authenticated and (not getattr(request.user, 'is_superuser', False)):
            a1 = staff_allowed_board_ids(request.user, for_action='moderate')
            a2 = staff_allowed_board_ids(request.user, for_action='delete')
            allowed_board_ids = set([*a1, *a2])

        # Pull more rows then filter in Python by board permissions.
        logs = list(qs[:400])
        if allowed_board_ids is not None:
            # Resolve board_id for each log.
            from forum.models import Post, Comment
            from resources.models import ResourceEntry

            post_ids = set()
            comment_ids = set()
            resource_ids = set()
            for log in logs:
                if log.target_type == 'post' and str(log.target_id or '').isdigit():
                    post_ids.add(int(log.target_id))
                elif log.target_type == 'comment' and str(log.target_id or '').isdigit():
                    comment_ids.add(int(log.target_id))
                elif log.target_type == 'resource' and str(log.target_id or '').isdigit():
                    resource_ids.add(int(log.target_id))
                else:
                    mid = (log.metadata or {})
                    if str(mid.get('post_id') or '').isdigit():
                        post_ids.add(int(mid.get('post_id')))
                    if str(mid.get('resource_id') or '').isdigit():
                        resource_ids.add(int(mid.get('resource_id')))

            post_board = {int(p.id): int(p.board_id) for p in Post.objects.filter(id__in=post_ids).values('id', 'board_id')}
            comment_post = {int(c.id): int(c.post_id) for c in Comment.objects.filter(id__in=comment_ids).values('id', 'post_id')}
            resource_post = {int(r.id): int(r.post_id) for r in ResourceEntry.objects.filter(id__in=resource_ids).values('id', 'post_id')}

            def resolve_board_id(log) -> int | None:
                mid = (log.metadata or {})
                if str(mid.get('board_id') or '').isdigit():
                    return int(mid.get('board_id'))
                if log.target_type == 'post' and str(log.target_id or '').isdigit():
                    return post_board.get(int(log.target_id))
                if log.target_type == 'comment' and str(log.target_id or '').isdigit():
                    pid = comment_post.get(int(log.target_id))
                    return post_board.get(pid) if pid else None
                if log.target_type == 'resource' and str(log.target_id or '').isdigit():
                    pid = resource_post.get(int(log.target_id))
                    return post_board.get(pid) if pid else None
                if str(mid.get('post_id') or '').isdigit():
                    return post_board.get(int(mid.get('post_id')))
                if str(mid.get('resource_id') or '').isdigit():
                    pid = resource_post.get(int(mid.get('resource_id')))
                    return post_board.get(pid) if pid else None
                return None

            filtered = []
            for log in logs:
                # Always allow the actor's own logs.
                if getattr(log, 'actor_id', None) == getattr(request.user, 'id', None):
                    filtered.append(log)
                    continue

                bid = resolve_board_id(log)
                if bid is None:
                    continue
                if bid in allowed_board_ids:
                    filtered.append(log)

            logs = filtered

        logs = logs[:200]
        data = [
            {
                'id': log.id,
                'created_at': log.created_at,
                # Keep legacy 'actor' for backward compatibility (username).
                'actor': log.actor.username if log.actor else None,
                'actor_username': log.actor.username if log.actor else None,
                'actor_nickname': log.actor.nickname if log.actor else None,
                'actor_pid': log.actor.pid if log.actor else None,
                'actor_id': log.actor.id if log.actor else None,
                'action': log.action,
                'target_type': log.target_type,
                'target_id': log.target_id,
                'ip': log.ip,
                'metadata': log.metadata,
            }
            for log in logs
        ]
        return Response(data)


class AdminGrantStaffView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id: int):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        _assert_can_manage(request.user, target)

        if target.is_superuser:
            # already at top; nothing to do
            target.is_staff = True
        else:
            target.is_staff = True
        target.save(update_fields=['is_staff'])

        write_audit_log(
            actor=request.user,
            action='user.grant_staff',
            target_type='user',
            target_id=str(target.id),
            request=request,
        )

        return Response(AdminUserSerializer(target).data)


class AdminRevokeStaffView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id: int):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        _assert_can_manage(request.user, target)

        if target.is_superuser:
            return Response({'detail': 'Cannot revoke staff from a superuser.'}, status=status.HTTP_400_BAD_REQUEST)

        target.is_staff = False
        target.save(update_fields=['is_staff'])

        write_audit_log(
            actor=request.user,
            action='user.revoke_staff',
            target_type='user',
            target_id=str(target.id),
            request=request,
        )

        return Response(AdminUserSerializer(target).data)


class AdminUserBoardPermsView(APIView):
    """Superuser configures staff permissions per board."""

    permission_classes = [IsAdmin]

    def get(self, request, user_id: int):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        _assert_can_manage(request.user, target)

        boards = list(Board.objects.order_by('id'))
        perms_qs = (
            StaffBoardPermission.objects.filter(user=target)
            .select_related('board')
            .order_by('board_id')
        )
        perms_by_board_id = {int(p.board_id): p for p in perms_qs}
        data = {
            'staff_board_scoped': bool(getattr(target, 'staff_board_scoped', False)),
            'permissions': [
                {
                    'board_id': b.id,
                    # Frontend expects these keys.
                    'slug': getattr(b, 'slug', ''),
                    'title': getattr(b, 'title', ''),
                    'can_moderate': bool(getattr(perms_by_board_id.get(int(b.id)), 'can_moderate', False)),
                    'can_delete': bool(getattr(perms_by_board_id.get(int(b.id)), 'can_delete', False)),
                }
                for b in boards
            ],
        }
        return Response(data)

    def put(self, request, user_id: int):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        _assert_can_manage(request.user, target)

        staff_board_scoped = bool(request.data.get('staff_board_scoped', False))
        items = request.data.get('permissions')
        if items is None:
            items = []
        if not isinstance(items, list):
            return Response({'detail': 'permissions must be a list.'}, status=status.HTTP_400_BAD_REQUEST)

        cleaned: list[dict] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            try:
                board_id = int(raw.get('board_id'))
            except Exception:
                continue
            cleaned.append(
                {
                    'board_id': board_id,
                    'can_moderate': bool(raw.get('can_moderate', False)),
                    'can_delete': bool(raw.get('can_delete', False)),
                }
            )

        # Only persist rows that actually grant something, and ignore unknown boards.
        valid_ids = set(Board.objects.filter(id__in=[c['board_id'] for c in cleaned]).values_list('id', flat=True))
        cleaned = [
            c
            for c in cleaned
            if (c['board_id'] in valid_ids) and (c['can_moderate'] or c['can_delete'])
        ]

        # Persist
        from django.db import transaction

        with transaction.atomic():
            target.staff_board_scoped = staff_board_scoped
            target.save(update_fields=['staff_board_scoped'])
            StaffBoardPermission.objects.filter(user=target).delete()
            StaffBoardPermission.objects.bulk_create(
                [
                    StaffBoardPermission(
                        user=target,
                        board_id=item['board_id'],
                        can_moderate=item['can_moderate'],
                        can_delete=item['can_delete'],
                    )
                    for item in cleaned
                ]
            )

        write_audit_log(
            actor=request.user,
            action='user.staff_board_perms.update',
            target_type='user',
            target_id=str(target.id),
            request=request,
            metadata={'staff_board_scoped': staff_board_scoped, 'count': len(cleaned)},
        )

        return self.get(request, user_id=user_id)
