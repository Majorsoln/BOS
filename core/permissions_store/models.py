"""
BOS Permissions Store - Relational Permission Grants
====================================================
RolePermission maps identity roles to canonical permission keys.
"""

from __future__ import annotations

from django.db import models


class RolePermission(models.Model):
    role = models.ForeignKey(
        "core_identity_store.Role",
        on_delete=models.PROTECT,
        related_name="role_permissions",
        db_column="role_id",
    )
    permission_key = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bos_role_permissions"
        ordering = ["role_id", "permission_key", "id"]
        indexes = [
            models.Index(fields=["permission_key"], name="idx_role_perm_key"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission_key"],
                name="uq_role_permission",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.role_id}:{self.permission_key}"
