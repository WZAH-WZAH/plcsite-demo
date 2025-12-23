import json
import uuid

import difflib

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import BooleanField, Count, DateTimeField, Exists, ExpressionWrapper, F, IntegerField, Max, OuterRef, Q, Value
from django.db.models.functions import Cast
from django.utils import timezone
from django.utils.decorators import method_decorator
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from django_ratelimit.decorators import ratelimit

from accounts.audit import write_audit_log
from accounts.permissions import IsModerator
from accounts.services import staff_allowed_board_ids, staff_can_moderate_board, staff_can_delete_board

from .models import Board, BoardFollow, BoardHeroSlide, Comment, HomeHeroSlide, Post, PostFavorite, PostLike
from .permissions import IsAuthorOrStaffOrReadOnly
from .serializers import (
    BoardSerializer,
    BoardHeroSlideSerializer,
    CommentCreateSerializer,
    CommentSerializer,
    HomeHeroSlideSerializer,
    PostRevisionDiffSerializer,
    PostRevisionSerializer,
    PostSerializer,
)
from .image_utils import validate_and_process_uploaded_image

from .models import PostRevision

from notifications.models import Notification

from resources.models import ResourceEntry, ResourceLink

from accounts.models import UserFollow

from .search_meili import meili_enabled


class BoardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Board.objects.filter(is_active=True)
    serializer_class = BoardSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    @action(detail=True, methods=['get'], url_path='hero', permission_classes=[permissions.AllowAny])
    def hero(self, request, slug=None):
        """Public board hero carousel slides.

        Slides are configured by admins in Django Admin.
        Only active slides are returned.
        """

        board = self.get_object()
        qs = BoardHeroSlide.objects.filter(board=board, is_active=True).select_related('post', 'post__author').order_by('sort_order', 'id')
        ser = BoardHeroSlideSerializer(qs, many=True, context={'request': request})
        return Response(ser.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='follow', permission_classes=[permissions.IsAuthenticated])
    def follow(self, request, slug=None):
        """Toggle follow/unfollow for a board.

        Used by the 'following' feed.
        """

        user = request.user
        if getattr(user, 'is_currently_banned', False):
            raise PermissionDenied('User is banned.')

        board = self.get_object()
        obj = BoardFollow.objects.filter(board=board, user=user).first()
        if obj is not None:
            obj.delete()
            following = False
            audit_action = 'board.unfollow'
        else:
            BoardFollow.objects.create(board=board, user=user)
            following = True
            audit_action = 'board.follow'

        write_audit_log(
            actor=user,
            action=audit_action,
            target_type='board',
            target_id=str(board.id),
            request=request,
        )

        followers_count = BoardFollow.objects.filter(board=board).count()
        return Response({'following': following, 'followers_count': followers_count}, status=status.HTTP_200_OK)


class HomeHeroSlideViewSet(viewsets.ReadOnlyModelViewSet):
    """Public homepage hero carousel slides.

    Slides are configured by admins in Django Admin.
    Only active slides are returned.
    """

    queryset = (
        HomeHeroSlide.objects.filter(is_active=True)
        .order_by('sort_order', 'id')
    )
    serializer_class = HomeHeroSlideSerializer
    permission_classes = [permissions.AllowAny]


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.select_related('board', 'author', 'reviewed_by').prefetch_related('resource__links')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrStaffOrReadOnly]

    @method_decorator(ratelimit(key='user_or_ip', rate='5/m', method='POST', block=False))
    def create(self, request, *args, **kwargs):
        if getattr(request, 'limited', False):
            return Response({'detail': 'Too many requests.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        try:
            Post.objects.filter(id=obj.id).update(views_count=F('views_count') + 1)
            # Avoid refresh_from_db here so we don't accidentally drop queryset annotations
            # (likes_count/favorites_count/comments_count flags) from the object.
            try:
                obj.views_count = int(getattr(obj, 'views_count', 0)) + 1
            except Exception:
                pass
        except Exception:
            # Avoid breaking reads if the counter update fails.
            pass

        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            filtered = qs
        elif user.is_authenticated:
            filtered = qs.filter(Q(status=Post.Status.PUBLISHED) | Q(author=user))
        else:
            filtered = qs.filter(status=Post.Status.PUBLISHED)

        board_id = self.request.query_params.get('board')
        if board_id:
            try:
                board_id_int = int(board_id)
                filtered = filtered.filter(board_id=board_id_int)
            except ValueError:
                pass

        q = (self.request.query_params.get('q') or '').strip()
        if q:
            q = q[:100]
            filtered = filtered.filter(Q(title__icontains=q) | Q(body__icontains=q))

        # Social annotations (counts + current-user flags)
        filtered = filtered.annotate(
            likes_count=Count('likes', distinct=True),
            favorites_count=Count('favorites', distinct=True),
            comments_count=Count('comments', filter=Q(comments__is_deleted=False), distinct=True),
        )
        if user and user.is_authenticated:
            filtered = filtered.annotate(
                is_liked=Exists(PostLike.objects.filter(post_id=OuterRef('pk'), user_id=user.id)),
                is_favorited=Exists(PostFavorite.objects.filter(post_id=OuterRef('pk'), user_id=user.id)),
                is_following_author=Exists(UserFollow.objects.filter(follower_id=user.id, following_id=OuterRef('author_id'))),
            )
        else:
            filtered = filtered.annotate(
                is_liked=Value(False, output_field=BooleanField()),
                is_favorited=Value(False, output_field=BooleanField()),
                is_following_author=Value(False, output_field=BooleanField()),
            )

        # Sorting
        # Supported:
        # - sort=created|updated|commented|hot
        # - range=week|month (for hot)
        # - end=ISO date/datetime (for hot history)
        sort = (self.request.query_params.get('sort') or 'created').strip().lower()
        if sort in ('created_at', 'created'):
            filtered = filtered.order_by('-is_pinned', '-created_at')
        elif sort in ('updated_at', 'updated'):
            filtered = filtered.order_by('-is_pinned', '-updated_at', '-created_at')
        elif sort in ('last_comment', 'commented', 'comment'):
            filtered = filtered.annotate(
                last_comment_at=Max(
                    'comments__created_at',
                    filter=Q(comments__is_deleted=False),
                    output_field=DateTimeField(),
                )
            ).order_by('-is_pinned', F('last_comment_at').desc(nulls_last=True), '-created_at')
        elif sort in ('hot', 'heat', 'trending'):
            range_value = (self.request.query_params.get('range') or 'week').strip().lower()
            window_days = 7 if range_value == 'week' else 30
            end_raw = (self.request.query_params.get('end') or '').strip()
            end_dt = None
            if end_raw:
                try:
                    end_dt = timezone.datetime.fromisoformat(end_raw)
                    if timezone.is_naive(end_dt):
                        end_dt = timezone.make_aware(end_dt, timezone.get_current_timezone())
                except Exception:
                    end_dt = None
            end_dt = end_dt or timezone.now()
            since = end_dt - timedelta(days=window_days)
            filtered = filtered.annotate(
                hot_likes=Count('likes', filter=Q(likes__created_at__gte=since), distinct=True),
                hot_favorites=Count('favorites', filter=Q(favorites__created_at__gte=since), distinct=True),
                hot_comments=Count(
                    'comments',
                    filter=Q(comments__created_at__gte=since, comments__is_deleted=False),
                    distinct=True,
                ),
            )

            # views_count is cumulative; scale it down so it complements recent interactions.
            # 1 point per 100 views.
            filtered = filtered.annotate(hot_views=Cast(F('views_count') / Value(100), IntegerField()))
            score = ExpressionWrapper(
                (1 * F('hot_views')) + (2 * F('hot_likes')) + (3 * F('hot_favorites')) + (2 * F('hot_comments')),
                output_field=IntegerField(),
            )
            filtered = filtered.annotate(hot_score=score).order_by('-is_pinned', '-hot_score', '-created_at')
        else:
            filtered = filtered.order_by('-is_pinned', '-created_at')

        return filtered

    def perform_create(self, serializer):
        user = self.request.user

        board = serializer.validated_data.get('board')
        if board is not None and getattr(board, 'slug', '') == 'announcements' and not user.is_staff:
            raise PermissionDenied('Only staff can post in announcements.')

        status_value = Post.Status.PUBLISHED if user.is_staff else Post.Status.PENDING
        extra = {}
        if not user.is_staff:
            # Defense-in-depth: even if client sends these fields, force them off.
            extra.update({'is_pinned': False, 'is_locked': False})

        post = serializer.save(author=user, status=status_value, **extra)

        self._create_revision(post=post, editor=user)
        write_audit_log(actor=user, action='post.create', target_type='post', target_id=str(post.id), request=self.request)

        data = getattr(self.request, 'data', {})
        resource_links = data.get('resource_links') if isinstance(data, dict) else data.get('resource_links')
        if isinstance(resource_links, str) and resource_links.strip():
            try:
                resource_links = json.loads(resource_links)
            except json.JSONDecodeError:
                resource_links = None
        has_resource_links = bool(isinstance(resource_links, list) and len(resource_links) > 0)

        # PLCoin: posting earns points (daily cap applies). First-time posting only.
        try:
            from accounts.services import try_award_post_points

            base_points = 2 if has_resource_links else 1
            awarded, new_balance = try_award_post_points(user, points=base_points, daily_cap=6)
            if awarded > 0:
                write_audit_log(
                    actor=user,
                    action='points.post',
                    target_type='post',
                    target_id=str(post.id),
                    request=self.request,
                    metadata={'awarded': int(awarded), 'balance': int(new_balance), 'has_resource_links': has_resource_links},
                )
        except Exception:
            # Points should not block post creation.
            pass

        if not has_resource_links:
            return

        if has_resource_links:
            resource_status = ResourceEntry.Status.PUBLISHED if user.is_staff else ResourceEntry.Status.PENDING
            resource = ResourceEntry.objects.create(
                post=post,
                created_by=user,
                title=post.title,
                description='',
                status=resource_status,
            )
            link_objs = []
            for item in resource_links:
                if not isinstance(item, dict):
                    continue
                link_type = item.get('link_type')
                url = item.get('url')
                if not link_type or not url:
                    continue
                link_objs.append(
                    ResourceLink(
                        resource=resource,
                        link_type=link_type,
                        url=url,
                        extraction_code='',
                        note='',
                        is_active=True,
                    )
                )
            if link_objs:
                ResourceLink.objects.bulk_create(link_objs)

    @action(detail=False, methods=['post'], url_path='images/upload', permission_classes=[permissions.IsAuthenticated])
    def upload_image(self, request):
        f = request.FILES.get('image')
        if not f:
            return Response({'detail': 'Missing image.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            processed = validate_and_process_uploaded_image(uploaded_file=f, field_name='image')
        except ValidationError as e:
            # Normalize Django ValidationError to DRF-friendly {detail: "..."}
            msg = ''
            message_dict = getattr(e, 'message_dict', None)
            if isinstance(message_dict, dict) and message_dict:
                first_val = next(iter(message_dict.values()))
                if isinstance(first_val, (list, tuple)) and first_val:
                    msg = str(first_val[0])
                else:
                    msg = str(first_val)
            else:
                messages = getattr(e, 'messages', None)
                if isinstance(messages, (list, tuple)) and messages:
                    msg = str(messages[0])

            return Response({'detail': msg or 'Invalid image.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'detail': 'Invalid image.'}, status=status.HTTP_400_BAD_REQUEST)

        path = f"uploads/{uuid.uuid4().hex}.{processed.ext}"
        saved_path = default_storage.save(path, processed.content)
        url = default_storage.url(saved_path)
        return Response({'url': url, 'width': processed.width, 'height': processed.height}, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        obj = self.get_object()
        user = self.request.user
        if obj.is_locked and not user.is_staff:
            raise PermissionDenied('Post is locked.')

        with transaction.atomic():
            updated = serializer.save()

            # Non-staff edits must go through moderation again.
            if not user.is_staff and updated.status != Post.Status.PENDING:
                updated.status = Post.Status.PENDING
                updated.reviewed_by = None
                updated.reviewed_at = None
                updated.reject_reason = ''
                updated.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'reject_reason'])

            self._create_revision(post=updated, editor=user)

        write_audit_log(actor=user, action='post.update', target_type='post', target_id=str(obj.id), request=self.request)

    def perform_destroy(self, instance):
        actor = self.request.user if getattr(self.request, 'user', None) and self.request.user.is_authenticated else None
        write_audit_log(actor=actor, action='post.delete', target_type='post', target_id=str(instance.id), request=self.request)
        return super().perform_destroy(instance)

    @action(detail=False, methods=['get'], url_path='search', permission_classes=[permissions.AllowAny])
    def search(self, request):
        """Enhanced search endpoint.

        Supports:
        - Autocomplete is handled via /api/posts/suggest/
        - Highlight info via match positions (client-side safe rendering)
        - Aggregations (facets) by board/author

        Advanced query syntax (space-separated):
        - board:<slug>
        - author:<username>
        - status:published|pending|rejected
        - is:locked / is:pinned

        Notes:
        - If Meilisearch is not configured, falls back to DB icontains search.
        """

        q = (request.query_params.get('q') or '').strip()
        limit = request.query_params.get('limit')
        offset = request.query_params.get('offset')
        try:
            limit_i = int(limit) if limit is not None else 20
        except ValueError:
            limit_i = 20
        try:
            offset_i = int(offset) if offset is not None else 0
        except ValueError:
            offset_i = 0

        if meili_enabled():
            from .search_meili import search_posts

            data = search_posts(user=request.user, raw_query=q, limit=limit_i, offset=offset_i)
            return Response(data, status=status.HTTP_200_OK)

        # DB fallback
        qs = self.get_queryset()
        # keep same visibility behavior as list
        if q:
            q2 = q[:100]
            qs = qs.filter(Q(title__icontains=q2) | Q(body__icontains=q2))
        else:
            qs = qs.none()

        total = qs.count()
        items = list(qs.order_by('-created_at')[offset_i : offset_i + min(limit_i, 50)])
        serializer = self.get_serializer(items, many=True)

        facets = {
            'board_slug': {},
            'author_username': {},
        }
        try:
            # Lightweight aggregations (published/visibility already applied by qs).
            for row in qs.values('board__slug').annotate(c=Count('id')).order_by('-c')[:20]:
                facets['board_slug'][row['board__slug'] or ''] = int(row['c'])
            for row in qs.values('author__username').annotate(c=Count('id')).order_by('-c')[:20]:
                facets['author_username'][row['author__username'] or ''] = int(row['c'])
        except Exception:
            pass

        return Response(
            {
                'engine': 'db',
                'query': q,
                'hits': serializer.data,
                'total': total,
                'limit': min(limit_i, 50),
                'offset': offset_i,
                'facets': facets,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='suggest', permission_classes=[permissions.AllowAny])
    def suggest(self, request):
        """Suggestions endpoint for topbar autocomplete."""

        q = (request.query_params.get('q') or '').strip()
        if not q:
            return Response({'engine': 'none', 'query': '', 'hits': []}, status=status.HTTP_200_OK)

        if meili_enabled():
            from .search_meili import suggest_posts

            data = suggest_posts(user=request.user, raw_query=q, limit=8)
            return Response(data, status=status.HTTP_200_OK)

        # DB fallback
        q2 = q[:100]
        qs = self.get_queryset().filter(Q(title__icontains=q2) | Q(body__icontains=q2)).order_by('-created_at')
        items = list(qs[:8])
        data = [
            {
                'id': p.id,
                'title': p.title,
                'board_slug': getattr(getattr(p, 'board', None), 'slug', ''),
                'author_username': getattr(getattr(p, 'author', None), 'username', ''),
            }
            for p in items
        ]
        return Response({'engine': 'db', 'query': q, 'hits': data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='like', permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        """Toggle like/unlike for a post."""

        user = request.user
        if getattr(user, 'is_currently_banned', False):
            raise PermissionDenied('User is banned.')

        post = self.get_object()
        if post.status != Post.Status.PUBLISHED and not getattr(user, 'is_staff', False) and post.author_id != user.id:
            raise PermissionDenied('Not allowed to like this post.')
        existing = PostLike.objects.filter(post=post, user=user).first()
        if existing is not None:
            existing.delete()
            liked = False
            audit_action = 'post.unlike'
        else:
            PostLike.objects.create(post=post, user=user)
            liked = True
            audit_action = 'post.like'

        write_audit_log(
            actor=user,
            action=audit_action,
            target_type='post',
            target_id=str(post.id),
            request=request,
        )

        likes_count = PostLike.objects.filter(post=post).count()
        return Response({'liked': liked, 'likes_count': likes_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='favorite', permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        """Toggle favorite/unfavorite for a post."""

        user = request.user
        if getattr(user, 'is_currently_banned', False):
            raise PermissionDenied('User is banned.')

        post = self.get_object()
        if post.status != Post.Status.PUBLISHED and not getattr(user, 'is_staff', False) and post.author_id != user.id:
            raise PermissionDenied('Not allowed to favorite this post.')
        existing = PostFavorite.objects.filter(post=post, user=user).first()
        if existing is not None:
            existing.delete()
            favorited = False
            audit_action = 'post.unfavorite'
        else:
            PostFavorite.objects.create(post=post, user=user)
            favorited = True
            audit_action = 'post.favorite'

            # PLCoin: first favorite of the day +1
            try:
                from accounts.services import try_award_first_favorite_bonus

                awarded, new_balance = try_award_first_favorite_bonus(user, points=1)
                if awarded:
                    write_audit_log(
                        actor=user,
                        action='points.favorite.first',
                        target_type='post',
                        target_id=str(post.id),
                        request=request,
                        metadata={'awarded': 1, 'balance': int(new_balance)},
                    )
            except Exception:
                pass

        write_audit_log(
            actor=user,
            action=audit_action,
            target_type='post',
            target_id=str(post.id),
            request=request,
        )

        favorites_count = PostFavorite.objects.filter(post=post).count()
        return Response({'favorited': favorited, 'favorites_count': favorites_count}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='feed/latest', permission_classes=[permissions.AllowAny])
    def feed_latest(self, request):
        """Latest published posts.

        Notes:
        - This is a lightweight placeholder for a future homepage feed.
        """

        qs = self.get_queryset().filter(status=Post.Status.PUBLISHED).order_by('-created_at')
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='feed/hot', permission_classes=[permissions.AllowAny])
    def feed_hot(self, request):
        """Hot posts by a simple recent-interaction score.

        Notes:
        - This is intentionally simple and explainable.
        - Future: add decay / normalization / per-board weights.
        """

        days = request.query_params.get('days')
        try:
            window_days = int(days) if days is not None else 7
        except ValueError:
            window_days = 7
        window_days = max(1, min(window_days, 30))

        since = timezone.now() - timedelta(days=window_days)
        qs = (
            self.get_queryset()
            .filter(status=Post.Status.PUBLISHED)
            .annotate(
                hot_likes=Count('likes', filter=Q(likes__created_at__gte=since), distinct=True),
                hot_favorites=Count('favorites', filter=Q(favorites__created_at__gte=since), distinct=True),
                hot_comments=Count(
                    'comments',
                    filter=Q(comments__created_at__gte=since, comments__is_deleted=False),
                    distinct=True,
                ),
            )
        )

        qs = qs.annotate(hot_views=Cast(F('views_count') / Value(100), IntegerField()))

        score = ExpressionWrapper(
            (1 * F('hot_views')) + (2 * F('hot_likes')) + (3 * F('hot_favorites')) + (2 * F('hot_comments')),
            output_field=IntegerField(),
        )
        qs = qs.annotate(hot_score=score).order_by('-hot_score', '-created_at')

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='feed/following', permission_classes=[permissions.IsAuthenticated])
    def feed_following(self, request):
        """Posts from followed authors or boards."""

        user = request.user
        if getattr(user, 'is_currently_banned', False):
            raise PermissionDenied('User is banned.')

        followed_user_ids = UserFollow.objects.filter(follower_id=user.id).values('following_id')
        followed_board_ids = BoardFollow.objects.filter(user_id=user.id).values('board_id')

        qs = (
            self.get_queryset()
            .filter(status=Post.Status.PUBLISHED)
            .filter(Q(author_id__in=followed_user_ids) | Q(board_id__in=followed_board_ids))
            .distinct()
            .order_by('-created_at')
        )

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='rankings', permission_classes=[permissions.AllowAny])
    def rankings(self, request):
        """Reserved endpoint for weekly/monthly rankings.

        Query params:
        - range=week|month (default week)

        Notes:
        - For now it reuses a simple hot-score over the window.
        """

        range_value = (request.query_params.get('range') or 'week').strip().lower()
        window_days = 7 if range_value == 'week' else 30

        end_raw = (request.query_params.get('end') or '').strip()
        end_dt = None
        if end_raw:
            try:
                end_dt = timezone.datetime.fromisoformat(end_raw)
                if timezone.is_naive(end_dt):
                    end_dt = timezone.make_aware(end_dt, timezone.get_current_timezone())
            except Exception:
                end_dt = None
        end_dt = end_dt or timezone.now()
        since = end_dt - timedelta(days=window_days)

        board_slug = (request.query_params.get('board_slug') or '').strip()

        limit = request.query_params.get('limit')
        offset = request.query_params.get('offset')
        try:
            limit_i = int(limit) if limit is not None else None
        except ValueError:
            limit_i = None
        try:
            offset_i = int(offset) if offset is not None else 0
        except ValueError:
            offset_i = 0
        if limit_i is not None:
            limit_i = max(1, min(limit_i, 50))
        offset_i = max(0, offset_i)

        qs = self.get_queryset().filter(status=Post.Status.PUBLISHED)
        if board_slug:
            qs = qs.filter(board__slug=board_slug)

        qs = (
            qs
            .annotate(
                hot_likes=Count('likes', filter=Q(likes__created_at__gte=since), distinct=True),
                hot_favorites=Count('favorites', filter=Q(favorites__created_at__gte=since), distinct=True),
                hot_comments=Count(
                    'comments',
                    filter=Q(comments__created_at__gte=since, comments__is_deleted=False),
                    distinct=True,
                ),
            )
        )

        qs = qs.annotate(hot_views=Cast(F('views_count') / Value(100), IntegerField()))

        score = ExpressionWrapper(
            (1 * F('hot_views')) + (2 * F('hot_likes')) + (3 * F('hot_favorites')) + (2 * F('hot_comments')),
            output_field=IntegerField(),
        )
        qs = qs.annotate(hot_score=score).order_by('-hot_score', '-created_at')

        def attach_hot_score_100(objs):
            raw_scores = []
            for o in objs:
                try:
                    raw_scores.append(int(getattr(o, 'hot_score', 0) or 0))
                except Exception:
                    raw_scores.append(0)
            max_raw = max(raw_scores) if raw_scores else 0
            if max_raw < 0:
                max_raw = 0

            for o in objs:
                try:
                    raw = int(getattr(o, 'hot_score', 0) or 0)
                except Exception:
                    raw = 0
                if raw < 0:
                    raw = 0
                if max_raw > 0:
                    v = int(round(100.0 * float(raw) / float(max_raw)))
                else:
                    v = 0
                if v < 0:
                    v = 0
                if v > 100:
                    v = 100
                setattr(o, 'hot_score_100', v)
            return objs

        # Support lightweight Top-N use cases (homepage / hot page).
        if limit_i is not None:
            items = list(qs[offset_i : offset_i + limit_i])
            attach_hot_score_100(items)
            return Response(self.get_serializer(items, many=True).data)

        page = self.paginate_queryset(qs)
        if page is not None:
            attach_hot_score_100(page)
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        items = list(qs)
        attach_hot_score_100(items)
        return Response(self.get_serializer(items, many=True).data)

    @action(
        detail=True,
        methods=['get', 'post'],
        url_path='comments',
        permission_classes=[permissions.IsAuthenticatedOrReadOnly],
    )
    @method_decorator(ratelimit(key='user_or_ip', rate='20/m', method='POST', block=False))
    def comments(self, request, pk=None):
        post = self.get_object()  # respects get_queryset visibility rules

        if request.method == 'GET':
            qs = (
                Comment.objects.select_related('author')
                .filter(post=post)
                .order_by('created_at', 'id')
            )
            page = self.paginate_queryset(qs)
            if page is not None:
                return self.get_paginated_response(CommentSerializer(page, many=True).data)
            return Response(CommentSerializer(qs, many=True).data)

        # POST
        if getattr(request, 'limited', False):
            return Response({'detail': 'Too many requests.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        user = request.user
        if getattr(user, 'is_currently_banned', False):
            raise PermissionDenied('User is banned.')
        if post.is_locked and not getattr(user, 'is_staff', False):
            raise PermissionDenied('Post is locked.')
        if post.status != Post.Status.PUBLISHED and not getattr(user, 'is_staff', False) and post.author_id != user.id:
            raise PermissionDenied('Not allowed to comment on this post.')

        serializer = CommentCreateSerializer(data=request.data, context={'post': post})
        serializer.is_valid(raise_exception=True)
        parent_obj = serializer.validated_data.get('parent')
        body = serializer.validated_data['body']
        comment = Comment.objects.create(post=post, author=user, parent=parent_obj, body=body)

        # PLCoin: first comment of the day +1
        try:
            from accounts.services import try_award_first_comment_bonus

            awarded, new_balance = try_award_first_comment_bonus(user, points=1)
            if awarded:
                write_audit_log(
                    actor=user,
                    action='points.comment.first',
                    target_type='comment',
                    target_id=str(comment.id),
                    request=request,
                    metadata={'awarded': 1, 'balance': int(new_balance), 'post_id': post.id},
                )
        except Exception:
            pass

        # Notifications
        try:
            if parent_obj is not None:
                recipient_id = getattr(parent_obj, 'author_id', None)
                if recipient_id and recipient_id != user.id:
                    Notification.objects.create(
                        recipient_id=recipient_id,
                        actor=user,
                        type=Notification.Type.REPLY_TO_COMMENT,
                        post=post,
                        comment=comment,
                    )
            else:
                recipient_id = getattr(post, 'author_id', None)
                if recipient_id and recipient_id != user.id:
                    Notification.objects.create(
                        recipient_id=recipient_id,
                        actor=user,
                        type=Notification.Type.COMMENT_ON_POST,
                        post=post,
                        comment=comment,
                    )
        except Exception:
            # Notifications should not block comment creation.
            pass

        write_audit_log(
            actor=user,
            action='comment.create',
            target_type='comment',
            target_id=str(comment.id),
            request=request,
            metadata={'post_id': post.id, 'parent_id': (parent_obj.id if parent_obj else None)},
        )
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    def _create_revision(self, *, post: Post, editor) -> None:
        # Sequence monotonic per post
        with transaction.atomic():
            last = PostRevision.objects.select_for_update().filter(post=post).order_by('-sequence').first()
            seq = (last.sequence + 1) if last else 1
            PostRevision.objects.create(
                post=post,
                editor=editor,
                sequence=seq,
                title=post.title,
                body=post.body or '',
                cover_image_name=(post.cover_image.name if getattr(post, 'cover_image', None) else ''),
            )


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.select_related('post', 'author', 'parent')
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    http_method_names = ['get', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        post_id = self.request.query_params.get('post')
        if post_id:
            try:
                return qs.filter(post_id=int(post_id))
            except ValueError:
                return qs.none()
        # Avoid exposing all comments by default.
        return qs.none()

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        user = request.user
        if not user or not user.is_authenticated:
            raise PermissionDenied('Authentication required.')
        is_author = obj.author_id == user.id
        if not (is_author or getattr(user, 'is_staff', False)):
            raise PermissionDenied('Not allowed.')

        # Scoped staff can only delete comments within allowed boards.
        if (not is_author) and getattr(user, 'is_staff', False) and getattr(user, 'staff_board_scoped', False) and (not getattr(user, 'is_superuser', False)):
            board_id = getattr(getattr(obj, 'post', None), 'board_id', None)
            if not staff_can_delete_board(user, board_id):
                raise PermissionDenied('Not allowed for this board.')

        if not obj.is_deleted:
            obj.is_deleted = True
            obj.body = ''
            obj.save(update_fields=['is_deleted', 'body', 'updated_at'])
            write_audit_log(
                actor=user,
                action='comment.delete',
                target_type='comment',
                target_id=str(obj.id),
                request=request,
                metadata={'post_id': obj.post_id},
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='revisions', permission_classes=[IsModerator])
    def revisions(self, request, pk=None):
        post = self.get_object()
        if getattr(request.user, 'staff_board_scoped', False) and (not getattr(request.user, 'is_superuser', False)):
            if not staff_can_moderate_board(request.user, getattr(post, 'board_id', None)):
                raise PermissionDenied('Not allowed for this board.')
        qs = PostRevision.objects.select_related('editor').filter(post=post).order_by('sequence')
        data = [
            {
                'id': r.id,
                'sequence': r.sequence,
                'editor_username': (r.editor.username if r.editor else ''),
                'created_at': r.created_at,
            }
            for r in qs
        ]
        return Response(PostRevisionSerializer(data, many=True).data)

    @action(detail=True, methods=['get'], url_path='revisions/(?P<rev_id>[^/.]+)/diff', permission_classes=[IsModerator])
    def revision_diff(self, request, pk=None, rev_id=None):
        post = self.get_object()
        if getattr(request.user, 'staff_board_scoped', False) and (not getattr(request.user, 'is_superuser', False)):
            if not staff_can_moderate_board(request.user, getattr(post, 'board_id', None)):
                raise PermissionDenied('Not allowed for this board.')
        try:
            rev = PostRevision.objects.get(post=post, id=rev_id)
        except PostRevision.DoesNotExist:
            return Response({'detail': 'Revision not found.'}, status=status.HTTP_404_NOT_FOUND)

        prev = (
            PostRevision.objects.filter(post=post, sequence__lt=rev.sequence)
            .order_by('-sequence')
            .first()
        )

        def udiff(a: str, b: str, from_name: str, to_name: str) -> str:
            return ''.join(
                difflib.unified_diff(
                    (a or '').splitlines(keepends=True),
                    (b or '').splitlines(keepends=True),
                    fromfile=from_name,
                    tofile=to_name,
                    lineterm=''
                )
            )

        title_diff = udiff(prev.title if prev else '', rev.title, 'title(prev)', f'title(rev {rev.sequence})')
        body_diff = udiff(prev.body if prev else '', rev.body, 'body(prev)', f'body(rev {rev.sequence})')
        cover_changed = (prev.cover_image_name if prev else '') != (rev.cover_image_name or '')

        payload = {
            'from_revision_id': prev.id if prev else None,
            'to_revision_id': rev.id,
            'title_diff': title_diff,
            'body_diff': body_diff,
            'cover_changed': cover_changed,
        }
        return Response(PostRevisionDiffSerializer(payload).data)

    @action(detail=False, methods=['get'], url_path='moderation/pending', permission_classes=[IsModerator])
    def pending(self, request):
        qs = Post.objects.select_related('board', 'author').filter(status=Post.Status.PENDING).order_by('-created_at')
        if getattr(request.user, 'staff_board_scoped', False) and (not getattr(request.user, 'is_superuser', False)):
            allowed = staff_allowed_board_ids(request.user, for_action='moderate')
            qs = qs.filter(board_id__in=allowed)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['post'], url_path='approve', permission_classes=[IsModerator])
    def approve(self, request, pk=None):
        post = self.get_object()
        if getattr(request.user, 'staff_board_scoped', False) and (not getattr(request.user, 'is_superuser', False)):
            if not staff_can_moderate_board(request.user, getattr(post, 'board_id', None)):
                raise PermissionDenied('Not allowed for this board.')
        post.status = Post.Status.PUBLISHED
        post.reviewed_by = request.user
        post.reviewed_at = timezone.now()
        post.reject_reason = ''
        post.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'reject_reason'])
        write_audit_log(
            actor=request.user,
            action='post.approve',
            target_type='post',
            target_id=str(post.id),
            request=request,
        )
        return Response(self.get_serializer(post).data)

    @action(detail=True, methods=['post'], url_path='reject', permission_classes=[IsModerator])
    def reject(self, request, pk=None):
        post = self.get_object()
        if getattr(request.user, 'staff_board_scoped', False) and (not getattr(request.user, 'is_superuser', False)):
            if not staff_can_moderate_board(request.user, getattr(post, 'board_id', None)):
                raise PermissionDenied('Not allowed for this board.')
        reason = (request.data.get('reason') or '')[:200]
        post.status = Post.Status.REJECTED
        post.reviewed_by = request.user
        post.reviewed_at = timezone.now()
        post.reject_reason = reason
        post.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'reject_reason'])
        write_audit_log(
            actor=request.user,
            action='post.reject',
            target_type='post',
            target_id=str(post.id),
            request=request,
            metadata={'reason': reason},
        )
        return Response(self.get_serializer(post).data, status=status.HTTP_200_OK)
