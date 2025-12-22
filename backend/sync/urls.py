from django.urls import path

from .views import TgSyncPlaceholderView


urlpatterns = [
    # 预留：TG Bot 同步入口（建议由 bot 端调用；后续可改成消息队列/后台任务）
    path('sync/tg/push/', TgSyncPlaceholderView.as_view(), name='sync-tg-push'),
]
