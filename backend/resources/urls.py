from rest_framework.routers import DefaultRouter

from .views import ResourceEntryViewSet, ResourceLinkViewSet

router = DefaultRouter()
router.register('resources', ResourceEntryViewSet, basename='resource')
router.register('links', ResourceLinkViewSet, basename='link')

urlpatterns = router.urls