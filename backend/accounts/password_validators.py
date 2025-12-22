from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class ComplexityValidator:
    """Require password to include lowercase + uppercase + digit."""

    def validate(self, password: str, user=None) -> None:
        if password is None:
            raise ValidationError(_('密码不能为空。'))

        has_lower = re.search(r"[a-z]", password) is not None
        has_upper = re.search(r"[A-Z]", password) is not None
        has_digit = re.search(r"\d", password) is not None

        if not (has_lower and has_upper and has_digit):
            raise ValidationError(_('需包含小写字母、大写字母和数字。'))

    def get_help_text(self) -> str:
        return str(_('密码需包含小写字母、大写字母和数字。'))
