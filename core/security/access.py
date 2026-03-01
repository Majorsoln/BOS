"""
BOS Core Security — Access Control
=====================================
Permission definitions and access control decisions.
Phase 8 stubs — interfaces defined, enforcement deferred.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional


# ══════════════════════════════════════════════════════════════
# PERMISSION CONSTANTS
# ══════════════════════════════════════════════════════════════

class Permission:
    """
    Atomic permission constants.

    Convention: engine.resource.action
    Extensible by each engine.
    """

    # Cash engine
    CASH_SESSION_OPEN = "cash.session.open"
    CASH_SESSION_CLOSE = "cash.session.close"
    CASH_CASHIN_CREATE = "cash.cashin.create"
    CASH_CASHOUT_CREATE = "cash.cashout.create"

    # Inventory engine
    INVENTORY_RECEIVE = "inventory.stock.receive"
    INVENTORY_ADJUST = "inventory.stock.adjust"
    INVENTORY_TRANSFER = "inventory.stock.transfer"

    # Procurement engine
    PROCUREMENT_ORDER_CREATE = "procurement.order.create"
    PROCUREMENT_ORDER_APPROVE = "procurement.order.approve"

    # Retail engine
    RETAIL_SALE_CREATE = "retail.sale.create"
    RETAIL_RETURN_CREATE = "retail.return.create"

    # Restaurant engine
    RESTAURANT_ORDER_CREATE = "restaurant.order.create"
    RESTAURANT_ORDER_MODIFY = "restaurant.order.modify"

    # HR engine
    HR_EMPLOYEE_CREATE = "hr.employee.create"
    HR_PAYROLL_RUN = "hr.payroll.run"

    # Accounting engine
    ACCOUNTING_JOURNAL_POST = "accounting.journal.post"
    ACCOUNTING_PERIOD_CLOSE = "accounting.period.close"

    # Workshop engine
    WORKSHOP_JOB_CREATE = "workshop.job.create"

    # Reporting engine
    REPORTING_QUERY = "reporting.query.execute"


# ══════════════════════════════════════════════════════════════
# ACCESS DECISION
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AccessDecision:
    """
    Result of an access control check.

    Phase 8 will populate this from role/permission stores.
    Currently always grants access (permissive default).
    """

    actor_id: str
    permission: str
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID]
    granted: bool
    reason: str = ""


def check_access(
    actor_id: str,
    permission: str,
    business_id: uuid.UUID,
    branch_id: Optional[uuid.UUID] = None,
) -> AccessDecision:
    """
    Check if an actor has a given permission.

    Phase 8 stub: currently returns granted=True (permissive).
    """
    return AccessDecision(
        actor_id=actor_id,
        permission=permission,
        business_id=business_id,
        branch_id=branch_id,
        granted=True,
        reason="Phase 8 stub — permissive default",
    )
