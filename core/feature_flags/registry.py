"""
BOS Feature Flags - Command to Flag Registry
============================================
Every major engine is wrapped behind a feature flag.
Default: OFF unless explicitly activated per business.
Doctrine: AGENTS.md Rule 14.
"""

from __future__ import annotations


# ══════════════════════════════════════════════════════════════
# FLAG KEY CONSTANTS — one per major engine/feature
# ══════════════════════════════════════════════════════════════

# Legacy / core flags
FLAG_ENABLE_COMPLIANCE_ENGINE = "ENABLE_COMPLIANCE_ENGINE"
FLAG_ENABLE_ADVANCED_POLICY_ESCALATION = "ENABLE_ADVANCED_POLICY_ESCALATION"
FLAG_ENABLE_DOCUMENT_DESIGNER = "ENABLE_DOCUMENT_DESIGNER"
FLAG_ENABLE_DOCUMENT_RENDER_PLAN = "ENABLE_DOCUMENT_RENDER_PLAN"

# Engine flags (Phase 5+)
FLAG_ENABLE_ACCOUNTING_ENGINE = "ENABLE_ACCOUNTING_ENGINE"
FLAG_ENABLE_CASH_ENGINE = "ENABLE_CASH_ENGINE"
FLAG_ENABLE_INVENTORY_ENGINE = "ENABLE_INVENTORY_ENGINE"
FLAG_ENABLE_PROCUREMENT_ENGINE = "ENABLE_PROCUREMENT_ENGINE"
FLAG_ENABLE_RETAIL_ENGINE = "ENABLE_RETAIL_ENGINE"
FLAG_ENABLE_RESTAURANT_ENGINE = "ENABLE_RESTAURANT_ENGINE"
FLAG_ENABLE_WORKSHOP_ENGINE = "ENABLE_WORKSHOP_ENGINE"
FLAG_ENABLE_PROMOTION_ENGINE = "ENABLE_PROMOTION_ENGINE"
FLAG_ENABLE_HR_ENGINE = "ENABLE_HR_ENGINE"
FLAG_ENABLE_REPORTING_ENGINE = "ENABLE_REPORTING_ENGINE"
FLAG_ENABLE_BILLING_ENGINE = "ENABLE_BILLING_ENGINE"


# ══════════════════════════════════════════════════════════════
# COMMAND → FLAG MAP
# Every command type for every major engine maps to its flag.
# Commands not listed here are always allowed (no flag check).
# ══════════════════════════════════════════════════════════════

COMMAND_FLAG_MAP: dict[str, str] = {
    # ── Legacy ────────────────────────────────────────────────
    "compliance.profile.assign.request": FLAG_ENABLE_COMPLIANCE_ENGINE,
    "policy.escalation.advanced.request": FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
    "document.template.design.request": FLAG_ENABLE_DOCUMENT_DESIGNER,
    "test.x.y.request": FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,

    # ── Accounting Engine ─────────────────────────────────────
    "accounting.journal.post.request": FLAG_ENABLE_ACCOUNTING_ENGINE,
    "accounting.journal.reverse.request": FLAG_ENABLE_ACCOUNTING_ENGINE,
    "accounting.account.create.request": FLAG_ENABLE_ACCOUNTING_ENGINE,
    "accounting.obligation.create.request": FLAG_ENABLE_ACCOUNTING_ENGINE,
    "accounting.obligation.fulfill.request": FLAG_ENABLE_ACCOUNTING_ENGINE,

    # ── Cash Engine ───────────────────────────────────────────
    "cash.session.open.request": FLAG_ENABLE_CASH_ENGINE,
    "cash.session.close.request": FLAG_ENABLE_CASH_ENGINE,
    "cash.payment.record.request": FLAG_ENABLE_CASH_ENGINE,
    "cash.deposit.record.request": FLAG_ENABLE_CASH_ENGINE,
    "cash.withdrawal.record.request": FLAG_ENABLE_CASH_ENGINE,

    # ── Inventory Engine ──────────────────────────────────────
    "inventory.item.register.request": FLAG_ENABLE_INVENTORY_ENGINE,
    "inventory.item.update.request": FLAG_ENABLE_INVENTORY_ENGINE,
    "inventory.stock.receive.request": FLAG_ENABLE_INVENTORY_ENGINE,
    "inventory.stock.issue.request": FLAG_ENABLE_INVENTORY_ENGINE,
    "inventory.stock.transfer.request": FLAG_ENABLE_INVENTORY_ENGINE,
    "inventory.stock.adjust.request": FLAG_ENABLE_INVENTORY_ENGINE,

    # ── Procurement Engine ────────────────────────────────────
    "procurement.order.create.request": FLAG_ENABLE_PROCUREMENT_ENGINE,
    "procurement.order.approve.request": FLAG_ENABLE_PROCUREMENT_ENGINE,
    "procurement.order.receive.request": FLAG_ENABLE_PROCUREMENT_ENGINE,
    "procurement.invoice.match.request": FLAG_ENABLE_PROCUREMENT_ENGINE,
    "procurement.order.cancel.request": FLAG_ENABLE_PROCUREMENT_ENGINE,
    "procurement.requisition.create.request": FLAG_ENABLE_PROCUREMENT_ENGINE,
    "procurement.requisition.approve.request": FLAG_ENABLE_PROCUREMENT_ENGINE,
    "procurement.payment.release.request": FLAG_ENABLE_PROCUREMENT_ENGINE,

    # ── Retail Engine ─────────────────────────────────────────
    "retail.sale.open.request": FLAG_ENABLE_RETAIL_ENGINE,
    "retail.sale.add_line.request": FLAG_ENABLE_RETAIL_ENGINE,
    "retail.sale.remove_line.request": FLAG_ENABLE_RETAIL_ENGINE,
    "retail.sale.apply_discount.request": FLAG_ENABLE_RETAIL_ENGINE,
    "retail.sale.complete.request": FLAG_ENABLE_RETAIL_ENGINE,
    "retail.sale.void.request": FLAG_ENABLE_RETAIL_ENGINE,
    "retail.refund.issue.request": FLAG_ENABLE_RETAIL_ENGINE,

    # ── Restaurant Engine ─────────────────────────────────────
    "restaurant.table.open.request": FLAG_ENABLE_RESTAURANT_ENGINE,
    "restaurant.order.place.request": FLAG_ENABLE_RESTAURANT_ENGINE,
    "restaurant.order.serve_item.request": FLAG_ENABLE_RESTAURANT_ENGINE,
    "restaurant.bill.settle.request": FLAG_ENABLE_RESTAURANT_ENGINE,
    "restaurant.table.close.request": FLAG_ENABLE_RESTAURANT_ENGINE,
    "restaurant.order.cancel.request": FLAG_ENABLE_RESTAURANT_ENGINE,
    "restaurant.kitchen.ticket.send.request": FLAG_ENABLE_RESTAURANT_ENGINE,
    "restaurant.bill.split.request": FLAG_ENABLE_RESTAURANT_ENGINE,

    # ── Workshop Engine ───────────────────────────────────────
    "workshop.job.create.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "workshop.job.assign.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "workshop.job.start.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "workshop.job.complete.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "workshop.job.invoice.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "workshop.production.execute.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "workshop.cutlist.generate.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "workshop.material.consume.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "workshop.offcut.record.request": FLAG_ENABLE_WORKSHOP_ENGINE,

    # ── Promotion Engine ──────────────────────────────────────
    "promotion.campaign.create.request": FLAG_ENABLE_PROMOTION_ENGINE,
    "promotion.campaign.activate.request": FLAG_ENABLE_PROMOTION_ENGINE,
    "promotion.campaign.deactivate.request": FLAG_ENABLE_PROMOTION_ENGINE,
    "promotion.coupon.issue.request": FLAG_ENABLE_PROMOTION_ENGINE,
    "promotion.coupon.redeem.request": FLAG_ENABLE_PROMOTION_ENGINE,

    # ── HR Engine ─────────────────────────────────────────────
    "hr.employee.onboard.request": FLAG_ENABLE_HR_ENGINE,
    "hr.employee.terminate.request": FLAG_ENABLE_HR_ENGINE,
    "hr.shift.start.request": FLAG_ENABLE_HR_ENGINE,
    "hr.shift.end.request": FLAG_ENABLE_HR_ENGINE,
    "hr.leave.request.request": FLAG_ENABLE_HR_ENGINE,
    "hr.payroll.run.request": FLAG_ENABLE_HR_ENGINE,

    # ── Billing Engine ───────────────────────────────────────
    "billing.plan.assign.request": FLAG_ENABLE_BILLING_ENGINE,
    "billing.subscription.start.request": FLAG_ENABLE_BILLING_ENGINE,
    "billing.payment.record.request": FLAG_ENABLE_BILLING_ENGINE,
    "billing.payment.reverse.request": FLAG_ENABLE_BILLING_ENGINE,
    "billing.subscription.suspend.request": FLAG_ENABLE_BILLING_ENGINE,
    "billing.subscription.renew.request": FLAG_ENABLE_BILLING_ENGINE,
    "billing.subscription.cancel.request": FLAG_ENABLE_BILLING_ENGINE,
    "billing.subscription.resume.request": FLAG_ENABLE_BILLING_ENGINE,
    "billing.subscription.plan_change.request": FLAG_ENABLE_BILLING_ENGINE,
    "billing.subscription.mark_delinquent.request": FLAG_ENABLE_BILLING_ENGINE,
    "billing.subscription.clear_delinquency.request": FLAG_ENABLE_BILLING_ENGINE,
    "billing.subscription.write_off.request": FLAG_ENABLE_BILLING_ENGINE,
    "billing.usage.meter.request": FLAG_ENABLE_BILLING_ENGINE,

    # ── Reporting / BI Engine ─────────────────────────────────
    "reporting.snapshot.record.request": FLAG_ENABLE_REPORTING_ENGINE,
    "reporting.kpi.record.request": FLAG_ENABLE_REPORTING_ENGINE,
    "reporting.report.generate.request": FLAG_ENABLE_REPORTING_ENGINE,
}


def resolve_flag_for_command(command_type: str) -> str | None:
    return COMMAND_FLAG_MAP.get(command_type)
