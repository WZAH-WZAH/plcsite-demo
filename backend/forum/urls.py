from rest_framework.routers import DefaultRouter

from .views import BoardViewSet, CommentViewSet, HomeHeroSlideViewSet, PostViewSet

router = DefaultRouter()
router.register('boards', BoardViewSet, basename='board')
router.register('home/hero', HomeHeroSlideViewSet, basename='home-hero')
router.register('posts', PostViewSet, basename='post')
router.register('comments', CommentViewSet, basename='comment')

urlpatterns = router.urls