from typing import Any, Dict, cast

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .enforcer import get_enforcer, invalidate_enforcer_cache
from .permissions import CanManageRBAC
from .serializers import AssignmentSerializer, PolicySerializer


class PolicyListCreateView(APIView):
    permission_classes = [CanManageRBAC]

    def get(self, request):
        e = get_enforcer()
        policies = [
            {"sub": p[0], "dom": p[1], "obj": p[2], "act": p[3]}
            for p in e.get_policy()
            if len(p) >= 4
        ]
        return Response({"results": policies})

    def post(self, request):
        ser = PolicySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = cast(Dict[str, Any], ser.validated_data)

        e = get_enforcer()
        ok = e.add_policy(d.get("sub", ""), d.get("dom", "*"), d.get("obj", ""), d.get("act", ""))
        invalidate_enforcer_cache()
        return Response({"ok": bool(ok)}, status=status.HTTP_201_CREATED)


class PolicyRemoveView(APIView):
    permission_classes = [CanManageRBAC]

    def post(self, request):
        ser = PolicySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = cast(Dict[str, Any], ser.validated_data)

        e = get_enforcer()
        ok = e.remove_policy(d.get("sub", ""), d.get("dom", "*"), d.get("obj", ""), d.get("act", ""))
        invalidate_enforcer_cache()
        return Response({"ok": bool(ok)})


class AssignmentListCreateView(APIView):
    permission_classes = [CanManageRBAC]

    def get(self, request):
        e = get_enforcer()
        grouping = [
            {"user": g[0], "role": g[1], "dom": g[2] if len(g) > 2 else "*"}
            for g in e.get_grouping_policy()
            if len(g) >= 2
        ]
        return Response({"results": grouping})

    def post(self, request):
        ser = AssignmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = cast(Dict[str, Any], ser.validated_data)

        e = get_enforcer()
        ok = e.add_grouping_policy(d.get("user", ""), d.get("role", ""), d.get("dom", "*"))
        invalidate_enforcer_cache()
        return Response({"ok": bool(ok)}, status=status.HTTP_201_CREATED)


class AssignmentRemoveView(APIView):
    permission_classes = [CanManageRBAC]

    def post(self, request):
        ser = AssignmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = cast(Dict[str, Any], ser.validated_data)

        e = get_enforcer()
        ok = e.remove_grouping_policy(d.get("user", ""), d.get("role", ""), d.get("dom", "*"))
        invalidate_enforcer_cache()
        return Response({"ok": bool(ok)})
