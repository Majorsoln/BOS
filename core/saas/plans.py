"""
BOS SaaS — Engine Combos & Region-Aware Pricing
====================================================
Leadership defines engine combinations (combos).
Users see combo names, select their region, and get
pricing in their local currency.

Design principles (BOS Doctrine):
  1. Leadership (not the user) defines which engines go together.
  2. Some engines are FREE (default) — every tenant gets them.
  3. User picks a combo name → enters region → sees monthly charge.
  4. Each combo is classified as B2B, B2C, or BOTH.
  5. Rates are region-specific and versioned.
  6. All changes are event-sourced and deterministic.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# EVENT TYPES
# ══════════════════════════════════════════════════════════════

ENGINE_REGISTERED_V1 = "saas.engine.registered.v1"
COMBO_DEFINED_V1 = "saas.combo.defined.v1"
COMBO_UPDATED_V1 = "saas.combo.updated.v1"
COMBO_DEACTIVATED_V1 = "saas.combo.deactivated.v1"
COMBO_RATE_SET_V1 = "saas.combo.rate_set.v1"

PLAN_EVENT_TYPES = (
    ENGINE_REGISTERED_V1,
    COMBO_DEFINED_V1,
    COMBO_UPDATED_V1,
    COMBO_DEACTIVATED_V1,
    COMBO_RATE_SET_V1,
)


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class EngineCategory(Enum):
    """Whether an engine is free for all tenants or requires a paid combo."""
    FREE = "FREE"       # included in every tenant, no charge
    PAID = "PAID"       # only available through a combo


class BusinessModel(Enum):
    """Classification of the tenant's primary business model."""
    B2C = "B2C"         # sells to consumers (duka, restaurant, salon)
    B2B = "B2B"         # sells to businesses (workshop, procurement, wholesale)
    BOTH = "BOTH"       # mixed (hotel: B2C guests + B2B corporate)


class ComboStatus(Enum):
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"


# ══════════════════════════════════════════════════════════════
# DATA MODELS (frozen, immutable)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class EngineEntry:
    """One engine in the BOS engine catalog."""
    engine_key: str                     # e.g. "retail", "restaurant", "cash"
    display_name: str                   # e.g. "Retail POS", "Restaurant & Bar"
    category: EngineCategory            # FREE or PAID
    description: str = ""


# ── Default / free engines (everyone gets these) ──────────────

FREE_ENGINES: Tuple[EngineEntry, ...] = (
    EngineEntry("cash", "Cash Management", EngineCategory.FREE,
                "Cash drawer, sessions, float tracking"),
    EngineEntry("documents", "Documents", EngineCategory.FREE,
                "Receipts, invoices, quotes — all document types"),
    EngineEntry("reporting", "Basic Reporting", EngineCategory.FREE,
                "KPI recording and daily snapshots"),
    EngineEntry("customer", "Customer Profiles", EngineCategory.FREE,
                "Basic customer tracking and lookup"),
)

FREE_ENGINE_KEYS: FrozenSet[str] = frozenset(e.engine_key for e in FREE_ENGINES)


@dataclass(frozen=True)
class ComboRate:
    """Monthly price for a combo in a specific region."""
    combo_id: uuid.UUID
    region_code: str                    # ISO 3166-1 alpha-2 e.g. "KE", "TZ"
    currency: str                       # ISO 4217 e.g. "KES", "TZS"
    monthly_amount: Decimal             # in major currency units
    rate_version: int                   # version of this rate (for governance)
    effective_from: Optional[datetime] = None


@dataclass(frozen=True)
class PlanQuota:
    """Usage limits for a combo subscription."""
    max_branches: int
    max_users: int
    max_api_calls_per_month: int
    max_documents_per_month: int


@dataclass(frozen=True)
class ComboDefinition:
    """
    A leadership-defined engine combination.

    Users don't compose plans — they pick a combo by name.
    The combo determines which paid engines are activated.
    Free engines are ALWAYS included on top.
    """
    combo_id: uuid.UUID
    name: str                           # display name e.g. "BOS Duka"
    slug: str                           # URL-safe e.g. "bos-duka"
    description: str
    business_model: BusinessModel       # B2B, B2C, or BOTH
    paid_engines: FrozenSet[str]        # engine keys that this combo activates
    quota: PlanQuota
    status: ComboStatus = ComboStatus.ACTIVE
    sort_order: int = 0                 # display ordering
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def all_engines(self) -> FrozenSet[str]:
        """All engines the tenant gets: free engines + combo's paid engines."""
        return FREE_ENGINE_KEYS | self.paid_engines


# ══════════════════════════════════════════════════════════════
# REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RegisterEngineRequest:
    engine_key: str
    display_name: str
    category: str                       # "FREE" or "PAID"
    description: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class DefineComboRequest:
    name: str
    slug: str
    description: str
    business_model: str                 # "B2B", "B2C", or "BOTH"
    paid_engines: Tuple[str, ...]
    max_branches: int
    max_users: int
    max_api_calls_per_month: int
    max_documents_per_month: int
    sort_order: int
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class UpdateComboRequest:
    combo_id: uuid.UUID
    name: Optional[str] = None
    description: Optional[str] = None
    paid_engines: Optional[Tuple[str, ...]] = None
    max_branches: Optional[int] = None
    max_users: Optional[int] = None
    max_api_calls_per_month: Optional[int] = None
    max_documents_per_month: Optional[int] = None
    sort_order: Optional[int] = None
    actor_id: str = ""
    issued_at: Optional[datetime] = None


@dataclass(frozen=True)
class DeactivateComboRequest:
    combo_id: uuid.UUID
    actor_id: str
    issued_at: datetime
    reason: str = ""


@dataclass(frozen=True)
class SetComboRateRequest:
    """Set (or update) the monthly price for a combo in a specific region."""
    combo_id: uuid.UUID
    region_code: str
    currency: str
    monthly_amount: Decimal
    effective_from: Optional[datetime] = None
    actor_id: str = ""
    issued_at: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# PROJECTION — in-memory state from events
# ══════════════════════════════════════════════════════════════

class PlanProjection:
    """
    In-memory projection of engine catalog, combos, and region rates.

    Rebuilt deterministically from plan events.
    """

    projection_name = "plan_projection"

    def __init__(self) -> None:
        self._engines: Dict[str, EngineEntry] = {}
        self._combos: Dict[uuid.UUID, ComboDefinition] = {}
        self._combo_by_slug: Dict[str, uuid.UUID] = {}
        # (combo_id, region_code) → ComboRate
        self._rates: Dict[Tuple[uuid.UUID, str], ComboRate] = {}
        # rate_version counter per combo
        self._rate_versions: Dict[uuid.UUID, int] = {}

    # ── apply ──────────────────────────────────────────────────

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == ENGINE_REGISTERED_V1:
            self._apply_engine_registered(payload)
        elif event_type == COMBO_DEFINED_V1:
            self._apply_combo_defined(payload)
        elif event_type == COMBO_UPDATED_V1:
            self._apply_combo_updated(payload)
        elif event_type == COMBO_DEACTIVATED_V1:
            self._apply_combo_deactivated(payload)
        elif event_type == COMBO_RATE_SET_V1:
            self._apply_rate_set(payload)

    def _apply_engine_registered(self, payload: Dict[str, Any]) -> None:
        key = payload["engine_key"]
        cat = EngineCategory(payload.get("category", "PAID"))
        self._engines[key] = EngineEntry(
            engine_key=key,
            display_name=payload.get("display_name", key),
            category=cat,
            description=payload.get("description", ""),
        )

    def _apply_combo_defined(self, payload: Dict[str, Any]) -> None:
        combo_id = uuid.UUID(str(payload["combo_id"]))
        bm = BusinessModel(payload.get("business_model", "BOTH"))
        engines = frozenset(payload.get("paid_engines", []))
        quota = PlanQuota(
            max_branches=payload.get("max_branches", 1),
            max_users=payload.get("max_users", 3),
            max_api_calls_per_month=payload.get("max_api_calls_per_month", 5000),
            max_documents_per_month=payload.get("max_documents_per_month", 500),
        )
        slug = payload.get("slug", "")
        self._combos[combo_id] = ComboDefinition(
            combo_id=combo_id,
            name=payload["name"],
            slug=slug,
            description=payload.get("description", ""),
            business_model=bm,
            paid_engines=engines,
            quota=quota,
            sort_order=payload.get("sort_order", 0),
            created_at=payload.get("issued_at"),
        )
        if slug:
            self._combo_by_slug[slug] = combo_id

    def _apply_combo_updated(self, payload: Dict[str, Any]) -> None:
        combo_id = uuid.UUID(str(payload["combo_id"]))
        old = self._combos.get(combo_id)
        if old is None:
            return
        engines = (
            frozenset(payload["paid_engines"])
            if "paid_engines" in payload
            else old.paid_engines
        )
        quota = PlanQuota(
            max_branches=payload.get("max_branches", old.quota.max_branches),
            max_users=payload.get("max_users", old.quota.max_users),
            max_api_calls_per_month=payload.get(
                "max_api_calls_per_month", old.quota.max_api_calls_per_month),
            max_documents_per_month=payload.get(
                "max_documents_per_month", old.quota.max_documents_per_month),
        )
        self._combos[combo_id] = ComboDefinition(
            combo_id=old.combo_id,
            name=payload.get("name", old.name),
            slug=old.slug,
            description=payload.get("description", old.description),
            business_model=old.business_model,
            paid_engines=engines,
            quota=quota,
            sort_order=payload.get("sort_order", old.sort_order),
            created_at=old.created_at,
            updated_at=payload.get("issued_at"),
        )

    def _apply_combo_deactivated(self, payload: Dict[str, Any]) -> None:
        combo_id = uuid.UUID(str(payload["combo_id"]))
        old = self._combos.get(combo_id)
        if old is None:
            return
        self._combos[combo_id] = ComboDefinition(
            combo_id=old.combo_id,
            name=old.name,
            slug=old.slug,
            description=old.description,
            business_model=old.business_model,
            paid_engines=old.paid_engines,
            quota=old.quota,
            status=ComboStatus.DEACTIVATED,
            sort_order=old.sort_order,
            created_at=old.created_at,
            updated_at=payload.get("issued_at"),
        )

    def _apply_rate_set(self, payload: Dict[str, Any]) -> None:
        combo_id = uuid.UUID(str(payload["combo_id"]))
        region_code = payload["region_code"]
        version = self._rate_versions.get(combo_id, 0) + 1
        self._rate_versions[combo_id] = version
        rate = ComboRate(
            combo_id=combo_id,
            region_code=region_code,
            currency=payload.get("currency", "USD"),
            monthly_amount=Decimal(str(payload["monthly_amount"])),
            rate_version=version,
            effective_from=payload.get("effective_from"),
        )
        self._rates[(combo_id, region_code)] = rate

    # ── queries ────────────────────────────────────────────────

    def get_engine(self, engine_key: str) -> Optional[EngineEntry]:
        return self._engines.get(engine_key)

    def list_engines(self) -> List[EngineEntry]:
        return list(self._engines.values())

    def get_combo(self, combo_id: uuid.UUID) -> Optional[ComboDefinition]:
        return self._combos.get(combo_id)

    def get_combo_by_slug(self, slug: str) -> Optional[ComboDefinition]:
        combo_id = self._combo_by_slug.get(slug)
        if combo_id is None:
            return None
        return self._combos.get(combo_id)

    def list_combos(self, active_only: bool = True) -> List[ComboDefinition]:
        combos = list(self._combos.values())
        if active_only:
            combos = [c for c in combos if c.status == ComboStatus.ACTIVE]
        combos.sort(key=lambda c: c.sort_order)
        return combos

    def list_combos_for_model(
        self, business_model: BusinessModel, active_only: bool = True,
    ) -> List[ComboDefinition]:
        """Return combos matching a business model (B2B, B2C, or BOTH)."""
        result = []
        for c in self.list_combos(active_only=active_only):
            if c.business_model == business_model or c.business_model == BusinessModel.BOTH:
                result.append(c)
        return result

    def get_rate(
        self, combo_id: uuid.UUID, region_code: str
    ) -> Optional[ComboRate]:
        return self._rates.get((combo_id, region_code))

    def list_rates_for_combo(self, combo_id: uuid.UUID) -> List[ComboRate]:
        return [
            r for r in self._rates.values()
            if r.combo_id == combo_id
        ]

    def list_rates_for_region(self, region_code: str) -> List[ComboRate]:
        return [
            r for r in self._rates.values()
            if r.region_code == region_code
        ]

    def get_combo_price_for_region(
        self, combo_id: uuid.UUID, region_code: str
    ) -> Optional[Dict[str, Any]]:
        """
        The core user-facing query:
        "I want combo X in region Y — what do I pay?"

        Returns combo details + region-specific price, or None.
        """
        combo = self._combos.get(combo_id)
        if combo is None or combo.status != ComboStatus.ACTIVE:
            return None
        rate = self._rates.get((combo_id, region_code))
        if rate is None:
            return None
        return {
            "combo_id": str(combo.combo_id),
            "combo_name": combo.name,
            "slug": combo.slug,
            "description": combo.description,
            "business_model": combo.business_model.value,
            "region_code": region_code,
            "currency": rate.currency,
            "monthly_amount": str(rate.monthly_amount),
            "rate_version": rate.rate_version,
            "free_engines": sorted(FREE_ENGINE_KEYS),
            "paid_engines": sorted(combo.paid_engines),
            "all_engines": sorted(combo.all_engines),
            "quota": {
                "max_branches": combo.quota.max_branches,
                "max_users": combo.quota.max_users,
                "max_api_calls_per_month": combo.quota.max_api_calls_per_month,
                "max_documents_per_month": combo.quota.max_documents_per_month,
            },
        }

    def truncate(self) -> None:
        self._engines.clear()
        self._combos.clear()
        self._combo_by_slug.clear()
        self._rates.clear()
        self._rate_versions.clear()


# ══════════════════════════════════════════════════════════════
# PLAN MANAGER — orchestrates combo operations
# ══════════════════════════════════════════════════════════════

class PlanManager:
    """
    Manages engine combos and region-specific pricing.

    All mutations produce events — no direct state writes.
    """

    def __init__(self, projection: PlanProjection) -> None:
        self._projection = projection

    def register_engine(self, request: RegisterEngineRequest) -> Dict[str, Any]:
        """Register an engine in the catalog."""
        try:
            EngineCategory(request.category)
        except ValueError:
            return {
                "rejected": RejectionReason(
                    code="INVALID_ENGINE_CATEGORY",
                    message=f"Invalid category: {request.category}. Must be FREE or PAID.",
                    policy_name="register_engine",
                ),
            }
        payload = {
            "engine_key": request.engine_key,
            "display_name": request.display_name,
            "category": request.category,
            "description": request.description,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(ENGINE_REGISTERED_V1, payload)
        return {
            "engine_key": request.engine_key,
            "events": [{"event_type": ENGINE_REGISTERED_V1, "payload": payload}],
        }

    def define_combo(self, request: DefineComboRequest) -> Dict[str, Any]:
        """Define a new engine combo (leadership decision)."""
        try:
            bm = BusinessModel(request.business_model)
        except ValueError:
            return {
                "rejected": RejectionReason(
                    code="INVALID_BUSINESS_MODEL",
                    message=f"Invalid business_model: {request.business_model}. "
                            f"Must be B2B, B2C, or BOTH.",
                    policy_name="define_combo",
                ),
            }

        # Check slug uniqueness
        existing = self._projection.get_combo_by_slug(request.slug)
        if existing is not None:
            return {
                "rejected": RejectionReason(
                    code="COMBO_SLUG_EXISTS",
                    message=f"A combo with slug '{request.slug}' already exists.",
                    policy_name="define_combo",
                ),
            }

        combo_id = uuid.uuid4()
        payload = {
            "combo_id": str(combo_id),
            "name": request.name,
            "slug": request.slug,
            "description": request.description,
            "business_model": bm.value,
            "paid_engines": list(request.paid_engines),
            "max_branches": request.max_branches,
            "max_users": request.max_users,
            "max_api_calls_per_month": request.max_api_calls_per_month,
            "max_documents_per_month": request.max_documents_per_month,
            "sort_order": request.sort_order,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(COMBO_DEFINED_V1, payload)
        return {
            "combo_id": combo_id,
            "events": [{"event_type": COMBO_DEFINED_V1, "payload": payload}],
        }

    def update_combo(
        self, request: UpdateComboRequest
    ) -> Optional[RejectionReason]:
        """Update an existing combo definition."""
        combo = self._projection.get_combo(request.combo_id)
        if combo is None:
            return RejectionReason(
                code="COMBO_NOT_FOUND",
                message="Combo not found.",
                policy_name="update_combo",
            )
        if combo.status != ComboStatus.ACTIVE:
            return RejectionReason(
                code="COMBO_DEACTIVATED",
                message="Cannot update a deactivated combo.",
                policy_name="update_combo",
            )
        payload: Dict[str, Any] = {
            "combo_id": str(request.combo_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        if request.name is not None:
            payload["name"] = request.name
        if request.description is not None:
            payload["description"] = request.description
        if request.paid_engines is not None:
            payload["paid_engines"] = list(request.paid_engines)
        if request.max_branches is not None:
            payload["max_branches"] = request.max_branches
        if request.max_users is not None:
            payload["max_users"] = request.max_users
        if request.max_api_calls_per_month is not None:
            payload["max_api_calls_per_month"] = request.max_api_calls_per_month
        if request.max_documents_per_month is not None:
            payload["max_documents_per_month"] = request.max_documents_per_month
        if request.sort_order is not None:
            payload["sort_order"] = request.sort_order
        self._projection.apply(COMBO_UPDATED_V1, payload)
        return None

    def deactivate_combo(
        self, request: DeactivateComboRequest
    ) -> Optional[RejectionReason]:
        """Deactivate a combo (no new signups, existing tenants unaffected)."""
        combo = self._projection.get_combo(request.combo_id)
        if combo is None:
            return RejectionReason(
                code="COMBO_NOT_FOUND",
                message="Combo not found.",
                policy_name="deactivate_combo",
            )
        if combo.status == ComboStatus.DEACTIVATED:
            return RejectionReason(
                code="COMBO_ALREADY_DEACTIVATED",
                message="Combo is already deactivated.",
                policy_name="deactivate_combo",
            )
        payload = {
            "combo_id": str(request.combo_id),
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(COMBO_DEACTIVATED_V1, payload)
        return None

    def set_combo_rate(self, request: SetComboRateRequest) -> Dict[str, Any]:
        """Set the monthly price for a combo in a specific region."""
        combo = self._projection.get_combo(request.combo_id)
        if combo is None:
            return {
                "rejected": RejectionReason(
                    code="COMBO_NOT_FOUND",
                    message="Combo not found.",
                    policy_name="set_combo_rate",
                ),
            }
        if request.monthly_amount < 0:
            return {
                "rejected": RejectionReason(
                    code="INVALID_RATE",
                    message="Monthly amount cannot be negative.",
                    policy_name="set_combo_rate",
                ),
            }
        payload = {
            "combo_id": str(request.combo_id),
            "region_code": request.region_code,
            "currency": request.currency,
            "monthly_amount": str(request.monthly_amount),
            "effective_from": request.effective_from,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(COMBO_RATE_SET_V1, payload)
        return {
            "events": [{"event_type": COMBO_RATE_SET_V1, "payload": payload}],
        }

    def resolve_engines_for_combo(
        self, combo_id: uuid.UUID
    ) -> FrozenSet[str]:
        """Return all engines a tenant gets for this combo (free + paid)."""
        combo = self._projection.get_combo(combo_id)
        if combo is None or combo.status != ComboStatus.ACTIVE:
            return FREE_ENGINE_KEYS  # at minimum, free engines
        return combo.all_engines

    def check_quota(
        self, combo_id: uuid.UUID, resource: str, current_usage: int
    ) -> Optional[RejectionReason]:
        """Check if usage is within combo quota limits."""
        combo = self._projection.get_combo(combo_id)
        if combo is None or combo.status != ComboStatus.ACTIVE:
            return RejectionReason(
                code="NO_ACTIVE_COMBO",
                message="No active combo found.",
                policy_name="check_quota",
            )
        limits = {
            "branches": combo.quota.max_branches,
            "users": combo.quota.max_users,
            "api_calls": combo.quota.max_api_calls_per_month,
            "documents": combo.quota.max_documents_per_month,
        }
        limit = limits.get(resource)
        if limit is None:
            return None
        if current_usage >= limit:
            return RejectionReason(
                code="QUOTA_EXCEEDED",
                message=f"Quota exceeded for {resource}: {current_usage}/{limit}.",
                policy_name="check_quota",
            )
        return None

    def get_pricing_catalog(
        self, region_code: str, business_model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        The user-facing catalog query:
        "Show me available combos for my region."

        Optionally filtered by business model (B2B/B2C).
        """
        bm_filter = None
        if business_model:
            try:
                bm_filter = BusinessModel(business_model)
            except ValueError:
                pass

        results = []
        combos = self._projection.list_combos(active_only=True)
        for combo in combos:
            if bm_filter and combo.business_model != bm_filter and combo.business_model != BusinessModel.BOTH:
                continue
            rate = self._projection.get_rate(combo.combo_id, region_code)
            if rate is None:
                continue  # combo not available in this region
            results.append({
                "combo_id": str(combo.combo_id),
                "name": combo.name,
                "slug": combo.slug,
                "description": combo.description,
                "business_model": combo.business_model.value,
                "currency": rate.currency,
                "monthly_amount": str(rate.monthly_amount),
                "free_engines": sorted(FREE_ENGINE_KEYS),
                "paid_engines": sorted(combo.paid_engines),
                "all_engines": sorted(combo.all_engines),
                "quota": {
                    "max_branches": combo.quota.max_branches,
                    "max_users": combo.quota.max_users,
                },
            })
        return results
