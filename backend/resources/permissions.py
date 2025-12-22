from __future__ import annotations

from rest_framework import permissions


class IsResourceOwnerOrStaffOrReadOnly(permissions.BasePermission):
    """Read for everyone; write only for resource creator (or staff)."""

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_staff', False):
            return True
        return getattr(obj, 'created_by_id', None) == getattr(user, 'id', None)


class IsResourceOwnerOrStaff(permissions.BasePermission):
    """Non-safe methods for ResourceLink; allow only owner/staff."""

    def has_permission(self, request, view) -> bool:
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_staff', False):
            return True
        # obj is ResourceLink
        resource = getattr(obj, 'resource', None)
        return getattr(resource, 'created_by_id', None) == getattr(user, 'id', None)
