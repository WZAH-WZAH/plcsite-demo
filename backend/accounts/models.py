from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
	activity_score = models.PositiveIntegerField(default=0)
	# 头像（个人中心改版用）。
	# 备注：
	# - 目前仅支持上传一张图片作为头像；后续可扩展为“头像框/挂件/预设头像”等。
	# - 前端在用户首次注册后会提示设置头像；首次设置不扣积分，后续更换可扣积分（见 /api/me/avatar/）。
	avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
	is_banned = models.BooleanField(default=False)
	banned_until = models.DateTimeField(null=True, blank=True)
	ban_reason = models.CharField(max_length=200, blank=True)

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
		return 1

	@property
	def daily_download_limit(self) -> int:
		return {1: 3, 2: 5, 3: 8, 4: 12, 5: 20, 6: 30}.get(self.level, 3)

	@property
	def is_currently_banned(self) -> bool:
		until = self.banned_until
		if self.is_banned:
			return until is None or until > timezone.now()
		if until is None:
			return False
		return until > timezone.now()


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
