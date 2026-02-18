"""
BOS Identity Store - Relational Identity State
==============================================
DB-backed identity primitives for business, branch, actor, roles, and grants.
"""

from __future__ import annotations

import uuid

from django.db import models


class IdentityActorType(models.TextChoices):
    HUMAN = "HUMAN", "Human"
    SYSTEM = "SYSTEM", "System"
    DEVICE = "DEVICE", "Device"
    AI = "AI", "AI"


class RoleAssignmentStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class Business(models.Model):
    business_id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    default_currency = models.CharField(max_length=16, default="USD")
    default_language = models.CharField(max_length=16, default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_identity_businesses"
        ordering = ["business_id"]

    def __str__(self) -> str:
        return f"{self.business_id} ({self.name})"


class Branch(models.Model):
    branch_id = models.UUIDField(primary_key=True, editable=False)
    business = models.ForeignKey(
        Business,
        on_delete=models.PROTECT,
        related_name="branches",
        db_column="business_id",
    )
    name = models.CharField(max_length=255)
    timezone = models.CharField(max_length=64, default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_identity_branches"
        ordering = ["business_id", "branch_id"]
        indexes = [
            models.Index(fields=["business", "branch_id"], name="idx_branch_biz_branch"),
        ]

    def __str__(self) -> str:
        return f"{self.branch_id} ({self.name})"


class Actor(models.Model):
    actor_id = models.CharField(primary_key=True, max_length=255)
    actor_type = models.CharField(max_length=20, choices=IdentityActorType.choices)
    display_name = models.CharField(max_length=255, default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_identity_actors"
        ordering = ["actor_id"]

    def __str__(self) -> str:
        return f"{self.actor_id} ({self.actor_type})"


class Role(models.Model):
    role_id = models.UUIDField(primary_key=True, editable=False)
    business = models.ForeignKey(
        Business,
        on_delete=models.PROTECT,
        related_name="roles",
        db_column="business_id",
    )
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_identity_roles"
        ordering = ["business_id", "name", "role_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "name"],
                name="uq_identity_role_business_name",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.business_id})"


class RoleAssignment(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    business = models.ForeignKey(
        Business,
        on_delete=models.PROTECT,
        related_name="role_assignments",
        db_column="business_id",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="role_assignments",
        db_column="branch_id",
    )
    actor = models.ForeignKey(
        Actor,
        on_delete=models.PROTECT,
        related_name="role_assignments",
        db_column="actor_id",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="assignments",
        db_column="role_id",
    )
    status = models.CharField(
        max_length=20,
        choices=RoleAssignmentStatus.choices,
        default=RoleAssignmentStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_identity_role_assignments"
        ordering = ["business_id", "actor_id", "branch_id", "role_id", "id"]
        indexes = [
            models.Index(
                fields=["business", "actor", "status"],
                name="idx_role_asg_biz_actor_status",
            ),
            models.Index(
                fields=["business", "branch", "status"],
                name="idx_role_asg_biz_branch_status",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "branch", "actor", "role"],
                name="uq_identity_role_assignment",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.actor_id}:{self.role_id}:{self.status}"
