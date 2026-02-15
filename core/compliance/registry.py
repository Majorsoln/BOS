"""
BOS Compliance - Command to Compliance Targets Registry
=======================================================
"""

from __future__ import annotations


COMPLIANCE_TARGET_MAP = {
    "retail.sale.complete.request": ("DOCUMENT:RECEIPT", "CASH:MOVE"),
    "cash.session.open.request": ("CASH:MOVE",),
    "cash.session.close.request": ("CASH:MOVE",),
    "inventory.stock.move.request": ("INVENTORY:MOVE",),
    "test.x.y.request": ("DOCUMENT:INVOICE",),
}


def resolve_compliance_targets(command_type: str) -> tuple[str, ...]:
    return COMPLIANCE_TARGET_MAP.get(command_type, tuple())

