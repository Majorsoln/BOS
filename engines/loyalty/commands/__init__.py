"""
BOS Loyalty Engine — Commands
=============================
Per-business loyalty program configuration and point operations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple

SCOPE_BUSINESS_ALLOWED = "BUSINESS_SCOPE"
ACTOR_REQUIRED = "ACTOR_REQUIRED"


@dataclass(frozen=True)
class ConfigureLoyaltyProgramRequest:
    """Configure or update a business's loyalty program policy."""
    business_id: uuid.UUID
    earn_rate_type: str       # FIXED_PER_AMOUNT | PERCENTAGE | PER_ITEM
    earn_rate_value: int      # e.g. 1 (point per amount unit) or 100 (basis points for %)
    expiry_mode: str          # NO_EXPIRY | EXPIRE_AFTER_DAYS | EXPIRE_END_OF_PERIOD
    actor_id: str
    issued_at: datetime
    expiry_days: int = 0
    min_redeem_points: int = 0
    redeem_step: int = 1
    max_redeem_percent_per_invoice: int = 100
    exclusions: Tuple[str, ...] = ()
    channels: Tuple[str, ...] = ()
    rounding_rule: str = "FLOOR"
    source_engine: str = "loyalty"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        from engines.loyalty.events import VALID_EARN_RATE_TYPES, VALID_EXPIRY_MODES
        if self.earn_rate_type not in VALID_EARN_RATE_TYPES:
            raise ValueError(f"Invalid earn_rate_type: {self.earn_rate_type}")
        if self.expiry_mode not in VALID_EXPIRY_MODES:
            raise ValueError(f"Invalid expiry_mode: {self.expiry_mode}")
        if self.earn_rate_value <= 0:
            raise ValueError("earn_rate_value must be > 0.")
        if self.rounding_rule not in ("FLOOR", "ROUND", "CEIL"):
            raise ValueError(f"Invalid rounding_rule: {self.rounding_rule}")

    def to_command(self) -> dict:
        return {
            "command_type": "loyalty.program.configure.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "earn_rate_type": self.earn_rate_type,
                "earn_rate_value": self.earn_rate_value,
                "expiry_mode": self.expiry_mode,
                "expiry_days": self.expiry_days,
                "min_redeem_points": self.min_redeem_points,
                "redeem_step": self.redeem_step,
                "max_redeem_percent_per_invoice": self.max_redeem_percent_per_invoice,
                "exclusions": list(self.exclusions),
                "channels": list(self.channels),
                "rounding_rule": self.rounding_rule,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class EarnPointsRequest:
    """Award loyalty points to a customer after sale completion."""
    business_id: uuid.UUID
    business_customer_id: str
    points: int
    actor_id: str
    issued_at: datetime
    source_sale_id: Optional[str] = None
    net_amount: int = 0
    source_engine: str = "loyalty"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if self.points <= 0:
            raise ValueError("points must be > 0.")

    def to_command(self) -> dict:
        return {
            "command_type": "loyalty.points.earn.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "points": self.points,
                "source_sale_id": self.source_sale_id,
                "net_amount": self.net_amount,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class RedeemPointsRequest:
    """Redeem loyalty points during sale checkout."""
    business_id: uuid.UUID
    business_customer_id: str
    points: int
    discount_value: int
    actor_id: str
    issued_at: datetime
    sale_id: Optional[str] = None
    source_engine: str = "loyalty"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if self.points <= 0:
            raise ValueError("points must be > 0.")
        if self.discount_value < 0:
            raise ValueError("discount_value must be >= 0.")

    def to_command(self) -> dict:
        return {
            "command_type": "loyalty.points.redeem.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "points": self.points,
                "sale_id": self.sale_id,
                "discount_value": self.discount_value,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class ExpirePointsRequest:
    """Expire points for a customer (system-triggered batch)."""
    business_id: uuid.UUID
    business_customer_id: str
    points: int
    actor_id: str
    issued_at: datetime
    reason: str = "EXPIRY"
    source_engine: str = "loyalty"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if self.points <= 0:
            raise ValueError("points must be > 0.")

    def to_command(self) -> dict:
        return {
            "command_type": "loyalty.points.expire.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "points": self.points,
                "reason": self.reason,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class AdjustPointsRequest:
    """Manual point adjustment (admin)."""
    business_id: uuid.UUID
    business_customer_id: str
    points: int
    adjustment_type: str  # CREDIT | DEBIT
    reason: str
    actor_id: str
    issued_at: datetime
    source_engine: str = "loyalty"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if self.points <= 0:
            raise ValueError("points must be > 0.")
        if self.adjustment_type not in ("CREDIT", "DEBIT"):
            raise ValueError("adjustment_type must be CREDIT or DEBIT.")

    def to_command(self) -> dict:
        return {
            "command_type": "loyalty.points.adjust.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "points": self.points,
                "adjustment_type": self.adjustment_type,
                "reason": self.reason,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class ReversePointsRequest:
    """Reverse points after refund/return."""
    business_id: uuid.UUID
    business_customer_id: str
    points: int
    actor_id: str
    issued_at: datetime
    original_sale_id: Optional[str] = None
    reason: str = "REFUND_REVERSAL"
    source_engine: str = "loyalty"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if self.points <= 0:
            raise ValueError("points must be > 0.")

    def to_command(self) -> dict:
        return {
            "command_type": "loyalty.points.reverse.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "points": self.points,
                "original_sale_id": self.original_sale_id,
                "reason": self.reason,
                "issued_at": str(self.issued_at),
            },
        }
