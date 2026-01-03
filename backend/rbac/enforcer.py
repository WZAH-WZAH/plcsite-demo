from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import casbin

from .adapter import DjangoAdapter


def _model_path() -> str:
    # rbac/casbin_model.conf
    here = Path(__file__).resolve().parent
    return str(here / "casbin_model.conf")


@lru_cache(maxsize=1)
def get_enforcer() -> casbin.Enforcer:
    adapter = DjangoAdapter()
    e = casbin.Enforcer(_model_path(), adapter)
    e.load_policy()
    e.enable_auto_save(True)
    return e


def enforce(user, dom: str, obj: str, act: str) -> bool:
    """Enforce permission for a Django user.

    - superuser: always allow
    - staff: can be granted permissions via direct policy on subject "role:staff"
      even without explicit grouping rules
    - normal users: use subject = user.pid (fallback to str(user.pk))
    """

    if getattr(user, "is_superuser", False):
        return True
    if not getattr(user, "is_authenticated", False):
        return False

    subject: Optional[str] = getattr(user, "pid", None)
    if not subject:
        subject = str(getattr(user, "pk", ""))

    e = get_enforcer()

    if e.enforce(subject, dom, obj, act):
        return True

    if getattr(user, "is_staff", False):
        return bool(e.enforce("role:staff", dom, obj, act))

    return False


def invalidate_enforcer_cache() -> None:
    get_enforcer.cache_clear()
