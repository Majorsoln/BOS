"""
BOS SaaS — Service-Based Pricing Engine
========================================
Replaces combo-based pricing with a 3-layer model:
  1. Services  — monthly rate per service per region
  2. Capacity  — tiered pricing per dimension per region
  3. Reductions — multi-service discount on service total

Also manages regions (countries) as dynamic entities.

Formula:
  monthly_total = (service_total - service_total * reduction_rate) + capacity_total
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RegionEntry:
    code: str
    name: str
    currency: str
    tax_name: str = "VAT"
    vat_rate: float = 0.0
    digital_tax_rate: float = 0.0
    b2b_reverse_charge: bool = False
    registration_required: bool = True
    is_active: bool = True


@dataclass
class ServiceRate:
    service_key: str
    region_code: str
    currency: str
    monthly_amount: Decimal


@dataclass
class CapacityTierRate:
    dimension: str
    tier_key: str
    region_code: str
    currency: str
    monthly_amount: Decimal


@dataclass
class ReductionRate:
    region_code: str
    service_count: int
    reduction_pct: Decimal  # e.g. 10 = 10%


@dataclass
class PriceBreakdown:
    region_code: str
    currency: str
    service_lines: List[Dict]       # [{service_key, monthly_amount}]
    service_total: Decimal
    reduction_pct: Decimal
    reduction_amount: Decimal
    service_after_reduction: Decimal
    capacity_lines: List[Dict]      # [{dimension, tier_key, monthly_amount}]
    capacity_total: Decimal
    monthly_total: Decimal


# ---------------------------------------------------------------------------
# Projection — in-memory state
# ---------------------------------------------------------------------------

class ServicePricingProjection:
    """In-memory state for service-based pricing."""

    def __init__(self) -> None:
        self._regions: Dict[str, RegionEntry] = {}
        self._service_active: Dict[str, bool] = {}
        self._service_rates: Dict[Tuple[str, str], ServiceRate] = {}       # (service_key, region_code)
        self._capacity_rates: Dict[Tuple[str, str, str], CapacityTierRate] = {}  # (dim, tier, region)
        self._reductions: Dict[Tuple[str, int], ReductionRate] = {}        # (region_code, count)

    # ── Apply events ────────────────────────────────────────────

    def apply(self, event_type: str, payload: dict) -> None:
        handler = {
            "saas.region.added.v1": self._apply_region_added,
            "saas.region.updated.v1": self._apply_region_updated,
            "saas.service.rate_set.v1": self._apply_service_rate_set,
            "saas.service.toggled.v1": self._apply_service_toggled,
            "saas.capacity.rate_set.v1": self._apply_capacity_rate_set,
            "saas.reduction.rate_set.v1": self._apply_reduction_rate_set,
        }.get(event_type)
        if handler:
            handler(payload)

    def _apply_region_added(self, p: dict) -> None:
        code = p["code"]
        self._regions[code] = RegionEntry(
            code=code,
            name=p.get("name", code),
            currency=p.get("currency", "USD"),
            tax_name=p.get("tax_name", "VAT"),
            vat_rate=float(p.get("vat_rate", 0)),
            digital_tax_rate=float(p.get("digital_tax_rate", 0)),
            b2b_reverse_charge=bool(p.get("b2b_reverse_charge", False)),
            registration_required=bool(p.get("registration_required", True)),
            is_active=bool(p.get("is_active", True)),
        )

    def _apply_region_updated(self, p: dict) -> None:
        code = p["code"]
        existing = self._regions.get(code)
        if not existing:
            self._apply_region_added(p)
            return
        if "name" in p:
            existing.name = p["name"]
        if "currency" in p:
            existing.currency = p["currency"]
        if "tax_name" in p:
            existing.tax_name = p["tax_name"]
        if "vat_rate" in p:
            existing.vat_rate = float(p["vat_rate"])
        if "digital_tax_rate" in p:
            existing.digital_tax_rate = float(p["digital_tax_rate"])
        if "b2b_reverse_charge" in p:
            existing.b2b_reverse_charge = bool(p["b2b_reverse_charge"])
        if "registration_required" in p:
            existing.registration_required = bool(p["registration_required"])
        if "is_active" in p:
            existing.is_active = bool(p["is_active"])

    def _apply_service_rate_set(self, p: dict) -> None:
        key = (p["service_key"], p["region_code"])
        self._service_rates[key] = ServiceRate(
            service_key=p["service_key"],
            region_code=p["region_code"],
            currency=p.get("currency", "USD"),
            monthly_amount=Decimal(str(p["monthly_amount"])),
        )

    def _apply_service_toggled(self, p: dict) -> None:
        self._service_active[p["service_key"]] = bool(p["active"])

    def _apply_capacity_rate_set(self, p: dict) -> None:
        key = (p["dimension"], p["tier_key"], p["region_code"])
        self._capacity_rates[key] = CapacityTierRate(
            dimension=p["dimension"],
            tier_key=p["tier_key"],
            region_code=p["region_code"],
            currency=p.get("currency", "USD"),
            monthly_amount=Decimal(str(p["monthly_amount"])),
        )

    def _apply_reduction_rate_set(self, p: dict) -> None:
        key = (p["region_code"], int(p["service_count"]))
        self._reductions[key] = ReductionRate(
            region_code=p["region_code"],
            service_count=int(p["service_count"]),
            reduction_pct=Decimal(str(p["reduction_pct"])),
        )

    # ── Query methods ───────────────────────────────────────────

    def list_regions(self) -> List[RegionEntry]:
        return sorted(self._regions.values(), key=lambda r: r.code)

    def get_region(self, code: str) -> Optional[RegionEntry]:
        return self._regions.get(code)

    def get_service_rates(self) -> Dict[str, Dict[str, dict]]:
        """Returns {service_key: {region_code: {monthly_amount, currency}}}."""
        out: Dict[str, Dict[str, dict]] = {}
        for (svc, rgn), rate in self._service_rates.items():
            out.setdefault(svc, {})[rgn] = {
                "monthly_amount": float(rate.monthly_amount),
                "currency": rate.currency,
            }
        return out

    def get_service_active_map(self) -> Dict[str, bool]:
        return dict(self._service_active)

    def get_capacity_rates(self) -> Dict[str, Dict[str, Dict[str, dict]]]:
        """Returns {dimension: {tier_key: {region_code: {monthly_amount, currency}}}}."""
        out: Dict[str, Dict[str, Dict[str, dict]]] = {}
        for (dim, tier, rgn), rate in self._capacity_rates.items():
            out.setdefault(dim, {}).setdefault(tier, {})[rgn] = {
                "monthly_amount": float(rate.monthly_amount),
                "currency": rate.currency,
            }
        return out

    def get_reduction_rates(self) -> Dict[str, Dict[int, float]]:
        """Returns {region_code: {service_count: reduction_pct}}."""
        out: Dict[str, Dict[int, float]] = {}
        for (rgn, cnt), rate in self._reductions.items():
            out.setdefault(rgn, {})[cnt] = float(rate.reduction_pct)
        return out

    def calculate_price(
        self,
        region_code: str,
        service_keys: List[str],
        capacity_selections: Dict[str, str],
    ) -> Optional[PriceBreakdown]:
        """Calculate monthly total for a given configuration."""
        region = self._regions.get(region_code)
        if not region:
            return None
        currency = region.currency

        # Service lines
        service_lines = []
        service_total = Decimal("0")
        for svc_key in service_keys:
            rate = self._service_rates.get((svc_key, region_code))
            amount = rate.monthly_amount if rate else Decimal("0")
            service_lines.append({"service_key": svc_key, "monthly_amount": float(amount)})
            service_total += amount

        # Reduction
        svc_count = len(service_keys)
        reduction_entry = self._reductions.get((region_code, svc_count))
        reduction_pct = reduction_entry.reduction_pct if reduction_entry else Decimal("0")
        reduction_amount = service_total * reduction_pct / Decimal("100")
        service_after_reduction = service_total - reduction_amount

        # Capacity lines
        capacity_lines = []
        capacity_total = Decimal("0")
        for dim, tier_key in capacity_selections.items():
            rate = self._capacity_rates.get((dim.upper(), tier_key, region_code))
            amount = rate.monthly_amount if rate else Decimal("0")
            capacity_lines.append({
                "dimension": dim,
                "tier_key": tier_key,
                "monthly_amount": float(amount),
            })
            capacity_total += amount

        monthly_total = service_after_reduction + capacity_total

        return PriceBreakdown(
            region_code=region_code,
            currency=currency,
            service_lines=service_lines,
            service_total=service_total,
            reduction_pct=reduction_pct,
            reduction_amount=reduction_amount,
            service_after_reduction=service_after_reduction,
            capacity_lines=capacity_lines,
            capacity_total=capacity_total,
            monthly_total=monthly_total,
        )
