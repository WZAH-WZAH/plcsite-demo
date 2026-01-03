from django.db import models


class CasbinRule(models.Model):
    """Casbin policy rule storage.

    Compatible with Casbin adapter expectations:
    - ptype: "p" or "g"
    - v0..v5: rule values
    """

    ptype = models.CharField(max_length=8)
    v0 = models.CharField(max_length=255, blank=True, default="")
    v1 = models.CharField(max_length=255, blank=True, default="")
    v2 = models.CharField(max_length=255, blank=True, default="")
    v3 = models.CharField(max_length=255, blank=True, default="")
    v4 = models.CharField(max_length=255, blank=True, default="")
    v5 = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["ptype"]),
            models.Index(fields=["ptype", "v0"]),
            models.Index(fields=["ptype", "v0", "v1"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["ptype", "v0", "v1", "v2", "v3", "v4", "v5"],
                name="uniq_casbin_rule",
            )
        ]

    def __str__(self) -> str:
        parts = [self.ptype, self.v0, self.v1, self.v2, self.v3, self.v4, self.v5]
        parts = [p for p in parts if p]
        return ",".join(parts)
