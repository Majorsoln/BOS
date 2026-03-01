"""
BOS SaaS — Regional Configuration Packs
===========================================
Country/region-specific configuration presets that auto-apply
tax rules, compliance defaults, currency, and date formats
when a tenant is provisioned.

Admin-only: only platform admins can define or apply packs.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# REGION PACK EVENT TYPES
# ══════════════════════════════════════════════════════════════

REGION_PACK_REGISTERED_V1 = "saas.region_pack.registered.v1"
REGION_PACK_APPLIED_V1 = "saas.region_pack.applied.v1"

REGION_PACK_EVENT_TYPES = (
    REGION_PACK_REGISTERED_V1,
    REGION_PACK_APPLIED_V1,
)


# ══════════════════════════════════════════════════════════════
# REGION PACK DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TaxPreset:
    """Tax rule preset within a region pack."""
    tax_code: str
    rate: Decimal
    description: str


@dataclass(frozen=True)
class RegionPack:
    """Immutable regional configuration pack."""
    pack_id: uuid.UUID
    region_code: str          # ISO 3166-1 alpha-2 or custom (e.g. "EAC")
    region_name: str
    default_currency: str     # ISO 4217
    default_timezone: str
    date_format: str          # e.g. "DD/MM/YYYY"
    tax_presets: Tuple[TaxPreset, ...]
    compliance_tags: Tuple[str, ...]
    created_at: Optional[datetime] = None


@dataclass(frozen=True)
class RegionPackApplication:
    """Record of a region pack being applied to a business."""
    business_id: uuid.UUID
    pack_id: uuid.UUID
    region_code: str
    applied_at: datetime
    applied_by: str


# ══════════════════════════════════════════════════════════════
# REGION PACK REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RegisterRegionPackRequest:
    region_code: str
    region_name: str
    default_currency: str
    default_timezone: str
    date_format: str
    tax_presets: Tuple[Dict[str, Any], ...]
    compliance_tags: Tuple[str, ...]
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class ApplyRegionPackRequest:
    business_id: uuid.UUID
    region_code: str
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# REGION PACK PROJECTION
# ══════════════════════════════════════════════════════════════

class RegionPackProjection:
    """
    In-memory projection of region packs and their applications.

    Rebuilt deterministically from region pack events.
    """

    projection_name = "region_pack_projection"

    def __init__(self) -> None:
        self._packs: Dict[str, RegionPack] = {}        # region_code → pack
        self._applications: Dict[uuid.UUID, RegionPackApplication] = {}  # business_id → application

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == REGION_PACK_REGISTERED_V1:
            pack_id = uuid.UUID(str(payload["pack_id"]))
            tax_presets = tuple(
                TaxPreset(
                    tax_code=t["tax_code"],
                    rate=Decimal(str(t["rate"])),
                    description=t.get("description", ""),
                )
                for t in payload.get("tax_presets", [])
            )
            compliance_tags = tuple(payload.get("compliance_tags", []))
            pack = RegionPack(
                pack_id=pack_id,
                region_code=payload["region_code"],
                region_name=payload.get("region_name", ""),
                default_currency=payload.get("default_currency", "USD"),
                default_timezone=payload.get("default_timezone", "UTC"),
                date_format=payload.get("date_format", "YYYY-MM-DD"),
                tax_presets=tax_presets,
                compliance_tags=compliance_tags,
                created_at=payload.get("issued_at"),
            )
            self._packs[pack.region_code] = pack

        elif event_type == REGION_PACK_APPLIED_V1:
            biz_id = uuid.UUID(str(payload["business_id"]))
            pack_id = uuid.UUID(str(payload["pack_id"]))
            self._applications[biz_id] = RegionPackApplication(
                business_id=biz_id,
                pack_id=pack_id,
                region_code=payload.get("region_code", ""),
                applied_at=payload.get("issued_at"),
                applied_by=payload.get("actor_id", ""),
            )

    def get_pack(self, region_code: str) -> Optional[RegionPack]:
        return self._packs.get(region_code)

    def list_packs(self) -> List[RegionPack]:
        return list(self._packs.values())

    def get_application(
        self, business_id: uuid.UUID
    ) -> Optional[RegionPackApplication]:
        return self._applications.get(business_id)

    def truncate(self) -> None:
        self._packs.clear()
        self._applications.clear()


# ══════════════════════════════════════════════════════════════
# REGION PACK SERVICE
# ══════════════════════════════════════════════════════════════

class RegionPackService:
    """
    Manages regional configuration packs.

    Admin-only: defines packs and applies them to tenants.
    All mutations produce events.
    """

    def __init__(self, projection: RegionPackProjection) -> None:
        self._projection = projection

    def register_pack(
        self, request: RegisterRegionPackRequest
    ) -> Dict[str, Any]:
        """Register a new region pack (or overwrite existing for the region)."""
        pack_id = uuid.uuid4()
        tax_presets_raw = [
            {
                "tax_code": t.get("tax_code", "") if isinstance(t, dict) else "",
                "rate": str(t.get("rate", "0")) if isinstance(t, dict) else "0",
                "description": t.get("description", "") if isinstance(t, dict) else "",
            }
            for t in request.tax_presets
        ]
        payload = {
            "pack_id": str(pack_id),
            "region_code": request.region_code,
            "region_name": request.region_name,
            "default_currency": request.default_currency,
            "default_timezone": request.default_timezone,
            "date_format": request.date_format,
            "tax_presets": tax_presets_raw,
            "compliance_tags": list(request.compliance_tags),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(REGION_PACK_REGISTERED_V1, payload)
        return {
            "pack_id": pack_id,
            "events": [{"event_type": REGION_PACK_REGISTERED_V1, "payload": payload}],
        }

    def apply_pack(
        self, request: ApplyRegionPackRequest
    ) -> Optional[RejectionReason]:
        """Apply a region pack to a business tenant."""
        pack = self._projection.get_pack(request.region_code)
        if pack is None:
            return RejectionReason(
                code="REGION_PACK_NOT_FOUND",
                message=f"No region pack found for: {request.region_code}.",
                policy_name="apply_region_pack",
            )
        payload = {
            "business_id": str(request.business_id),
            "pack_id": str(pack.pack_id),
            "region_code": request.region_code,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(REGION_PACK_APPLIED_V1, payload)
        return None

    def get_tax_presets_for_business(
        self, business_id: uuid.UUID
    ) -> List[TaxPreset]:
        """Return the tax presets from the business's applied region pack."""
        app = self._projection.get_application(business_id)
        if app is None:
            return []
        pack = self._projection.get_pack(app.region_code)
        if pack is None:
            return []
        return list(pack.tax_presets)

    def get_region_defaults(
        self, region_code: str
    ) -> Optional[Dict[str, Any]]:
        """Return the defaults for a region."""
        pack = self._projection.get_pack(region_code)
        if pack is None:
            return None
        return {
            "region_code": pack.region_code,
            "region_name": pack.region_name,
            "default_currency": pack.default_currency,
            "default_timezone": pack.default_timezone,
            "date_format": pack.date_format,
            "tax_presets": [
                {"tax_code": t.tax_code, "rate": str(t.rate), "description": t.description}
                for t in pack.tax_presets
            ],
            "compliance_tags": list(pack.compliance_tags),
        }
