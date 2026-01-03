from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        COMMENT_ON_POST = 'comment_on_post', 'Comment on post'
        REPLY_TO_COMMENT = 'reply_to_comment', 'Reply to comment'
        USER_FOLLOW = 'user_follow', 'User follow'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='notifications_sent',
    )
    type = models.CharField(max_length=40, choices=Type.choices)

    post = models.ForeignKey('forum.Post', null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')
    comment = models.ForeignKey('forum.Comment', null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['post', '-created_at']),
        ]

    def __str__(self) -> str:
        return f"notify:{getattr(self, 'id', '')} to:{getattr(self, 'recipient_id', '')} {self.type}"
