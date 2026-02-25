"""
BOS Credit Wallet Engine — Commands
====================================
Ledger-based credit wallet with FEFO bucket consumption and credit policies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

SCOPE_BUSINESS_ALLOWED = "BUSINESS_SCOPE"
ACTOR_REQUIRED = "ACTOR_REQUIRED"


@dataclass(frozen=True)
class ConfigureCreditPolicyRequest:
    """Configure credit policy for a customer within a business."""
    business_id: uuid.UUID
    business_customer_id: str
    customer_credit_limit: int
    actor_id: str
    issued_at: datetime
    max_outstanding_credit: int = 0
    max_open_buckets: int = 0
    allow_negative_balance: bool = False
    approval_required_above: int = 0
    max_apply_percent_per_invoice: int = 100
    pin_otp_threshold: int = 0
    expiry_mode: str = "NO_EXPIRY"
    expiry_days: int = 0
    eligible_categories: Tuple[str, ...] = ()
    source_engine: str = "wallet"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if self.customer_credit_limit < 0:
            raise ValueError("customer_credit_limit must be >= 0.")
        from engines.wallet.events import VALID_WALLET_EXPIRY_MODES
        if self.expiry_mode not in VALID_WALLET_EXPIRY_MODES:
            raise ValueError(f"Invalid expiry_mode: {self.expiry_mode}")

    def to_command(self) -> dict:
        return {
            "command_type": "wallet.policy.configure.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "customer_credit_limit": self.customer_credit_limit,
                "max_outstanding_credit": self.max_outstanding_credit,
                "max_open_buckets": self.max_open_buckets,
                "allow_negative_balance": self.allow_negative_balance,
                "approval_required_above": self.approval_required_above,
                "max_apply_percent_per_invoice": self.max_apply_percent_per_invoice,
                "pin_otp_threshold": self.pin_otp_threshold,
                "expiry_mode": self.expiry_mode,
                "expiry_days": self.expiry_days,
                "eligible_categories": list(self.eligible_categories),
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class IssueCreditRequest:
    """Issue credit to a customer's wallet (from credit note, refund, rebate, etc.)."""
    business_id: uuid.UUID
    business_customer_id: str
    bucket_id: str
    amount: int
    source: str  # CREDIT_NOTE | REFUND | REBATE | MANUAL_ISSUE | REFUND_REVERSAL
    actor_id: str
    issued_at: datetime
    reference_id: Optional[str] = None
    expiry_date: Optional[str] = None
    source_engine: str = "wallet"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if not self.bucket_id:
            raise ValueError("bucket_id must be non-empty.")
        if self.amount <= 0:
            raise ValueError("amount must be > 0.")
        from engines.wallet.events import VALID_CREDIT_SOURCES
        if self.source not in VALID_CREDIT_SOURCES:
            raise ValueError(f"Invalid source: {self.source}")

    def to_command(self) -> dict:
        return {
            "command_type": "wallet.credit.issue.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "bucket_id": self.bucket_id,
                "amount": self.amount,
                "source": self.source,
                "reference_id": self.reference_id,
                "expiry_date": self.expiry_date,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class SpendCreditRequest:
    """Spend credit from wallet during checkout (FEFO allocation)."""
    business_id: uuid.UUID
    business_customer_id: str
    amount: int
    actor_id: str
    issued_at: datetime
    sale_id: Optional[str] = None
    bucket_allocations: Tuple[dict, ...] = ()  # [{"bucket_id": ..., "amount": ...}]
    source_engine: str = "wallet"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if self.amount <= 0:
            raise ValueError("amount must be > 0.")

    def to_command(self) -> dict:
        return {
            "command_type": "wallet.credit.spend.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "amount": self.amount,
                "sale_id": self.sale_id,
                "bucket_allocations": [dict(a) for a in self.bucket_allocations],
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class ReverseCreditRequest:
    """Reverse credit back to wallet after refund of order that used credit."""
    business_id: uuid.UUID
    business_customer_id: str
    bucket_id: str
    amount: int
    actor_id: str
    issued_at: datetime
    original_sale_id: Optional[str] = None
    reason: str = "REFUND_REVERSAL"
    source_engine: str = "wallet"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if not self.bucket_id:
            raise ValueError("bucket_id must be non-empty.")
        if self.amount <= 0:
            raise ValueError("amount must be > 0.")

    def to_command(self) -> dict:
        return {
            "command_type": "wallet.credit.reverse.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "bucket_id": self.bucket_id,
                "amount": self.amount,
                "original_sale_id": self.original_sale_id,
                "reason": self.reason,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class ExpireCreditRequest:
    """Expire a credit bucket (system-triggered)."""
    business_id: uuid.UUID
    business_customer_id: str
    bucket_id: str
    amount: int
    actor_id: str
    issued_at: datetime
    source_engine: str = "wallet"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if not self.bucket_id:
            raise ValueError("bucket_id must be non-empty.")
        if self.amount <= 0:
            raise ValueError("amount must be > 0.")

    def to_command(self) -> dict:
        return {
            "command_type": "wallet.credit.expire.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "bucket_id": self.bucket_id,
                "amount": self.amount,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class FreezeCreditRequest:
    """Customer freezes credit usage."""
    business_id: uuid.UUID
    business_customer_id: str
    actor_id: str
    issued_at: datetime
    reason: str = "CUSTOMER_REQUEST"
    source_engine: str = "wallet"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "wallet.credit.freeze.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "reason": self.reason,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class UnfreezeCreditRequest:
    """Customer unfreezes credit usage."""
    business_id: uuid.UUID
    business_customer_id: str
    actor_id: str
    issued_at: datetime
    reason: str = "CUSTOMER_REQUEST"
    source_engine: str = "wallet"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "wallet.credit.unfreeze.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "reason": self.reason,
                "issued_at": str(self.issued_at),
            },
        }
