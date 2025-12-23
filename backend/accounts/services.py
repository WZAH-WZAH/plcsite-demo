from __future__ import annotations

from django.utils import timezone
from django.db import transaction

from .models import DailyDownloadStat, DailyLoginStat, DailyPointStat, StaffBoardPermission, User


def get_or_create_today_stat(user: User) -> DailyDownloadStat:
    today = timezone.localdate()
    stat, _created = DailyDownloadStat.objects.get_or_create(user=user, date=today)
    return stat


def get_or_create_today_point_stat(user: User) -> DailyPointStat:
    today = timezone.localdate()
    stat, _created = DailyPointStat.objects.get_or_create(user=user, date=today)
    return stat


def record_login_day(user: User) -> None:
    """Record today's login (idempotent)."""

    today = timezone.localdate()
    DailyLoginStat.objects.get_or_create(user=user, date=today)


def get_login_days_count(user: User) -> int:
    return DailyLoginStat.objects.filter(user=user).count()


def _add_points(user: User, delta: int) -> int:
    delta_int = int(delta)
    if delta_int <= 0:
        return int(getattr(user, 'activity_score', 0) or 0)
    cur = int(getattr(user, 'activity_score', 0) or 0)
    user.activity_score = cur + delta_int
    user.save(update_fields=['activity_score'])
    return int(user.activity_score)


def try_award_checkin_points(user: User, *, points: int = 2) -> tuple[bool, int]:
    """Daily check-in. Returns (awarded, new_balance)."""

    today = timezone.localdate()
    with transaction.atomic():
        stat, _created = DailyPointStat.objects.select_for_update().get_or_create(user=user, date=today)
        if stat.checked_in:
            return False, int(getattr(user, 'activity_score', 0) or 0)
        stat.checked_in = True
        stat.save(update_fields=['checked_in'])
        return True, _add_points(user, points)


def try_award_post_points(
    user: User,
    *,
    points: int,
    daily_cap: int = 6,
) -> tuple[int, int]:
    """Award points for posting, respecting daily cap.

    Returns (awarded_points, new_balance).
    """

    today = timezone.localdate()
    points_int = max(0, int(points))
    cap_int = max(0, int(daily_cap))
    with transaction.atomic():
        stat, _created = DailyPointStat.objects.select_for_update().get_or_create(user=user, date=today)
        earned = int(stat.post_points_earned or 0)
        remaining = max(0, cap_int - earned)
        award = min(points_int, remaining)
        if award <= 0:
            return 0, int(getattr(user, 'activity_score', 0) or 0)
        stat.post_points_earned = earned + award
        stat.save(update_fields=['post_points_earned'])
        return award, _add_points(user, award)


def try_award_first_comment_bonus(user: User, *, points: int = 1) -> tuple[bool, int]:
    """Award a once-per-day bonus for the first comment."""

    today = timezone.localdate()
    with transaction.atomic():
        stat, _created = DailyPointStat.objects.select_for_update().get_or_create(user=user, date=today)
        if stat.got_first_comment_bonus:
            return False, int(getattr(user, 'activity_score', 0) or 0)
        stat.got_first_comment_bonus = True
        stat.save(update_fields=['got_first_comment_bonus'])
        return True, _add_points(user, points)


def try_award_first_favorite_bonus(user: User, *, points: int = 1) -> tuple[bool, int]:
    """Award a once-per-day bonus for the first favorite."""

    today = timezone.localdate()
    with transaction.atomic():
        stat, _created = DailyPointStat.objects.select_for_update().get_or_create(user=user, date=today)
        if stat.got_first_favorite_bonus:
            return False, int(getattr(user, 'activity_score', 0) or 0)
        stat.got_first_favorite_bonus = True
        stat.save(update_fields=['got_first_favorite_bonus'])
        return True, _add_points(user, points)


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


def staff_can_moderate_board(user: User, board_id: int | None) -> bool:
    if not board_id:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    if not getattr(user, 'is_staff', False):
        return False
    if not getattr(user, 'staff_board_scoped', False):
        return True
    return StaffBoardPermission.objects.filter(user=user, board_id=int(board_id), can_moderate=True).exists()


def staff_can_delete_board(user: User, board_id: int | None) -> bool:
    if not board_id:
        return False
    if getattr(user, 'is_superuser', False):
        return True
    if not getattr(user, 'is_staff', False):
        return False
    if not getattr(user, 'staff_board_scoped', False):
        return True
    return StaffBoardPermission.objects.filter(user=user, board_id=int(board_id), can_delete=True).exists()


def staff_allowed_board_ids(user: User, *, for_action: str) -> list[int]:
    """Return allowed board IDs for a scoped staff user.

    for_action: 'moderate' | 'delete'
    """

    if getattr(user, 'is_superuser', False):
        return []
    if not getattr(user, 'is_staff', False):
        return []
    if not getattr(user, 'staff_board_scoped', False):
        return []
    field = 'can_moderate' if for_action == 'moderate' else 'can_delete'
    qs = StaffBoardPermission.objects.filter(user=user).filter(**{field: True}).values_list('board_id', flat=True)
    return [int(x) for x in qs]