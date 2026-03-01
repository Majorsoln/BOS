"""
BOS Loyalty Engine — Service Layer
==================================
Per-business loyalty program with configurable earn/redeem/expire policies.
Points are calculated on net-of-discount before tax.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.commands.rejection import RejectionReason

from engines.loyalty.events import (
    LOYALTY_PROGRAM_CONFIGURED_V1,
    POINTS_EARNED_V1,
    POINTS_REDEEMED_V1,
    POINTS_EXPIRED_V1,
    POINTS_ADJUSTED_V1,
    POINTS_REVERSED_V1,
    COMMAND_TO_EVENT_TYPE,
    PAYLOAD_BUILDERS,
)


# ── Program Policy Record ─────────────────────────────────────

@dataclass(frozen=True)
class LoyaltyProgramPolicy:
    earn_rate_type: str
    earn_rate_value: int
    expiry_mode: str
    expiry_days: int
    min_redeem_points: int
    redeem_step: int
    max_redeem_percent_per_invoice: int
    exclusions: tuple
    channels: tuple
    rounding_rule: str


# ── Projection Store ──────────────────────────────────────────

class LoyaltyProjectionStore:
    """In-memory projection of loyalty points per business customer."""

    def __init__(self):
        self._events: List[dict] = []
        self._balances: Dict[str, int] = {}  # business_customer_id → balance
        self._total_earned: Dict[str, int] = {}
        self._total_redeemed: Dict[str, int] = {}
        self._total_expired: Dict[str, int] = {}
        self._program: Optional[LoyaltyProgramPolicy] = None

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type == LOYALTY_PROGRAM_CONFIGURED_V1:
            self._program = LoyaltyProgramPolicy(
                earn_rate_type=payload["earn_rate_type"],
                earn_rate_value=payload["earn_rate_value"],
                expiry_mode=payload["expiry_mode"],
                expiry_days=payload.get("expiry_days", 0),
                min_redeem_points=payload.get("min_redeem_points", 0),
                redeem_step=payload.get("redeem_step", 1),
                max_redeem_percent_per_invoice=payload.get("max_redeem_percent_per_invoice", 100),
                exclusions=tuple(payload.get("exclusions", [])),
                channels=tuple(payload.get("channels", [])),
                rounding_rule=payload.get("rounding_rule", "FLOOR"),
            )

        elif event_type == POINTS_EARNED_V1:
            cid = payload["business_customer_id"]
            pts = payload["points"]
            self._balances[cid] = self._balances.get(cid, 0) + pts
            self._total_earned[cid] = self._total_earned.get(cid, 0) + pts

        elif event_type == POINTS_REDEEMED_V1:
            cid = payload["business_customer_id"]
            pts = payload["points"]
            self._balances[cid] = self._balances.get(cid, 0) - pts
            self._total_redeemed[cid] = self._total_redeemed.get(cid, 0) + pts

        elif event_type == POINTS_EXPIRED_V1:
            cid = payload["business_customer_id"]
            pts = payload["points"]
            self._balances[cid] = self._balances.get(cid, 0) - pts
            self._total_expired[cid] = self._total_expired.get(cid, 0) + pts

        elif event_type == POINTS_ADJUSTED_V1:
            cid = payload["business_customer_id"]
            pts = payload["points"]
            if payload["adjustment_type"] == "CREDIT":
                self._balances[cid] = self._balances.get(cid, 0) + pts
            else:
                self._balances[cid] = self._balances.get(cid, 0) - pts

        elif event_type == POINTS_REVERSED_V1:
            cid = payload["business_customer_id"]
            pts = payload["points"]
            self._balances[cid] = self._balances.get(cid, 0) - pts

    def get_balance(self, business_customer_id: str) -> int:
        return self._balances.get(business_customer_id, 0)

    def get_total_earned(self, business_customer_id: str) -> int:
        return self._total_earned.get(business_customer_id, 0)

    def get_total_redeemed(self, business_customer_id: str) -> int:
        return self._total_redeemed.get(business_customer_id, 0)

    def get_total_expired(self, business_customer_id: str) -> int:
        return self._total_expired.get(business_customer_id, 0)

    @property
    def program(self) -> Optional[LoyaltyProgramPolicy]:
        return self._program

    def calculate_earn_points(self, net_amount: int) -> int:
        """Calculate how many points to award for a given net amount (before tax)."""
        if self._program is None:
            return 0
        p = self._program
        if p.earn_rate_type == "FIXED_PER_AMOUNT":
            raw = net_amount / p.earn_rate_value if p.earn_rate_value > 0 else 0
        elif p.earn_rate_type == "PERCENTAGE":
            raw = net_amount * p.earn_rate_value / 10000  # basis points
        else:
            return 0  # PER_ITEM handled at item level

        if p.rounding_rule == "FLOOR":
            return int(math.floor(raw))
        elif p.rounding_rule == "CEIL":
            return int(math.ceil(raw))
        else:
            return int(round(raw))

    @property
    def event_count(self) -> int:
        return len(self._events)

    def truncate(self):
        self._events.clear()
        self._balances.clear()
        self._total_earned.clear()
        self._total_redeemed.clear()
        self._total_expired.clear()
        self._program = None


# ── Service ───────────────────────────────────────────────────

class LoyaltyService:
    """Loyalty engine service. All point mutations produce events."""

    def __init__(
        self,
        *,
        event_factory,
        persist_event,
        event_type_registry,
        projection_store: LoyaltyProjectionStore,
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
