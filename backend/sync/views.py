import hmac
import os

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class TgSyncPlaceholderView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # 可选加固：如果你在环境变量中设置了 DJANGO_TG_SYNC_SECRET，
        # 则必须在请求头带上：X-Webhook-Secret: <secret>
        expected = os.environ.get('DJANGO_TG_SYNC_SECRET')
        if expected:
            provided = request.META.get('HTTP_X_WEBHOOK_SECRET') or ''
            if not hmac.compare_digest(provided, expected):
                return Response({'detail': 'Invalid webhook secret.'}, status=status.HTTP_403_FORBIDDEN)

        # NOTE: 占位：后续我们会做成“bot 推送一条消息 -> 解析 -> 创建/更新资源/帖子”。
        return Response({'ok': True, 'detail': 'tg sync placeholder'}, status=status.HTTP_200_OK)
