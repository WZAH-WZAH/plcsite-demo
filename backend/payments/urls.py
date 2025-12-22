from django.urls import path

from .views import SifangCallbackView


urlpatterns = [
    # 预留：四方支付回调（后续按你选定的聚合支付/四方文档实现验签与幂等）
    path('payments/sifang/callback/', SifangCallbackView.as_view(), name='payments-sifang-callback'),
]
