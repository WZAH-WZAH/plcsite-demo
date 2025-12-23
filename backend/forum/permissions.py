from __future__ import annotations

from rest_framework import permissions


class IsAuthorOrStaffOrReadOnly(permissions.BasePermission):
    """Read for everyone.

    - Author can edit/delete own post.
    - Staff can delete any post but cannot edit others.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        is_author = getattr(obj, 'author_id', None) == getattr(user, 'id', None)

        if request.method == 'DELETE':
            if is_author:
                return True
            if getattr(user, 'is_superuser', False):
                return True
            if getattr(user, 'is_staff', False):
                if getattr(user, 'staff_board_scoped', False):
                    try:
                        from accounts.services import staff_can_delete_board

                        return bool(staff_can_delete_board(user, getattr(obj, 'board_id', None)))
                    except Exception:
                        return False
                return True
            return False

        # PUT/PATCH/etc: only author
        return bool(is_author)


class IsCommentAuthorOrStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        user = getattr(request, 'user', None)
        if request.method in permissions.SAFE_METHODS:
            return True
        if not user or not user.is_authenticated:
            return False
        is_author = getattr(obj, 'author_id', None) == getattr(user, 'id', None)
        if is_author:
            return True
        if getattr(user, 'is_superuser', False):
            return True
        if getattr(user, 'is_staff', False):
            if getattr(user, 'staff_board_scoped', False):
                try:
                    from accounts.services import staff_can_delete_board

                    post = getattr(obj, 'post', None)
                    board_id = getattr(post, 'board_id', None)
                    return bool(staff_can_delete_board(user, board_id))
                except Exception:
                    return False
            return True
        return False
