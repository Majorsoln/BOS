"""
BOS SaaS — Referral Program ("Alika Rafiki")
================================================
Event-sourced referral tracking with qualification
rules and anti-fraud protections.

How it works:
  1. Every tenant gets a unique referral_code.
  2. New signups can enter a referral code during onboarding.
  3. Referrer is rewarded ONLY after referee qualifies
     (30 days active + ≥10 transactions).
  4. Referrer gets: 30 free days per qualified referral.
  5. Referee gets: extended trial (e.g. +30 days on top of default).

Anti-fraud:
  - Max 12 referrals per year per referrer.
  - Referee must be unique by phone/email.
  - Self-referral (same phone/device) → rejected.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# EVENT TYPES
# ══════════════════════════════════════════════════════════════

REFERRAL_POLICY_SET_V1 = "saas.referral_policy.set.v1"
REFERRAL_CODE_GENERATED_V1 = "saas.referral_code.generated.v1"
REFERRAL_SUBMITTED_V1 = "saas.referral.submitted.v1"
REFERRAL_QUALIFIED_V1 = "saas.referral.qualified.v1"
REFERRAL_REWARDED_V1 = "saas.referral.rewarded.v1"
REFERRAL_REJECTED_V1 = "saas.referral.rejected.v1"

REFERRAL_EVENT_TYPES = (
    REFERRAL_POLICY_SET_V1,
    REFERRAL_CODE_GENERATED_V1,
    REFERRAL_SUBMITTED_V1,
    REFERRAL_QUALIFIED_V1,
    REFERRAL_REWARDED_V1,
    REFERRAL_REJECTED_V1,
)


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class ReferralStatus(Enum):
    PENDING = "PENDING"             # referee signed up, not yet qualified
    QUALIFIED = "QUALIFIED"         # referee met activity threshold
    REWARDED = "REWARDED"           # referrer received their reward
    REJECTED = "REJECTED"           # fraud detected or referee churned


# ══════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ReferralPolicy:
    """Platform-wide referral program configuration."""
    referrer_reward_days: int           # free days per qualified referral
    referee_bonus_days: int             # extra trial days for referee
    qualification_days: int             # days referee must be active
    qualification_min_transactions: int # minimum transactions
    max_referrals_per_year: int         # anti-fraud cap per referrer
    champion_threshold: int             # referrals for "BOS Champion" badge
    version: str
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class ReferralCode:
    """A tenant's unique referral code."""
    business_id: uuid.UUID
    code: str                           # e.g. "BOS-MAMA-MBOGA-7X3K"
    created_at: datetime


@dataclass(frozen=True)
class ReferralRecord:
    """Tracks one referral from submission to reward."""
    referral_id: uuid.UUID
    referrer_business_id: uuid.UUID     # who referred
    referee_business_id: uuid.UUID      # who was referred
    referral_code: str
    status: ReferralStatus
    submitted_at: datetime
    qualified_at: Optional[datetime] = None
    rewarded_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: str = ""


# ══════════════════════════════════════════════════════════════
# REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SetReferralPolicyRequest:
    referrer_reward_days: int
    referee_bonus_days: int
    qualification_days: int
    qualification_min_transactions: int
    max_referrals_per_year: int
    champion_threshold: int
    version: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class GenerateReferralCodeRequest:
    business_id: uuid.UUID
    business_name: str                  # used to generate readable code
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class SubmitReferralRequest:
    """A new signup entering a referral code."""
    referral_code: str
    referee_business_id: uuid.UUID
    referee_phone: str                  # for uniqueness check
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class QualifyReferralRequest:
    """Mark a referral as qualified (referee met activity threshold)."""
    referee_business_id: uuid.UUID
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# PROJECTION
# ══════════════════════════════════════════════════════════════

class ReferralProjection:
    """In-memory projection of referral program state."""

    projection_name = "referral_projection"

    def __init__(self) -> None:
        self._policy: Optional[ReferralPolicy] = None
        # business_id → ReferralCode
        self._codes: Dict[uuid.UUID, ReferralCode] = {}
        # code string → business_id
        self._code_lookup: Dict[str, uuid.UUID] = {}
        # referral_id → ReferralRecord
        self._referrals: Dict[uuid.UUID, ReferralRecord] = {}
        # referee_business_id → referral_id (one referral per referee)
        self._referee_index: Dict[uuid.UUID, uuid.UUID] = {}
        # referrer_business_id → list of referral_ids
        self._referrer_index: Dict[uuid.UUID, List[uuid.UUID]] = {}
        # phone hash → business_id (anti-fraud)
        self._phone_index: Dict[str, uuid.UUID] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == REFERRAL_POLICY_SET_V1:
            self._apply_policy(payload)
        elif event_type == REFERRAL_CODE_GENERATED_V1:
            self._apply_code_generated(payload)
        elif event_type == REFERRAL_SUBMITTED_V1:
            self._apply_submitted(payload)
        elif event_type == REFERRAL_QUALIFIED_V1:
            self._apply_qualified(payload)
        elif event_type == REFERRAL_REWARDED_V1:
            self._apply_rewarded(payload)
        elif event_type == REFERRAL_REJECTED_V1:
            self._apply_rejected(payload)

    def _apply_policy(self, payload: Dict[str, Any]) -> None:
        self._policy = ReferralPolicy(
            referrer_reward_days=payload["referrer_reward_days"],
            referee_bonus_days=payload["referee_bonus_days"],
            qualification_days=payload.get("qualification_days", 30),
            qualification_min_transactions=payload.get("qualification_min_transactions", 10),
            max_referrals_per_year=payload.get("max_referrals_per_year", 12),
            champion_threshold=payload.get("champion_threshold", 10),
            version=payload.get("version", "v1"),
            updated_at=payload.get("issued_at"),
        )

    def _apply_code_generated(self, payload: Dict[str, Any]) -> None:
        biz_id = uuid.UUID(str(payload["business_id"]))
        code = payload["code"]
        self._codes[biz_id] = ReferralCode(
            business_id=biz_id,
            code=code,
            created_at=payload.get("issued_at", datetime.utcnow()),
        )
        self._code_lookup[code] = biz_id

    def _apply_submitted(self, payload: Dict[str, Any]) -> None:
        ref_id = uuid.UUID(str(payload["referral_id"]))
        referrer_id = uuid.UUID(str(payload["referrer_business_id"]))
        referee_id = uuid.UUID(str(payload["referee_business_id"]))
        record = ReferralRecord(
            referral_id=ref_id,
            referrer_business_id=referrer_id,
            referee_business_id=referee_id,
            referral_code=payload.get("referral_code", ""),
            status=ReferralStatus.PENDING,
            submitted_at=payload.get("issued_at", datetime.utcnow()),
        )
        self._referrals[ref_id] = record
        self._referee_index[referee_id] = ref_id
        self._referrer_index.setdefault(referrer_id, []).append(ref_id)
        phone_hash = payload.get("referee_phone_hash", "")
        if phone_hash:
            self._phone_index[phone_hash] = referee_id

    def _apply_qualified(self, payload: Dict[str, Any]) -> None:
        referee_id = uuid.UUID(str(payload["referee_business_id"]))
        ref_id = self._referee_index.get(referee_id)
        if ref_id is None:
            return
        old = self._referrals.get(ref_id)
        if old is None:
            return
        self._referrals[ref_id] = ReferralRecord(
            referral_id=old.referral_id,
            referrer_business_id=old.referrer_business_id,
            referee_business_id=old.referee_business_id,
            referral_code=old.referral_code,
            status=ReferralStatus.QUALIFIED,
            submitted_at=old.submitted_at,
            qualified_at=payload.get("issued_at"),
        )

    def _apply_rewarded(self, payload: Dict[str, Any]) -> None:
        ref_id = uuid.UUID(str(payload["referral_id"]))
        old = self._referrals.get(ref_id)
        if old is None:
            return
        self._referrals[ref_id] = ReferralRecord(
            referral_id=old.referral_id,
            referrer_business_id=old.referrer_business_id,
            referee_business_id=old.referee_business_id,
            referral_code=old.referral_code,
            status=ReferralStatus.REWARDED,
            submitted_at=old.submitted_at,
            qualified_at=old.qualified_at,
            rewarded_at=payload.get("issued_at"),
        )

    def _apply_rejected(self, payload: Dict[str, Any]) -> None:
        ref_id = uuid.UUID(str(payload["referral_id"]))
        old = self._referrals.get(ref_id)
        if old is None:
            return
        self._referrals[ref_id] = ReferralRecord(
            referral_id=old.referral_id,
            referrer_business_id=old.referrer_business_id,
            referee_business_id=old.referee_business_id,
            referral_code=old.referral_code,
            status=ReferralStatus.REJECTED,
            submitted_at=old.submitted_at,
            rejected_at=payload.get("issued_at"),
            rejection_reason=payload.get("reason", ""),
        )

    # ── queries ────────────────────────────────────────────────

    def get_policy(self) -> Optional[ReferralPolicy]:
        return self._policy

    def get_code(self, business_id: uuid.UUID) -> Optional[ReferralCode]:
        return self._codes.get(business_id)

    def resolve_referrer(self, code: str) -> Optional[uuid.UUID]:
        """Look up which business owns a referral code."""
        return self._code_lookup.get(code)

    def get_referral_for_referee(
        self, referee_business_id: uuid.UUID
    ) -> Optional[ReferralRecord]:
        ref_id = self._referee_index.get(referee_business_id)
        if ref_id is None:
            return None
        return self._referrals.get(ref_id)

    def count_referrals_this_year(
        self, referrer_business_id: uuid.UUID, year: int
    ) -> int:
        ref_ids = self._referrer_index.get(referrer_business_id, [])
        count = 0
        for rid in ref_ids:
            rec = self._referrals.get(rid)
            if rec and rec.submitted_at.year == year:
                count += 1
        return count

    def count_qualified_referrals(
        self, referrer_business_id: uuid.UUID
    ) -> int:
        ref_ids = self._referrer_index.get(referrer_business_id, [])
        return sum(
            1 for rid in ref_ids
            if self._referrals.get(rid) and self._referrals[rid].status in (
                ReferralStatus.QUALIFIED, ReferralStatus.REWARDED
            )
        )

    def is_champion(self, referrer_business_id: uuid.UUID) -> bool:
        threshold = self._policy.champion_threshold if self._policy else 10
        return self.count_qualified_referrals(referrer_business_id) >= threshold

    def is_phone_used(self, phone_hash: str) -> bool:
        return phone_hash in self._phone_index

    def truncate(self) -> None:
        self._policy = None
        self._codes.clear()
        self._code_lookup.clear()
        self._referrals.clear()
        self._referee_index.clear()
        self._referrer_index.clear()
        self._phone_index.clear()


# ══════════════════════════════════════════════════════════════
# SERVICE
# ══════════════════════════════════════════════════════════════

class ReferralService:
    """
    Manages the referral program lifecycle.

    Core rules:
    - Referrer is only rewarded after referee qualifies
    - Max referrals per year enforced (anti-fraud)
    - Same phone/email can't be used twice (uniqueness)
    """

    def __init__(self, projection: ReferralProjection) -> None:
        self._projection = projection

    @staticmethod
    def _hash_phone(phone: str) -> str:
        """One-way hash for phone uniqueness without storing raw phone."""
        normalised = phone.strip().replace(" ", "").replace("-", "")
        return hashlib.sha256(normalised.encode()).hexdigest()[:16]

    @staticmethod
    def _generate_code(business_name: str) -> str:
        """Generate a human-readable referral code from business name."""
        # Take first word, uppercase, max 10 chars
        words = business_name.strip().upper().split()
        name_part = words[0][:10] if words else "BOS"
        # Add random suffix
        suffix = uuid.uuid4().hex[:4].upper()
        return f"BOS-{name_part}-{suffix}"

    def set_policy(self, request: SetReferralPolicyRequest) -> Dict[str, Any]:
        payload = {
            "referrer_reward_days": request.referrer_reward_days,
            "referee_bonus_days": request.referee_bonus_days,
            "qualification_days": request.qualification_days,
            "qualification_min_transactions": request.qualification_min_transactions,
            "max_referrals_per_year": request.max_referrals_per_year,
            "champion_threshold": request.champion_threshold,
            "version": request.version,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(REFERRAL_POLICY_SET_V1, payload)
        return {
            "events": [{"event_type": REFERRAL_POLICY_SET_V1, "payload": payload}],
        }

    def generate_code(
        self, request: GenerateReferralCodeRequest
    ) -> Dict[str, Any]:
        """Generate a unique referral code for a tenant."""
        existing = self._projection.get_code(request.business_id)
        if existing is not None:
            return {"code": existing.code, "events": []}

        code = self._generate_code(request.business_name)
        # Ensure uniqueness
        while self._projection.resolve_referrer(code) is not None:
            code = self._generate_code(request.business_name)

        payload = {
            "business_id": str(request.business_id),
            "code": code,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(REFERRAL_CODE_GENERATED_V1, payload)
        return {
            "code": code,
            "events": [{"event_type": REFERRAL_CODE_GENERATED_V1, "payload": payload}],
        }

    def submit_referral(
        self, request: SubmitReferralRequest
    ) -> Dict[str, Any]:
        """Submit a referral during new tenant signup."""
        referrer_id = self._projection.resolve_referrer(request.referral_code)
        if referrer_id is None:
            return {
                "rejected": RejectionReason(
                    code="INVALID_REFERRAL_CODE",
                    message="Referral code not found.",
                    policy_name="submit_referral",
                ),
            }

        # Self-referral check
        if referrer_id == request.referee_business_id:
            return {
                "rejected": RejectionReason(
                    code="SELF_REFERRAL",
                    message="Cannot refer yourself.",
                    policy_name="submit_referral",
                ),
            }

        # Phone uniqueness check
        phone_hash = self._hash_phone(request.referee_phone)
        if self._projection.is_phone_used(phone_hash):
            return {
                "rejected": RejectionReason(
                    code="PHONE_ALREADY_REFERRED",
                    message="This phone number has already been used for a referral.",
                    policy_name="submit_referral",
                ),
            }

        # Annual cap check
        policy = self._projection.get_policy()
        max_per_year = policy.max_referrals_per_year if policy else 12
        year = request.issued_at.year
        count = self._projection.count_referrals_this_year(referrer_id, year)
        if count >= max_per_year:
            return {
                "rejected": RejectionReason(
                    code="REFERRAL_LIMIT_REACHED",
                    message=f"Referrer has reached the {max_per_year} referral limit for {year}.",
                    policy_name="submit_referral",
                ),
            }

        # Already referred check
        existing = self._projection.get_referral_for_referee(request.referee_business_id)
        if existing is not None:
            return {
                "rejected": RejectionReason(
                    code="ALREADY_REFERRED",
                    message="This business already has a referral on record.",
                    policy_name="submit_referral",
                ),
            }

        ref_id = uuid.uuid4()
        payload = {
            "referral_id": str(ref_id),
            "referrer_business_id": str(referrer_id),
            "referee_business_id": str(request.referee_business_id),
            "referral_code": request.referral_code,
            "referee_phone_hash": phone_hash,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(REFERRAL_SUBMITTED_V1, payload)

        # Return bonus days for the referee
        bonus_days = policy.referee_bonus_days if policy else 30
        return {
            "referral_id": ref_id,
            "referee_bonus_days": bonus_days,
            "events": [{"event_type": REFERRAL_SUBMITTED_V1, "payload": payload}],
        }

    def qualify_referral(
        self, request: QualifyReferralRequest
    ) -> Dict[str, Any]:
        """
        Mark a referral as qualified.

        Called by the system when referee meets activity threshold
        (e.g., 30 days active + ≥10 transactions).
        """
        record = self._projection.get_referral_for_referee(request.referee_business_id)
        if record is None:
            return {"qualified": False, "events": []}

        if record.status != ReferralStatus.PENDING:
            return {"qualified": False, "events": []}

        # Qualify
        qualify_payload = {
            "referee_business_id": str(request.referee_business_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(REFERRAL_QUALIFIED_V1, qualify_payload)
        events = [{"event_type": REFERRAL_QUALIFIED_V1, "payload": qualify_payload}]

        # Auto-reward referrer
        policy = self._projection.get_policy()
        reward_days = policy.referrer_reward_days if policy else 30
        reward_payload = {
            "referral_id": str(record.referral_id),
            "referrer_business_id": str(record.referrer_business_id),
            "reward_days": reward_days,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(REFERRAL_REWARDED_V1, reward_payload)
        events.append({"event_type": REFERRAL_REWARDED_V1, "payload": reward_payload})

        return {
            "qualified": True,
            "referrer_business_id": record.referrer_business_id,
            "reward_days": reward_days,
            "is_champion": self._projection.is_champion(record.referrer_business_id),
            "events": events,
        }
