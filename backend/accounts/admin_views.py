from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import write_audit_log
from .models import AuditLog
from .permissions import IsAdmin
from .serializers import AdminUserSerializer
from .models import StaffBoardPermission

User = get_user_model()


class AdminUserListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        qs = User.objects.order_by('-date_joined')[:200]
        return Response(AdminUserSerializer(qs, many=True).data)


class AdminBanUserView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, user_id: int):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

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


class AdminAuditLogListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        qs = AuditLog.objects.select_related('actor').order_by('-created_at')[:200]
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
            for log in qs
        ]
        return Response(data)


class AdminGrantStaffView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, user_id: int):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

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

        perms = (
            StaffBoardPermission.objects.filter(user=target)
            .select_related('board')
            .order_by('board_id')
        )
        data = {
            'staff_board_scoped': bool(getattr(target, 'staff_board_scoped', False)),
            'permissions': [
                {
                    'board_id': p.board_id,
                    'board_slug': getattr(p.board, 'slug', ''),
                    'board_title': getattr(p.board, 'title', ''),
                    'can_moderate': bool(p.can_moderate),
                    'can_delete': bool(p.can_delete),
                }
                for p in perms
            ],
        }
        return Response(data)

    def put(self, request, user_id: int):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

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
