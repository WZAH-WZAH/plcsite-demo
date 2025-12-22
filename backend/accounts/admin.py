from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import DailyDownloadStat, User
from .models import UserFollow


@admin.register(User)
class CustomUserAdmin(UserAdmin):
	fieldsets = UserAdmin.fieldsets + (
		(
			'Forum',
			{
				'fields': (
					'activity_score',
				)
			},
		),
	)
	list_display = UserAdmin.list_display + ('activity_score',)


@admin.register(DailyDownloadStat)
class DailyDownloadStatAdmin(admin.ModelAdmin):
	list_display = ('user', 'date', 'count')
	search_fields = ('user__username',)
	list_filter = ('date',)

@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
	list_display = ('id', 'follower', 'following', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('follower__username', 'following__username')
