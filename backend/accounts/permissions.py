from rest_framework import permissions


class IsModerator(permissions.BasePermission):
    """Baseline moderator: is_staff. (后续可扩展到 Group/角色权限)"""

    def has_permission(self, request, view) -> bool:
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated and user.is_staff)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated and user.is_superuser)
