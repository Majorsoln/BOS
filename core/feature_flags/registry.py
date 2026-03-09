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

# Document engine — gates all standard document issuance (receipts, invoices, quotes, etc.)
# Separate from DOCUMENT_DESIGNER which gates custom template editing in the UI.
FLAG_ENABLE_DOCUMENT_ENGINE = "ENABLE_DOCUMENT_ENGINE"

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
FLAG_ENABLE_HOTEL_ENGINE = "ENABLE_HOTEL_ENGINE"
FLAG_ENABLE_LOYALTY_ENGINE = "ENABLE_LOYALTY_ENGINE"
FLAG_ENABLE_WALLET_ENGINE = "ENABLE_WALLET_ENGINE"
FLAG_ENABLE_CUSTOMER_ENGINE = "ENABLE_CUSTOMER_ENGINE"
FLAG_ENABLE_QR_MENU_ENGINE = "ENABLE_QR_MENU_ENGINE"

# Catalog of all valid flag keys — prevents typo gaps at configuration time
VALID_FLAG_KEYS: frozenset[str] = frozenset(
    {
        FLAG_ENABLE_COMPLIANCE_ENGINE,
        FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
        FLAG_ENABLE_DOCUMENT_DESIGNER,
        FLAG_ENABLE_DOCUMENT_RENDER_PLAN,
        FLAG_ENABLE_DOCUMENT_ENGINE,
        FLAG_ENABLE_ACCOUNTING_ENGINE,
        FLAG_ENABLE_CASH_ENGINE,
        FLAG_ENABLE_INVENTORY_ENGINE,
        FLAG_ENABLE_PROCUREMENT_ENGINE,
        FLAG_ENABLE_RETAIL_ENGINE,
        FLAG_ENABLE_RESTAURANT_ENGINE,
        FLAG_ENABLE_WORKSHOP_ENGINE,
        FLAG_ENABLE_PROMOTION_ENGINE,
        FLAG_ENABLE_HR_ENGINE,
        FLAG_ENABLE_REPORTING_ENGINE,
        FLAG_ENABLE_HOTEL_ENGINE,
        FLAG_ENABLE_LOYALTY_ENGINE,
        FLAG_ENABLE_WALLET_ENGINE,
        FLAG_ENABLE_CUSTOMER_ENGINE,
        FLAG_ENABLE_QR_MENU_ENGINE,
    }
)


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
    "accounting.statement.generate.request": FLAG_ENABLE_ACCOUNTING_ENGINE,
    "accounting.ar_aging.snapshot.request": FLAG_ENABLE_ACCOUNTING_ENGINE,

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
    # Phase 16 — Style Registry & Quote Engine
    "workshop.style.register.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "workshop.style.update.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "workshop.style.deactivate.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "workshop.quote.generate.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    # Phase 17 — Multi-Item Project Quotes
    "workshop.project.quote.generate.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    # Phase 18 — Quote Acceptance / Rejection
    "workshop.quote.accept.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "workshop.quote.reject.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    # Material Requisition
    "workshop.material.requisition.request": FLAG_ENABLE_WORKSHOP_ENGINE,

    # ── Restaurant Engine (additional) ───────────────────────
    "restaurant.bill.present.request": FLAG_ENABLE_RESTAURANT_ENGINE,

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

    # ── Reporting / BI Engine ─────────────────────────────────
    "reporting.snapshot.record.request": FLAG_ENABLE_REPORTING_ENGINE,
    "reporting.kpi.record.request": FLAG_ENABLE_REPORTING_ENGINE,
    "reporting.report.generate.request": FLAG_ENABLE_REPORTING_ENGINE,

    # ── Hotel Engine ──────────────────────────────────────────
    "hotel.reservation.create.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.reservation.confirm.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.reservation.modify.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.reservation.cancel.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.reservation.no_show.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.guest.check_in.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.guest.check_out.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.stay.extend.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.early_departure.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.folio.open.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.folio.post_charge.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.folio.receive_payment.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.folio.settle.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.folio.adjust.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.folio.apply_credit.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.folio.split.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.folio.transfer.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.room.create.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.room.change_status.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.room.move.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.room.set_out_of_order.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.room.return_to_service.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.room_type.define.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.room_type.update.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.room_night.post_charge.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.rate_plan.create.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.rate_plan.update.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.rate_plan.deactivate.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.seasonal_rate.set.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.night_audit.run.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.property.configure.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.housekeeping.assign_task.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.housekeeping.start_task.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.housekeeping.complete_task.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.housekeeping.inspect_room.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.housekeeping.fail_inspection.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.lost_found.log.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.lost_found.claim.request": FLAG_ENABLE_HOTEL_ENGINE,
    "hotel.maintenance.resolve.request": FLAG_ENABLE_HOTEL_ENGINE,

    # ── Loyalty Engine ────────────────────────────────────────
    "loyalty.program.configure.request": FLAG_ENABLE_LOYALTY_ENGINE,
    "loyalty.points.earn.request": FLAG_ENABLE_LOYALTY_ENGINE,
    "loyalty.points.redeem.request": FLAG_ENABLE_LOYALTY_ENGINE,
    "loyalty.points.adjust.request": FLAG_ENABLE_LOYALTY_ENGINE,
    "loyalty.points.expire.request": FLAG_ENABLE_LOYALTY_ENGINE,
    "loyalty.points.reverse.request": FLAG_ENABLE_LOYALTY_ENGINE,

    # ── Wallet Engine ─────────────────────────────────────────
    "wallet.policy.configure.request": FLAG_ENABLE_WALLET_ENGINE,
    "wallet.credit.issue.request": FLAG_ENABLE_WALLET_ENGINE,
    "wallet.credit.spend.request": FLAG_ENABLE_WALLET_ENGINE,
    "wallet.credit.reverse.request": FLAG_ENABLE_WALLET_ENGINE,
    "wallet.credit.expire.request": FLAG_ENABLE_WALLET_ENGINE,
    "wallet.credit.freeze.request": FLAG_ENABLE_WALLET_ENGINE,
    "wallet.credit.unfreeze.request": FLAG_ENABLE_WALLET_ENGINE,
    "wallet.credit.adjust.request": FLAG_ENABLE_WALLET_ENGINE,

    # ── Customer Engine ───────────────────────────────────────
    "customer.profile.create.request": FLAG_ENABLE_CUSTOMER_ENGINE,
    "customer.profile.update.request": FLAG_ENABLE_CUSTOMER_ENGINE,
    "customer.global.register.request": FLAG_ENABLE_CUSTOMER_ENGINE,
    "customer.link.request.request": FLAG_ENABLE_CUSTOMER_ENGINE,
    "customer.link.approve.request": FLAG_ENABLE_CUSTOMER_ENGINE,
    "customer.link.revoke.request": FLAG_ENABLE_CUSTOMER_ENGINE,
    "customer.segment.assign.request": FLAG_ENABLE_CUSTOMER_ENGINE,
    "customer.consent.update_scope.request": FLAG_ENABLE_CUSTOMER_ENGINE,

    # ── QR Menu Engine ────────────────────────────────────────
    "qr_menu.register.request": FLAG_ENABLE_QR_MENU_ENGINE,
    "qr_menu.session.create.request": FLAG_ENABLE_QR_MENU_ENGINE,
    "qr_menu.session.expire.request": FLAG_ENABLE_QR_MENU_ENGINE,
    "qr_menu.item.order.request": FLAG_ENABLE_QR_MENU_ENGINE,
    "qr_menu.item.remove.request": FLAG_ENABLE_QR_MENU_ENGINE,
    "qr_menu.order.submit.request": FLAG_ENABLE_QR_MENU_ENGINE,
    "qr_menu.order.accept.request": FLAG_ENABLE_QR_MENU_ENGINE,
    "qr_menu.order.reject.request": FLAG_ENABLE_QR_MENU_ENGINE,
    "qr_menu.order.clarify.request": FLAG_ENABLE_QR_MENU_ENGINE,
}


def resolve_flag_for_command(command_type: str) -> str | None:
    return COMMAND_FLAG_MAP.get(command_type)
