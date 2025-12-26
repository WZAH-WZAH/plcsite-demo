from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter

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
    AuthEmailVerifyCodeSendView,
    AuthEmailVerifyCodeVerifyView,
    CustomTokenObtainPairView,
    MeEmailVerifyCodeSendView,
    MeEmailVerifyCodeVerifyView,
    MeAvatarView,
    MeBioView,
    MeCheckinView,
    MeNicknameView,
    MePasswordChangeView,
    MePostsView,
    MeUsernameView,
    MeView,
    PasswordCheckView,
    PasswordResetView,
    RegisterView,
    UserViewSet,
)


router = DefaultRouter()
router.register('users', UserViewSet, basename='user')


urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/email/verify-code/send/', AuthEmailVerifyCodeSendView.as_view(), name='auth-email-verify-code-send'),
    path('auth/email/verify-code/verify/', AuthEmailVerifyCodeVerifyView.as_view(), name='auth-email-verify-code-verify'),
    path('auth/password/reset/', PasswordResetView.as_view(), name='auth-password-reset'),
    path('auth/password/check/', PasswordCheckView.as_view(), name='auth-password-check'),
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='auth-token'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('me/', MeView.as_view(), name='me'),
    path('me/avatar/', MeAvatarView.as_view(), name='me-avatar'),
    path('me/checkin/', MeCheckinView.as_view(), name='me-checkin'),
    path('me/bio/', MeBioView.as_view(), name='me-bio'),
    path('me/nickname/', MeNicknameView.as_view(), name='me-nickname'),
    path('me/username/', MeUsernameView.as_view(), name='me-username'),
    path('me/password/', MePasswordChangeView.as_view(), name='me-password-change'),
    path('me/email/verify-code/send/', MeEmailVerifyCodeSendView.as_view(), name='me-email-verify-code-send'),
    path('me/email/verify-code/verify/', MeEmailVerifyCodeVerifyView.as_view(), name='me-email-verify-code-verify'),
    path('me/posts/', MePostsView.as_view(), name='me-posts'),

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

urlpatterns += router.urls