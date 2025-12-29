from rest_framework.routers import DefaultRouter

from .views import BoardViewSet, CommentViewSet, HomeHeroSlideViewSet, PostViewSet, TagViewSet

router = DefaultRouter()
router.register('boards', BoardViewSet, basename='board')
router.register('home/hero', HomeHeroSlideViewSet, basename='home-hero')
router.register('posts', PostViewSet, basename='post')
router.register('comments', CommentViewSet, basename='comment')
router.register('tags', TagViewSet, basename='tag')

urlpatterns = router.urls