from __future__ import annotations

from django.utils import timezone
from django.db import transaction

from .models import DailyDownloadStat, User


def get_or_create_today_stat(user: User) -> DailyDownloadStat:
    today = timezone.localdate()
    stat, _created = DailyDownloadStat.objects.get_or_create(user=user, date=today)
    return stat


def try_consume_download_quota(user: User) -> tuple[bool, int, int]:
    """Return (ok, used_today, remaining_today)."""
    if getattr(user, 'is_currently_banned', False):
        return False, 0, 0

    limit_today = int(user.daily_download_limit)
    today = timezone.localdate()

    with transaction.atomic():
        stat, _created = DailyDownloadStat.objects.select_for_update().get_or_create(user=user, date=today)
        used_today = int(stat.count)
        remaining = limit_today - used_today
        if remaining <= 0:
            return False, used_today, 0
        stat.count = used_today + 1
        stat.save(update_fields=['count'])
        return True, used_today + 1, max(0, limit_today - (used_today + 1))