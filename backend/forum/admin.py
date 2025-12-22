from django.contrib import admin

from .models import Board, BoardFollow, BoardHeroSlide, Comment, HomeHeroSlide, Post, PostFavorite, PostLike


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
	list_display = ('title', 'slug', 'sort_order', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('title', 'slug')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
	list_display = ('title', 'board', 'author', 'views_count', 'is_pinned', 'is_locked', 'created_at')
	list_filter = ('board', 'is_pinned', 'is_locked')
	search_fields = ('title', 'body', 'author__username')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
	list_display = ('id', 'post', 'author', 'parent', 'is_deleted', 'created_at')
	list_filter = ('is_deleted', 'created_at')
	search_fields = ('body', 'author__username', 'post__title')


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
	list_display = ('id', 'post', 'user', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('post__title', 'user__username')


@admin.register(PostFavorite)
class PostFavoriteAdmin(admin.ModelAdmin):
	list_display = ('id', 'post', 'user', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('post__title', 'user__username')


@admin.register(BoardFollow)
class BoardFollowAdmin(admin.ModelAdmin):
	list_display = ('id', 'board', 'user', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('board__title', 'user__username')


@admin.register(HomeHeroSlide)
class HomeHeroSlideAdmin(admin.ModelAdmin):
	list_display = ('id', 'title', 'link_url', 'sort_order', 'is_active', 'updated_at')
	list_filter = ('is_active',)
	search_fields = ('title', 'description', 'link_url')
	ordering = ('sort_order', 'id')


@admin.register(BoardHeroSlide)
class BoardHeroSlideAdmin(admin.ModelAdmin):
	list_display = ('id', 'board', 'post', 'sort_order', 'is_active', 'updated_at')
	list_filter = ('is_active', 'board')
	search_fields = ('title', 'description', 'post__title', 'board__title')
	ordering = ('board', 'sort_order', 'id')
