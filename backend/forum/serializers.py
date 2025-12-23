from rest_framework import serializers

from .models import Board, BoardHeroSlide, Comment, HomeHeroSlide, Post
from .image_utils import validate_and_process_uploaded_image
from .sanitize import sanitize_user_html_in_markdown


class PostResourceLinkInputSerializer(serializers.Serializer):
    link_type = serializers.ChoiceField(choices=['tg', 'baidu', 'quark', 'other'])
    url = serializers.URLField(max_length=1000)


class PostResourceLinkSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    link_type = serializers.CharField()
    url = serializers.URLField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class PostResourceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    links = PostResourceLinkSerializer(many=True)


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ('id', 'slug', 'title', 'description', 'sort_order', 'is_active')


class PostSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    author_nickname = serializers.CharField(source='author.nickname', read_only=True)
    author_pid = serializers.CharField(source='author.pid', read_only=True)
    board_slug = serializers.CharField(source='board.slug', read_only=True)
    cover_image_url = serializers.SerializerMethodField(read_only=True)
    # Social fields (interaction layer)
    # Notes:
    # - Counts/flags are provided by queryset annotations in PostViewSet for performance.
    # - Fallback defaults keep serializer robust if annotations are missing.
    likes_count = serializers.IntegerField(read_only=True, required=False, default=0)
    favorites_count = serializers.IntegerField(read_only=True, required=False, default=0)
    comments_count = serializers.IntegerField(read_only=True, required=False, default=0)
    is_liked = serializers.BooleanField(read_only=True, required=False, default=False)
    is_favorited = serializers.BooleanField(read_only=True, required=False, default=False)
    is_following_author = serializers.BooleanField(read_only=True, required=False, default=False)
    views_count = serializers.IntegerField(read_only=True, required=False, default=0)
    # Ranking / hot-score (0..100). Filled by ranking endpoints; defaults to 0 elsewhere.
    hot_score_100 = serializers.IntegerField(read_only=True, required=False, default=0)
    remove_cover_image = serializers.BooleanField(write_only=True, required=False)
    resource = PostResourceSerializer(read_only=True)
    resource_links = PostResourceLinkInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Post
        fields = (
            'id',
            'board',
            'board_slug',
            'author',
            'author_nickname',
            'author_username',
            'author_pid',
            'title',
			'cover_image',
			'cover_image_url',
            'remove_cover_image',
            'body',
            'views_count',
			'hot_score_100',
			'likes_count',
			'favorites_count',
            'comments_count',
			'is_liked',
			'is_favorited',
			'is_following_author',
			'resource',
			'resource_links',
			'status',
            'is_pinned',
            'is_locked',
			'reviewed_by',
			'reviewed_at',
			'reject_reason',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'author',
            'status',
            'is_pinned',
            'is_locked',
            'reviewed_by',
            'reviewed_at',
            'reject_reason',
            'created_at',
            'updated_at',
            'views_count',
            'author_nickname',
            'author_username',
            'author_pid',
            'board_slug',
            'cover_image_url',
            'hot_score_100',
            'likes_count',
            'favorites_count',
            'comments_count',
            'is_liked',
            'is_favorited',
            'is_following_author',
            'resource',
        )

    def get_cover_image_url(self, obj):
        try:
            f = getattr(obj, 'cover_image', None)
            return f.url if f else ''
        except Exception:
            return ''

    def validate_cover_image(self, value):
        if value is None:
            return value
        processed = validate_and_process_uploaded_image(uploaded_file=value, field_name='cover_image')
        processed.content.name = f"cover.{processed.ext}"
        return processed.content

    def validate_body(self, value):
        # Whitelist raw HTML in markdown (XSS defense-in-depth).
        return sanitize_user_html_in_markdown(value)

    def create(self, validated_data):
        # These are serializer-only helper inputs (not Post model fields).
        remove_cover = bool(validated_data.pop('remove_cover_image', False))
        validated_data.pop('resource_links', None)

        # For create, allow clients to explicitly indicate no cover.
        if remove_cover:
            validated_data.pop('cover_image', None)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Ignore serializer-only inputs (resource_links handled by view).
        validated_data.pop('resource_links', None)
        if validated_data.pop('remove_cover_image', False):
            instance.cover_image = None
        return super().update(instance, validated_data)


class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)
    author_nickname = serializers.CharField(source='author.nickname', read_only=True)
    parent_id = serializers.IntegerField(source='parent.id', allow_null=True, read_only=True)

    class Meta:
        model = Comment
        fields = (
            'id',
            'post',
            'parent_id',
            'author',
            'author_nickname',
            'author_username',
            'body',
            'is_deleted',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'post',
            'author',
            'author_nickname',
            'author_username',
            'is_deleted',
            'created_at',
            'updated_at',
        )


class CommentCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=20000, allow_blank=False, trim_whitespace=False)
    parent = serializers.IntegerField(required=False, allow_null=True)

    def validate_body(self, value):
        text = (value or '')
        if not text.strip():
            raise serializers.ValidationError('Body cannot be empty.')
        return sanitize_user_html_in_markdown(text)

    def validate(self, attrs):
        post = self.context.get('post')
        if post is None:
            raise serializers.ValidationError('Missing post context.')

        parent_id = attrs.get('parent', None)
        if parent_id is None:
            return attrs
        if parent_id is False:
            attrs['parent'] = None
            return attrs
        if parent_id == 0:
            attrs['parent'] = None
            return attrs

        try:
            parent_obj = Comment.objects.get(id=parent_id)
        except Comment.DoesNotExist:
            raise serializers.ValidationError({'parent': 'Parent comment not found.'})

        if getattr(parent_obj, 'post_id', None) != post.id:
            raise serializers.ValidationError({'parent': 'Parent comment must be under the same post.'})
        if parent_obj.is_deleted:
            raise serializers.ValidationError({'parent': 'Cannot reply to a deleted comment.'})

        attrs['parent'] = parent_obj
        return attrs


class HomeHeroSlideSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = HomeHeroSlide
        fields = (
            'id',
            'sort_order',
            'title',
            'description',
            'link_url',
            'image_url',
        )

    def get_image_url(self, obj):
        try:
            f = getattr(obj, 'image', None)
            return f.url if f else ''
        except Exception:
            return ''


class BoardHeroSlideSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)
    post_id = serializers.IntegerField(source='post.id', read_only=True)
    post_title = serializers.CharField(source='post.title', read_only=True)
    post_author_username = serializers.CharField(source='post.author.username', read_only=True)
    post_cover_image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = BoardHeroSlide
        fields = (
            'id',
            'sort_order',
            'is_active',
            'title',
            'description',
            'image_url',
            'post_id',
            'post_title',
            'post_author_username',
            'post_cover_image_url',
        )

    def get_image_url(self, obj):
        try:
            f = getattr(obj, 'image', None)
            return f.url if f else ''
        except Exception:
            return ''

    def get_post_cover_image_url(self, obj):
        try:
            f = getattr(obj.post, 'cover_image', None)
            return f.url if f else ''
        except Exception:
            return ''


class PostRevisionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    sequence = serializers.IntegerField()
    editor_username = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class PostRevisionDiffSerializer(serializers.Serializer):
    from_revision_id = serializers.IntegerField(allow_null=True)
    to_revision_id = serializers.IntegerField()
    title_diff = serializers.CharField()
    body_diff = serializers.CharField()
    cover_changed = serializers.BooleanField()

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request is not None else None
        if user and user.is_authenticated and getattr(user, 'is_staff', False):
            return attrs

        protected = {
            'status',
            'is_pinned',
            'is_locked',
            'reviewed_by',
            'reviewed_at',
            'reject_reason',
        }
        if any(k in attrs for k in protected):
            raise serializers.ValidationError('Not allowed.')
        return attrs