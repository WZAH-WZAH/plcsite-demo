from typing import Any, cast

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import MarkReadSerializer, NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.select_related('actor', 'post', 'comment').filter(recipient=self.request.user)

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        cnt = self.get_queryset().filter(is_read=False).count()
        return Response({'unread': cnt})

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request):
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        ids = data.get('ids') or []
        qs = self.get_queryset().filter(id__in=ids)
        updated = qs.update(is_read=True)
        return Response({'updated': updated}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'updated': updated}, status=status.HTTP_200_OK)
