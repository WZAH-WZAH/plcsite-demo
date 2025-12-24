from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .admin_views import (
    AdminAuditLogListView,
    AdminBanUserView,
    AdminMuteUserView,
    AdminMuteUserView,
    AdminGrantStaffView,
    AdminRevokeStaffView,
    AdminUnmuteUserView,
    AdminUnbanUserView,
    AdminUnmuteUserView,
    AdminUserBoardPermsView,
    AdminUserListView,
)
from .views import (
    CustomTokenObtainPairView,
    MeAvatarView,
    MeBioView,
    MeCheckinView,
    MeNicknameView,
    MePostsView,
    MeUsernameView,
    MeSecondaryPasswordView,
    MeSecondaryPasswordVerifyView,
    MeView,
    PasswordCheckView,
    RegisterView,
    UserFollowToggleView,
)


urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/password/check/', PasswordCheckView.as_view(), name='auth-password-check'),
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='auth-token'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('me/', MeView.as_view(), name='me'),
    path('me/avatar/', MeAvatarView.as_view(), name='me-avatar'),
    path('me/checkin/', MeCheckinView.as_view(), name='me-checkin'),
    path('me/bio/', MeBioView.as_view(), name='me-bio'),
    path('me/nickname/', MeNicknameView.as_view(), name='me-nickname'),
    path('me/username/', MeUsernameView.as_view(), name='me-username'),
    path('me/secondary-password/', MeSecondaryPasswordView.as_view(), name='me-secondary-password'),
    path('me/secondary-password/verify/', MeSecondaryPasswordVerifyView.as_view(), name='me-secondary-password-verify'),
    path('me/posts/', MePostsView.as_view(), name='me-posts'),

    # Social APIs
    path('users/<int:user_id>/follow/', UserFollowToggleView.as_view(), name='user-follow-toggle'),

    # Admin APIs (基础管理：用户封禁/审计)
    path('admin/users/', AdminUserListView.as_view(), name='admin-users'),
    path('admin/users/<int:user_id>/ban/', AdminBanUserView.as_view(), name='admin-user-ban'),
    path('admin/users/<int:user_id>/mute/', AdminMuteUserView.as_view(), name='admin-user-mute'),
    path('admin/users/<int:user_id>/unban/', AdminUnbanUserView.as_view(), name='admin-user-unban'),
    path('admin/users/<int:user_id>/unmute/', AdminUnmuteUserView.as_view(), name='admin-user-unmute'),
    path('admin/users/<int:user_id>/grant-staff/', AdminGrantStaffView.as_view(), name='admin-user-grant-staff'),
    path('admin/users/<int:user_id>/revoke-staff/', AdminRevokeStaffView.as_view(), name='admin-user-revoke-staff'),
    path('admin/users/<int:user_id>/board-perms/', AdminUserBoardPermsView.as_view(), name='admin-user-board-perms'),
    path('admin/audit/', AdminAuditLogListView.as_view(), name='admin-audit'),
]