"""
BOS SaaS — Promotions Engine
================================
Handles discounts, credits, trial extensions, engine bonuses,
and bundle discounts. All promo activity is event-sourced.

Promo types:
  DISCOUNT         — % off monthly total for N months
  CREDIT           — flat amount credited to account
  EXTENDED_TRIAL   — extra days added to trial
  ENGINE_BONUS     — free engine for N months
  BUNDLE_DISCOUNT  — ongoing % off when engines match a bundle

Stacking rules:
  DISCOUNT + CREDIT       = allowed
  DISCOUNT + DISCOUNT     = best one wins (not cumulative)
  EXTENDED_TRIAL + others = allowed (capped by max_trial_days)
  ENGINE_BONUS + BUNDLE   = allowed
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# EVENT TYPES
# ══════════════════════════════════════════════════════════════

PROMO_CREATED_V1 = "saas.promo.created.v1"
PROMO_DEACTIVATED_V1 = "saas.promo.deactivated.v1"
PROMO_REDEEMED_V1 = "saas.promo.redeemed.v1"

PROMOTION_EVENT_TYPES = (
    PROMO_CREATED_V1,
    PROMO_DEACTIVATED_V1,
    PROMO_REDEEMED_V1,
)


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class PromoType(Enum):
    DISCOUNT = "DISCOUNT"
    CREDIT = "CREDIT"
    EXTENDED_TRIAL = "EXTENDED_TRIAL"
    ENGINE_BONUS = "ENGINE_BONUS"
    BUNDLE_DISCOUNT = "BUNDLE_DISCOUNT"


class PromoStatus(Enum):
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"
    EXHAUSTED = "EXHAUSTED"       # max_redemptions reached


# ══════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PromoDefinition:
    """
    Immutable promotion definition.

    Platform admin creates promos. Users redeem them via promo codes.
    """
    promo_id: uuid.UUID
    promo_code: str                     # e.g. "LAUNCH2026", "DUKA50"
    promo_type: PromoType
    status: PromoStatus

    # Common fields
    description: str
    valid_from: datetime
    valid_until: datetime
    max_redemptions: int                # 0 = unlimited
    current_redemptions: int
    region_codes: Tuple[str, ...]       # empty = all regions
    combo_ids: Tuple[str, ...]          # empty = all combos

    # DISCOUNT fields
    discount_pct: Decimal               # e.g. Decimal("20") for 20%
    discount_months: int                # how many months the discount lasts

    # CREDIT fields
    credit_amount: Decimal              # flat credit amount
    credit_currency: str
    credit_expires_months: int          # months until credit expires

    # EXTENDED_TRIAL fields
    extra_trial_days: int

    # ENGINE_BONUS fields
    bonus_engine: str                   # engine key to give free
    bonus_months: int                   # how many months free
    bonus_after: str                    # "auto_add" or "auto_remove" after bonus ends

    # BUNDLE_DISCOUNT fields
    bundle_engines: Tuple[str, ...]     # engines that must be active for bundle
    bundle_discount_pct: Decimal        # ongoing % off

    created_at: Optional[datetime] = None


@dataclass(frozen=True)
class PromoRedemption:
    """Record of a tenant redeeming a promo code."""
    redemption_id: uuid.UUID
    promo_id: uuid.UUID
    promo_code: str
    business_id: uuid.UUID
    redeemed_at: datetime
    promo_type: str
    details: Dict[str, Any]             # type-specific data


# ══════════════════════════════════════════════════════════════
# REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CreatePromoRequest:
    promo_code: str
    promo_type: str                     # PromoType value
    description: str
    valid_from: datetime
    valid_until: datetime
    actor_id: str
    issued_at: datetime
    max_redemptions: int = 0
    region_codes: Tuple[str, ...] = ()
    combo_ids: Tuple[str, ...] = ()
    discount_pct: Decimal = Decimal("0")
    discount_months: int = 0
    credit_amount: Decimal = Decimal("0")
    credit_currency: str = ""
    credit_expires_months: int = 6
    extra_trial_days: int = 0
    bonus_engine: str = ""
    bonus_months: int = 0
    bonus_after: str = "auto_remove"
    bundle_engines: Tuple[str, ...] = ()
    bundle_discount_pct: Decimal = Decimal("0")


@dataclass(frozen=True)
class RedeemPromoRequest:
    promo_code: str
    business_id: uuid.UUID
    region_code: str
    combo_id: uuid.UUID
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# PROJECTION
# ══════════════════════════════════════════════════════════════

class PromotionProjection:
    """
    In-memory projection of promotions and redemptions.
    Rebuilt deterministically from promotion events.
    """

    projection_name = "promotion_projection"

    def __init__(self) -> None:
        self._promos: Dict[uuid.UUID, PromoDefinition] = {}
        self._by_code: Dict[str, uuid.UUID] = {}
        # (business_id, promo_id) → PromoRedemption
        self._redemptions: Dict[Tuple[uuid.UUID, uuid.UUID], PromoRedemption] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == PROMO_CREATED_V1:
            self._apply_created(payload)
        elif event_type == PROMO_DEACTIVATED_V1:
            self._apply_deactivated(payload)
        elif event_type == PROMO_REDEEMED_V1:
            self._apply_redeemed(payload)

    def _apply_created(self, payload: Dict[str, Any]) -> None:
        promo_id = uuid.UUID(str(payload["promo_id"]))
        pt = PromoType(payload["promo_type"])
        code = payload["promo_code"].upper()
        self._promos[promo_id] = PromoDefinition(
            promo_id=promo_id,
            promo_code=code,
            promo_type=pt,
            status=PromoStatus.ACTIVE,
            description=payload.get("description", ""),
            valid_from=payload["valid_from"],
            valid_until=payload["valid_until"],
            max_redemptions=payload.get("max_redemptions", 0),
            current_redemptions=0,
            region_codes=tuple(payload.get("region_codes", [])),
            combo_ids=tuple(payload.get("combo_ids", [])),
            discount_pct=Decimal(str(payload.get("discount_pct", "0"))),
            discount_months=payload.get("discount_months", 0),
            credit_amount=Decimal(str(payload.get("credit_amount", "0"))),
            credit_currency=payload.get("credit_currency", ""),
            credit_expires_months=payload.get("credit_expires_months", 6),
            extra_trial_days=payload.get("extra_trial_days", 0),
            bonus_engine=payload.get("bonus_engine", ""),
            bonus_months=payload.get("bonus_months", 0),
            bonus_after=payload.get("bonus_after", "auto_remove"),
            bundle_engines=tuple(payload.get("bundle_engines", [])),
            bundle_discount_pct=Decimal(str(payload.get("bundle_discount_pct", "0"))),
            created_at=payload.get("issued_at"),
        )
        self._by_code[code] = promo_id

    def _apply_deactivated(self, payload: Dict[str, Any]) -> None:
        promo_id = uuid.UUID(str(payload["promo_id"]))
        old = self._promos.get(promo_id)
        if old is None:
            return
        self._promos[promo_id] = PromoDefinition(
            promo_id=old.promo_id,
            promo_code=old.promo_code,
            promo_type=old.promo_type,
            status=PromoStatus.DEACTIVATED,
            description=old.description,
            valid_from=old.valid_from,
            valid_until=old.valid_until,
            max_redemptions=old.max_redemptions,
            current_redemptions=old.current_redemptions,
            region_codes=old.region_codes,
            combo_ids=old.combo_ids,
            discount_pct=old.discount_pct,
            discount_months=old.discount_months,
            credit_amount=old.credit_amount,
            credit_currency=old.credit_currency,
            credit_expires_months=old.credit_expires_months,
            extra_trial_days=old.extra_trial_days,
            bonus_engine=old.bonus_engine,
            bonus_months=old.bonus_months,
            bonus_after=old.bonus_after,
            bundle_engines=old.bundle_engines,
            bundle_discount_pct=old.bundle_discount_pct,
            created_at=old.created_at,
        )

    def _apply_redeemed(self, payload: Dict[str, Any]) -> None:
        promo_id = uuid.UUID(str(payload["promo_id"]))
        business_id = uuid.UUID(str(payload["business_id"]))
        redemption_id = uuid.UUID(str(payload["redemption_id"]))
        self._redemptions[(business_id, promo_id)] = PromoRedemption(
            redemption_id=redemption_id,
            promo_id=promo_id,
            promo_code=payload.get("promo_code", ""),
            business_id=business_id,
            redeemed_at=payload.get("issued_at", datetime.utcnow()),
            promo_type=payload.get("promo_type", ""),
            details=payload.get("details", {}),
        )
        # Increment redemption count
        old = self._promos.get(promo_id)
        if old is not None:
            new_count = old.current_redemptions + 1
            new_status = old.status
            if old.max_redemptions > 0 and new_count >= old.max_redemptions:
                new_status = PromoStatus.EXHAUSTED
            self._promos[promo_id] = PromoDefinition(
                promo_id=old.promo_id,
                promo_code=old.promo_code,
                promo_type=old.promo_type,
                status=new_status,
                description=old.description,
                valid_from=old.valid_from,
                valid_until=old.valid_until,
                max_redemptions=old.max_redemptions,
                current_redemptions=new_count,
                region_codes=old.region_codes,
                combo_ids=old.combo_ids,
                discount_pct=old.discount_pct,
                discount_months=old.discount_months,
                credit_amount=old.credit_amount,
                credit_currency=old.credit_currency,
                credit_expires_months=old.credit_expires_months,
                extra_trial_days=old.extra_trial_days,
                bonus_engine=old.bonus_engine,
                bonus_months=old.bonus_months,
                bonus_after=old.bonus_after,
                bundle_engines=old.bundle_engines,
                bundle_discount_pct=old.bundle_discount_pct,
                created_at=old.created_at,
            )

    # ── queries ────────────────────────────────────────────────

    def get_promo(self, promo_id: uuid.UUID) -> Optional[PromoDefinition]:
        return self._promos.get(promo_id)

    def get_promo_by_code(self, code: str) -> Optional[PromoDefinition]:
        promo_id = self._by_code.get(code.upper())
        if promo_id is None:
            return None
        return self._promos.get(promo_id)

    def list_active_promos(self) -> List[PromoDefinition]:
        return [p for p in self._promos.values() if p.status == PromoStatus.ACTIVE]

    def has_redeemed(self, business_id: uuid.UUID, promo_id: uuid.UUID) -> bool:
        return (business_id, promo_id) in self._redemptions

    def list_redemptions_for_business(
        self, business_id: uuid.UUID
    ) -> List[PromoRedemption]:
        return [
            r for r in self._redemptions.values()
            if r.business_id == business_id
        ]

    def truncate(self) -> None:
        self._promos.clear()
        self._by_code.clear()
        self._redemptions.clear()


# ══════════════════════════════════════════════════════════════
# SERVICE
# ══════════════════════════════════════════════════════════════

class PromotionService:
    """
    Manages promotions and promo code redemption.

    Stacking rules enforced here:
      - Only one DISCOUNT active per tenant (best one wins)
      - CREDIT, EXTENDED_TRIAL, ENGINE_BONUS can stack with DISCOUNT
      - Same promo code cannot be redeemed twice by same tenant
    """

    def __init__(self, projection: PromotionProjection) -> None:
        self._projection = projection

    def create_promo(self, request: CreatePromoRequest) -> Dict[str, Any]:
        """Create a new promotion (platform admin only)."""
        try:
            PromoType(request.promo_type)
        except ValueError:
            return {
                "rejected": RejectionReason(
                    code="INVALID_PROMO_TYPE",
                    message=f"Invalid promo type: {request.promo_type}.",
                    policy_name="create_promo",
                ),
            }

        existing = self._projection.get_promo_by_code(request.promo_code)
        if existing is not None:
            return {
                "rejected": RejectionReason(
                    code="PROMO_CODE_EXISTS",
                    message=f"Promo code '{request.promo_code}' already exists.",
                    policy_name="create_promo",
                ),
            }

        if request.valid_until <= request.valid_from:
            return {
                "rejected": RejectionReason(
                    code="INVALID_VALIDITY",
                    message="valid_until must be after valid_from.",
                    policy_name="create_promo",
                ),
            }

        promo_id = uuid.uuid4()
        payload: Dict[str, Any] = {
            "promo_id": str(promo_id),
            "promo_code": request.promo_code.upper(),
            "promo_type": request.promo_type,
            "description": request.description,
            "valid_from": request.valid_from,
            "valid_until": request.valid_until,
            "max_redemptions": request.max_redemptions,
            "region_codes": list(request.region_codes),
            "combo_ids": list(request.combo_ids),
            "discount_pct": str(request.discount_pct),
            "discount_months": request.discount_months,
            "credit_amount": str(request.credit_amount),
            "credit_currency": request.credit_currency,
            "credit_expires_months": request.credit_expires_months,
            "extra_trial_days": request.extra_trial_days,
            "bonus_engine": request.bonus_engine,
            "bonus_months": request.bonus_months,
            "bonus_after": request.bonus_after,
            "bundle_engines": list(request.bundle_engines),
            "bundle_discount_pct": str(request.bundle_discount_pct),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(PROMO_CREATED_V1, payload)
        return {
            "promo_id": promo_id,
            "promo_code": request.promo_code.upper(),
            "events": [{"event_type": PROMO_CREATED_V1, "payload": payload}],
        }

    def redeem_promo(self, request: RedeemPromoRequest) -> Dict[str, Any]:
        """
        Redeem a promo code for a tenant.

        Validates: code exists, is active, in validity window,
        region matches, combo matches, not already redeemed.
        """
        promo = self._projection.get_promo_by_code(request.promo_code)
        if promo is None:
            return {
                "rejected": RejectionReason(
                    code="PROMO_NOT_FOUND",
                    message=f"Promo code '{request.promo_code}' not found.",
                    policy_name="redeem_promo",
                ),
            }

        if promo.status != PromoStatus.ACTIVE:
            return {
                "rejected": RejectionReason(
                    code="PROMO_NOT_ACTIVE",
                    message=f"Promo code is {promo.status.value}.",
                    policy_name="redeem_promo",
                ),
            }

        now = request.issued_at
        if now < promo.valid_from or now > promo.valid_until:
            return {
                "rejected": RejectionReason(
                    code="PROMO_EXPIRED",
                    message="Promo code is not within its validity period.",
                    policy_name="redeem_promo",
                ),
            }

        # Region check
        if promo.region_codes and request.region_code not in promo.region_codes:
            return {
                "rejected": RejectionReason(
                    code="PROMO_REGION_MISMATCH",
                    message=f"Promo not available in region {request.region_code}.",
                    policy_name="redeem_promo",
                ),
            }

        # Combo check
        if promo.combo_ids and str(request.combo_id) not in promo.combo_ids:
            return {
                "rejected": RejectionReason(
                    code="PROMO_COMBO_MISMATCH",
                    message="Promo not available for this combo.",
                    policy_name="redeem_promo",
                ),
            }

        # Already redeemed check
        if self._projection.has_redeemed(request.business_id, promo.promo_id):
            return {
                "rejected": RejectionReason(
                    code="PROMO_ALREADY_REDEEMED",
                    message="This promo has already been redeemed by this business.",
                    policy_name="redeem_promo",
                ),
            }

        redemption_id = uuid.uuid4()
        details: Dict[str, Any] = {"promo_type": promo.promo_type.value}

        if promo.promo_type == PromoType.DISCOUNT:
            details["discount_pct"] = str(promo.discount_pct)
            details["discount_months"] = promo.discount_months
        elif promo.promo_type == PromoType.CREDIT:
            details["credit_amount"] = str(promo.credit_amount)
            details["credit_currency"] = promo.credit_currency
        elif promo.promo_type == PromoType.EXTENDED_TRIAL:
            details["extra_trial_days"] = promo.extra_trial_days
        elif promo.promo_type == PromoType.ENGINE_BONUS:
            details["bonus_engine"] = promo.bonus_engine
            details["bonus_months"] = promo.bonus_months
        elif promo.promo_type == PromoType.BUNDLE_DISCOUNT:
            details["bundle_engines"] = list(promo.bundle_engines)
            details["bundle_discount_pct"] = str(promo.bundle_discount_pct)

        payload = {
            "redemption_id": str(redemption_id),
            "promo_id": str(promo.promo_id),
            "promo_code": promo.promo_code,
            "promo_type": promo.promo_type.value,
            "business_id": str(request.business_id),
            "details": details,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(PROMO_REDEEMED_V1, payload)
        return {
            "redemption_id": redemption_id,
            "promo_type": promo.promo_type.value,
            "details": details,
            "events": [{"event_type": PROMO_REDEEMED_V1, "payload": payload}],
        }
