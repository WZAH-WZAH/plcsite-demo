import hmac
import os

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class SifangCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # 可选加固：如果你在环境变量中设置了 DJANGO_PAYMENTS_WEBHOOK_SECRET，
        # 则必须在请求头带上：X-Webhook-Secret: <secret>
        expected = os.environ.get('DJANGO_PAYMENTS_WEBHOOK_SECRET')
        if expected:
            provided = request.META.get('HTTP_X_WEBHOOK_SECRET') or ''
            if not hmac.compare_digest(provided, expected):
                return Response({'detail': 'Invalid webhook secret.'}, status=status.HTTP_403_FORBIDDEN)

        # NOTE: 这里只是占位，后续需要：
        # 1) 验签 2) 订单幂等 3) 记录支付流水 4) 升级会员/加积分
        return Response({'ok': True, 'detail': 'callback placeholder'}, status=status.HTTP_200_OK)
