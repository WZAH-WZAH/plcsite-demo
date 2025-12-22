from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .admin_views import (
    AdminAuditLogListView,
    AdminBanUserView,
    AdminGrantStaffView,
    AdminRevokeStaffView,
    AdminUnbanUserView,
    AdminUserListView,
)
from .views import MeAvatarView, MeView, PasswordCheckView, RegisterView, UserFollowToggleView


urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/password/check/', PasswordCheckView.as_view(), name='auth-password-check'),
    path('auth/token/', TokenObtainPairView.as_view(), name='auth-token'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('me/', MeView.as_view(), name='me'),
    path('me/avatar/', MeAvatarView.as_view(), name='me-avatar'),

    # Social APIs
    path('users/<int:user_id>/follow/', UserFollowToggleView.as_view(), name='user-follow-toggle'),

    # Admin APIs (基础管理：用户封禁/审计)
    path('admin/users/', AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:user_id>/ban/', AdminBanUserView.as_view(), name='admin-user-ban'),
    path('admin/users/<int:user_id>/unban/', AdminUnbanUserView.as_view(), name='admin-user-unban'),
    path('admin/users/<int:user_id>/grant-staff/', AdminGrantStaffView.as_view(), name='admin-user-grant-staff'),
    path('admin/users/<int:user_id>/revoke-staff/', AdminRevokeStaffView.as_view(), name='admin-user-revoke-staff'),
    path('admin/audit/', AdminAuditLogListView.as_view(), name='admin-audit'),
]