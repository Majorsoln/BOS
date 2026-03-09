"""
BOS SaaS — Subscription Lifecycle Management
================================================
Event-sourced subscription lifecycle:
TRIAL → ACTIVE → RENEWED / SUSPENDED / CANCELLED / UPGRADED

Each business has at most one subscription at a time.
Subscriptions reference a combo_id (leadership-defined engine combo).

Lifecycle:
  TRIAL     — free trial period (governed by TrialAgreement)
  ACTIVE    — paying customer
  SUSPENDED — payment failed or admin action
  CANCELLED — terminal (churn or voluntary)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION EVENT TYPES
# ══════════════════════════════════════════════════════════════

SUBSCRIPTION_TRIAL_STARTED_V1 = "saas.subscription.trial_started.v1"
SUBSCRIPTION_ACTIVATED_V1 = "saas.subscription.activated.v1"
SUBSCRIPTION_RENEWED_V1 = "saas.subscription.renewed.v1"
SUBSCRIPTION_CANCELLED_V1 = "saas.subscription.cancelled.v1"
SUBSCRIPTION_SUSPENDED_V1 = "saas.subscription.suspended.v1"
SUBSCRIPTION_UPGRADED_V1 = "saas.subscription.upgraded.v1"
SUBSCRIPTION_COMBO_CHANGED_V1 = "saas.subscription.combo_changed.v1"

SUBSCRIPTION_EVENT_TYPES = (
    SUBSCRIPTION_TRIAL_STARTED_V1,
    SUBSCRIPTION_ACTIVATED_V1,
    SUBSCRIPTION_RENEWED_V1,
    SUBSCRIPTION_CANCELLED_V1,
    SUBSCRIPTION_SUSPENDED_V1,
    SUBSCRIPTION_UPGRADED_V1,
    SUBSCRIPTION_COMBO_CHANGED_V1,
)


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION STATUS
# ══════════════════════════════════════════════════════════════

class SubscriptionStatus(Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


_VALID_TRANSITIONS: Dict[SubscriptionStatus, List[SubscriptionStatus]] = {
    SubscriptionStatus.TRIAL: [
        SubscriptionStatus.ACTIVE,      # conversion — user starts paying
        SubscriptionStatus.SUSPENDED,   # admin/system suspension during trial
        SubscriptionStatus.CANCELLED,   # user cancels during trial
    ],
    SubscriptionStatus.ACTIVE: [
        SubscriptionStatus.SUSPENDED,
        SubscriptionStatus.CANCELLED,
    ],
    SubscriptionStatus.SUSPENDED: [
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.CANCELLED,
    ],
    SubscriptionStatus.CANCELLED: [],  # terminal
}


def _can_transition(current: SubscriptionStatus, target: SubscriptionStatus) -> bool:
    return target in _VALID_TRANSITIONS.get(current, [])


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SubscriptionRecord:
    """Immutable subscription state."""
    subscription_id: uuid.UUID
    business_id: uuid.UUID
    plan_id: uuid.UUID                      # legacy compat — same as combo_id
    status: SubscriptionStatus
    activated_at: datetime
    combo_id: Optional[uuid.UUID] = None    # leadership-defined engine combo
    trial_agreement_id: Optional[uuid.UUID] = None
    billing_starts_at: Optional[datetime] = None
    renewed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    renewal_count: int = 0


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StartTrialRequest:
    """Start a trial subscription linked to a combo and trial agreement."""
    business_id: uuid.UUID
    combo_id: uuid.UUID
    trial_agreement_id: uuid.UUID
    billing_starts_at: datetime
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class ActivateSubscriptionRequest:
    business_id: uuid.UUID
    plan_id: uuid.UUID
    actor_id: str
    issued_at: datetime
    combo_id: Optional[uuid.UUID] = None


@dataclass(frozen=True)
class RenewSubscriptionRequest:
    business_id: uuid.UUID
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class CancelSubscriptionRequest:
    business_id: uuid.UUID
    actor_id: str
    issued_at: datetime
    reason: str = ""


@dataclass(frozen=True)
class SuspendSubscriptionRequest:
    business_id: uuid.UUID
    actor_id: str
    issued_at: datetime
    reason: str = ""


@dataclass(frozen=True)
class UpgradeSubscriptionRequest:
    business_id: uuid.UUID
    new_plan_id: uuid.UUID
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class ChangeComboRequest:
    """Switch to a different engine combo (up or downgrade)."""
    business_id: uuid.UUID
    new_combo_id: uuid.UUID
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION PROJECTION
# ══════════════════════════════════════════════════════════════

class SubscriptionProjection:
    """
    In-memory projection of subscriptions per business.

    Each business has at most one subscription record (latest wins).
    Rebuilt deterministically from subscription events.
    """

    projection_name = "subscription_projection"

    def __init__(self) -> None:
        # { business_id: SubscriptionRecord }
        self._subscriptions: Dict[uuid.UUID, SubscriptionRecord] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        biz_id = uuid.UUID(str(payload["business_id"]))

        if event_type == SUBSCRIPTION_TRIAL_STARTED_V1:
            sub_id = uuid.UUID(str(payload["subscription_id"]))
            combo_id = uuid.UUID(str(payload["combo_id"]))
            agreement_id = payload.get("trial_agreement_id")
            billing_starts = payload.get("billing_starts_at")
            self._subscriptions[biz_id] = SubscriptionRecord(
                subscription_id=sub_id,
                business_id=biz_id,
                plan_id=combo_id,               # plan_id = combo_id for compat
                status=SubscriptionStatus.TRIAL,
                activated_at=payload.get("issued_at"),
                combo_id=combo_id,
                trial_agreement_id=(
                    uuid.UUID(str(agreement_id)) if agreement_id else None
                ),
                billing_starts_at=billing_starts,
            )

        elif event_type == SUBSCRIPTION_ACTIVATED_V1:
            sub_id = uuid.UUID(str(payload["subscription_id"]))
            plan_id = uuid.UUID(str(payload["plan_id"]))
            combo_id_raw = payload.get("combo_id")
            combo_id = uuid.UUID(str(combo_id_raw)) if combo_id_raw else None
            # Check if upgrading from TRIAL
            old = self._subscriptions.get(biz_id)
            agreement_id = old.trial_agreement_id if old else None
            billing_starts = old.billing_starts_at if old else None
            self._subscriptions[biz_id] = SubscriptionRecord(
                subscription_id=sub_id,
                business_id=biz_id,
                plan_id=plan_id,
                status=SubscriptionStatus.ACTIVE,
                activated_at=payload.get("issued_at"),
                combo_id=combo_id or (old.combo_id if old else None),
                trial_agreement_id=agreement_id,
                billing_starts_at=billing_starts,
            )

        elif event_type == SUBSCRIPTION_RENEWED_V1:
            old = self._subscriptions.get(biz_id)
            if old is None:
                return
            self._subscriptions[biz_id] = SubscriptionRecord(
                subscription_id=old.subscription_id,
                business_id=old.business_id,
                plan_id=old.plan_id,
                status=SubscriptionStatus.ACTIVE,
                activated_at=old.activated_at,
                combo_id=old.combo_id,
                trial_agreement_id=old.trial_agreement_id,
                billing_starts_at=old.billing_starts_at,
                renewed_at=payload.get("issued_at"),
                renewal_count=old.renewal_count + 1,
            )

        elif event_type == SUBSCRIPTION_CANCELLED_V1:
            old = self._subscriptions.get(biz_id)
            if old is None:
                return
            self._subscriptions[biz_id] = SubscriptionRecord(
                subscription_id=old.subscription_id,
                business_id=old.business_id,
                plan_id=old.plan_id,
                status=SubscriptionStatus.CANCELLED,
                activated_at=old.activated_at,
                combo_id=old.combo_id,
                trial_agreement_id=old.trial_agreement_id,
                billing_starts_at=old.billing_starts_at,
                renewed_at=old.renewed_at,
                cancelled_at=payload.get("issued_at"),
                renewal_count=old.renewal_count,
            )

        elif event_type == SUBSCRIPTION_SUSPENDED_V1:
            old = self._subscriptions.get(biz_id)
            if old is None:
                return
            self._subscriptions[biz_id] = SubscriptionRecord(
                subscription_id=old.subscription_id,
                business_id=old.business_id,
                plan_id=old.plan_id,
                status=SubscriptionStatus.SUSPENDED,
                activated_at=old.activated_at,
                combo_id=old.combo_id,
                trial_agreement_id=old.trial_agreement_id,
                billing_starts_at=old.billing_starts_at,
                renewed_at=old.renewed_at,
                suspended_at=payload.get("issued_at"),
                renewal_count=old.renewal_count,
            )

        elif event_type == SUBSCRIPTION_UPGRADED_V1:
            old = self._subscriptions.get(biz_id)
            if old is None:
                return
            new_plan_id = uuid.UUID(str(payload["new_plan_id"]))
            self._subscriptions[biz_id] = SubscriptionRecord(
                subscription_id=old.subscription_id,
                business_id=old.business_id,
                plan_id=new_plan_id,
                status=SubscriptionStatus.ACTIVE,
                activated_at=old.activated_at,
                combo_id=old.combo_id,
                trial_agreement_id=old.trial_agreement_id,
                billing_starts_at=old.billing_starts_at,
                renewed_at=payload.get("issued_at"),
                renewal_count=old.renewal_count,
            )

        elif event_type == SUBSCRIPTION_COMBO_CHANGED_V1:
            old = self._subscriptions.get(biz_id)
            if old is None:
                return
            new_combo_id = uuid.UUID(str(payload["new_combo_id"]))
            self._subscriptions[biz_id] = SubscriptionRecord(
                subscription_id=old.subscription_id,
                business_id=old.business_id,
                plan_id=new_combo_id,           # plan_id follows combo_id
                status=old.status,
                activated_at=old.activated_at,
                combo_id=new_combo_id,
                trial_agreement_id=old.trial_agreement_id,
                billing_starts_at=old.billing_starts_at,
                renewed_at=old.renewed_at,
                renewal_count=old.renewal_count,
            )

    def get_subscription(
        self, business_id: uuid.UUID
    ) -> Optional[SubscriptionRecord]:
        return self._subscriptions.get(business_id)

    def list_active_subscriptions(self) -> List[SubscriptionRecord]:
        return [
            s for s in self._subscriptions.values()
            if s.status == SubscriptionStatus.ACTIVE
        ]

    def list_trial_subscriptions(self) -> List[SubscriptionRecord]:
        return [
            s for s in self._subscriptions.values()
            if s.status == SubscriptionStatus.TRIAL
        ]

    def list_by_plan(self, plan_id: uuid.UUID) -> List[SubscriptionRecord]:
        return [
            s for s in self._subscriptions.values()
            if s.plan_id == plan_id
        ]

    def list_by_combo(self, combo_id: uuid.UUID) -> List[SubscriptionRecord]:
        return [
            s for s in self._subscriptions.values()
            if s.combo_id == combo_id
        ]

    def truncate(self, business_id: Optional[uuid.UUID] = None) -> None:
        if business_id:
            self._subscriptions.pop(business_id, None)
        else:
            self._subscriptions.clear()


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION MANAGER
# ══════════════════════════════════════════════════════════════

class SubscriptionManager:
    """
    Manages subscription lifecycle per business.

    All mutations produce events — no direct state writes.
    """

    def __init__(self, projection: SubscriptionProjection) -> None:
        self._projection = projection

    def start_trial(
        self, request: StartTrialRequest
    ) -> Dict[str, Any]:
        """Start a trial subscription for a new tenant."""
        existing = self._projection.get_subscription(request.business_id)
        if existing and existing.status in (
            SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE
        ):
            return {
                "rejected": RejectionReason(
                    code="SUBSCRIPTION_EXISTS",
                    message="Business already has an active or trial subscription.",
                    policy_name="start_trial",
                ),
            }

        sub_id = uuid.uuid4()
        payload = {
            "subscription_id": str(sub_id),
            "business_id": str(request.business_id),
            "combo_id": str(request.combo_id),
            "trial_agreement_id": str(request.trial_agreement_id),
            "billing_starts_at": request.billing_starts_at,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(SUBSCRIPTION_TRIAL_STARTED_V1, payload)
        return {
            "subscription_id": sub_id,
            "status": SubscriptionStatus.TRIAL.value,
            "events": [{"event_type": SUBSCRIPTION_TRIAL_STARTED_V1, "payload": payload}],
        }

    def activate(
        self, request: ActivateSubscriptionRequest
    ) -> Dict[str, Any]:
        """
        Activate a subscription.

        If currently TRIAL → converts to ACTIVE (trial conversion).
        If no subscription → creates new ACTIVE subscription.
        """
        existing = self._projection.get_subscription(request.business_id)

        if existing and existing.status == SubscriptionStatus.ACTIVE:
            return {
                "rejected": RejectionReason(
                    code="SUBSCRIPTION_ALREADY_ACTIVE",
                    message="Business already has an active subscription.",
                    policy_name="activate_subscription",
                ),
            }

        # TRIAL → ACTIVE conversion
        if existing and existing.status == SubscriptionStatus.TRIAL:
            sub_id = existing.subscription_id
        else:
            sub_id = uuid.uuid4()

        combo_id = request.combo_id or (
            existing.combo_id if existing else None
        )

        payload: Dict[str, Any] = {
            "subscription_id": str(sub_id),
            "business_id": str(request.business_id),
            "plan_id": str(request.plan_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        if combo_id:
            payload["combo_id"] = str(combo_id)

        self._projection.apply(SUBSCRIPTION_ACTIVATED_V1, payload)
        return {
            "subscription_id": sub_id,
            "events": [{"event_type": SUBSCRIPTION_ACTIVATED_V1, "payload": payload}],
        }

    def renew(
        self, request: RenewSubscriptionRequest
    ) -> Optional[RejectionReason]:
        """Renew an existing active subscription."""
        sub = self._projection.get_subscription(request.business_id)
        if sub is None:
            return RejectionReason(
                code="NO_SUBSCRIPTION",
                message="No subscription found for this business.",
                policy_name="renew_subscription",
            )
        if sub.status != SubscriptionStatus.ACTIVE:
            return RejectionReason(
                code="SUBSCRIPTION_NOT_ACTIVE",
                message=f"Cannot renew: subscription is {sub.status.value}.",
                policy_name="renew_subscription",
            )
        self._projection.apply(SUBSCRIPTION_RENEWED_V1, {
            "business_id": str(request.business_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def cancel(
        self, request: CancelSubscriptionRequest
    ) -> Optional[RejectionReason]:
        sub = self._projection.get_subscription(request.business_id)
        if sub is None:
            return RejectionReason(
                code="NO_SUBSCRIPTION",
                message="No subscription found for this business.",
                policy_name="cancel_subscription",
            )
        if not _can_transition(sub.status, SubscriptionStatus.CANCELLED):
            return RejectionReason(
                code="INVALID_SUBSCRIPTION_TRANSITION",
                message=f"Cannot cancel: subscription is {sub.status.value}.",
                policy_name="cancel_subscription",
            )
        self._projection.apply(SUBSCRIPTION_CANCELLED_V1, {
            "business_id": str(request.business_id),
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def suspend(
        self, request: SuspendSubscriptionRequest
    ) -> Optional[RejectionReason]:
        sub = self._projection.get_subscription(request.business_id)
        if sub is None:
            return RejectionReason(
                code="NO_SUBSCRIPTION",
                message="No subscription found for this business.",
                policy_name="suspend_subscription",
            )
        if not _can_transition(sub.status, SubscriptionStatus.SUSPENDED):
            return RejectionReason(
                code="INVALID_SUBSCRIPTION_TRANSITION",
                message=f"Cannot suspend: subscription is {sub.status.value}.",
                policy_name="suspend_subscription",
            )
        self._projection.apply(SUBSCRIPTION_SUSPENDED_V1, {
            "business_id": str(request.business_id),
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def upgrade(
        self, request: UpgradeSubscriptionRequest
    ) -> Optional[RejectionReason]:
        sub = self._projection.get_subscription(request.business_id)
        if sub is None:
            return RejectionReason(
                code="NO_SUBSCRIPTION",
                message="No subscription found for this business.",
                policy_name="upgrade_subscription",
            )
        if sub.status != SubscriptionStatus.ACTIVE:
            return RejectionReason(
                code="SUBSCRIPTION_NOT_ACTIVE",
                message=f"Cannot upgrade: subscription is {sub.status.value}.",
                policy_name="upgrade_subscription",
            )
        if sub.plan_id == request.new_plan_id:
            return RejectionReason(
                code="SAME_PLAN",
                message="Already on this plan.",
                policy_name="upgrade_subscription",
            )
        self._projection.apply(SUBSCRIPTION_UPGRADED_V1, {
            "business_id": str(request.business_id),
            "new_plan_id": str(request.new_plan_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def change_combo(
        self, request: ChangeComboRequest
    ) -> Optional[RejectionReason]:
        """Switch to a different engine combo."""
        sub = self._projection.get_subscription(request.business_id)
        if sub is None:
            return RejectionReason(
                code="NO_SUBSCRIPTION",
                message="No subscription found for this business.",
                policy_name="change_combo",
            )
        if sub.status not in (SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE):
            return RejectionReason(
                code="SUBSCRIPTION_NOT_ACTIVE",
                message=f"Cannot change combo: subscription is {sub.status.value}.",
                policy_name="change_combo",
            )
        if sub.combo_id == request.new_combo_id:
            return RejectionReason(
                code="SAME_COMBO",
                message="Already on this combo.",
                policy_name="change_combo",
            )
        self._projection.apply(SUBSCRIPTION_COMBO_CHANGED_V1, {
            "business_id": str(request.business_id),
            "new_combo_id": str(request.new_combo_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def is_active(self, business_id: uuid.UUID) -> bool:
        sub = self._projection.get_subscription(business_id)
        return sub is not None and sub.status == SubscriptionStatus.ACTIVE

    def is_active_or_trial(self, business_id: uuid.UUID) -> bool:
        """Check if business has an active or trial subscription."""
        sub = self._projection.get_subscription(business_id)
        return sub is not None and sub.status in (
            SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL
        )
