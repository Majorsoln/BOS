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
    # Legal / document compliance fields
    address = models.CharField(max_length=512, default="", blank=True)
    city = models.CharField(max_length=128, default="", blank=True)
    country_code = models.CharField(max_length=8, default="", blank=True)
    phone = models.CharField(max_length=64, default="", blank=True)
    email = models.CharField(max_length=255, default="", blank=True)
    tax_id = models.CharField(max_length=64, default="", blank=True)
    logo_url = models.CharField(max_length=512, default="", blank=True)
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


class ActorStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class Actor(models.Model):
    actor_id = models.CharField(primary_key=True, max_length=255)
    actor_type = models.CharField(max_length=20, choices=IdentityActorType.choices)
    display_name = models.CharField(max_length=255, default="", blank=True)
    status = models.CharField(
        max_length=20,
        choices=ActorStatus.choices,
        default=ActorStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_identity_actors"
        ordering = ["actor_id"]
        indexes = [
            models.Index(fields=["status"], name="idx_actor_status"),
        ]

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


class PlatformAdminRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    FINANCE_ADMIN = "FINANCE_ADMIN", "Finance Admin"
    AGENT_MANAGER = "AGENT_MANAGER", "Agent Manager"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER", "Compliance Officer"
    VIEWER = "VIEWER", "Viewer"


class PlatformAdminStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"


class PlatformAdminUser(models.Model):
    """
    Platform-level administrator with role-based access.
    Completely separate from tenant/business actors.
    """
    admin_id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=30,
        choices=PlatformAdminRole.choices,
        default=PlatformAdminRole.VIEWER,
    )
    status = models.CharField(
        max_length=20,
        choices=PlatformAdminStatus.choices,
        default=PlatformAdminStatus.ACTIVE,
    )
    api_key_hash = models.CharField(max_length=64, unique=True, blank=True, default="")
    created_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "bos_platform_admin_users"
        ordering = ["role", "name"]
        indexes = [
            models.Index(fields=["role", "status"], name="idx_padmin_role_status"),
            models.Index(fields=["email"], name="idx_padmin_email"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.role})"


# ---------- ROLE PERMISSIONS MATRIX ----------
# Which nav sections each role can access. Enforced in the frontend sidebar
# and used by backend guards. Extend here when new sections are added.

PLATFORM_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "SUPER_ADMIN": frozenset([
        "dashboard", "agents", "finance", "pricing", "rates",
        "subscriptions", "trials", "promotions", "regions", "compliance",
        "audit", "health", "tenants", "admins", "governance",
    ]),
    "FINANCE_ADMIN": frozenset([
        "dashboard", "finance", "rates", "subscriptions", "trials",
        "audit", "health",
    ]),
    "AGENT_MANAGER": frozenset([
        "dashboard", "agents", "tenants", "promotions", "subscriptions",
        "trials", "audit",
    ]),
    "COMPLIANCE_OFFICER": frozenset([
        "dashboard", "compliance", "regions", "governance", "audit", "health",
    ]),
    "VIEWER": frozenset([
        "dashboard", "audit",
    ]),
}


class CustomerProfileStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class CustomerProfile(models.Model):
    """Persistent customer profile scoped to a business."""
    customer_id = models.UUIDField(primary_key=True, editable=False)
    business = models.ForeignKey(
        Business,
        on_delete=models.PROTECT,
        related_name="customer_profiles",
        db_column="business_id",
    )
    display_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=64, default="", blank=True)
    email = models.CharField(max_length=255, default="", blank=True)
    address = models.CharField(max_length=512, default="", blank=True)
    status = models.CharField(
        max_length=20,
        choices=CustomerProfileStatus.choices,
        default=CustomerProfileStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bos_identity_customer_profiles"
        ordering = ["business_id", "display_name"]
        indexes = [
            models.Index(
                fields=["business", "status"],
                name="idx_custprof_biz_status",
            ),
            models.Index(
                fields=["business", "phone"],
                name="idx_custprof_biz_phone",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.customer_id} ({self.display_name})"
