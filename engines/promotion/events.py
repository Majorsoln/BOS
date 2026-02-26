"""
BOS Promotion Engine — Event Types and Payload Builders
=========================================================
Engine: Promotion (Campaigns, Discounts, Loyalty)

v1: Simple campaigns + coupons (preserved, additive only)
v2: Composable PromotionPrograms with rule sets, timing, tax_mode, settlement
"""

from __future__ import annotations

from core.commands.base import Command

# ── v1 Events (preserved, unchanged) ─────────────────────────
PROMOTION_CAMPAIGN_CREATED_V1 = "promotion.campaign.created.v1"
PROMOTION_CAMPAIGN_ACTIVATED_V1 = "promotion.campaign.activated.v1"
PROMOTION_CAMPAIGN_DEACTIVATED_V1 = "promotion.campaign.deactivated.v1"
PROMOTION_COUPON_ISSUED_V1 = "promotion.coupon.issued.v1"
PROMOTION_COUPON_REDEEMED_V1 = "promotion.coupon.redeemed.v1"

# ── v2 Events (composable programs, additive) ─────────────────
PROMOTION_PROGRAM_CREATED_V2 = "promotion.program.created.v2"
PROMOTION_PROGRAM_ACTIVATED_V2 = "promotion.program.activated.v2"
PROMOTION_PROGRAM_DEACTIVATED_V2 = "promotion.program.deactivated.v2"
PROMOTION_RULE_ADDED_V1 = "promotion.rule.added.v1"
PROMOTION_EVALUATED_V1 = "promotion.evaluated.v1"
PROMOTION_APPLIED_V1 = "promotion.applied.v1"
PROMOTION_CREDIT_NOTE_ISSUED_V1 = "promotion.credit_note.issued.v1"
PROMOTION_REBATE_SETTLED_V1 = "promotion.rebate.settled.v1"

# ── Timing Modes ──────────────────────────────────────────────
TIMING_AT_SALE = "AT_SALE"
TIMING_AT_PAYMENT = "AT_PAYMENT"
TIMING_POST_PERIOD = "POST_PERIOD"
VALID_TIMING_MODES = frozenset({TIMING_AT_SALE, TIMING_AT_PAYMENT, TIMING_POST_PERIOD})

# ── Tax Handling Modes ────────────────────────────────────────
TAX_MODE_REDUCE_BASE_NOW = "REDUCE_TAX_BASE_NOW"
TAX_MODE_FULL_THEN_ADJUST = "TAX_ON_FULL_THEN_ADJUST"
TAX_MODE_DEPENDS_ON_COUPON = "TAXABLE_BASE_DEPENDS_ON_COUPON_TYPE"
VALID_TAX_MODES = frozenset({
    TAX_MODE_REDUCE_BASE_NOW, TAX_MODE_FULL_THEN_ADJUST, TAX_MODE_DEPENDS_ON_COUPON,
})

# ── Settlement Methods ────────────────────────────────────────
SETTLEMENT_INVOICE_LINE = "INVOICE_LINE_DISCOUNT"
SETTLEMENT_CREDIT_NOTE = "CREDIT_NOTE"
SETTLEMENT_REFUND = "REFUND"
SETTLEMENT_WALLET = "WALLET"
VALID_SETTLEMENT_METHODS = frozenset({
    SETTLEMENT_INVOICE_LINE, SETTLEMENT_CREDIT_NOTE,
    SETTLEMENT_REFUND, SETTLEMENT_WALLET,
})

# ── Stackability ──────────────────────────────────────────────
STACK_STACKABLE = "STACKABLE"
STACK_EXCLUSIVE = "EXCLUSIVE"
STACK_WITH_TAGS = "STACK_WITH_TAGS"
VALID_STACKABILITY = frozenset({STACK_STACKABLE, STACK_EXCLUSIVE, STACK_WITH_TAGS})

# ── Rule Types ────────────────────────────────────────────────
RULE_PERCENTAGE = "PERCENTAGE"
RULE_FIXED_AMOUNT = "FIXED_AMOUNT"
RULE_BUY_X_GET_Y = "BUY_X_GET_Y"
RULE_FIRST_N_CUSTOMERS = "FIRST_N_CUSTOMERS"
RULE_TIME_WINDOW = "TIME_WINDOW"
RULE_VOLUME_THRESHOLD = "VOLUME_THRESHOLD"
RULE_BUNDLE = "BUNDLE"
VALID_RULE_TYPES = frozenset({
    RULE_PERCENTAGE, RULE_FIXED_AMOUNT, RULE_BUY_X_GET_Y,
    RULE_FIRST_N_CUSTOMERS, RULE_TIME_WINDOW, RULE_VOLUME_THRESHOLD, RULE_BUNDLE,
})

PROMOTION_EVENT_TYPES = (
    PROMOTION_CAMPAIGN_CREATED_V1,
    PROMOTION_CAMPAIGN_ACTIVATED_V1,
    PROMOTION_CAMPAIGN_DEACTIVATED_V1,
    PROMOTION_COUPON_ISSUED_V1,
    PROMOTION_COUPON_REDEEMED_V1,
    PROMOTION_PROGRAM_CREATED_V2,
    PROMOTION_PROGRAM_ACTIVATED_V2,
    PROMOTION_PROGRAM_DEACTIVATED_V2,
    PROMOTION_RULE_ADDED_V1,
    PROMOTION_EVALUATED_V1,
    PROMOTION_APPLIED_V1,
    PROMOTION_CREDIT_NOTE_ISSUED_V1,
    PROMOTION_REBATE_SETTLED_V1,
)

COMMAND_TO_EVENT_TYPE = {
    # v1
    "promotion.campaign.create.request": PROMOTION_CAMPAIGN_CREATED_V1,
    "promotion.campaign.activate.request": PROMOTION_CAMPAIGN_ACTIVATED_V1,
    "promotion.campaign.deactivate.request": PROMOTION_CAMPAIGN_DEACTIVATED_V1,
    "promotion.coupon.issue.request": PROMOTION_COUPON_ISSUED_V1,
    "promotion.coupon.redeem.request": PROMOTION_COUPON_REDEEMED_V1,
    # v2
    "promotion.program.create.request": PROMOTION_PROGRAM_CREATED_V2,
    "promotion.program.activate.request": PROMOTION_PROGRAM_ACTIVATED_V2,
    "promotion.program.deactivate.request": PROMOTION_PROGRAM_DEACTIVATED_V2,
    "promotion.rule.add.request": PROMOTION_RULE_ADDED_V1,
    "promotion.basket.evaluate.request": PROMOTION_EVALUATED_V1,
    "promotion.apply.request": PROMOTION_APPLIED_V1,
    "promotion.credit_note.issue.request": PROMOTION_CREDIT_NOTE_ISSUED_V1,
    "promotion.rebate.settle.request": PROMOTION_REBATE_SETTLED_V1,
}


def resolve_promotion_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_promotion_event_types(event_type_registry) -> None:
    for et in sorted(PROMOTION_EVENT_TYPES):
        event_type_registry.register(et)


def _base_payload(command: Command) -> dict:
    return {
        "business_id": command.business_id, "branch_id": command.branch_id,
        "actor_id": command.actor_id, "actor_type": command.actor_type,
        "correlation_id": command.correlation_id, "command_id": command.command_id,
    }


def build_campaign_created_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "campaign_id": command.payload["campaign_id"],
        "name": command.payload["name"],
        "campaign_type": command.payload["campaign_type"],
        "discount_type": command.payload["discount_type"],
        "discount_value": command.payload["discount_value"],
        "start_date": command.payload["start_date"],
        "end_date": command.payload["end_date"],
        "created_at": command.issued_at,
    })
    return p


def build_campaign_activated_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({"campaign_id": command.payload["campaign_id"], "activated_at": command.issued_at})
    return p


def build_campaign_deactivated_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "campaign_id": command.payload["campaign_id"],
        "reason": command.payload.get("reason", ""),
        "deactivated_at": command.issued_at,
    })
    return p


def build_coupon_issued_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "coupon_id": command.payload["coupon_id"],
        "campaign_id": command.payload["campaign_id"],
        "customer_id": command.payload.get("customer_id"),
        "issued_at": command.issued_at,
    })
    return p


def build_coupon_redeemed_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "coupon_id": command.payload["coupon_id"],
        "sale_id": command.payload["sale_id"],
        "discount_applied": command.payload["discount_applied"],
        "redeemed_at": command.issued_at,
    })
    return p


# ── v2 Payload Builders ───────────────────────────────────────

def build_program_created_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "program_id": command.payload["program_id"],
        "name": command.payload["name"],
        "timing": command.payload["timing"],
        "tax_mode": command.payload["tax_mode"],
        "settlement": command.payload["settlement"],
        "stackability": command.payload["stackability"],
        "stack_tags": command.payload.get("stack_tags", []),
        "budget_ceiling": command.payload.get("budget_ceiling", 0),
        "usage_cap": command.payload.get("usage_cap", 0),
        "customer_cap": command.payload.get("customer_cap", 0),
        "scope": command.payload.get("scope", {}),
        "validity": command.payload.get("validity", {}),
        "created_at": command.issued_at,
    })
    return p


def build_program_activated_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "program_id": command.payload["program_id"],
        "activated_at": command.issued_at,
    })
    return p


def build_program_deactivated_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "program_id": command.payload["program_id"],
        "reason": command.payload.get("reason", ""),
        "deactivated_at": command.issued_at,
    })
    return p


def build_rule_added_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "program_id": command.payload["program_id"],
        "rule_id": command.payload["rule_id"],
        "rule_type": command.payload["rule_type"],
        "rule_params": command.payload.get("rule_params", {}),
        "added_at": command.issued_at,
    })
    return p


def build_evaluated_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "evaluation_id": command.payload["evaluation_id"],
        "sale_id": command.payload.get("sale_id"),
        "business_customer_id": command.payload.get("business_customer_id"),
        "basket_items": command.payload.get("basket_items", []),
        "basket_net_amount": command.payload.get("basket_net_amount", 0),
        "applicable_programs": command.payload.get("applicable_programs", []),
        "evaluated_at": command.issued_at,
    })
    return p


def build_applied_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "application_id": command.payload["application_id"],
        "sale_id": command.payload["sale_id"],
        "program_id": command.payload["program_id"],
        "business_customer_id": command.payload.get("business_customer_id"),
        "discount_amount": command.payload["discount_amount"],
        "adjusted_net_amount": command.payload["adjusted_net_amount"],
        "tax_mode": command.payload["tax_mode"],
        "settlement": command.payload["settlement"],
        "applied_at": command.issued_at,
    })
    return p


def build_credit_note_issued_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "credit_note_id": command.payload["credit_note_id"],
        "original_invoice_id": command.payload["original_invoice_id"],
        "discount_amount": command.payload["discount_amount"],
        "tax_adjustment": command.payload.get("tax_adjustment", 0),
        "business_customer_id": command.payload.get("business_customer_id"),
        "issued_at": command.issued_at,
    })
    return p


def build_rebate_settled_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "rebate_id": command.payload["rebate_id"],
        "program_id": command.payload["program_id"],
        "business_customer_id": command.payload["business_customer_id"],
        "period_start": command.payload["period_start"],
        "period_end": command.payload["period_end"],
        "rebate_amount": command.payload["rebate_amount"],
        "settlement_method": command.payload["settlement_method"],
        "settled_at": command.issued_at,
    })
    return p


# ── v2 resolver helpers ───────────────────────────────────────

V2_PAYLOAD_BUILDERS = {
    "promotion.program.create.request": build_program_created_payload,
    "promotion.program.activate.request": build_program_activated_payload,
    "promotion.program.deactivate.request": build_program_deactivated_payload,
    "promotion.rule.add.request": build_rule_added_payload,
    "promotion.basket.evaluate.request": build_evaluated_payload,
    "promotion.apply.request": build_applied_payload,
    "promotion.credit_note.issue.request": build_credit_note_issued_payload,
    "promotion.rebate.settle.request": build_rebate_settled_payload,
}
