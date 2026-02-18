"""
BOS Permissions - Public API
============================
"""

from core.permissions.constants import (
    GRANT_STATUS_ACTIVE,
    GRANT_STATUS_INACTIVE,
    PERMISSION_ADMIN_CONFIGURE,
    PERMISSION_CASH_MOVE,
    PERMISSION_CMD_EXECUTE_GENERIC,
    PERMISSION_DOC_ISSUE,
    PERMISSION_INVENTORY_MOVE,
    PERMISSION_POS_SELL,
    SCOPE_GRANT_BRANCH,
    SCOPE_GRANT_BUSINESS,
)
from core.permissions.db_provider import DbPermissionProvider
from core.permissions.models import Role, ScopeGrant
from core.permissions.provider import (
    InMemoryPermissionProvider,
    PermissionProvider,
)
from core.permissions.registry import resolve_required_permission


def __getattr__(name: str):
    if name in {"PermissionEvaluator", "PermissionEvaluationResult"}:
        from core.permissions.evaluator import (
            PermissionEvaluationResult,
            PermissionEvaluator,
        )

        if name == "PermissionEvaluator":
            return PermissionEvaluator
        return PermissionEvaluationResult
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "PERMISSION_CMD_EXECUTE_GENERIC",
    "PERMISSION_ADMIN_CONFIGURE",
    "PERMISSION_POS_SELL",
    "PERMISSION_CASH_MOVE",
    "PERMISSION_INVENTORY_MOVE",
    "PERMISSION_DOC_ISSUE",
    "SCOPE_GRANT_BUSINESS",
    "SCOPE_GRANT_BRANCH",
    "GRANT_STATUS_ACTIVE",
    "GRANT_STATUS_INACTIVE",
    "Role",
    "ScopeGrant",
    "PermissionProvider",
    "InMemoryPermissionProvider",
    "DbPermissionProvider",
    "PermissionEvaluator",
    "PermissionEvaluationResult",
    "resolve_required_permission",
]
