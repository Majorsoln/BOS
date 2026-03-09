"""
BOS SaaS — Reseller Program ("Wakala wa BOS")
================================================
Event-sourced reseller management with tiered commissions
and payout tracking.

Tiers:
  BRONZE  (0-10 active tenants)   → 10% commission
  SILVER  (11-50 active tenants)  → 15% commission
  GOLD    (51+ active tenants)    → 20% commission

Rules:
  - Commission calculated on paying tenants only (not trial).
  - Churn clawback: if tenant churns within 90 days, commission reversed.
  - Payout via M-Pesa (KE), Mobile Money (TZ/UG), Bank Transfer.
  - Reseller provides first-line (L1) support for their tenants.
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

RESELLER_REGISTERED_V1 = "saas.reseller.registered.v1"
RESELLER_UPDATED_V1 = "saas.reseller.updated.v1"
RESELLER_SUSPENDED_V1 = "saas.reseller.suspended.v1"
RESELLER_REACTIVATED_V1 = "saas.reseller.reactivated.v1"
RESELLER_TERMINATED_V1 = "saas.reseller.terminated.v1"
RESELLER_TENANT_LINKED_V1 = "saas.reseller.tenant_linked.v1"
RESELLER_TENANT_UNLINKED_V1 = "saas.reseller.tenant_unlinked.v1"
RESELLER_COMMISSION_ACCRUED_V1 = "saas.reseller.commission_accrued.v1"
RESELLER_PAYOUT_REQUESTED_V1 = "saas.reseller.payout_requested.v1"
RESELLER_PAYOUT_COMPLETED_V1 = "saas.reseller.payout_completed.v1"
RESELLER_CLAWBACK_V1 = "saas.reseller.clawback.v1"

RESELLER_EVENT_TYPES = (
    RESELLER_REGISTERED_V1,
    RESELLER_UPDATED_V1,
    RESELLER_SUSPENDED_V1,
    RESELLER_REACTIVATED_V1,
    RESELLER_TERMINATED_V1,
    RESELLER_TENANT_LINKED_V1,
    RESELLER_TENANT_UNLINKED_V1,
    RESELLER_COMMISSION_ACCRUED_V1,
    RESELLER_PAYOUT_REQUESTED_V1,
    RESELLER_PAYOUT_COMPLETED_V1,
    RESELLER_CLAWBACK_V1,
)


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class ResellerTier(Enum):
    BRONZE = "BRONZE"       # 0-10 active tenants
    SILVER = "SILVER"       # 11-50 active tenants
    GOLD = "GOLD"           # 51+ active tenants


class ResellerStatus(Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class PayoutMethod(Enum):
    MPESA = "MPESA"
    MOBILE_MONEY = "MOBILE_MONEY"
    BANK_TRANSFER = "BANK_TRANSFER"


class PayoutStatus(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Tier thresholds and commission rates
TIER_CONFIG = {
    ResellerTier.BRONZE: {
        "min_tenants": 0,
        "max_tenants": 10,
        "commission_rate": Decimal("0.10"),     # 10%
        "payout_frequency": "MONTHLY",
    },
    ResellerTier.SILVER: {
        "min_tenants": 11,
        "max_tenants": 50,
        "commission_rate": Decimal("0.15"),     # 15%
        "payout_frequency": "MONTHLY",
    },
    ResellerTier.GOLD: {
        "min_tenants": 51,
        "max_tenants": 999999,
        "commission_rate": Decimal("0.20"),     # 20%
        "payout_frequency": "WEEKLY",
    },
}

# Churn clawback period (days)
CLAWBACK_PERIOD_DAYS = 90


# ══════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PayoutDetails:
    """How the reseller receives commission payouts."""
    method: PayoutMethod
    # M-Pesa / Mobile Money
    phone: str
    # Bank Transfer
    bank_name: str
    account_number: str
    account_name: str


@dataclass(frozen=True)
class ResellerRecord:
    """Immutable reseller state."""
    reseller_id: uuid.UUID
    company_name: str
    contact_person: str
    phone: str
    email: str
    region_codes: Tuple[str, ...]       # regions this reseller covers
    tier: ResellerTier
    status: ResellerStatus
    commission_rate: Decimal            # from tier
    payout_method: str                  # PayoutMethod value
    payout_phone: str
    payout_bank_name: str
    payout_account_number: str
    payout_account_name: str
    active_tenant_count: int
    total_commission_earned: Decimal     # lifetime
    total_commission_paid: Decimal
    pending_commission: Decimal          # earned - paid
    registered_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class ResellerTenantLink:
    """Record that a tenant was onboarded by this reseller."""
    reseller_id: uuid.UUID
    business_id: uuid.UUID
    linked_at: datetime
    is_active: bool = True


@dataclass(frozen=True)
class CommissionEntry:
    """One commission accrual or clawback."""
    entry_id: uuid.UUID
    reseller_id: uuid.UUID
    business_id: uuid.UUID
    amount: Decimal
    currency: str
    period: str                         # e.g. "2026-03" (month)
    is_clawback: bool
    recorded_at: datetime


@dataclass(frozen=True)
class PayoutRecord:
    """Record of a commission payout to a reseller."""
    payout_id: uuid.UUID
    reseller_id: uuid.UUID
    amount: Decimal
    currency: str
    status: PayoutStatus
    method: str
    requested_at: datetime
    completed_at: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RegisterResellerRequest:
    company_name: str
    contact_person: str
    phone: str
    email: str
    region_codes: Tuple[str, ...]
    payout_method: str
    payout_phone: str
    payout_bank_name: str
    payout_account_number: str
    payout_account_name: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class LinkTenantRequest:
    """Link a tenant to a reseller (reseller onboarded them)."""
    reseller_id: uuid.UUID
    business_id: uuid.UUID
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class AccrueCommissionRequest:
    """Record commission for a reseller on a paying tenant."""
    reseller_id: uuid.UUID
    business_id: uuid.UUID
    tenant_monthly_amount: Decimal
    currency: str
    period: str                         # e.g. "2026-03"
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class RequestPayoutRequest:
    reseller_id: uuid.UUID
    amount: Decimal
    currency: str
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# PROJECTION
# ══════════════════════════════════════════════════════════════

class ResellerProjection:
    """In-memory projection of reseller program state."""

    projection_name = "reseller_projection"

    def __init__(self) -> None:
        self._resellers: Dict[uuid.UUID, ResellerRecord] = {}
        # reseller_id → list of business_ids
        self._tenant_links: Dict[uuid.UUID, Dict[uuid.UUID, ResellerTenantLink]] = {}
        # commission entries
        self._commissions: List[CommissionEntry] = []
        # payout records
        self._payouts: Dict[uuid.UUID, PayoutRecord] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == RESELLER_REGISTERED_V1:
            self._apply_registered(payload)
        elif event_type == RESELLER_UPDATED_V1:
            self._apply_updated(payload)
        elif event_type == RESELLER_SUSPENDED_V1:
            self._apply_status_change(payload, ResellerStatus.SUSPENDED)
        elif event_type == RESELLER_REACTIVATED_V1:
            self._apply_status_change(payload, ResellerStatus.ACTIVE)
        elif event_type == RESELLER_TERMINATED_V1:
            self._apply_status_change(payload, ResellerStatus.TERMINATED)
        elif event_type == RESELLER_TENANT_LINKED_V1:
            self._apply_tenant_linked(payload)
        elif event_type == RESELLER_TENANT_UNLINKED_V1:
            self._apply_tenant_unlinked(payload)
        elif event_type == RESELLER_COMMISSION_ACCRUED_V1:
            self._apply_commission(payload, is_clawback=False)
        elif event_type == RESELLER_CLAWBACK_V1:
            self._apply_commission(payload, is_clawback=True)
        elif event_type == RESELLER_PAYOUT_REQUESTED_V1:
            self._apply_payout_requested(payload)
        elif event_type == RESELLER_PAYOUT_COMPLETED_V1:
            self._apply_payout_completed(payload)

    def _determine_tier(self, active_count: int) -> ResellerTier:
        for tier, config in TIER_CONFIG.items():
            if config["min_tenants"] <= active_count <= config["max_tenants"]:
                return tier
        return ResellerTier.GOLD

    def _apply_registered(self, payload: Dict[str, Any]) -> None:
        reseller_id = uuid.UUID(str(payload["reseller_id"]))
        tier = ResellerTier.BRONZE
        self._resellers[reseller_id] = ResellerRecord(
            reseller_id=reseller_id,
            company_name=payload["company_name"],
            contact_person=payload.get("contact_person", ""),
            phone=payload.get("phone", ""),
            email=payload.get("email", ""),
            region_codes=tuple(payload.get("region_codes", [])),
            tier=tier,
            status=ResellerStatus.ACTIVE,
            commission_rate=TIER_CONFIG[tier]["commission_rate"],
            payout_method=payload.get("payout_method", "MPESA"),
            payout_phone=payload.get("payout_phone", ""),
            payout_bank_name=payload.get("payout_bank_name", ""),
            payout_account_number=payload.get("payout_account_number", ""),
            payout_account_name=payload.get("payout_account_name", ""),
            active_tenant_count=0,
            total_commission_earned=Decimal("0"),
            total_commission_paid=Decimal("0"),
            pending_commission=Decimal("0"),
            registered_at=payload.get("issued_at"),
        )
        self._tenant_links[reseller_id] = {}

    def _apply_updated(self, payload: Dict[str, Any]) -> None:
        reseller_id = uuid.UUID(str(payload["reseller_id"]))
        old = self._resellers.get(reseller_id)
        if old is None:
            return
        self._resellers[reseller_id] = ResellerRecord(
            reseller_id=old.reseller_id,
            company_name=payload.get("company_name", old.company_name),
            contact_person=payload.get("contact_person", old.contact_person),
            phone=payload.get("phone", old.phone),
            email=payload.get("email", old.email),
            region_codes=tuple(payload.get("region_codes", old.region_codes)),
            tier=old.tier,
            status=old.status,
            commission_rate=old.commission_rate,
            payout_method=payload.get("payout_method", old.payout_method),
            payout_phone=payload.get("payout_phone", old.payout_phone),
            payout_bank_name=payload.get("payout_bank_name", old.payout_bank_name),
            payout_account_number=payload.get("payout_account_number", old.payout_account_number),
            payout_account_name=payload.get("payout_account_name", old.payout_account_name),
            active_tenant_count=old.active_tenant_count,
            total_commission_earned=old.total_commission_earned,
            total_commission_paid=old.total_commission_paid,
            pending_commission=old.pending_commission,
            registered_at=old.registered_at,
            updated_at=payload.get("issued_at"),
        )

    def _apply_status_change(
        self, payload: Dict[str, Any], new_status: ResellerStatus
    ) -> None:
        reseller_id = uuid.UUID(str(payload["reseller_id"]))
        old = self._resellers.get(reseller_id)
        if old is None:
            return
        self._resellers[reseller_id] = ResellerRecord(
            reseller_id=old.reseller_id,
            company_name=old.company_name,
            contact_person=old.contact_person,
            phone=old.phone,
            email=old.email,
            region_codes=old.region_codes,
            tier=old.tier,
            status=new_status,
            commission_rate=old.commission_rate,
            payout_method=old.payout_method,
            payout_phone=old.payout_phone,
            payout_bank_name=old.payout_bank_name,
            payout_account_number=old.payout_account_number,
            payout_account_name=old.payout_account_name,
            active_tenant_count=old.active_tenant_count,
            total_commission_earned=old.total_commission_earned,
            total_commission_paid=old.total_commission_paid,
            pending_commission=old.pending_commission,
            registered_at=old.registered_at,
            updated_at=payload.get("issued_at"),
        )

    def _apply_tenant_linked(self, payload: Dict[str, Any]) -> None:
        reseller_id = uuid.UUID(str(payload["reseller_id"]))
        business_id = uuid.UUID(str(payload["business_id"]))
        links = self._tenant_links.setdefault(reseller_id, {})
        links[business_id] = ResellerTenantLink(
            reseller_id=reseller_id,
            business_id=business_id,
            linked_at=payload.get("issued_at", datetime.utcnow()),
            is_active=True,
        )
        # Recalculate tier
        self._recalc_tier(reseller_id)

    def _apply_tenant_unlinked(self, payload: Dict[str, Any]) -> None:
        reseller_id = uuid.UUID(str(payload["reseller_id"]))
        business_id = uuid.UUID(str(payload["business_id"]))
        links = self._tenant_links.get(reseller_id, {})
        old_link = links.get(business_id)
        if old_link:
            links[business_id] = ResellerTenantLink(
                reseller_id=reseller_id,
                business_id=business_id,
                linked_at=old_link.linked_at,
                is_active=False,
            )
        self._recalc_tier(reseller_id)

    def _apply_commission(
        self, payload: Dict[str, Any], is_clawback: bool
    ) -> None:
        reseller_id = uuid.UUID(str(payload["reseller_id"]))
        business_id = uuid.UUID(str(payload["business_id"]))
        amount = Decimal(str(payload["amount"]))
        entry = CommissionEntry(
            entry_id=uuid.UUID(str(payload.get("entry_id", uuid.uuid4()))),
            reseller_id=reseller_id,
            business_id=business_id,
            amount=amount,
            currency=payload.get("currency", ""),
            period=payload.get("period", ""),
            is_clawback=is_clawback,
            recorded_at=payload.get("issued_at", datetime.utcnow()),
        )
        self._commissions.append(entry)

        old = self._resellers.get(reseller_id)
        if old is not None:
            if is_clawback:
                new_earned = old.total_commission_earned - amount
                new_pending = old.pending_commission - amount
            else:
                new_earned = old.total_commission_earned + amount
                new_pending = old.pending_commission + amount
            self._resellers[reseller_id] = ResellerRecord(
                reseller_id=old.reseller_id,
                company_name=old.company_name,
                contact_person=old.contact_person,
                phone=old.phone,
                email=old.email,
                region_codes=old.region_codes,
                tier=old.tier,
                status=old.status,
                commission_rate=old.commission_rate,
                payout_method=old.payout_method,
                payout_phone=old.payout_phone,
                payout_bank_name=old.payout_bank_name,
                payout_account_number=old.payout_account_number,
                payout_account_name=old.payout_account_name,
                active_tenant_count=old.active_tenant_count,
                total_commission_earned=new_earned,
                total_commission_paid=old.total_commission_paid,
                pending_commission=new_pending,
                registered_at=old.registered_at,
                updated_at=payload.get("issued_at"),
            )

    def _apply_payout_requested(self, payload: Dict[str, Any]) -> None:
        payout_id = uuid.UUID(str(payload["payout_id"]))
        self._payouts[payout_id] = PayoutRecord(
            payout_id=payout_id,
            reseller_id=uuid.UUID(str(payload["reseller_id"])),
            amount=Decimal(str(payload["amount"])),
            currency=payload.get("currency", ""),
            status=PayoutStatus.PENDING,
            method=payload.get("method", ""),
            requested_at=payload.get("issued_at", datetime.utcnow()),
        )

    def _apply_payout_completed(self, payload: Dict[str, Any]) -> None:
        payout_id = uuid.UUID(str(payload["payout_id"]))
        old = self._payouts.get(payout_id)
        if old is None:
            return
        self._payouts[payout_id] = PayoutRecord(
            payout_id=old.payout_id,
            reseller_id=old.reseller_id,
            amount=old.amount,
            currency=old.currency,
            status=PayoutStatus.COMPLETED,
            method=old.method,
            requested_at=old.requested_at,
            completed_at=payload.get("issued_at"),
        )
        # Update reseller's paid amount
        reseller = self._resellers.get(old.reseller_id)
        if reseller is not None:
            self._resellers[old.reseller_id] = ResellerRecord(
                reseller_id=reseller.reseller_id,
                company_name=reseller.company_name,
                contact_person=reseller.contact_person,
                phone=reseller.phone,
                email=reseller.email,
                region_codes=reseller.region_codes,
                tier=reseller.tier,
                status=reseller.status,
                commission_rate=reseller.commission_rate,
                payout_method=reseller.payout_method,
                payout_phone=reseller.payout_phone,
                payout_bank_name=reseller.payout_bank_name,
                payout_account_number=reseller.payout_account_number,
                payout_account_name=reseller.payout_account_name,
                active_tenant_count=reseller.active_tenant_count,
                total_commission_earned=reseller.total_commission_earned,
                total_commission_paid=reseller.total_commission_paid + old.amount,
                pending_commission=reseller.pending_commission - old.amount,
                registered_at=reseller.registered_at,
                updated_at=payload.get("issued_at"),
            )

    def _recalc_tier(self, reseller_id: uuid.UUID) -> None:
        """Recalculate tier based on active tenant count."""
        links = self._tenant_links.get(reseller_id, {})
        active = sum(1 for link in links.values() if link.is_active)
        new_tier = self._determine_tier(active)
        old = self._resellers.get(reseller_id)
        if old is None:
            return
        self._resellers[reseller_id] = ResellerRecord(
            reseller_id=old.reseller_id,
            company_name=old.company_name,
            contact_person=old.contact_person,
            phone=old.phone,
            email=old.email,
            region_codes=old.region_codes,
            tier=new_tier,
            status=old.status,
            commission_rate=TIER_CONFIG[new_tier]["commission_rate"],
            payout_method=old.payout_method,
            payout_phone=old.payout_phone,
            payout_bank_name=old.payout_bank_name,
            payout_account_number=old.payout_account_number,
            payout_account_name=old.payout_account_name,
            active_tenant_count=active,
            total_commission_earned=old.total_commission_earned,
            total_commission_paid=old.total_commission_paid,
            pending_commission=old.pending_commission,
            registered_at=old.registered_at,
            updated_at=old.updated_at,
        )

    # ── queries ────────────────────────────────────────────────

    def get_reseller(self, reseller_id: uuid.UUID) -> Optional[ResellerRecord]:
        return self._resellers.get(reseller_id)

    def list_resellers(
        self, active_only: bool = True
    ) -> List[ResellerRecord]:
        resellers = list(self._resellers.values())
        if active_only:
            resellers = [r for r in resellers if r.status == ResellerStatus.ACTIVE]
        return resellers

    def get_reseller_for_tenant(
        self, business_id: uuid.UUID
    ) -> Optional[uuid.UUID]:
        """Find which reseller onboarded a given tenant."""
        for reseller_id, links in self._tenant_links.items():
            link = links.get(business_id)
            if link and link.is_active:
                return reseller_id
        return None

    def get_tenant_links(
        self, reseller_id: uuid.UUID
    ) -> List[ResellerTenantLink]:
        links = self._tenant_links.get(reseller_id, {})
        return list(links.values())

    def get_commissions(
        self, reseller_id: uuid.UUID, period: Optional[str] = None
    ) -> List[CommissionEntry]:
        result = [c for c in self._commissions if c.reseller_id == reseller_id]
        if period:
            result = [c for c in result if c.period == period]
        return result

    def get_payouts(self, reseller_id: uuid.UUID) -> List[PayoutRecord]:
        return [p for p in self._payouts.values() if p.reseller_id == reseller_id]

    def truncate(self) -> None:
        self._resellers.clear()
        self._tenant_links.clear()
        self._commissions.clear()
        self._payouts.clear()


# ══════════════════════════════════════════════════════════════
# SERVICE
# ══════════════════════════════════════════════════════════════

class ResellerService:
    """
    Manages the reseller program.

    Core rules:
    - Tier auto-upgrades/downgrades based on active tenant count.
    - Commission = tenant_monthly_amount × reseller_commission_rate.
    - Clawback if tenant churns within 90 days of onboarding.
    - Payouts processed via configured method (M-Pesa, bank, etc.).
    """

    def __init__(self, projection: ResellerProjection) -> None:
        self._projection = projection

    def register_reseller(
        self, request: RegisterResellerRequest
    ) -> Dict[str, Any]:
        """Register a new reseller."""
        reseller_id = uuid.uuid4()
        payload = {
            "reseller_id": str(reseller_id),
            "company_name": request.company_name,
            "contact_person": request.contact_person,
            "phone": request.phone,
            "email": request.email,
            "region_codes": list(request.region_codes),
            "payout_method": request.payout_method,
            "payout_phone": request.payout_phone,
            "payout_bank_name": request.payout_bank_name,
            "payout_account_number": request.payout_account_number,
            "payout_account_name": request.payout_account_name,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(RESELLER_REGISTERED_V1, payload)
        return {
            "reseller_id": reseller_id,
            "tier": ResellerTier.BRONZE.value,
            "commission_rate": str(TIER_CONFIG[ResellerTier.BRONZE]["commission_rate"]),
            "events": [{"event_type": RESELLER_REGISTERED_V1, "payload": payload}],
        }

    def link_tenant(self, request: LinkTenantRequest) -> Dict[str, Any]:
        """Link a tenant to a reseller (reseller onboarded them)."""
        reseller = self._projection.get_reseller(request.reseller_id)
        if reseller is None:
            return {
                "rejected": RejectionReason(
                    code="RESELLER_NOT_FOUND",
                    message="Reseller not found.",
                    policy_name="link_tenant",
                ),
            }
        if reseller.status != ResellerStatus.ACTIVE:
            return {
                "rejected": RejectionReason(
                    code="RESELLER_NOT_ACTIVE",
                    message=f"Reseller is {reseller.status.value}.",
                    policy_name="link_tenant",
                ),
            }

        # Check if tenant already linked to another reseller
        existing = self._projection.get_reseller_for_tenant(request.business_id)
        if existing is not None and existing != request.reseller_id:
            return {
                "rejected": RejectionReason(
                    code="TENANT_ALREADY_LINKED",
                    message="Tenant is already linked to another reseller.",
                    policy_name="link_tenant",
                ),
            }

        payload = {
            "reseller_id": str(request.reseller_id),
            "business_id": str(request.business_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(RESELLER_TENANT_LINKED_V1, payload)
        reseller = self._projection.get_reseller(request.reseller_id)
        return {
            "new_tier": reseller.tier.value if reseller else "BRONZE",
            "active_tenant_count": reseller.active_tenant_count if reseller else 0,
            "events": [{"event_type": RESELLER_TENANT_LINKED_V1, "payload": payload}],
        }

    def accrue_commission(
        self, request: AccrueCommissionRequest
    ) -> Dict[str, Any]:
        """Calculate and record commission for a paying tenant."""
        reseller = self._projection.get_reseller(request.reseller_id)
        if reseller is None or reseller.status != ResellerStatus.ACTIVE:
            return {"accrued": False, "events": []}

        commission = request.tenant_monthly_amount * reseller.commission_rate
        entry_id = uuid.uuid4()
        payload = {
            "entry_id": str(entry_id),
            "reseller_id": str(request.reseller_id),
            "business_id": str(request.business_id),
            "amount": str(commission),
            "currency": request.currency,
            "period": request.period,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(RESELLER_COMMISSION_ACCRUED_V1, payload)
        return {
            "accrued": True,
            "commission": str(commission),
            "rate": str(reseller.commission_rate),
            "events": [{"event_type": RESELLER_COMMISSION_ACCRUED_V1, "payload": payload}],
        }

    def clawback_commission(
        self,
        reseller_id: uuid.UUID,
        business_id: uuid.UUID,
        amount: Decimal,
        currency: str,
        reason: str,
        actor_id: str,
        issued_at: datetime,
    ) -> Dict[str, Any]:
        """Reverse commission when tenant churns within clawback period."""
        entry_id = uuid.uuid4()
        payload = {
            "entry_id": str(entry_id),
            "reseller_id": str(reseller_id),
            "business_id": str(business_id),
            "amount": str(amount),
            "currency": currency,
            "reason": reason,
            "period": "",
            "actor_id": actor_id,
            "issued_at": issued_at,
        }
        self._projection.apply(RESELLER_CLAWBACK_V1, payload)
        return {
            "clawback_amount": str(amount),
            "events": [{"event_type": RESELLER_CLAWBACK_V1, "payload": payload}],
        }

    def request_payout(
        self, request: RequestPayoutRequest
    ) -> Dict[str, Any]:
        """Request a commission payout."""
        reseller = self._projection.get_reseller(request.reseller_id)
        if reseller is None:
            return {
                "rejected": RejectionReason(
                    code="RESELLER_NOT_FOUND",
                    message="Reseller not found.",
                    policy_name="request_payout",
                ),
            }
        if request.amount > reseller.pending_commission:
            return {
                "rejected": RejectionReason(
                    code="INSUFFICIENT_BALANCE",
                    message=f"Requested {request.amount} but only {reseller.pending_commission} available.",
                    policy_name="request_payout",
                ),
            }

        payout_id = uuid.uuid4()
        payload = {
            "payout_id": str(payout_id),
            "reseller_id": str(request.reseller_id),
            "amount": str(request.amount),
            "currency": request.currency,
            "method": reseller.payout_method,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(RESELLER_PAYOUT_REQUESTED_V1, payload)
        return {
            "payout_id": payout_id,
            "events": [{"event_type": RESELLER_PAYOUT_REQUESTED_V1, "payload": payload}],
        }
