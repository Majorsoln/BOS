"""
BOS Loyalty Engine — Event Types
================================
Per-business loyalty points. Customer-controlled redemption.
"""

# ── Event Types ───────────────────────────────────────────────

LOYALTY_PROGRAM_CONFIGURED_V1 = "loyalty.program.configured.v1"
POINTS_EARNED_V1 = "loyalty.points.earned.v1"
POINTS_REDEEMED_V1 = "loyalty.points.redeemed.v1"
POINTS_EXPIRED_V1 = "loyalty.points.expired.v1"
POINTS_ADJUSTED_V1 = "loyalty.points.adjusted.v1"
POINTS_REVERSED_V1 = "loyalty.points.reversed.v1"

ALL_EVENT_TYPES = (
    LOYALTY_PROGRAM_CONFIGURED_V1,
    POINTS_EARNED_V1,
    POINTS_REDEEMED_V1,
    POINTS_EXPIRED_V1,
    POINTS_ADJUSTED_V1,
    POINTS_REVERSED_V1,
)

# ── Earn Rate Types ───────────────────────────────────────────

EARN_FIXED_PER_AMOUNT = "FIXED_PER_AMOUNT"     # e.g. 1 point per TZS 1,000
EARN_PERCENTAGE = "PERCENTAGE"                   # e.g. 1% of spending
EARN_PER_ITEM = "PER_ITEM"                       # e.g. item X = 12 points

VALID_EARN_RATE_TYPES = frozenset({
    EARN_FIXED_PER_AMOUNT, EARN_PERCENTAGE, EARN_PER_ITEM,
})

# ── Expiry Modes ──────────────────────────────────────────────

EXPIRY_NONE = "NO_EXPIRY"
EXPIRY_AFTER_DAYS = "EXPIRE_AFTER_DAYS"
EXPIRY_END_OF_PERIOD = "EXPIRE_END_OF_PERIOD"

VALID_EXPIRY_MODES = frozenset({
    EXPIRY_NONE, EXPIRY_AFTER_DAYS, EXPIRY_END_OF_PERIOD,
})


# ── Payload Builders ──────────────────────────────────────────

def _base_fields(cmd):
    return {
        "business_id": str(cmd.business_id),
        "branch_id": str(cmd.branch_id) if getattr(cmd, "branch_id", None) else None,
        "actor_id": getattr(cmd, "actor_id", None),
        "actor_type": getattr(cmd, "actor_type", None),
        "correlation_id": str(cmd.correlation_id) if hasattr(cmd, "correlation_id") else None,
        "command_id": str(cmd.command_id) if hasattr(cmd, "command_id") else None,
    }


def _program_configured(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "earn_rate_type": p["earn_rate_type"],
        "earn_rate_value": p["earn_rate_value"],
        "expiry_mode": p["expiry_mode"],
        "expiry_days": p.get("expiry_days", 0),
        "min_redeem_points": p.get("min_redeem_points", 0),
        "redeem_step": p.get("redeem_step", 1),
        "max_redeem_percent_per_invoice": p.get("max_redeem_percent_per_invoice", 100),
        "exclusions": p.get("exclusions", []),
        "channels": p.get("channels", []),
        "rounding_rule": p.get("rounding_rule", "FLOOR"),
        "configured_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _points_earned(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "points": p["points"],
        "source_sale_id": p.get("source_sale_id"),
        "net_amount": p.get("net_amount", 0),
        "earned_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _points_redeemed(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "points": p["points"],
        "sale_id": p.get("sale_id"),
        "discount_value": p.get("discount_value", 0),
        "redeemed_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _points_expired(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "points": p["points"],
        "reason": p.get("reason", "EXPIRY"),
        "expired_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _points_adjusted(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "points": p["points"],
        "adjustment_type": p["adjustment_type"],  # CREDIT / DEBIT
        "reason": p.get("reason", ""),
        "adjusted_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _points_reversed(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "points": p["points"],
        "original_sale_id": p.get("original_sale_id"),
        "reason": p.get("reason", "REFUND_REVERSAL"),
        "reversed_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


PAYLOAD_BUILDERS = {
    LOYALTY_PROGRAM_CONFIGURED_V1: _program_configured,
    POINTS_EARNED_V1: _points_earned,
    POINTS_REDEEMED_V1: _points_redeemed,
    POINTS_EXPIRED_V1: _points_expired,
    POINTS_ADJUSTED_V1: _points_adjusted,
    POINTS_REVERSED_V1: _points_reversed,
}

COMMAND_TO_EVENT_TYPE = {
    "loyalty.program.configure.request": LOYALTY_PROGRAM_CONFIGURED_V1,
    "loyalty.points.earn.request": POINTS_EARNED_V1,
    "loyalty.points.redeem.request": POINTS_REDEEMED_V1,
    "loyalty.points.expire.request": POINTS_EXPIRED_V1,
    "loyalty.points.adjust.request": POINTS_ADJUSTED_V1,
    "loyalty.points.reverse.request": POINTS_REVERSED_V1,
}


def register_loyalty_event_types(registry):
    for event_type, builder in PAYLOAD_BUILDERS.items():
        registry.register(event_type, builder)


def resolve_loyalty_event_type(name: str):
    return PAYLOAD_BUILDERS.get(name)
