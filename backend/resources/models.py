from django.conf import settings
from django.db import models


class ResourceEntry(models.Model):
	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		PUBLISHED = 'published', 'Published'
		REJECTED = 'rejected', 'Rejected'

	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.PROTECT,
		related_name='resources',
	)
	post = models.OneToOneField(
		'forum.Post',
		null=True,
		blank=True,
		on_delete=models.CASCADE,
		related_name='resource',
	)
	title = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	reviewed_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='reviewed_resources',
	)
	reviewed_at = models.DateTimeField(null=True, blank=True)
	reject_reason = models.CharField(max_length=200, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return self.title


class ResourceLink(models.Model):
	class LinkType(models.TextChoices):
		TG = 'tg', 'TG'
		BAIDU = 'baidu', 'Baidu'
		QUARK = 'quark', 'Quark'
		OTHER = 'other', 'Other'

	resource = models.ForeignKey(ResourceEntry, on_delete=models.CASCADE, related_name='links')
	link_type = models.CharField(max_length=20, choices=LinkType.choices)
	url = models.URLField(max_length=1000)
	extraction_code = models.CharField(max_length=50, blank=True)
	note = models.CharField(max_length=200, blank=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		indexes = [
			models.Index(fields=['link_type', 'is_active']),
		]

	def __str__(self) -> str:
		return f"{self.resource_id}:{self.link_type}"


class DownloadEvent(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='download_events')
	link = models.ForeignKey(ResourceLink, on_delete=models.PROTECT, related_name='download_events')
	ip = models.GenericIPAddressField(null=True, blank=True)
	user_agent = models.CharField(max_length=300, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		indexes = [
			models.Index(fields=['user', '-created_at']),
			models.Index(fields=['link', '-created_at']),
		]
