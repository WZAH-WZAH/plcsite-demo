from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class User(AbstractUser):
	# Public identity
	# - pid: system-generated 8-digit numeric string (may include leading zeros)
	# - nickname: display name (can be duplicated)
	# - username: handle, stored with leading '@', case-insensitive unique (enforced by app logic/migration)
	pid = models.CharField(max_length=8, unique=True, null=True, blank=True, db_index=True)
	nickname = models.CharField(max_length=20, blank=True, default='')
	bio = models.CharField(max_length=200, blank=True, default='')

	activity_score = models.PositiveIntegerField(default=0)
	# 头像（个人中心改版用）。
	# 备注：
	# - 目前仅支持上传一张图片作为头像；后续可扩展为“头像框/挂件/预设头像”等。
	# - 前端在用户首次注册后会提示设置头像；首次设置不扣积分，后续更换可扣积分（见 /api/me/avatar/）。
	avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
	is_banned = models.BooleanField(default=False)
	banned_until = models.DateTimeField(null=True, blank=True)
	ban_reason = models.CharField(max_length=200, blank=True)

	# Mute (can read but cannot post/comment/upload resources)
	is_muted = models.BooleanField(default=False)
	muted_until = models.DateTimeField(null=True, blank=True)
	mute_reason = models.CharField(max_length=200, blank=True)

	# Secondary password (2FA-like step-up for high-risk actions)
	secondary_password_hash = models.CharField(max_length=200, blank=True, default='')
	secondary_verified_at = models.DateTimeField(null=True, blank=True)

	# Staff board permissions
	# - When False: staff users keep legacy behavior (can moderate/delete across all boards).
	# - When True: staff users can only moderate/delete boards explicitly granted.
	staff_board_scoped = models.BooleanField(default=False)

	@property
	def level(self) -> int:
		score = int(self.activity_score or 0)
		if score >= 5000:
			return 6
		if score >= 2000:
			return 5
		if score >= 800:
			return 4
		if score >= 300:
			return 3
		if score >= 100:
			return 2
		return 0

	@property
	def daily_download_limit(self) -> int:
		# Download quota is intentionally NOT tied to account level.
		return 3

	@property
	def is_currently_banned(self) -> bool:
		until = self.banned_until
		if self.is_banned:
			return until is None or until > timezone.now()
		if until is None:
			return False
		return until > timezone.now()

	@property
	def is_currently_muted(self) -> bool:
		until = self.muted_until
		if self.is_muted:
			return until is None or until > timezone.now()
		if until is None:
			return False
		return until > timezone.now()

	class Meta(AbstractUser.Meta):
		constraints = [
			models.UniqueConstraint(Lower('username'), name='accounts_user_username_lower_uniq'),
		]


class DailyDownloadStat(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_download_stats')
	date = models.DateField(default=timezone.localdate)
	count = models.PositiveIntegerField(default=0)

	class Meta:
		unique_together = (('user', 'date'),)
		indexes = [
			models.Index(fields=['user', 'date']),
		]

	def __str__(self) -> str:
		return f"{self.user_id}@{self.date}: {self.count}"


class DailyPointStat(models.Model):
	"""Per-user daily point earning state.

	We store a small amount of state so we can enforce daily caps and
	"first time today" bonuses efficiently.
	"""

	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_point_stats')
	date = models.DateField(default=timezone.localdate)
	post_points_earned = models.PositiveIntegerField(default=0)
	checked_in = models.BooleanField(default=False)
	got_first_comment_bonus = models.BooleanField(default=False)
	got_first_favorite_bonus = models.BooleanField(default=False)

	class Meta:
		unique_together = (('user', 'date'),)
		indexes = [
			models.Index(fields=['user', 'date']),
		]

	def __str__(self) -> str:
		return f"points:{self.user_id}@{self.date}"


class DailyLoginStat(models.Model):
	"""Tracks days a user has logged in (for cumulative login day count)."""

	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_login_stats')
	date = models.DateField(default=timezone.localdate)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = (('user', 'date'),)
		indexes = [
			models.Index(fields=['user', 'date']),
		]

	def __str__(self) -> str:
		return f"login:{self.user_id}@{self.date}"


class AuditLog(models.Model):
	actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs')
	action = models.CharField(max_length=80)
	target_type = models.CharField(max_length=80, blank=True)
	target_id = models.CharField(max_length=80, blank=True)
	ip = models.GenericIPAddressField(null=True, blank=True)
	user_agent = models.CharField(max_length=300, blank=True)
	metadata = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		indexes = [
			models.Index(fields=['action', '-created_at']),
			models.Index(fields=['target_type', 'target_id', '-created_at']),
		]


class UserFollow(models.Model):
	"""Follower relationship between users.

	This is used by the 'following' feed:
	- show posts created by followed authors

	Notes:
	- We intentionally keep this minimal (no notifications yet).
	"""

	follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_users')
	following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follower_users')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = (('follower', 'following'),)
		indexes = [
			models.Index(fields=['follower', '-created_at']),
			models.Index(fields=['following', '-created_at']),
		]

	def __str__(self) -> str:
		return f"{self.follower_id}->{self.following_id}"


class StaffBoardPermission(models.Model):
	"""Per-board permissions for staff users.

	Only takes effect when user.staff_board_scoped=True.
	"""

	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='staff_board_perms')
	board = models.ForeignKey('forum.Board', on_delete=models.CASCADE, related_name='staff_perms')
	can_moderate = models.BooleanField(default=False)
	can_delete = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = (('user', 'board'),)
		indexes = [
			models.Index(fields=['user', 'board']),
			models.Index(fields=['user', 'can_moderate']),
			models.Index(fields=['user', 'can_delete']),
		]
