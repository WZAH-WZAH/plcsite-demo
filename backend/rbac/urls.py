from django.urls import path

from .views import (
    AssignmentListCreateView,
    AssignmentRemoveView,
    PolicyListCreateView,
    PolicyRemoveView,
)

urlpatterns = [
    path("admin/rbac/policies/", PolicyListCreateView.as_view(), name="rbac-policies"),
    path("admin/rbac/policies/remove/", PolicyRemoveView.as_view(), name="rbac-policies-remove"),
    path("admin/rbac/assignments/", AssignmentListCreateView.as_view(), name="rbac-assignments"),
    path(
        "admin/rbac/assignments/remove/",
        AssignmentRemoveView.as_view(),
        name="rbac-assignments-remove",
    ),
]
