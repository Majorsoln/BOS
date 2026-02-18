"""
BOS Permissions - Command to Permission Registry
================================================
"""

from __future__ import annotations

from core.permissions.constants import (
    PERMISSION_ADMIN_CONFIGURE,
    PERMISSION_CASH_MOVE,
    PERMISSION_CMD_EXECUTE_GENERIC,
    PERMISSION_DOC_ISSUE,
    PERMISSION_INVENTORY_MOVE,
    PERMISSION_POS_SELL,
)

COMMAND_PERMISSION_MAP = {
    "inventory.stock.move.request": PERMISSION_INVENTORY_MOVE,
    "cash.session.open.request": PERMISSION_CASH_MOVE,
    "cash.session.close.request": PERMISSION_CASH_MOVE,
    "retail.sale.complete.request": PERMISSION_POS_SELL,
    "retail.sale.apply_discount.request": PERMISSION_POS_SELL,
    "retail.cart.apply_promotion.request": PERMISSION_POS_SELL,
    "doc.receipt.issue.request": PERMISSION_DOC_ISSUE,
    "doc.quote.issue.request": PERMISSION_DOC_ISSUE,
    "doc.invoice.issue.request": PERMISSION_DOC_ISSUE,
    "admin.feature_flag.set.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.feature_flag.clear.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.compliance_profile.upsert.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.compliance_profile.deactivate.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.document_template.upsert.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.document_template.deactivate.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.api_key.create.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.api_key.revoke.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.api_key.rotate.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.api_key.list.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.identity.bootstrap.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.roles.assign.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.roles.revoke.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.roles.list.request": PERMISSION_ADMIN_CONFIGURE,
    "admin.actors.list.request": PERMISSION_ADMIN_CONFIGURE,
    "test.thing.do.request": PERMISSION_CMD_EXECUTE_GENERIC,
    "test.x.y.request": PERMISSION_CMD_EXECUTE_GENERIC,
}


def resolve_required_permission(command_type: str) -> str | None:
    """Resolve required permission for a command type."""
    return COMMAND_PERMISSION_MAP.get(command_type)
