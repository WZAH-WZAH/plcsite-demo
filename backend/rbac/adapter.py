from __future__ import annotations

from typing import Iterable, List

from casbin.persist.adapter import Adapter

from .models import CasbinRule


class DjangoAdapter(Adapter):
    """Casbin adapter backed by Django ORM."""

    def load_policy(self, model):
        for rule in CasbinRule.objects.all().iterator():
            line = ", ".join(
                [
                    rule.ptype,
                    rule.v0,
                    rule.v1,
                    rule.v2,
                    rule.v3,
                    rule.v4,
                    rule.v5,
                ]
            ).strip()
            self._load_policy_line(line, model)

    def save_policy(self, model) -> bool:
        CasbinRule.objects.all().delete()

        rules: List[CasbinRule] = []

        for ptype, ast in model.model.items():
            for sec, assertion in ast.items():
                if sec not in ("p", "g"):
                    continue
                for rule in assertion.policy:
                    v = list(rule) + [""] * (6 - len(rule))
                    rules.append(
                        CasbinRule(
                            ptype=ptype,
                            v0=v[0],
                            v1=v[1],
                            v2=v[2],
                            v3=v[3],
                            v4=v[4],
                            v5=v[5],
                        )
                    )

        CasbinRule.objects.bulk_create(rules, ignore_conflicts=True)
        return True

    def add_policy(self, sec, ptype, rule: Iterable[str]):
        values = list(rule)
        v = values + [""] * (6 - len(values))
        CasbinRule.objects.get_or_create(
            ptype=ptype,
            v0=v[0],
            v1=v[1],
            v2=v[2],
            v3=v[3],
            v4=v[4],
            v5=v[5],
        )

    def remove_policy(self, sec, ptype, rule: Iterable[str]):
        values = list(rule)
        v = values + [""] * (6 - len(values))
        CasbinRule.objects.filter(
            ptype=ptype,
            v0=v[0],
            v1=v[1],
            v2=v[2],
            v3=v[3],
            v4=v[4],
            v5=v[5],
        ).delete()

    def remove_filtered_policy(self, sec, ptype, field_index, *field_values):
        qs = CasbinRule.objects.filter(ptype=ptype)
        fields = ["v0", "v1", "v2", "v3", "v4", "v5"]
        for idx, field_value in enumerate(field_values):
            if field_value:
                qs = qs.filter(**{fields[field_index + idx]: field_value})
        qs.delete()

    @staticmethod
    def _load_policy_line(line: str, model) -> None:
        import casbin

        casbin.persist.load_policy_line(line, model)
