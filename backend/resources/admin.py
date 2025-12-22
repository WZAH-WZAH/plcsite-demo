from django.contrib import admin

from .models import DownloadEvent, ResourceEntry, ResourceLink


class ResourceLinkInline(admin.TabularInline):
	model = ResourceLink
	extra = 0


@admin.register(ResourceEntry)
class ResourceEntryAdmin(admin.ModelAdmin):
	list_display = ('title', 'created_at')
	search_fields = ('title', 'description')
	inlines = [ResourceLinkInline]


@admin.register(ResourceLink)
class ResourceLinkAdmin(admin.ModelAdmin):
	list_display = ('resource', 'link_type', 'is_active', 'created_at')
	list_filter = ('link_type', 'is_active')
	search_fields = ('resource__title', 'url')


@admin.register(DownloadEvent)
class DownloadEventAdmin(admin.ModelAdmin):
	list_display = ('user', 'link', 'ip', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('user__username', 'link__url')
