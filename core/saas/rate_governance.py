"""
BOS SaaS — Rate Governance & Trial Agreements
================================================
Protects users from surprise rate changes and enforces
immutable trial agreements.

BOS Doctrine:
  1. Trial duration (default 180 days) is configurable by platform.
  2. Once a user signs up, their trial agreement is IMMUTABLE —
     even if default trial days change later, their terms are honoured.
  3. Rate snapshots are locked at signup — user pays what they were shown.
  4. Rate changes require 90-day advance notification before the
     user's current plan/cycle expires.
  5. Rate decreases take effect immediately on next cycle.
  6. Rate increases > 25% trigger double notification (immediate + 30 days before).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# EVENT TYPES
# ══════════════════════════════════════════════════════════════

TRIAL_POLICY_SET_V1 = "saas.trial_policy.set.v1"
TRIAL_AGREEMENT_CREATED_V1 = "saas.trial_agreement.created.v1"
TRIAL_AGREEMENT_EXTENDED_V1 = "saas.trial_agreement.extended.v1"
TRIAL_AGREEMENT_CONVERTED_V1 = "saas.trial_agreement.converted.v1"
TRIAL_AGREEMENT_EXPIRED_V1 = "saas.trial_agreement.expired.v1"
RATE_CHANGE_PUBLISHED_V1 = "saas.rate_change.published.v1"
RATE_CHANGE_NOTIFICATION_SENT_V1 = "saas.rate_change.notification_sent.v1"

RATE_GOVERNANCE_EVENT_TYPES = (
    TRIAL_POLICY_SET_V1,
    TRIAL_AGREEMENT_CREATED_V1,
    TRIAL_AGREEMENT_EXTENDED_V1,
    TRIAL_AGREEMENT_CONVERTED_V1,
    TRIAL_AGREEMENT_EXPIRED_V1,
    RATE_CHANGE_PUBLISHED_V1,
    RATE_CHANGE_NOTIFICATION_SENT_V1,
)


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class TrialStatus(Enum):
    ACTIVE = "ACTIVE"           # user is within trial period
    CONVERTED = "CONVERTED"     # trial ended, user started paying
    EXPIRED = "EXPIRED"         # trial ended, user did not convert


class NotificationUrgency(Enum):
    STANDARD = "STANDARD"       # normal 90-day notice
    ELEVATED = "ELEVATED"       # rate increase > 25%: double notification


# ══════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TrialPolicy:
    """
    Platform-wide trial configuration.

    This can change at any time, but EXISTING agreements are not affected.
    New signups get the policy that is active at their signup time.
    """
    default_trial_days: int         # e.g. 180
    max_trial_days: int             # cap including extensions e.g. 365
    grace_period_days: int          # days after trial before suspension e.g. 7
    rate_notice_days: int           # minimum advance notice for rate changes e.g. 90
    version: str                    # e.g. "v2026.03"
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class RateSnapshot:
    """
    Frozen copy of rates at the moment the user signed up.

    This is what the user agreed to pay. Even if rates change,
    this snapshot determines their first billing cycle charge.
    """
    combo_id: str
    region_code: str
    currency: str
    monthly_amount: Decimal         # rate at signup
    rate_version: int               # version number from ComboRate


@dataclass(frozen=True)
class TrialAgreement:
    """
    Immutable contract between BOS and a tenant.

    Once created, these terms do NOT change — even if platform
    policy or rates are updated later. This is a legal agreement.
    """
    agreement_id: uuid.UUID
    business_id: uuid.UUID
    combo_id: uuid.UUID
    region_code: str

    # Trial terms (frozen at signup)
    trial_days: int                 # actual days (from policy at signup time)
    trial_starts_at: datetime
    trial_ends_at: datetime
    billing_starts_at: datetime     # = trial_ends_at + 1 day

    # Rate terms (frozen at signup)
    rate_snapshot: RateSnapshot
    rate_guaranteed_until: datetime  # rate honoured for at least first billing cycle

    # Policy version that was active at signup
    terms_version: str              # e.g. "v2026.03"

    # Status
    status: TrialStatus = TrialStatus.ACTIVE
    converted_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None

    # Referral / promo adjustments (additive)
    bonus_days: int = 0             # e.g. +30 from referral
    promo_code: str = ""            # promo code used at signup


@dataclass(frozen=True)
class RateChangeRecord:
    """Tracks a rate change that affects existing tenants."""
    change_id: uuid.UUID
    combo_id: uuid.UUID
    region_code: str
    old_amount: Decimal
    new_amount: Decimal
    old_version: int
    new_version: int
    currency: str
    published_at: datetime
    effective_from: datetime     # when new rate takes effect for existing users
    urgency: NotificationUrgency


@dataclass(frozen=True)
class RateChangeNotification:
    """Record that a tenant was notified about a rate change."""
    notification_id: uuid.UUID
    business_id: uuid.UUID
    change_id: uuid.UUID
    notified_at: datetime
    channel: str                    # "sms", "email", "whatsapp", "in_app"
    plan_expires_at: datetime       # when their current cycle ends
    days_notice: int                # how many days of advance notice given


# ══════════════════════════════════════════════════════════════
# REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SetTrialPolicyRequest:
    """Update the platform-wide trial policy (affects new signups only)."""
    default_trial_days: int
    max_trial_days: int
    grace_period_days: int
    rate_notice_days: int
    version: str
    actor_id: str
    issued_at: datetime

    def __post_init__(self) -> None:
        if self.default_trial_days < 1:
            raise ValueError("default_trial_days must be ≥ 1")
        if self.max_trial_days < self.default_trial_days:
            raise ValueError("max_trial_days must be ≥ default_trial_days")
        if self.grace_period_days < 0:
            raise ValueError("grace_period_days must be ≥ 0")
        if self.rate_notice_days < 30:
            raise ValueError("rate_notice_days must be ≥ 30")


@dataclass(frozen=True)
class CreateTrialAgreementRequest:
    """Create an immutable trial agreement for a new tenant."""
    business_id: uuid.UUID
    combo_id: uuid.UUID
    region_code: str
    currency: str
    monthly_amount: Decimal
    rate_version: int
    actor_id: str
    issued_at: datetime
    referral_bonus_days: int = 0
    promo_code: str = ""


@dataclass(frozen=True)
class ExtendTrialRequest:
    """Extend an existing trial (e.g. from promotion or support gesture)."""
    business_id: uuid.UUID
    extra_days: int
    reason: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class ConvertTrialRequest:
    """Mark a trial as converted (user started paying)."""
    business_id: uuid.UUID
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class PublishRateChangeRequest:
    """Publish a rate change that will affect existing tenants."""
    combo_id: uuid.UUID
    region_code: str
    old_amount: Decimal
    new_amount: Decimal
    old_version: int
    new_version: int
    currency: str
    effective_from: datetime
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# PROJECTION
# ══════════════════════════════════════════════════════════════

class RateGovernanceProjection:
    """
    In-memory projection of trial policies, agreements, and rate changes.

    Rebuilt deterministically from governance events.
    """

    projection_name = "rate_governance_projection"

    def __init__(self) -> None:
        self._trial_policy: Optional[TrialPolicy] = None
        # business_id → TrialAgreement
        self._agreements: Dict[uuid.UUID, TrialAgreement] = {}
        # change_id → RateChangeRecord
        self._rate_changes: Dict[uuid.UUID, RateChangeRecord] = {}
        # (business_id, change_id) → RateChangeNotification
        self._notifications: Dict[tuple, RateChangeNotification] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == TRIAL_POLICY_SET_V1:
            self._apply_trial_policy(payload)
        elif event_type == TRIAL_AGREEMENT_CREATED_V1:
            self._apply_agreement_created(payload)
        elif event_type == TRIAL_AGREEMENT_EXTENDED_V1:
            self._apply_agreement_extended(payload)
        elif event_type == TRIAL_AGREEMENT_CONVERTED_V1:
            self._apply_agreement_converted(payload)
        elif event_type == TRIAL_AGREEMENT_EXPIRED_V1:
            self._apply_agreement_expired(payload)
        elif event_type == RATE_CHANGE_PUBLISHED_V1:
            self._apply_rate_change(payload)
        elif event_type == RATE_CHANGE_NOTIFICATION_SENT_V1:
            self._apply_notification(payload)

    def _apply_trial_policy(self, payload: Dict[str, Any]) -> None:
        self._trial_policy = TrialPolicy(
            default_trial_days=payload["default_trial_days"],
            max_trial_days=payload["max_trial_days"],
            grace_period_days=payload.get("grace_period_days", 7),
            rate_notice_days=payload.get("rate_notice_days", 90),
            version=payload.get("version", "v1"),
            updated_at=payload.get("issued_at"),
        )

    def _apply_agreement_created(self, payload: Dict[str, Any]) -> None:
        agreement_id = uuid.UUID(str(payload["agreement_id"]))
        business_id = uuid.UUID(str(payload["business_id"]))
        combo_id = uuid.UUID(str(payload["combo_id"]))
        trial_starts = payload["trial_starts_at"]
        trial_days = payload["trial_days"]
        bonus_days = payload.get("bonus_days", 0)
        total_days = trial_days + bonus_days

        if isinstance(trial_starts, str):
            trial_starts = datetime.fromisoformat(trial_starts)

        trial_ends = trial_starts + timedelta(days=total_days)
        billing_starts = trial_ends + timedelta(days=1)
        # Rate guaranteed for first billing cycle (30 days after trial)
        rate_guaranteed = billing_starts + timedelta(days=30)

        rate_snap = RateSnapshot(
            combo_id=str(combo_id),
            region_code=payload["region_code"],
            currency=payload["currency"],
            monthly_amount=Decimal(str(payload["monthly_amount"])),
            rate_version=payload.get("rate_version", 1),
        )

        self._agreements[business_id] = TrialAgreement(
            agreement_id=agreement_id,
            business_id=business_id,
            combo_id=combo_id,
            region_code=payload["region_code"],
            trial_days=trial_days,
            trial_starts_at=trial_starts,
            trial_ends_at=trial_ends,
            billing_starts_at=billing_starts,
            rate_snapshot=rate_snap,
            rate_guaranteed_until=rate_guaranteed,
            terms_version=payload.get("terms_version", "v1"),
            bonus_days=bonus_days,
            promo_code=payload.get("promo_code", ""),
        )

    def _apply_agreement_extended(self, payload: Dict[str, Any]) -> None:
        business_id = uuid.UUID(str(payload["business_id"]))
        old = self._agreements.get(business_id)
        if old is None or old.status != TrialStatus.ACTIVE:
            return
        extra_days = payload.get("extra_days", 0)
        new_bonus = old.bonus_days + extra_days
        new_trial_ends = old.trial_starts_at + timedelta(
            days=old.trial_days + new_bonus
        )
        new_billing = new_trial_ends + timedelta(days=1)
        new_rate_guaranteed = new_billing + timedelta(days=30)

        self._agreements[business_id] = TrialAgreement(
            agreement_id=old.agreement_id,
            business_id=old.business_id,
            combo_id=old.combo_id,
            region_code=old.region_code,
            trial_days=old.trial_days,
            trial_starts_at=old.trial_starts_at,
            trial_ends_at=new_trial_ends,
            billing_starts_at=new_billing,
            rate_snapshot=old.rate_snapshot,
            rate_guaranteed_until=new_rate_guaranteed,
            terms_version=old.terms_version,
            bonus_days=new_bonus,
            promo_code=old.promo_code,
        )

    def _apply_agreement_converted(self, payload: Dict[str, Any]) -> None:
        business_id = uuid.UUID(str(payload["business_id"]))
        old = self._agreements.get(business_id)
        if old is None:
            return
        self._agreements[business_id] = TrialAgreement(
            agreement_id=old.agreement_id,
            business_id=old.business_id,
            combo_id=old.combo_id,
            region_code=old.region_code,
            trial_days=old.trial_days,
            trial_starts_at=old.trial_starts_at,
            trial_ends_at=old.trial_ends_at,
            billing_starts_at=old.billing_starts_at,
            rate_snapshot=old.rate_snapshot,
            rate_guaranteed_until=old.rate_guaranteed_until,
            terms_version=old.terms_version,
            status=TrialStatus.CONVERTED,
            converted_at=payload.get("issued_at"),
            bonus_days=old.bonus_days,
            promo_code=old.promo_code,
        )

    def _apply_agreement_expired(self, payload: Dict[str, Any]) -> None:
        business_id = uuid.UUID(str(payload["business_id"]))
        old = self._agreements.get(business_id)
        if old is None:
            return
        self._agreements[business_id] = TrialAgreement(
            agreement_id=old.agreement_id,
            business_id=old.business_id,
            combo_id=old.combo_id,
            region_code=old.region_code,
            trial_days=old.trial_days,
            trial_starts_at=old.trial_starts_at,
            trial_ends_at=old.trial_ends_at,
            billing_starts_at=old.billing_starts_at,
            rate_snapshot=old.rate_snapshot,
            rate_guaranteed_until=old.rate_guaranteed_until,
            terms_version=old.terms_version,
            status=TrialStatus.EXPIRED,
            expired_at=payload.get("issued_at"),
            bonus_days=old.bonus_days,
            promo_code=old.promo_code,
        )

    def _apply_rate_change(self, payload: Dict[str, Any]) -> None:
        change_id = uuid.UUID(str(payload["change_id"]))
        combo_id = uuid.UUID(str(payload["combo_id"]))
        old_amount = Decimal(str(payload["old_amount"]))
        new_amount = Decimal(str(payload["new_amount"]))

        # Determine urgency
        if new_amount > old_amount:
            pct_increase = ((new_amount - old_amount) / old_amount * 100) if old_amount > 0 else Decimal("100")
            urgency = (
                NotificationUrgency.ELEVATED
                if pct_increase > 25
                else NotificationUrgency.STANDARD
            )
        else:
            urgency = NotificationUrgency.STANDARD

        self._rate_changes[change_id] = RateChangeRecord(
            change_id=change_id,
            combo_id=combo_id,
            region_code=payload["region_code"],
            old_amount=old_amount,
            new_amount=new_amount,
            old_version=payload.get("old_version", 0),
            new_version=payload.get("new_version", 0),
            currency=payload.get("currency", ""),
            published_at=payload.get("issued_at", datetime.utcnow()),
            effective_from=payload["effective_from"],
            urgency=urgency,
        )

    def _apply_notification(self, payload: Dict[str, Any]) -> None:
        notification_id = uuid.UUID(str(payload["notification_id"]))
        business_id = uuid.UUID(str(payload["business_id"]))
        change_id = uuid.UUID(str(payload["change_id"]))
        self._notifications[(business_id, change_id)] = RateChangeNotification(
            notification_id=notification_id,
            business_id=business_id,
            change_id=change_id,
            notified_at=payload.get("notified_at", datetime.utcnow()),
            channel=payload.get("channel", "in_app"),
            plan_expires_at=payload.get("plan_expires_at", datetime.utcnow()),
            days_notice=payload.get("days_notice", 0),
        )

    # ── queries ────────────────────────────────────────────────

    def get_trial_policy(self) -> Optional[TrialPolicy]:
        return self._trial_policy

    def get_current_trial_days(self) -> int:
        """Return current default trial days (for new signups)."""
        if self._trial_policy:
            return self._trial_policy.default_trial_days
        return 180  # BOS default

    def get_agreement(self, business_id: uuid.UUID) -> Optional[TrialAgreement]:
        return self._agreements.get(business_id)

    def list_active_trials(self) -> List[TrialAgreement]:
        return [
            a for a in self._agreements.values()
            if a.status == TrialStatus.ACTIVE
        ]

    def list_expiring_trials(self, within_days: int = 30) -> List[TrialAgreement]:
        """Trials ending within N days (for conversion outreach)."""
        now = datetime.utcnow()
        cutoff = now + timedelta(days=within_days)
        return [
            a for a in self._agreements.values()
            if a.status == TrialStatus.ACTIVE and a.trial_ends_at <= cutoff
        ]

    def get_pending_rate_changes(
        self, combo_id: uuid.UUID, region_code: str
    ) -> List[RateChangeRecord]:
        """Rate changes that haven't taken effect yet."""
        now = datetime.utcnow()
        return [
            rc for rc in self._rate_changes.values()
            if rc.combo_id == combo_id
            and rc.region_code == region_code
            and rc.effective_from > now
        ]

    def is_tenant_notified(
        self, business_id: uuid.UUID, change_id: uuid.UUID
    ) -> bool:
        return (business_id, change_id) in self._notifications

    def get_tenants_needing_notification(
        self, change_id: uuid.UUID
    ) -> List[uuid.UUID]:
        """Return business_ids that should be notified about a rate change."""
        change = self._rate_changes.get(change_id)
        if change is None:
            return []
        result = []
        for biz_id, agreement in self._agreements.items():
            if (
                str(agreement.combo_id) == str(change.combo_id)
                and agreement.region_code == change.region_code
                and agreement.status in (TrialStatus.ACTIVE, TrialStatus.CONVERTED)
                and not self.is_tenant_notified(biz_id, change_id)
            ):
                result.append(biz_id)
        return result

    def truncate(self) -> None:
        self._trial_policy = None
        self._agreements.clear()
        self._rate_changes.clear()
        self._notifications.clear()


# ══════════════════════════════════════════════════════════════
# SERVICE
# ══════════════════════════════════════════════════════════════

class RateGovernanceService:
    """
    Manages trial agreements and rate change governance.

    Core invariants:
      - Trial agreements are immutable once created
      - Rate changes require minimum notice period
      - Original terms are always honoured
    """

    def __init__(self, projection: RateGovernanceProjection) -> None:
        self._projection = projection

    def set_trial_policy(
        self, request: SetTrialPolicyRequest
    ) -> Dict[str, Any]:
        """Update platform trial policy. Only affects NEW signups."""
        payload = {
            "default_trial_days": request.default_trial_days,
            "max_trial_days": request.max_trial_days,
            "grace_period_days": request.grace_period_days,
            "rate_notice_days": request.rate_notice_days,
            "version": request.version,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(TRIAL_POLICY_SET_V1, payload)
        return {
            "events": [{"event_type": TRIAL_POLICY_SET_V1, "payload": payload}],
        }

    def create_trial_agreement(
        self, request: CreateTrialAgreementRequest
    ) -> Dict[str, Any]:
        """
        Create an immutable trial agreement for a new tenant.

        Uses the CURRENT trial policy to set trial_days, but once
        created, the agreement is frozen regardless of future changes.
        """
        existing = self._projection.get_agreement(request.business_id)
        if existing is not None:
            return {
                "rejected": RejectionReason(
                    code="AGREEMENT_EXISTS",
                    message="A trial agreement already exists for this business.",
                    policy_name="create_trial_agreement",
                ),
            }

        policy = self._projection.get_trial_policy()
        trial_days = policy.default_trial_days if policy else 180
        max_trial = policy.max_trial_days if policy else 365
        terms_version = policy.version if policy else "v1"

        # Apply referral bonus (capped at max)
        bonus = min(request.referral_bonus_days, max_trial - trial_days)
        if bonus < 0:
            bonus = 0

        agreement_id = uuid.uuid4()
        trial_starts = request.issued_at

        payload = {
            "agreement_id": str(agreement_id),
            "business_id": str(request.business_id),
            "combo_id": str(request.combo_id),
            "region_code": request.region_code,
            "currency": request.currency,
            "monthly_amount": str(request.monthly_amount),
            "rate_version": request.rate_version,
            "trial_days": trial_days,
            "trial_starts_at": trial_starts.isoformat() if isinstance(trial_starts, datetime) else trial_starts,
            "bonus_days": bonus,
            "promo_code": request.promo_code,
            "terms_version": terms_version,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(TRIAL_AGREEMENT_CREATED_V1, payload)
        agreement = self._projection.get_agreement(request.business_id)
        return {
            "agreement_id": agreement_id,
            "trial_days": trial_days + bonus,
            "trial_ends_at": agreement.trial_ends_at if agreement else None,
            "billing_starts_at": agreement.billing_starts_at if agreement else None,
            "monthly_amount": str(request.monthly_amount),
            "currency": request.currency,
            "events": [{"event_type": TRIAL_AGREEMENT_CREATED_V1, "payload": payload}],
        }

    def extend_trial(
        self, request: ExtendTrialRequest
    ) -> Optional[RejectionReason]:
        """Extend an active trial (promotion, support, referral reward)."""
        agreement = self._projection.get_agreement(request.business_id)
        if agreement is None:
            return RejectionReason(
                code="NO_AGREEMENT",
                message="No trial agreement found for this business.",
                policy_name="extend_trial",
            )
        if agreement.status != TrialStatus.ACTIVE:
            return RejectionReason(
                code="TRIAL_NOT_ACTIVE",
                message=f"Trial is {agreement.status.value}, cannot extend.",
                policy_name="extend_trial",
            )

        # Check max trial cap
        policy = self._projection.get_trial_policy()
        max_trial = policy.max_trial_days if policy else 365
        total_after = agreement.trial_days + agreement.bonus_days + request.extra_days
        if total_after > max_trial:
            return RejectionReason(
                code="EXCEEDS_MAX_TRIAL",
                message=f"Total trial would be {total_after} days, max is {max_trial}.",
                policy_name="extend_trial",
            )

        self._projection.apply(TRIAL_AGREEMENT_EXTENDED_V1, {
            "business_id": str(request.business_id),
            "extra_days": request.extra_days,
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def convert_trial(
        self, request: ConvertTrialRequest
    ) -> Optional[RejectionReason]:
        """Mark trial as converted — user started paying."""
        agreement = self._projection.get_agreement(request.business_id)
        if agreement is None:
            return RejectionReason(
                code="NO_AGREEMENT",
                message="No trial agreement found.",
                policy_name="convert_trial",
            )
        if agreement.status == TrialStatus.CONVERTED:
            return RejectionReason(
                code="ALREADY_CONVERTED",
                message="Trial already converted.",
                policy_name="convert_trial",
            )
        self._projection.apply(TRIAL_AGREEMENT_CONVERTED_V1, {
            "business_id": str(request.business_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def publish_rate_change(
        self, request: PublishRateChangeRequest
    ) -> Dict[str, Any]:
        """
        Publish a rate change affecting existing tenants.

        Validates that notice period is respected:
        effective_from must be ≥ rate_notice_days from now.
        """
        policy = self._projection.get_trial_policy()
        notice_days = policy.rate_notice_days if policy else 90
        min_effective = request.issued_at + timedelta(days=notice_days)

        if request.effective_from < min_effective:
            return {
                "rejected": RejectionReason(
                    code="INSUFFICIENT_NOTICE",
                    message=(
                        f"Rate change must be at least {notice_days} days from now. "
                        f"Earliest effective date: {min_effective.date().isoformat()}."
                    ),
                    policy_name="publish_rate_change",
                ),
            }

        change_id = uuid.uuid4()
        payload = {
            "change_id": str(change_id),
            "combo_id": str(request.combo_id),
            "region_code": request.region_code,
            "old_amount": str(request.old_amount),
            "new_amount": str(request.new_amount),
            "old_version": request.old_version,
            "new_version": request.new_version,
            "currency": request.currency,
            "effective_from": request.effective_from,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(RATE_CHANGE_PUBLISHED_V1, payload)

        return {
            "change_id": change_id,
            "tenants_to_notify": self._projection.get_tenants_needing_notification(change_id),
            "events": [{"event_type": RATE_CHANGE_PUBLISHED_V1, "payload": payload}],
        }

    def should_user_pay_old_rate(
        self, business_id: uuid.UUID, as_of: datetime
    ) -> bool:
        """
        Check if a tenant should still pay their original (locked) rate.

        True if current date is before rate_guaranteed_until.
        """
        agreement = self._projection.get_agreement(business_id)
        if agreement is None:
            return False
        return as_of <= agreement.rate_guaranteed_until

    def get_effective_rate(
        self, business_id: uuid.UUID, as_of: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Return the rate a tenant should be charged right now.

        Rules:
        1. During trial → charge = 0 (free)
        2. Before rate_guaranteed_until → charge = rate_snapshot
        3. After rate_guaranteed_until → charge = latest rate (or new rate if published)
        """
        agreement = self._projection.get_agreement(business_id)
        if agreement is None:
            return None

        if agreement.status == TrialStatus.ACTIVE:
            return {
                "amount": "0",
                "currency": agreement.rate_snapshot.currency,
                "reason": "TRIAL_ACTIVE",
                "trial_ends_at": agreement.trial_ends_at,
            }

        if as_of <= agreement.rate_guaranteed_until:
            return {
                "amount": str(agreement.rate_snapshot.monthly_amount),
                "currency": agreement.rate_snapshot.currency,
                "reason": "RATE_GUARANTEED",
                "guaranteed_until": agreement.rate_guaranteed_until,
                "rate_version": agreement.rate_snapshot.rate_version,
            }

        # After guarantee period — check for published rate changes
        combo_id = agreement.combo_id
        region_code = agreement.region_code
        latest_change = None
        for rc in self._projection._rate_changes.values():
            if (
                rc.combo_id == combo_id
                and rc.region_code == region_code
                and rc.effective_from <= as_of
            ):
                if latest_change is None or rc.effective_from > latest_change.effective_from:
                    latest_change = rc

        if latest_change:
            return {
                "amount": str(latest_change.new_amount),
                "currency": latest_change.currency,
                "reason": "RATE_UPDATED",
                "rate_version": latest_change.new_version,
            }

        # No change published — still on snapshot rate
        return {
            "amount": str(agreement.rate_snapshot.monthly_amount),
            "currency": agreement.rate_snapshot.currency,
            "reason": "ORIGINAL_RATE",
            "rate_version": agreement.rate_snapshot.rate_version,
        }
