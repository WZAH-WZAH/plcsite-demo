from django.conf import settings
from django.db import models


class Board(models.Model):
	slug = models.SlugField(unique=True)
	title = models.CharField(max_length=100)
	description = models.TextField(blank=True)
	sort_order = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['sort_order', 'id']

	def __str__(self) -> str:
		return self.title


class Post(models.Model):
	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		PUBLISHED = 'published', 'Published'
		REJECTED = 'rejected', 'Rejected'

	board = models.ForeignKey(Board, on_delete=models.PROTECT, related_name='posts')
	author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='posts')
	title = models.CharField(max_length=200)
	cover_image = models.ImageField(upload_to='covers/', null=True, blank=True)
	body = models.TextField()
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	is_pinned = models.BooleanField(default=False)
	is_locked = models.BooleanField(default=False)
	reviewed_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='reviewed_posts',
	)
	reviewed_at = models.DateTimeField(null=True, blank=True)
	reject_reason = models.CharField(max_length=200, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-is_pinned', '-created_at']
		indexes = [
			models.Index(fields=['board', '-created_at']),
			models.Index(fields=['author', '-created_at']),
			models.Index(fields=['status', '-created_at']),
		]

	def __str__(self) -> str:
		return self.title


class PostRevision(models.Model):
	post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='revisions')
	editor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='post_revisions')
	sequence = models.PositiveIntegerField()
	title = models.CharField(max_length=200)
	body = models.TextField(blank=True)
	cover_image_name = models.CharField(max_length=300, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['sequence']
		indexes = [
			models.Index(fields=['post', 'sequence']),
			models.Index(fields=['post', '-created_at']),
		]

	def __str__(self) -> str:
		return f"post:{self.post_id} rev:{self.sequence}"


class Comment(models.Model):
	post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
	author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='comments')
	parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
	body = models.TextField()
	is_deleted = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['created_at', 'id']
		indexes = [
			models.Index(fields=['post', 'created_at']),
			models.Index(fields=['author', '-created_at']),
			models.Index(fields=['parent', 'created_at']),
		]

	def __str__(self) -> str:
		return f"comment:{self.id} post:{self.post_id}"


class PostLike(models.Model):
	"""A user's 'like' on a post.

	Notes:
	- We keep this as a separate table (not a counter field) so we can:
	  - prevent duplicates via unique constraint
	  - derive hot/ranking scores by time window later (weekly/monthly)
	  - audit/abuse-detect if needed
	"""

	post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_likes')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = (('post', 'user'),)
		indexes = [
			models.Index(fields=['post', '-created_at']),
			models.Index(fields=['user', '-created_at']),
		]


class PostFavorite(models.Model):
	"""A user's 'favorite/bookmark' on a post."""

	post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='favorites')
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_favorites')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = (('post', 'user'),)
		indexes = [
			models.Index(fields=['post', '-created_at']),
			models.Index(fields=['user', '-created_at']),
		]


class BoardFollow(models.Model):
	"""User follows a board.

	Used by the 'following' feed:
	- show posts from followed boards
	"""

	board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='followers')
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followed_boards')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = (('board', 'user'),)
		indexes = [
			models.Index(fields=['board', '-created_at']),
			models.Index(fields=['user', '-created_at']),
		]


class HomeHeroSlide(models.Model):
	"""Admin-configured hero carousel slides for the homepage."""

	title = models.CharField(max_length=120, blank=True)
	description = models.CharField(max_length=200, blank=True)
	image = models.ImageField(upload_to='hero/', null=True, blank=True)
	link_url = models.URLField(max_length=1000, blank=True, default='')
	sort_order = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['sort_order', 'id']
		indexes = [
			models.Index(fields=['is_active', 'sort_order', 'id']),
		]

	def __str__(self) -> str:
		return f"hero:{self.id} {self.title or self.link_url}"
