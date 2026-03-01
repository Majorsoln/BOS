"""
BOS Credit Wallet Engine — Service Layer
========================================
Ledger-based wallet with FEFO (First Expiring, First Out) bucket consumption.
Each credit is stored as a bucket with source, remaining amount, and expiry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.commands.rejection import RejectionReason

from engines.wallet.events import (
    CREDIT_POLICY_CONFIGURED_V1,
    CREDIT_ISSUED_V1,
    CREDIT_SPENT_V1,
    CREDIT_REVERSED_V1,
    CREDIT_EXPIRED_V1,
    CREDIT_ADJUSTED_V1,
    CREDIT_FROZEN_V1,
    CREDIT_UNFROZEN_V1,
    COMMAND_TO_EVENT_TYPE,
    PAYLOAD_BUILDERS,
)


# ── Data Records ──────────────────────────────────────────────

@dataclass(frozen=True)
class CreditPolicy:
    customer_credit_limit: int
    max_outstanding_credit: int
    max_open_buckets: int
    allow_negative_balance: bool
    approval_required_above: int
    max_apply_percent_per_invoice: int
    pin_otp_threshold: int
    expiry_mode: str
    expiry_days: int
    eligible_categories: tuple


@dataclass
class CreditBucket:
    """Mutable bucket tracking remaining credit."""
    bucket_id: str
    source: str
    original_amount: int
    remaining_amount: int
    expiry_date: Optional[str]
    reference_id: Optional[str]
    issued_at: str


# ── Projection Store ──────────────────────────────────────────

class WalletProjectionStore:
    """In-memory projection of credit wallet per business customer.

    Implements FEFO: First Expiring, First Out for credit consumption.
    """

    def __init__(self):
        self._events: List[dict] = []
        self._policies: Dict[str, CreditPolicy] = {}  # cid → policy
        self._buckets: Dict[str, Dict[str, CreditBucket]] = {}  # cid → {bucket_id → bucket}
        self._total_issued: Dict[str, int] = {}
        self._total_spent: Dict[str, int] = {}
        self._frozen: Dict[str, bool] = {}  # cid → is_frozen

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type == CREDIT_POLICY_CONFIGURED_V1:
            cid = payload["business_customer_id"]
            self._policies[cid] = CreditPolicy(
                customer_credit_limit=payload["customer_credit_limit"],
                max_outstanding_credit=payload.get("max_outstanding_credit", 0),
                max_open_buckets=payload.get("max_open_buckets", 0),
                allow_negative_balance=payload.get("allow_negative_balance", False),
                approval_required_above=payload.get("approval_required_above", 0),
                max_apply_percent_per_invoice=payload.get("max_apply_percent_per_invoice", 100),
                pin_otp_threshold=payload.get("pin_otp_threshold", 0),
                expiry_mode=payload.get("expiry_mode", "NO_EXPIRY"),
                expiry_days=payload.get("expiry_days", 0),
                eligible_categories=tuple(payload.get("eligible_categories", [])),
            )

        elif event_type == CREDIT_ISSUED_V1:
            cid = payload["business_customer_id"]
            bid = payload["bucket_id"]
            amount = payload["amount"]
            if cid not in self._buckets:
                self._buckets[cid] = {}
            self._buckets[cid][bid] = CreditBucket(
                bucket_id=bid,
                source=payload["source"],
                original_amount=amount,
                remaining_amount=amount,
                expiry_date=payload.get("expiry_date"),
                reference_id=payload.get("reference_id"),
                issued_at=payload.get("issued_at", ""),
            )
            self._total_issued[cid] = self._total_issued.get(cid, 0) + amount

        elif event_type == CREDIT_SPENT_V1:
            cid = payload["business_customer_id"]
            amount = payload["amount"]
            allocations = payload.get("bucket_allocations", [])
            for alloc in allocations:
                bid = alloc["bucket_id"]
                alloc_amount = alloc["amount"]
                bucket = self._buckets.get(cid, {}).get(bid)
                if bucket:
                    bucket.remaining_amount = max(0, bucket.remaining_amount - alloc_amount)
            self._total_spent[cid] = self._total_spent.get(cid, 0) + amount

        elif event_type == CREDIT_REVERSED_V1:
            cid = payload["business_customer_id"]
            bid = payload["bucket_id"]
            amount = payload["amount"]
            bucket = self._buckets.get(cid, {}).get(bid)
            if bucket:
                bucket.remaining_amount += amount
            else:
                # Create new bucket for the reversed amount
                if cid not in self._buckets:
                    self._buckets[cid] = {}
                self._buckets[cid][bid] = CreditBucket(
                    bucket_id=bid,
                    source="REFUND_REVERSAL",
                    original_amount=amount,
                    remaining_amount=amount,
                    expiry_date=None,
                    reference_id=payload.get("original_sale_id"),
                    issued_at=payload.get("reversed_at", ""),
                )
            self._total_spent[cid] = max(0, self._total_spent.get(cid, 0) - amount)

        elif event_type == CREDIT_EXPIRED_V1:
            cid = payload["business_customer_id"]
            bid = payload["bucket_id"]
            bucket = self._buckets.get(cid, {}).get(bid)
            if bucket:
                bucket.remaining_amount = 0

        elif event_type == CREDIT_ADJUSTED_V1:
            cid = payload["business_customer_id"]
            amount = payload["amount"]
            bid = payload.get("bucket_id")
            if payload["adjustment_type"] == "CREDIT" and bid:
                bucket = self._buckets.get(cid, {}).get(bid)
                if bucket:
                    bucket.remaining_amount += amount
            elif payload["adjustment_type"] == "DEBIT" and bid:
                bucket = self._buckets.get(cid, {}).get(bid)
                if bucket:
                    bucket.remaining_amount = max(0, bucket.remaining_amount - amount)

        elif event_type == CREDIT_FROZEN_V1:
            cid = payload["business_customer_id"]
            self._frozen[cid] = True

        elif event_type == CREDIT_UNFROZEN_V1:
            cid = payload["business_customer_id"]
            self._frozen[cid] = False

    # ── Queries ───────────────────────────────────────────────

    def get_balance(self, business_customer_id: str) -> int:
        """Total remaining credit across all active buckets."""
        buckets = self._buckets.get(business_customer_id, {})
        return sum(b.remaining_amount for b in buckets.values())

    def get_policy(self, business_customer_id: str) -> Optional[CreditPolicy]:
        return self._policies.get(business_customer_id)

    def is_frozen(self, business_customer_id: str) -> bool:
        return self._frozen.get(business_customer_id, False)

    def get_active_buckets(self, business_customer_id: str) -> List[CreditBucket]:
        """Return buckets with remaining > 0, sorted by FEFO (expiry first, then issued_at)."""
        buckets = self._buckets.get(business_customer_id, {})
        active = [b for b in buckets.values() if b.remaining_amount > 0]
        # FEFO: buckets with expiry come first (sorted by expiry_date), then no-expiry
        def fefo_key(b):
            if b.expiry_date:
                return (0, b.expiry_date, b.issued_at)
            return (1, "", b.issued_at)
        return sorted(active, key=fefo_key)

    def allocate_fefo(self, business_customer_id: str, amount: int) -> List[dict]:
        """Allocate credit from buckets using FEFO. Returns allocation list."""
        buckets = self.get_active_buckets(business_customer_id)
        allocations = []
        remaining = amount
        for bucket in buckets:
            if remaining <= 0:
                break
            take = min(remaining, bucket.remaining_amount)
            allocations.append({"bucket_id": bucket.bucket_id, "amount": take})
            remaining -= take
        return allocations

    def get_total_issued(self, business_customer_id: str) -> int:
        return self._total_issued.get(business_customer_id, 0)

    def get_total_spent(self, business_customer_id: str) -> int:
        return self._total_spent.get(business_customer_id, 0)

    def get_credit_limit(self, business_customer_id: str) -> int:
        policy = self._policies.get(business_customer_id)
        return policy.customer_credit_limit if policy else 0

    def get_available_credit(self, business_customer_id: str) -> int:
        """Available = min(balance, remaining credit limit usage)."""
        balance = self.get_balance(business_customer_id)
        return balance

    @property
    def event_count(self) -> int:
        return len(self._events)

    def truncate(self):
        self._events.clear()
        self._policies.clear()
        self._buckets.clear()
        self._total_issued.clear()
        self._total_spent.clear()
        self._frozen.clear()


# ── Service ───────────────────────────────────────────────────

class WalletService:
    """Credit wallet engine service. All mutations produce events."""

    def __init__(
        self,
        *,
        event_factory,
        persist_event,
        event_type_registry,
        projection_store: WalletProjectionStore,
        feature_flag_evaluator=None,
    ):
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection = projection_store
        self._feature_flags = feature_flag_evaluator

    def _execute_command(self, command) -> dict:
        event_type = COMMAND_TO_EVENT_TYPE.get(command.command_type)
        if event_type is None:
            return {"rejected": RejectionReason(
                code="UNKNOWN_COMMAND",
                message=f"Unknown command: {command.command_type}",
                policy_name="_execute_command",
            )}

        builder = PAYLOAD_BUILDERS.get(event_type)
        if builder is None:
            return {"rejected": RejectionReason(
                code="NO_PAYLOAD_BUILDER",
                message=f"No payload builder for: {event_type}",
                policy_name="_execute_command",
            )}

        payload = builder(command)
        event_data = self._event_factory.create(
            event_type, payload, command.business_id,
            getattr(command, "branch_id", None),
        )
        self._persist_event(event_data)
        self._projection.apply(event_type, payload)
        return {"event_type": event_type, "payload": payload}
