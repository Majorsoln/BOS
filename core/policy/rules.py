"""
BOS Policy Engine — Initial Rule Set
========================================
Minimal deterministic rules for initial deployment.

Rules:
1. INV-001: Cannot sell negative stock (BLOCK)
2. PROMO-001: Discount > threshold (ESCALATE)
3. LIFE-001: Cannot modify CLOSED business (BLOCK)
4. COMP-001: Missing VAT validation for B2B zero-rating (ESCALATE)

All rules are pure. No DB. No persistence. No events.
"""

from __future__ import annotations

from typing import Any

from core.policy.contracts import BaseRule
from core.policy.result import RuleResult, Severity


# ══════════════════════════════════════════════════════════════
# INV-001: Cannot sell negative stock (BLOCK)
# ══════════════════════════════════════════════════════════════

class NegativeStockBlock(BaseRule):
    """
    BLOCK if requested quantity exceeds available stock.

    projected_state must contain:
        available_stock: int (current available quantity)

    command.payload must contain:
        quantity: int (requested quantity)
    """

    rule_id = "INV-001"
    version = "1.0.0"
    domain = "inventory"
    severity = Severity.BLOCK
    applies_to = [
        "inventory.stock.move.request",
        "inventory.stock.sell.request",
    ]

    def evaluate(
        self, command: Any, context: Any, projected_state: dict
    ) -> RuleResult:
        requested = command.payload.get("quantity", 0)
        available = projected_state.get("available_stock")

        if available is None:
            return self.pass_rule(
                message="No projected stock state available — skipping."
            )

        if requested > available:
            return self.fail(
                message=(
                    f"Insufficient stock: requested {requested}, "
                    f"available {available}."
                ),
                metadata={
                    "requested": requested,
                    "available": available,
                    "deficit": requested - available,
                },
            )

        return self.pass_rule(
            message=f"Stock sufficient: {requested} <= {available}."
        )


# ══════════════════════════════════════════════════════════════
# PROMO-001: Discount > threshold requires escalation (ESCALATE)
# ══════════════════════════════════════════════════════════════

class HighDiscountEscalate(BaseRule):
    """
    ESCALATE if discount percentage exceeds threshold.

    projected_state must contain:
        discount_threshold: float (e.g. 0.30 for 30%)

    command.payload must contain:
        discount_percent: float (e.g. 0.50 for 50%)
    """

    rule_id = "PROMO-001"
    version = "1.0.0"
    domain = "promotion"
    severity = Severity.ESCALATE
    applies_to = [
        "retail.sale.apply_discount.request",
        "retail.cart.apply_promotion.request",
    ]

    def evaluate(
        self, command: Any, context: Any, projected_state: dict
    ) -> RuleResult:
        discount = command.payload.get("discount_percent", 0.0)
        threshold = projected_state.get("discount_threshold", 0.30)

        if discount > threshold:
            return self.fail(
                message=(
                    f"Discount {discount:.0%} exceeds threshold "
                    f"{threshold:.0%}. Requires manager review."
                ),
                metadata={
                    "discount_percent": discount,
                    "threshold": threshold,
                    "excess": discount - threshold,
                },
            )

        return self.pass_rule(
            message=f"Discount {discount:.0%} within threshold."
        )


# ══════════════════════════════════════════════════════════════
# LIFE-001: Cannot modify CLOSED business (BLOCK)
# ══════════════════════════════════════════════════════════════

class ClosedBusinessBlock(BaseRule):
    """
    BLOCK if business lifecycle state is CLOSED.

    context must implement:
        get_business_lifecycle_state() → str
    """

    rule_id = "LIFE-001"
    version = "1.0.0"
    domain = "lifecycle"
    severity = Severity.BLOCK
    applies_to = [
        "inventory.stock.move.request",
        "inventory.stock.sell.request",
        "cash.session.open.request",
        "cash.session.close.request",
        "retail.sale.complete.request",
        "retail.sale.apply_discount.request",
        "retail.cart.apply_promotion.request",
    ]

    def evaluate(
        self, command: Any, context: Any, projected_state: dict
    ) -> RuleResult:
        lifecycle = context.get_business_lifecycle_state()

        if lifecycle == "CLOSED":
            return self.fail(
                message=(
                    "Business is CLOSED. No modifications permitted."
                ),
                metadata={"lifecycle_state": lifecycle},
            )

        return self.pass_rule(
            message=f"Business lifecycle '{lifecycle}' allows operations."
        )


# ══════════════════════════════════════════════════════════════
# COMP-001: Missing VAT validation for B2B zero-rating (ESCALATE)
# ══════════════════════════════════════════════════════════════

class MissingVATEscalate(BaseRule):
    """
    ESCALATE if B2B transaction claims zero-rate VAT but
    no VAT registration number is provided.

    command.payload must contain:
        vat_rate: float (0.0 for zero-rated)
        customer_type: str ('B2B' or 'B2C')
        customer_vat_number: str (may be empty)
    """

    rule_id = "COMP-001"
    version = "1.0.0"
    domain = "compliance"
    severity = Severity.ESCALATE
    applies_to = [
        "retail.sale.complete.request",
    ]

    def evaluate(
        self, command: Any, context: Any, projected_state: dict
    ) -> RuleResult:
        vat_rate = command.payload.get("vat_rate")
        customer_type = command.payload.get("customer_type", "B2C")
        vat_number = command.payload.get("customer_vat_number", "")

        if customer_type != "B2B" or vat_rate != 0.0:
            return self.pass_rule(
                message="Not a B2B zero-rated transaction — rule N/A."
            )

        if not vat_number or not vat_number.strip():
            return self.fail(
                message=(
                    "B2B zero-rated VAT claimed but no customer VAT "
                    "registration number provided. Requires review."
                ),
                metadata={
                    "vat_rate": vat_rate,
                    "customer_type": customer_type,
                },
            )

        return self.pass_rule(
            message=f"B2B zero-rate VAT validated with number: {vat_number}."
        )
