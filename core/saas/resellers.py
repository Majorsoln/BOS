"""
BOS SaaS — Reseller Program ("Wakala wa BOS")
================================================
Event-sourced reseller management with tiered commissions,
regional hierarchy, territory management, and payout tracking.

Hierarchy:
  Platform Admin → Regional Manager → Reseller

Tiers:
  BRONZE  (0-10 active tenants)   → 10% commission
  SILVER  (11-50 active tenants)  → 15% commission
  GOLD    (51+ active tenants)    → 20% commission

Regional Management:
  - Each region can have ONE regional manager (promoted from GOLD resellers).
  - Regional managers get a management bonus (default 3% on all regional commissions).
  - Territories are named sub-areas within a region (e.g. "Nairobi CBD", "Westlands").
  - Commission overrides allow per-region rate adjustments (e.g. +2% for new markets).
  - Regional targets set monthly goals (tenant_count, revenue) per region.

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

# Regional management events
REGIONAL_MANAGER_APPOINTED_V1 = "saas.region.manager_appointed.v1"
REGIONAL_MANAGER_REMOVED_V1 = "saas.region.manager_removed.v1"
RESELLER_TERRITORY_ASSIGNED_V1 = "saas.reseller.territory_assigned.v1"
RESELLER_TERRITORY_REVOKED_V1 = "saas.reseller.territory_revoked.v1"
REGIONAL_COMMISSION_OVERRIDE_SET_V1 = "saas.region.commission_override_set.v1"
REGIONAL_TARGET_SET_V1 = "saas.region.target_set.v1"
RESELLER_TRANSFERRED_V1 = "saas.reseller.transferred.v1"
PAYOUT_APPROVED_V1 = "saas.reseller.payout_approved.v1"
PAYOUT_REJECTED_V1 = "saas.reseller.payout_rejected.v1"

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
    REGIONAL_MANAGER_APPOINTED_V1,
    REGIONAL_MANAGER_REMOVED_V1,
    RESELLER_TERRITORY_ASSIGNED_V1,
    RESELLER_TERRITORY_REVOKED_V1,
    REGIONAL_COMMISSION_OVERRIDE_SET_V1,
    REGIONAL_TARGET_SET_V1,
    RESELLER_TRANSFERRED_V1,
    PAYOUT_APPROVED_V1,
    PAYOUT_REJECTED_V1,
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

# Regional manager bonus rate (on all commissions in their region)
REGIONAL_MANAGER_BONUS_RATE = Decimal("0.03")  # 3%


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
    rejection_reason: str = ""


# ── Regional Management Models ────────────────────────────────

@dataclass(frozen=True)
class RegionalManagerRecord:
    """A reseller promoted to manage a specific region."""
    region_code: str
    reseller_id: uuid.UUID
    bonus_rate: Decimal               # extra % on all regional commissions
    appointed_at: datetime
    total_bonus_earned: Decimal = Decimal("0")


@dataclass(frozen=True)
class TerritoryAssignment:
    """Named sub-area within a region assigned to a reseller."""
    territory_id: uuid.UUID
    region_code: str
    territory_name: str               # e.g. "Nairobi CBD", "Westlands"
    reseller_id: uuid.UUID
    is_active: bool
    assigned_at: datetime


@dataclass(frozen=True)
class RegionalCommissionOverride:
    """Per-region commission rate adjustment (additive)."""
    region_code: str
    override_rate: Decimal            # e.g. +0.02 means +2% for this region
    reason: str
    set_at: datetime


@dataclass(frozen=True)
class RegionalTarget:
    """Monthly performance target for a region."""
    region_code: str
    period: str                       # e.g. "2026-03"
    target_tenant_count: int          # new tenants to onboard this month
    target_revenue: Decimal           # target monthly recurring revenue
    currency: str
    set_at: datetime


@dataclass(frozen=True)
class RegionalPerformanceSummary:
    """Computed performance snapshot for a region."""
    region_code: str
    period: str
    total_resellers: int
    active_resellers: int
    total_tenants: int
    active_tenants: int
    total_commission_accrued: Decimal
    total_commission_paid: Decimal
    regional_manager_id: Optional[uuid.UUID]
    regional_manager_name: str
    target_tenant_count: int
    target_revenue: Decimal
    actual_revenue: Decimal
    currency: str


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


# ── Regional Management Request DTOs ──────────────────────────

@dataclass(frozen=True)
class AppointRegionalManagerRequest:
    """Promote a reseller to regional manager for a specific region."""
    reseller_id: uuid.UUID
    region_code: str
    bonus_rate: Decimal               # default REGIONAL_MANAGER_BONUS_RATE
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class RemoveRegionalManagerRequest:
    region_code: str
    reason: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class AssignTerritoryRequest:
    reseller_id: uuid.UUID
    region_code: str
    territory_name: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class RevokeTerritoryRequest:
    territory_id: uuid.UUID
    reason: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class SetRegionalCommissionOverrideRequest:
    region_code: str
    override_rate: Decimal            # additive e.g. Decimal("0.02") = +2%
    reason: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class SetRegionalTargetRequest:
    region_code: str
    period: str                       # e.g. "2026-03"
    target_tenant_count: int
    target_revenue: Decimal
    currency: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class TransferResellerRequest:
    """Transfer a reseller from one region to another."""
    reseller_id: uuid.UUID
    from_region_code: str
    to_region_code: str
    reason: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class UpdateResellerRequest:
    """Update reseller profile fields."""
    reseller_id: uuid.UUID
    company_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    region_codes: Optional[Tuple[str, ...]] = None
    payout_method: Optional[str] = None
    payout_phone: Optional[str] = None
    payout_bank_name: Optional[str] = None
    payout_account_number: Optional[str] = None
    payout_account_name: Optional[str] = None
    actor_id: str = ""
    issued_at: Optional[datetime] = None


@dataclass(frozen=True)
class ApprovePayoutRequest:
    payout_id: uuid.UUID
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class RejectPayoutRequest:
    payout_id: uuid.UUID
    reason: str
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# PROJECTION
# ══════════════════════════════════════════════════════════════

class ResellerProjection:
    """In-memory projection of reseller program state with regional management."""

    projection_name = "reseller_projection"

    def __init__(self) -> None:
        self._resellers: Dict[uuid.UUID, ResellerRecord] = {}
        # reseller_id → list of business_ids
        self._tenant_links: Dict[uuid.UUID, Dict[uuid.UUID, ResellerTenantLink]] = {}
        # commission entries
        self._commissions: List[CommissionEntry] = []
        # payout records
        self._payouts: Dict[uuid.UUID, PayoutRecord] = {}
        # ── Regional management state ──
        # region_code → RegionalManagerRecord
        self._regional_managers: Dict[str, RegionalManagerRecord] = {}
        # territory_id → TerritoryAssignment
        self._territories: Dict[uuid.UUID, TerritoryAssignment] = {}
        # region_code → RegionalCommissionOverride
        self._commission_overrides: Dict[str, RegionalCommissionOverride] = {}
        # (region_code, period) → RegionalTarget
        self._regional_targets: Dict[Tuple[str, str], RegionalTarget] = {}

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
        # Regional management events
        elif event_type == REGIONAL_MANAGER_APPOINTED_V1:
            self._apply_regional_manager_appointed(payload)
        elif event_type == REGIONAL_MANAGER_REMOVED_V1:
            self._apply_regional_manager_removed(payload)
        elif event_type == RESELLER_TERRITORY_ASSIGNED_V1:
            self._apply_territory_assigned(payload)
        elif event_type == RESELLER_TERRITORY_REVOKED_V1:
            self._apply_territory_revoked(payload)
        elif event_type == REGIONAL_COMMISSION_OVERRIDE_SET_V1:
            self._apply_commission_override_set(payload)
        elif event_type == REGIONAL_TARGET_SET_V1:
            self._apply_regional_target_set(payload)
        elif event_type == RESELLER_TRANSFERRED_V1:
            self._apply_reseller_transferred(payload)
        elif event_type == PAYOUT_APPROVED_V1:
            self._apply_payout_completed(payload)
        elif event_type == PAYOUT_REJECTED_V1:
            self._apply_payout_rejected(payload)

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

    # ── regional management apply methods ─────────────────────

    def _apply_regional_manager_appointed(self, payload: Dict[str, Any]) -> None:
        region_code = payload["region_code"]
        reseller_id = uuid.UUID(str(payload["reseller_id"]))
        self._regional_managers[region_code] = RegionalManagerRecord(
            region_code=region_code,
            reseller_id=reseller_id,
            bonus_rate=Decimal(str(payload.get("bonus_rate", REGIONAL_MANAGER_BONUS_RATE))),
            appointed_at=payload.get("issued_at", datetime.utcnow()),
        )

    def _apply_regional_manager_removed(self, payload: Dict[str, Any]) -> None:
        region_code = payload["region_code"]
        self._regional_managers.pop(region_code, None)

    def _apply_territory_assigned(self, payload: Dict[str, Any]) -> None:
        territory_id = uuid.UUID(str(payload["territory_id"]))
        self._territories[territory_id] = TerritoryAssignment(
            territory_id=territory_id,
            region_code=payload["region_code"],
            territory_name=payload["territory_name"],
            reseller_id=uuid.UUID(str(payload["reseller_id"])),
            is_active=True,
            assigned_at=payload.get("issued_at", datetime.utcnow()),
        )

    def _apply_territory_revoked(self, payload: Dict[str, Any]) -> None:
        territory_id = uuid.UUID(str(payload["territory_id"]))
        old = self._territories.get(territory_id)
        if old:
            self._territories[territory_id] = TerritoryAssignment(
                territory_id=old.territory_id,
                region_code=old.region_code,
                territory_name=old.territory_name,
                reseller_id=old.reseller_id,
                is_active=False,
                assigned_at=old.assigned_at,
            )

    def _apply_commission_override_set(self, payload: Dict[str, Any]) -> None:
        region_code = payload["region_code"]
        self._commission_overrides[region_code] = RegionalCommissionOverride(
            region_code=region_code,
            override_rate=Decimal(str(payload["override_rate"])),
            reason=payload.get("reason", ""),
            set_at=payload.get("issued_at", datetime.utcnow()),
        )

    def _apply_regional_target_set(self, payload: Dict[str, Any]) -> None:
        region_code = payload["region_code"]
        period = payload["period"]
        self._regional_targets[(region_code, period)] = RegionalTarget(
            region_code=region_code,
            period=period,
            target_tenant_count=int(payload.get("target_tenant_count", 0)),
            target_revenue=Decimal(str(payload.get("target_revenue", "0"))),
            currency=payload.get("currency", ""),
            set_at=payload.get("issued_at", datetime.utcnow()),
        )

    def _apply_reseller_transferred(self, payload: Dict[str, Any]) -> None:
        reseller_id = uuid.UUID(str(payload["reseller_id"]))
        to_region = payload["to_region_code"]
        old = self._resellers.get(reseller_id)
        if old is None:
            return
        # Replace region_codes: remove from_region, add to_region
        from_region = payload.get("from_region_code", "")
        new_regions = tuple(
            r for r in old.region_codes if r != from_region
        ) + (to_region,)
        # Deduplicate
        new_regions = tuple(dict.fromkeys(new_regions))
        self._resellers[reseller_id] = ResellerRecord(
            reseller_id=old.reseller_id,
            company_name=old.company_name,
            contact_person=old.contact_person,
            phone=old.phone,
            email=old.email,
            region_codes=new_regions,
            tier=old.tier,
            status=old.status,
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

    def _apply_payout_rejected(self, payload: Dict[str, Any]) -> None:
        payout_id = uuid.UUID(str(payload["payout_id"]))
        old = self._payouts.get(payout_id)
        if old is None:
            return
        self._payouts[payout_id] = PayoutRecord(
            payout_id=old.payout_id,
            reseller_id=old.reseller_id,
            amount=old.amount,
            currency=old.currency,
            status=PayoutStatus.FAILED,
            method=old.method,
            requested_at=old.requested_at,
            completed_at=payload.get("issued_at"),
            rejection_reason=payload.get("reason", ""),
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

    def list_all_payouts(
        self, status: Optional[str] = None
    ) -> List[PayoutRecord]:
        """List all payouts across all resellers (admin view)."""
        payouts = list(self._payouts.values())
        if status:
            payouts = [p for p in payouts if p.status.value == status]
        return payouts

    def get_payout(self, payout_id: uuid.UUID) -> Optional[PayoutRecord]:
        return self._payouts.get(payout_id)

    # ── regional queries ──────────────────────────────────────

    def list_resellers_by_region(
        self, region_code: str, active_only: bool = True
    ) -> List[ResellerRecord]:
        """List all resellers operating in a specific region."""
        result = [
            r for r in self._resellers.values()
            if region_code in r.region_codes
        ]
        if active_only:
            result = [r for r in result if r.status == ResellerStatus.ACTIVE]
        return result

    def get_regional_manager(
        self, region_code: str
    ) -> Optional[RegionalManagerRecord]:
        return self._regional_managers.get(region_code)

    def list_regional_managers(self) -> List[RegionalManagerRecord]:
        return list(self._regional_managers.values())

    def get_territories_for_region(
        self, region_code: str, active_only: bool = True
    ) -> List[TerritoryAssignment]:
        result = [
            t for t in self._territories.values()
            if t.region_code == region_code
        ]
        if active_only:
            result = [t for t in result if t.is_active]
        return result

    def get_territories_for_reseller(
        self, reseller_id: uuid.UUID, active_only: bool = True
    ) -> List[TerritoryAssignment]:
        result = [
            t for t in self._territories.values()
            if t.reseller_id == reseller_id
        ]
        if active_only:
            result = [t for t in result if t.is_active]
        return result

    def get_territory(
        self, territory_id: uuid.UUID
    ) -> Optional[TerritoryAssignment]:
        return self._territories.get(territory_id)

    def get_commission_override(
        self, region_code: str
    ) -> Optional[RegionalCommissionOverride]:
        return self._commission_overrides.get(region_code)

    def list_commission_overrides(self) -> List[RegionalCommissionOverride]:
        return list(self._commission_overrides.values())

    def get_regional_target(
        self, region_code: str, period: str
    ) -> Optional[RegionalTarget]:
        return self._regional_targets.get((region_code, period))

    def list_regional_targets(
        self, region_code: Optional[str] = None
    ) -> List[RegionalTarget]:
        targets = list(self._regional_targets.values())
        if region_code:
            targets = [t for t in targets if t.region_code == region_code]
        return targets

    def get_effective_commission_rate(
        self, reseller_id: uuid.UUID
    ) -> Decimal:
        """Get effective commission rate = tier rate + regional override (if any)."""
        reseller = self._resellers.get(reseller_id)
        if reseller is None:
            return Decimal("0")
        base_rate = reseller.commission_rate
        # Apply the best regional override (highest) for regions this reseller covers
        best_override = Decimal("0")
        for rc in reseller.region_codes:
            override = self._commission_overrides.get(rc)
            if override and override.override_rate > best_override:
                best_override = override.override_rate
        return base_rate + best_override

    def compute_regional_performance(
        self, region_code: str, period: str
    ) -> RegionalPerformanceSummary:
        """Compute aggregated performance for a region in a given period."""
        resellers_in_region = self.list_resellers_by_region(
            region_code, active_only=False
        )
        active_resellers = [
            r for r in resellers_in_region if r.status == ResellerStatus.ACTIVE
        ]
        total_tenants = 0
        active_tenants = 0
        for r in resellers_in_region:
            links = self._tenant_links.get(r.reseller_id, {})
            total_tenants += len(links)
            active_tenants += sum(1 for lnk in links.values() if lnk.is_active)

        # Commission totals for this region's resellers in this period
        region_reseller_ids = {r.reseller_id for r in resellers_in_region}
        region_commissions = [
            c for c in self._commissions
            if c.reseller_id in region_reseller_ids and c.period == period
        ]
        total_accrued = sum(
            c.amount for c in region_commissions if not c.is_clawback
        )
        total_clawback = sum(
            c.amount for c in region_commissions if c.is_clawback
        )

        # Paid out for this region
        region_payouts = [
            p for p in self._payouts.values()
            if p.reseller_id in region_reseller_ids
            and p.status == PayoutStatus.COMPLETED
        ]
        total_paid = sum(p.amount for p in region_payouts)

        mgr = self._regional_managers.get(region_code)
        mgr_name = ""
        if mgr:
            mgr_reseller = self._resellers.get(mgr.reseller_id)
            if mgr_reseller:
                mgr_name = mgr_reseller.company_name

        target = self._regional_targets.get((region_code, period))
        currency = ""
        if target:
            currency = target.currency
        elif region_commissions:
            currency = region_commissions[0].currency

        return RegionalPerformanceSummary(
            region_code=region_code,
            period=period,
            total_resellers=len(resellers_in_region),
            active_resellers=len(active_resellers),
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            total_commission_accrued=total_accrued - total_clawback,
            total_commission_paid=total_paid,
            regional_manager_id=mgr.reseller_id if mgr else None,
            regional_manager_name=mgr_name,
            target_tenant_count=target.target_tenant_count if target else 0,
            target_revenue=target.target_revenue if target else Decimal("0"),
            actual_revenue=total_accrued - total_clawback,
            currency=currency,
        )

    def truncate(self) -> None:
        self._resellers.clear()
        self._tenant_links.clear()
        self._commissions.clear()
        self._payouts.clear()
        self._regional_managers.clear()
        self._territories.clear()
        self._commission_overrides.clear()
        self._regional_targets.clear()


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

    # ══════════════════════════════════════════════════════════
    # RESELLER MANAGEMENT (suspend / reinstate / update / terminate)
    # ══════════════════════════════════════════════════════════

    def suspend_reseller(
        self, reseller_id: uuid.UUID, reason: str, actor_id: str, issued_at: datetime
    ) -> Dict[str, Any]:
        reseller = self._projection.get_reseller(reseller_id)
        if reseller is None:
            return {"rejected": RejectionReason(
                code="RESELLER_NOT_FOUND", message="Reseller not found.",
                policy_name="suspend_reseller")}
        if reseller.status != ResellerStatus.ACTIVE:
            return {"rejected": RejectionReason(
                code="RESELLER_NOT_ACTIVE",
                message=f"Reseller is {reseller.status.value}, cannot suspend.",
                policy_name="suspend_reseller")}
        payload = {
            "reseller_id": str(reseller_id), "reason": reason,
            "actor_id": actor_id, "issued_at": issued_at,
        }
        self._projection.apply(RESELLER_SUSPENDED_V1, payload)
        return {"status": "SUSPENDED", "events": [
            {"event_type": RESELLER_SUSPENDED_V1, "payload": payload}]}

    def reinstate_reseller(
        self, reseller_id: uuid.UUID, actor_id: str, issued_at: datetime
    ) -> Dict[str, Any]:
        reseller = self._projection.get_reseller(reseller_id)
        if reseller is None:
            return {"rejected": RejectionReason(
                code="RESELLER_NOT_FOUND", message="Reseller not found.",
                policy_name="reinstate_reseller")}
        if reseller.status != ResellerStatus.SUSPENDED:
            return {"rejected": RejectionReason(
                code="NOT_SUSPENDED",
                message=f"Reseller is {reseller.status.value}, not suspended.",
                policy_name="reinstate_reseller")}
        payload = {
            "reseller_id": str(reseller_id),
            "actor_id": actor_id, "issued_at": issued_at,
        }
        self._projection.apply(RESELLER_REACTIVATED_V1, payload)
        return {"status": "ACTIVE", "events": [
            {"event_type": RESELLER_REACTIVATED_V1, "payload": payload}]}

    def terminate_reseller(
        self, reseller_id: uuid.UUID, reason: str, actor_id: str, issued_at: datetime
    ) -> Dict[str, Any]:
        reseller = self._projection.get_reseller(reseller_id)
        if reseller is None:
            return {"rejected": RejectionReason(
                code="RESELLER_NOT_FOUND", message="Reseller not found.",
                policy_name="terminate_reseller")}
        payload = {
            "reseller_id": str(reseller_id), "reason": reason,
            "actor_id": actor_id, "issued_at": issued_at,
        }
        self._projection.apply(RESELLER_TERMINATED_V1, payload)
        # Remove from regional manager if applicable
        for rc, mgr in list(self._projection._regional_managers.items()):
            if mgr.reseller_id == reseller_id:
                self._projection.apply(REGIONAL_MANAGER_REMOVED_V1, {
                    "region_code": rc, "reason": "Reseller terminated",
                    "actor_id": actor_id, "issued_at": issued_at,
                })
        return {"status": "TERMINATED", "events": [
            {"event_type": RESELLER_TERMINATED_V1, "payload": payload}]}

    def update_reseller(
        self, request: UpdateResellerRequest
    ) -> Dict[str, Any]:
        reseller = self._projection.get_reseller(request.reseller_id)
        if reseller is None:
            return {"rejected": RejectionReason(
                code="RESELLER_NOT_FOUND", message="Reseller not found.",
                policy_name="update_reseller")}
        payload: Dict[str, Any] = {
            "reseller_id": str(request.reseller_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        if request.company_name is not None:
            payload["company_name"] = request.company_name
        if request.contact_person is not None:
            payload["contact_person"] = request.contact_person
        if request.phone is not None:
            payload["phone"] = request.phone
        if request.email is not None:
            payload["email"] = request.email
        if request.region_codes is not None:
            payload["region_codes"] = list(request.region_codes)
        if request.payout_method is not None:
            payload["payout_method"] = request.payout_method
        if request.payout_phone is not None:
            payload["payout_phone"] = request.payout_phone
        if request.payout_bank_name is not None:
            payload["payout_bank_name"] = request.payout_bank_name
        if request.payout_account_number is not None:
            payload["payout_account_number"] = request.payout_account_number
        if request.payout_account_name is not None:
            payload["payout_account_name"] = request.payout_account_name
        self._projection.apply(RESELLER_UPDATED_V1, payload)
        return {"status": "ok", "events": [
            {"event_type": RESELLER_UPDATED_V1, "payload": payload}]}

    def approve_payout(
        self, request: ApprovePayoutRequest
    ) -> Dict[str, Any]:
        payout = self._projection.get_payout(request.payout_id)
        if payout is None:
            return {"rejected": RejectionReason(
                code="PAYOUT_NOT_FOUND", message="Payout not found.",
                policy_name="approve_payout")}
        if payout.status != PayoutStatus.PENDING:
            return {"rejected": RejectionReason(
                code="PAYOUT_NOT_PENDING",
                message=f"Payout is {payout.status.value}.",
                policy_name="approve_payout")}
        payload = {
            "payout_id": str(request.payout_id),
            "reseller_id": str(payout.reseller_id),
            "actor_id": request.actor_id, "issued_at": request.issued_at,
        }
        self._projection.apply(RESELLER_PAYOUT_COMPLETED_V1, payload)
        return {"status": "COMPLETED", "events": [
            {"event_type": PAYOUT_APPROVED_V1, "payload": payload}]}

    def reject_payout(
        self, request: RejectPayoutRequest
    ) -> Dict[str, Any]:
        payout = self._projection.get_payout(request.payout_id)
        if payout is None:
            return {"rejected": RejectionReason(
                code="PAYOUT_NOT_FOUND", message="Payout not found.",
                policy_name="reject_payout")}
        if payout.status != PayoutStatus.PENDING:
            return {"rejected": RejectionReason(
                code="PAYOUT_NOT_PENDING",
                message=f"Payout is {payout.status.value}.",
                policy_name="reject_payout")}
        payload = {
            "payout_id": str(request.payout_id),
            "reason": request.reason,
            "actor_id": request.actor_id, "issued_at": request.issued_at,
        }
        self._projection.apply(PAYOUT_REJECTED_V1, payload)
        return {"status": "REJECTED", "reason": request.reason, "events": [
            {"event_type": PAYOUT_REJECTED_V1, "payload": payload}]}

    # ══════════════════════════════════════════════════════════
    # REGIONAL MANAGEMENT
    # ══════════════════════════════════════════════════════════

    def appoint_regional_manager(
        self, request: AppointRegionalManagerRequest
    ) -> Dict[str, Any]:
        """Promote a reseller to regional manager for a region."""
        reseller = self._projection.get_reseller(request.reseller_id)
        if reseller is None:
            return {"rejected": RejectionReason(
                code="RESELLER_NOT_FOUND", message="Reseller not found.",
                policy_name="appoint_regional_manager")}
        if reseller.status != ResellerStatus.ACTIVE:
            return {"rejected": RejectionReason(
                code="RESELLER_NOT_ACTIVE",
                message="Reseller must be ACTIVE to be appointed.",
                policy_name="appoint_regional_manager")}
        # Check if region already has a manager
        existing = self._projection.get_regional_manager(request.region_code)
        if existing is not None:
            existing_reseller = self._projection.get_reseller(existing.reseller_id)
            mgr_name = existing_reseller.company_name if existing_reseller else "Unknown"
            return {"rejected": RejectionReason(
                code="REGION_ALREADY_HAS_MANAGER",
                message=f"Region {request.region_code} already managed by {mgr_name}.",
                policy_name="appoint_regional_manager")}
        # Reseller must cover this region
        if request.region_code not in reseller.region_codes:
            return {"rejected": RejectionReason(
                code="RESELLER_NOT_IN_REGION",
                message=f"Reseller does not cover region {request.region_code}.",
                policy_name="appoint_regional_manager")}

        payload = {
            "reseller_id": str(request.reseller_id),
            "region_code": request.region_code,
            "bonus_rate": str(request.bonus_rate),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(REGIONAL_MANAGER_APPOINTED_V1, payload)
        return {
            "region_code": request.region_code,
            "reseller_id": str(request.reseller_id),
            "bonus_rate": str(request.bonus_rate),
            "events": [{"event_type": REGIONAL_MANAGER_APPOINTED_V1, "payload": payload}],
        }

    def remove_regional_manager(
        self, request: RemoveRegionalManagerRequest
    ) -> Dict[str, Any]:
        existing = self._projection.get_regional_manager(request.region_code)
        if existing is None:
            return {"rejected": RejectionReason(
                code="NO_MANAGER_FOR_REGION",
                message=f"No regional manager for {request.region_code}.",
                policy_name="remove_regional_manager")}
        payload = {
            "region_code": request.region_code,
            "reseller_id": str(existing.reseller_id),
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(REGIONAL_MANAGER_REMOVED_V1, payload)
        return {
            "region_code": request.region_code,
            "removed_reseller_id": str(existing.reseller_id),
            "events": [{"event_type": REGIONAL_MANAGER_REMOVED_V1, "payload": payload}],
        }

    def assign_territory(
        self, request: AssignTerritoryRequest
    ) -> Dict[str, Any]:
        reseller = self._projection.get_reseller(request.reseller_id)
        if reseller is None:
            return {"rejected": RejectionReason(
                code="RESELLER_NOT_FOUND", message="Reseller not found.",
                policy_name="assign_territory")}
        if reseller.status != ResellerStatus.ACTIVE:
            return {"rejected": RejectionReason(
                code="RESELLER_NOT_ACTIVE",
                message="Reseller must be ACTIVE to be assigned territory.",
                policy_name="assign_territory")}
        # Check for duplicate territory name in same region
        existing = self._projection.get_territories_for_region(request.region_code)
        for t in existing:
            if t.territory_name.lower() == request.territory_name.lower():
                return {"rejected": RejectionReason(
                    code="TERRITORY_EXISTS",
                    message=f"Territory '{request.territory_name}' already exists in {request.region_code}.",
                    policy_name="assign_territory")}

        territory_id = uuid.uuid4()
        payload = {
            "territory_id": str(territory_id),
            "region_code": request.region_code,
            "territory_name": request.territory_name,
            "reseller_id": str(request.reseller_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(RESELLER_TERRITORY_ASSIGNED_V1, payload)
        return {
            "territory_id": str(territory_id),
            "events": [{"event_type": RESELLER_TERRITORY_ASSIGNED_V1, "payload": payload}],
        }

    def revoke_territory(
        self, request: RevokeTerritoryRequest
    ) -> Dict[str, Any]:
        territory = self._projection.get_territory(request.territory_id)
        if territory is None:
            return {"rejected": RejectionReason(
                code="TERRITORY_NOT_FOUND", message="Territory not found.",
                policy_name="revoke_territory")}
        if not territory.is_active:
            return {"rejected": RejectionReason(
                code="TERRITORY_ALREADY_REVOKED",
                message="Territory is already revoked.",
                policy_name="revoke_territory")}
        payload = {
            "territory_id": str(request.territory_id),
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(RESELLER_TERRITORY_REVOKED_V1, payload)
        return {
            "territory_id": str(request.territory_id),
            "events": [{"event_type": RESELLER_TERRITORY_REVOKED_V1, "payload": payload}],
        }

    def set_regional_commission_override(
        self, request: SetRegionalCommissionOverrideRequest
    ) -> Dict[str, Any]:
        if request.override_rate < Decimal("-0.10") or request.override_rate > Decimal("0.20"):
            return {"rejected": RejectionReason(
                code="INVALID_OVERRIDE_RATE",
                message="Override rate must be between -10% and +20%.",
                policy_name="set_regional_commission_override")}
        payload = {
            "region_code": request.region_code,
            "override_rate": str(request.override_rate),
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(REGIONAL_COMMISSION_OVERRIDE_SET_V1, payload)
        return {
            "region_code": request.region_code,
            "override_rate": str(request.override_rate),
            "events": [{"event_type": REGIONAL_COMMISSION_OVERRIDE_SET_V1, "payload": payload}],
        }

    def set_regional_target(
        self, request: SetRegionalTargetRequest
    ) -> Dict[str, Any]:
        payload = {
            "region_code": request.region_code,
            "period": request.period,
            "target_tenant_count": request.target_tenant_count,
            "target_revenue": str(request.target_revenue),
            "currency": request.currency,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(REGIONAL_TARGET_SET_V1, payload)
        return {
            "region_code": request.region_code,
            "period": request.period,
            "events": [{"event_type": REGIONAL_TARGET_SET_V1, "payload": payload}],
        }

    def transfer_reseller(
        self, request: TransferResellerRequest
    ) -> Dict[str, Any]:
        reseller = self._projection.get_reseller(request.reseller_id)
        if reseller is None:
            return {"rejected": RejectionReason(
                code="RESELLER_NOT_FOUND", message="Reseller not found.",
                policy_name="transfer_reseller")}
        if request.from_region_code not in reseller.region_codes:
            return {"rejected": RejectionReason(
                code="NOT_IN_SOURCE_REGION",
                message=f"Reseller not in region {request.from_region_code}.",
                policy_name="transfer_reseller")}
        # Cannot transfer if they're the regional manager for from_region
        mgr = self._projection.get_regional_manager(request.from_region_code)
        if mgr and mgr.reseller_id == request.reseller_id:
            return {"rejected": RejectionReason(
                code="IS_REGIONAL_MANAGER",
                message="Remove regional manager role before transferring.",
                policy_name="transfer_reseller")}
        payload = {
            "reseller_id": str(request.reseller_id),
            "from_region_code": request.from_region_code,
            "to_region_code": request.to_region_code,
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(RESELLER_TRANSFERRED_V1, payload)
        return {
            "reseller_id": str(request.reseller_id),
            "from_region_code": request.from_region_code,
            "to_region_code": request.to_region_code,
            "events": [{"event_type": RESELLER_TRANSFERRED_V1, "payload": payload}],
        }

    def get_regional_performance(
        self, region_code: str, period: str
    ) -> Dict[str, Any]:
        perf = self._projection.compute_regional_performance(region_code, period)
        return {
            "region_code": perf.region_code,
            "period": perf.period,
            "total_resellers": perf.total_resellers,
            "active_resellers": perf.active_resellers,
            "total_tenants": perf.total_tenants,
            "active_tenants": perf.active_tenants,
            "total_commission_accrued": str(perf.total_commission_accrued),
            "total_commission_paid": str(perf.total_commission_paid),
            "regional_manager_id": str(perf.regional_manager_id) if perf.regional_manager_id else None,
            "regional_manager_name": perf.regional_manager_name,
            "target_tenant_count": perf.target_tenant_count,
            "target_revenue": str(perf.target_revenue),
            "actual_revenue": str(perf.actual_revenue),
            "currency": perf.currency,
        }

    def get_region_summary(self, region_code: str) -> Dict[str, Any]:
        """Full summary for a region: manager, resellers, territories, overrides, targets."""
        mgr = self._projection.get_regional_manager(region_code)
        resellers = self._projection.list_resellers_by_region(region_code)
        territories = self._projection.get_territories_for_region(region_code)
        override = self._projection.get_commission_override(region_code)
        targets = [
            t for t in self._projection.list_regional_targets(region_code)
        ]

        mgr_dict = None
        if mgr:
            mgr_reseller = self._projection.get_reseller(mgr.reseller_id)
            mgr_dict = {
                "reseller_id": str(mgr.reseller_id),
                "company_name": mgr_reseller.company_name if mgr_reseller else "",
                "bonus_rate": str(mgr.bonus_rate),
                "appointed_at": str(mgr.appointed_at) if mgr.appointed_at else None,
            }

        return {
            "region_code": region_code,
            "regional_manager": mgr_dict,
            "reseller_count": len(resellers),
            "resellers": [
                {
                    "reseller_id": str(r.reseller_id),
                    "company_name": r.company_name,
                    "tier": r.tier.value,
                    "active_tenant_count": r.active_tenant_count,
                    "commission_rate": str(r.commission_rate),
                }
                for r in resellers
            ],
            "territories": [
                {
                    "territory_id": str(t.territory_id),
                    "territory_name": t.territory_name,
                    "reseller_id": str(t.reseller_id),
                    "is_active": t.is_active,
                }
                for t in territories
            ],
            "commission_override": {
                "override_rate": str(override.override_rate),
                "reason": override.reason,
            } if override else None,
            "targets": [
                {
                    "period": t.period,
                    "target_tenant_count": t.target_tenant_count,
                    "target_revenue": str(t.target_revenue),
                    "currency": t.currency,
                }
                for t in targets
            ],
        }
