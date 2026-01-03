from __future__ import annotations

from rest_framework.permissions import BasePermission

from .enforcer import enforce


def casbin_permission(obj: str, act: str, dom: str = "*"):
    """Create a DRF permission class backed by Casbin."""

    class _CasbinPermission(BasePermission):
        message = "Not allowed."

        def has_permission(self, request, view):
            return enforce(request.user, dom, obj, act)

    return _CasbinPermission


class CanManageRBAC(BasePermission):
    """Only allow users who can manage RBAC policies."""

    message = "You do not have permission to manage RBAC."

    def has_permission(self, request, view):
        return enforce(request.user, "*", "rbac", "manage")
