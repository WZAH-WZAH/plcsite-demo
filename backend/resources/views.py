from django.db.models import Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.audit import write_audit_log
from accounts.permissions import IsModerator
from accounts.services import staff_allowed_board_ids, staff_can_delete_board, staff_can_moderate_board, try_consume_download_quota

from .models import DownloadEvent, ResourceEntry, ResourceLink
from .permissions import IsResourceOwnerOrStaff, IsResourceOwnerOrStaffOrReadOnly
from .serializers import ResourceEntrySerializer, ResourceLinkSerializer


def _get_client_ip(request) -> str | None:
    # Baseline: prefer REMOTE_ADDR; do not trust X-Forwarded-For by default.
    return request.META.get('REMOTE_ADDR')


class ResourceEntryViewSet(viewsets.ModelViewSet):
    queryset = ResourceEntry.objects.select_related('created_by', 'reviewed_by').prefetch_related('links')
    serializer_class = ResourceEntrySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsResourceOwnerOrStaffOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return qs
        if user.is_authenticated:
            return qs.filter(Q(status=ResourceEntry.Status.PUBLISHED) | Q(created_by=user))
        return qs.filter(status=ResourceEntry.Status.PUBLISHED)

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, 'is_currently_muted', False):
            raise PermissionDenied('User is muted.')
        status_value = ResourceEntry.Status.PUBLISHED if user.is_staff else ResourceEntry.Status.PENDING
        serializer.save(created_by=user, status=status_value)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        user = request.user
        if user and user.is_authenticated and getattr(user, 'is_staff', False) and (not getattr(user, 'is_superuser', False)):
            is_owner = getattr(obj, 'created_by_id', None) == getattr(user, 'id', None)
            if not is_owner:
                board_id = getattr(getattr(obj, 'post', None), 'board_id', None)
                if not staff_can_delete_board(user, board_id):
                    raise PermissionDenied('Not allowed for this board.')
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='links/(?P<link_id>[^/.]+)/download', permission_classes=[permissions.IsAuthenticated])
    @method_decorator(ratelimit(key='ip', rate='30/m', block=True))
    def download(self, request, pk=None, link_id=None):
        resource = self.get_object()
        if getattr(request.user, 'is_currently_banned', False):
            return Response({'detail': 'Account is banned.'}, status=status.HTTP_403_FORBIDDEN)
        if (not request.user.is_staff) and resource.status != ResourceEntry.Status.PUBLISHED:
            return Response({'detail': 'Resource not published.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            link = resource.links.get(id=link_id, is_active=True)
        except ResourceLink.DoesNotExist:
            return Response({'detail': 'Link not found.'}, status=status.HTTP_404_NOT_FOUND)

        ok, used, remaining = try_consume_download_quota(request.user)
        if not ok:
            return Response(
                {'detail': 'Daily download limit reached.', 'downloads_today': used, 'remaining_today': remaining},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        DownloadEvent.objects.create(
            user=request.user,
            link=link,
            ip=_get_client_ip(request),
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:300],
        )

        write_audit_log(
            actor=request.user,
            action='download.consume',
            target_type='resource_link',
            target_id=str(link.id),
            request=request,
            metadata={'resource_id': resource.id, 'link_type': link.link_type},
        )

        return Response(
            {
                'url': link.url,
                'downloads_today': used,
                'remaining_today': remaining,
            }
        )

    @action(detail=False, methods=['get'], url_path='moderation/pending', permission_classes=[IsModerator])
    def pending(self, request):
        return Response({'detail': 'Resource moderation is disabled.'}, status=status.HTTP_410_GONE)

    @action(detail=True, methods=['post'], url_path='approve', permission_classes=[IsModerator])
    def approve(self, request, pk=None):
        return Response({'detail': 'Resource moderation is disabled.'}, status=status.HTTP_410_GONE)

    @action(detail=True, methods=['post'], url_path='reject', permission_classes=[IsModerator])
    def reject(self, request, pk=None):
        return Response({'detail': 'Resource moderation is disabled.'}, status=status.HTTP_410_GONE)


class ResourceLinkViewSet(viewsets.ModelViewSet):
    queryset = ResourceLink.objects.select_related('resource')
    serializer_class = ResourceLinkSerializer
    permission_classes = [IsResourceOwnerOrStaff]

    def get_queryset(self):
        qs = super().get_queryset().select_related('resource', 'resource__created_by')
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return qs
        if user.is_authenticated:
            return qs.filter(resource__created_by=user)
        return qs.none()

    def perform_create(self, serializer):
        resource = serializer.validated_data.get('resource')
        user = self.request.user
        user_id = getattr(user, 'id', None)
        if (not user.is_staff) and getattr(resource, 'created_by_id', None) != user_id:
            raise PermissionDenied('Not allowed.')
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        user = request.user
        if user and user.is_authenticated and getattr(user, 'is_staff', False) and (not getattr(user, 'is_superuser', False)):
            resource = getattr(obj, 'resource', None)
            is_owner = getattr(resource, 'created_by_id', None) == getattr(user, 'id', None)
            if not is_owner:
                board_id = getattr(getattr(resource, 'post', None), 'board_id', None)
                if not staff_can_delete_board(user, board_id):
                    raise PermissionDenied('Not allowed for this board.')
        return super().destroy(request, *args, **kwargs)
