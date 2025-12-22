from __future__ import annotations

from typing import Any

from .models import AuditLog


def get_client_ip(request) -> str | None:
    return request.META.get('REMOTE_ADDR')


def write_audit_log(
    *,
    actor: Any | None,
    action: str,
    target_type: str = '',
    target_id: str = '',
    request=None,
    metadata: dict[str, Any] | None = None,
) -> None:
    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        ip=get_client_ip(request) if request is not None else None,
        user_agent=((request.META.get('HTTP_USER_AGENT') or '')[:300] if request is not None else ''),
        metadata=metadata or {},
    )
