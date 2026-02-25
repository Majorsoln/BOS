"""
BOS Credit Wallet Engine — Event Types
=======================================
Per-business, ledger-based credit wallet with FEFO bucket consumption.
"""

# ── Event Types ───────────────────────────────────────────────

CREDIT_POLICY_CONFIGURED_V1 = "wallet.policy.configured.v1"
CREDIT_ISSUED_V1 = "wallet.credit.issued.v1"
CREDIT_SPENT_V1 = "wallet.credit.spent.v1"
CREDIT_REVERSED_V1 = "wallet.credit.reversed.v1"
CREDIT_EXPIRED_V1 = "wallet.credit.expired.v1"
CREDIT_ADJUSTED_V1 = "wallet.credit.adjusted.v1"
CREDIT_FROZEN_V1 = "wallet.credit.frozen.v1"
CREDIT_UNFROZEN_V1 = "wallet.credit.unfrozen.v1"

ALL_EVENT_TYPES = (
    CREDIT_POLICY_CONFIGURED_V1,
    CREDIT_ISSUED_V1,
    CREDIT_SPENT_V1,
    CREDIT_REVERSED_V1,
    CREDIT_EXPIRED_V1,
    CREDIT_ADJUSTED_V1,
    CREDIT_FROZEN_V1,
    CREDIT_UNFROZEN_V1,
)

# ── Credit Sources ────────────────────────────────────────────

SOURCE_CREDIT_NOTE = "CREDIT_NOTE"
SOURCE_REFUND = "REFUND"
SOURCE_REBATE = "REBATE"
SOURCE_MANUAL_ISSUE = "MANUAL_ISSUE"
SOURCE_REFUND_REVERSAL = "REFUND_REVERSAL"

VALID_CREDIT_SOURCES = frozenset({
    SOURCE_CREDIT_NOTE, SOURCE_REFUND, SOURCE_REBATE,
    SOURCE_MANUAL_ISSUE, SOURCE_REFUND_REVERSAL,
})

# ── Expiry Modes ──────────────────────────────────────────────

WALLET_EXPIRY_NONE = "NO_EXPIRY"
WALLET_EXPIRY_AFTER_DAYS = "EXPIRE_AFTER_DAYS"

VALID_WALLET_EXPIRY_MODES = frozenset({
    WALLET_EXPIRY_NONE, WALLET_EXPIRY_AFTER_DAYS,
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


def _policy_configured(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "customer_credit_limit": p["customer_credit_limit"],
        "max_outstanding_credit": p.get("max_outstanding_credit", 0),
        "max_open_buckets": p.get("max_open_buckets", 0),
        "allow_negative_balance": p.get("allow_negative_balance", False),
        "approval_required_above": p.get("approval_required_above", 0),
        "max_apply_percent_per_invoice": p.get("max_apply_percent_per_invoice", 100),
        "pin_otp_threshold": p.get("pin_otp_threshold", 0),
        "expiry_mode": p.get("expiry_mode", "NO_EXPIRY"),
        "expiry_days": p.get("expiry_days", 0),
        "eligible_categories": p.get("eligible_categories", []),
        "configured_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _credit_issued(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "bucket_id": p["bucket_id"],
        "amount": p["amount"],
        "source": p["source"],
        "reference_id": p.get("reference_id"),
        "expiry_date": p.get("expiry_date"),
        "issued_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _credit_spent(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "amount": p["amount"],
        "sale_id": p.get("sale_id"),
        "bucket_allocations": p.get("bucket_allocations", []),
        "spent_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _credit_reversed(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "bucket_id": p["bucket_id"],
        "amount": p["amount"],
        "original_sale_id": p.get("original_sale_id"),
        "reason": p.get("reason", "REFUND_REVERSAL"),
        "reversed_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _credit_expired(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "bucket_id": p["bucket_id"],
        "amount": p["amount"],
        "expired_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _credit_adjusted(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "bucket_id": p.get("bucket_id"),
        "amount": p["amount"],
        "adjustment_type": p["adjustment_type"],  # CREDIT / DEBIT
        "reason": p.get("reason", ""),
        "adjusted_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _credit_frozen(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "reason": p.get("reason", "CUSTOMER_REQUEST"),
        "frozen_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _credit_unfrozen(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "reason": p.get("reason", "CUSTOMER_REQUEST"),
        "unfrozen_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


PAYLOAD_BUILDERS = {
    CREDIT_POLICY_CONFIGURED_V1: _policy_configured,
    CREDIT_ISSUED_V1: _credit_issued,
    CREDIT_SPENT_V1: _credit_spent,
    CREDIT_REVERSED_V1: _credit_reversed,
    CREDIT_EXPIRED_V1: _credit_expired,
    CREDIT_ADJUSTED_V1: _credit_adjusted,
    CREDIT_FROZEN_V1: _credit_frozen,
    CREDIT_UNFROZEN_V1: _credit_unfrozen,
}

COMMAND_TO_EVENT_TYPE = {
    "wallet.policy.configure.request": CREDIT_POLICY_CONFIGURED_V1,
    "wallet.credit.issue.request": CREDIT_ISSUED_V1,
    "wallet.credit.spend.request": CREDIT_SPENT_V1,
    "wallet.credit.reverse.request": CREDIT_REVERSED_V1,
    "wallet.credit.expire.request": CREDIT_EXPIRED_V1,
    "wallet.credit.adjust.request": CREDIT_ADJUSTED_V1,
    "wallet.credit.freeze.request": CREDIT_FROZEN_V1,
    "wallet.credit.unfreeze.request": CREDIT_UNFROZEN_V1,
}


def register_wallet_event_types(registry):
    for event_type, builder in PAYLOAD_BUILDERS.items():
        registry.register(event_type, builder)


def resolve_wallet_event_type(name: str):
    return PAYLOAD_BUILDERS.get(name)
