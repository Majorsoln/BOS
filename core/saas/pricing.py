"""
BOS SaaS — Service-Based Pricing Engine
========================================
Replaces combo-based pricing with a 3-layer model:
  1. Services  — monthly rate per service per region
  2. Capacity  — tiered pricing per dimension per region
  3. Reductions — multi-service discount on service total

Also manages regions (countries/markets) as full operational entities with:
  - Financial channels (M-Pesa, MTN MoMo, bank settlement)
  - Lifecycle management (DRAFT → PILOT → ACTIVE → SUSPENDED → SUNSET)
  - Regulatory compliance settings
  - Support & operations configuration

Formula:
  monthly_total = (service_total - service_total * reduction_rate) + capacity_total
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Region lifecycle
# ---------------------------------------------------------------------------

class RegionStatus(Enum):
    DRAFT = "DRAFT"           # Region configured but not launched
    PILOT = "PILOT"           # Limited rollout — capped tenant count
    ACTIVE = "ACTIVE"         # Fully live — accepting all tenants
    SUSPENDED = "SUSPENDED"   # Temporarily halted — no new signups, existing tenants OK
    SUNSET = "SUNSET"         # Winding down — no new signups, migration out encouraged


# Region lifecycle event types
REGION_ADDED_V1 = "saas.region.added.v1"
REGION_UPDATED_V1 = "saas.region.updated.v1"
REGION_LAUNCHED_V1 = "saas.region.launched.v1"
REGION_SUSPENDED_V1 = "saas.region.suspended.v1"
REGION_REACTIVATED_V1 = "saas.region.reactivated.v1"
REGION_SUNSET_V1 = "saas.region.sunset.v1"
REGION_PAYMENT_CHANNEL_SET_V1 = "saas.region.payment_channel_set.v1"
REGION_PAYMENT_CHANNEL_REMOVED_V1 = "saas.region.payment_channel_removed.v1"
REGION_SETTLEMENT_SET_V1 = "saas.region.settlement_set.v1"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PaymentChannelConfig:
    """A payment collection method available in a region."""
    channel_key: str              # e.g. "mpesa_ke", "mtn_momo_ug", "flutterwave", "bank_transfer"
    display_name: str             # e.g. "M-Pesa (Kenya)"
    provider: str                 # e.g. "SAFARICOM", "MTN", "FLUTTERWAVE", "DPO"
    channel_type: str             # MOBILE_MONEY, CARD, BANK_TRANSFER, USSD
    is_active: bool
    config: Dict[str, Any]        # provider-specific: paybill, shortcode, api_key_ref, etc.
    min_amount: Decimal           # minimum transaction amount
    max_amount: Decimal           # maximum per transaction
    settlement_delay_days: int    # T+N settlement


@dataclass
class SettlementAccountConfig:
    """Where collected funds settle for a region."""
    bank_name: str
    account_name: str
    account_number: str
    branch_code: str
    swift_code: str
    currency: str
    is_primary: bool


@dataclass
class RegionEntry:
    """Full operational definition of a market/country."""
    # ── Identity ──
    code: str                         # ISO 3166-1 alpha-2 (KE, TZ, UG, RW, ET, etc.)
    name: str                         # "Kenya", "Tanzania", etc.
    currency: str                     # ISO 4217 (KES, TZS, UGX, RWF, ETB)
    status: str = "ACTIVE"            # RegionStatus value

    # ── Tax & Compliance ──
    tax_name: str = "VAT"
    vat_rate: float = 0.0             # e.g. 0.16 = 16%
    digital_tax_rate: float = 0.0     # digital services tax
    b2b_reverse_charge: bool = False
    registration_required: bool = True
    regulatory_body: str = ""         # e.g. "KRA" (Kenya Revenue Authority)
    business_license_required: bool = True
    data_residency_required: bool = False   # must data stay in-country?

    # ── Financial ──
    payment_channels: Dict[str, PaymentChannelConfig] = field(default_factory=dict)
    settlement_accounts: List[SettlementAccountConfig] = field(default_factory=list)
    min_payout_amount: Decimal = Decimal("0")    # minimum commission payout
    payout_currency: str = ""         # currency for reseller payouts (defaults to region currency)

    # ── Operations ──
    default_language: str = "en"      # ISO 639-1
    timezone: str = "Africa/Nairobi"  # IANA timezone
    support_phone: str = ""
    support_email: str = ""
    support_hours: str = ""           # e.g. "Mon-Fri 08:00-18:00 EAT"
    country_calling_code: str = ""    # e.g. "+254"
    phone_format: str = ""            # e.g. "07XXXXXXXX" or "+2547XXXXXXXX"

    # ── Launch Management ──
    launched_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    sunset_at: Optional[datetime] = None
    pilot_tenant_limit: int = 0       # 0 = no limit (fully active)
    pilot_tenant_count: int = 0       # current count during pilot
    launch_notes: str = ""

    # ── Governance (Two-Level Model per Governance Memo) ──
    region_owner_type: str = "PLATFORM"   # PLATFORM | AGENT | PARTNER
    region_owner_id: str = ""             # reseller_id or partner_id if not PLATFORM
    filing_owner: str = "MAIN_ADMIN"      # MAIN_ADMIN | REGION_AGENT — who files taxes?
    privacy_regime: str = "NONE"          # NONE | KENYA_DPA | GDPR | POPIA | etc.
    privacy_regulator: str = ""           # e.g. "ODPC", "ICO"
    data_localization: str = "NONE"       # NONE | IN_COUNTRY | IN_REGION | ANYWHERE
    e_invoicing_system: str = ""          # eTIMS, EFDMS, EFRIS, etc.
    e_invoicing_mandatory: bool = False
    fiscal_year_start_month: int = 1      # 1=Jan, 7=Jul
    reporting_frequency: str = "MONTHLY"  # MONTHLY | QUARTERLY | ANNUAL
    compliance_pack_ref: str = ""         # pinned compliance pack for this region
    escalation_email: str = ""            # compliance escalation contact
    local_payment_processor: str = ""     # primary local payment processor
    withholding_tax_rate: float = 0.0     # WHT rate for this region
    transfer_pricing_required: bool = False

    # ── Legacy ──
    is_active: bool = True            # backward compat — derived from status


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
            REGION_ADDED_V1: self._apply_region_added,
            REGION_UPDATED_V1: self._apply_region_updated,
            REGION_LAUNCHED_V1: self._apply_region_launched,
            REGION_SUSPENDED_V1: self._apply_region_suspended,
            REGION_REACTIVATED_V1: self._apply_region_reactivated,
            REGION_SUNSET_V1: self._apply_region_sunset,
            REGION_PAYMENT_CHANNEL_SET_V1: self._apply_payment_channel_set,
            REGION_PAYMENT_CHANNEL_REMOVED_V1: self._apply_payment_channel_removed,
            REGION_SETTLEMENT_SET_V1: self._apply_settlement_set,
            "saas.service.rate_set.v1": self._apply_service_rate_set,
            "saas.service.toggled.v1": self._apply_service_toggled,
            "saas.capacity.rate_set.v1": self._apply_capacity_rate_set,
            "saas.reduction.rate_set.v1": self._apply_reduction_rate_set,
        }.get(event_type)
        if handler:
            handler(payload)

    def _apply_region_added(self, p: dict) -> None:
        code = p["code"]
        status_val = p.get("status", "ACTIVE")
        self._regions[code] = RegionEntry(
            code=code,
            name=p.get("name", code),
            currency=p.get("currency", "USD"),
            status=status_val,
            tax_name=p.get("tax_name", "VAT"),
            vat_rate=float(p.get("vat_rate", 0)),
            digital_tax_rate=float(p.get("digital_tax_rate", 0)),
            b2b_reverse_charge=bool(p.get("b2b_reverse_charge", False)),
            registration_required=bool(p.get("registration_required", True)),
            regulatory_body=p.get("regulatory_body", ""),
            business_license_required=bool(p.get("business_license_required", True)),
            data_residency_required=bool(p.get("data_residency_required", False)),
            min_payout_amount=Decimal(str(p.get("min_payout_amount", "0"))),
            payout_currency=p.get("payout_currency", ""),
            default_language=p.get("default_language", "en"),
            timezone=p.get("timezone", "Africa/Nairobi"),
            support_phone=p.get("support_phone", ""),
            support_email=p.get("support_email", ""),
            support_hours=p.get("support_hours", ""),
            country_calling_code=p.get("country_calling_code", ""),
            phone_format=p.get("phone_format", ""),
            pilot_tenant_limit=int(p.get("pilot_tenant_limit", 0)),
            launch_notes=p.get("launch_notes", ""),
            # Governance
            region_owner_type=p.get("region_owner_type", "PLATFORM"),
            region_owner_id=p.get("region_owner_id", ""),
            filing_owner=p.get("filing_owner", "MAIN_ADMIN"),
            privacy_regime=p.get("privacy_regime", "NONE"),
            privacy_regulator=p.get("privacy_regulator", ""),
            data_localization=p.get("data_localization", "NONE"),
            e_invoicing_system=p.get("e_invoicing_system", ""),
            e_invoicing_mandatory=bool(p.get("e_invoicing_mandatory", False)),
            fiscal_year_start_month=int(p.get("fiscal_year_start_month", 1)),
            reporting_frequency=p.get("reporting_frequency", "MONTHLY"),
            compliance_pack_ref=p.get("compliance_pack_ref", ""),
            escalation_email=p.get("escalation_email", ""),
            local_payment_processor=p.get("local_payment_processor", ""),
            withholding_tax_rate=float(p.get("withholding_tax_rate", 0)),
            transfer_pricing_required=bool(p.get("transfer_pricing_required", False)),
            is_active=status_val in ("ACTIVE", "PILOT"),
        )

    def _apply_region_updated(self, p: dict) -> None:
        code = p["code"]
        existing = self._regions.get(code)
        if not existing:
            self._apply_region_added(p)
            return
        # Tax & compliance
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
        if "regulatory_body" in p:
            existing.regulatory_body = p["regulatory_body"]
        if "business_license_required" in p:
            existing.business_license_required = bool(p["business_license_required"])
        if "data_residency_required" in p:
            existing.data_residency_required = bool(p["data_residency_required"])
        # Financial
        if "min_payout_amount" in p:
            existing.min_payout_amount = Decimal(str(p["min_payout_amount"]))
        if "payout_currency" in p:
            existing.payout_currency = p["payout_currency"]
        # Operations
        if "default_language" in p:
            existing.default_language = p["default_language"]
        if "timezone" in p:
            existing.timezone = p["timezone"]
        if "support_phone" in p:
            existing.support_phone = p["support_phone"]
        if "support_email" in p:
            existing.support_email = p["support_email"]
        if "support_hours" in p:
            existing.support_hours = p["support_hours"]
        if "country_calling_code" in p:
            existing.country_calling_code = p["country_calling_code"]
        if "phone_format" in p:
            existing.phone_format = p["phone_format"]
        # Launch
        if "pilot_tenant_limit" in p:
            existing.pilot_tenant_limit = int(p["pilot_tenant_limit"])
        if "launch_notes" in p:
            existing.launch_notes = p["launch_notes"]
        # Governance
        if "region_owner_type" in p:
            existing.region_owner_type = p["region_owner_type"]
        if "region_owner_id" in p:
            existing.region_owner_id = p["region_owner_id"]
        if "filing_owner" in p:
            existing.filing_owner = p["filing_owner"]
        if "privacy_regime" in p:
            existing.privacy_regime = p["privacy_regime"]
        if "privacy_regulator" in p:
            existing.privacy_regulator = p["privacy_regulator"]
        if "data_localization" in p:
            existing.data_localization = p["data_localization"]
        if "e_invoicing_system" in p:
            existing.e_invoicing_system = p["e_invoicing_system"]
        if "e_invoicing_mandatory" in p:
            existing.e_invoicing_mandatory = bool(p["e_invoicing_mandatory"])
        if "fiscal_year_start_month" in p:
            existing.fiscal_year_start_month = int(p["fiscal_year_start_month"])
        if "reporting_frequency" in p:
            existing.reporting_frequency = p["reporting_frequency"]
        if "compliance_pack_ref" in p:
            existing.compliance_pack_ref = p["compliance_pack_ref"]
        if "escalation_email" in p:
            existing.escalation_email = p["escalation_email"]
        if "local_payment_processor" in p:
            existing.local_payment_processor = p["local_payment_processor"]
        if "withholding_tax_rate" in p:
            existing.withholding_tax_rate = float(p["withholding_tax_rate"])
        if "transfer_pricing_required" in p:
            existing.transfer_pricing_required = bool(p["transfer_pricing_required"])
        # Legacy compat
        if "is_active" in p:
            existing.is_active = bool(p["is_active"])
        if "status" in p:
            existing.status = p["status"]
            existing.is_active = p["status"] in ("ACTIVE", "PILOT")

    def _apply_region_launched(self, p: dict) -> None:
        code = p["code"]
        existing = self._regions.get(code)
        if not existing:
            return
        target = p.get("target_status", "ACTIVE")
        existing.status = target
        existing.is_active = True
        existing.launched_at = p.get("issued_at")
        if target == "PILOT":
            existing.pilot_tenant_limit = int(p.get("pilot_tenant_limit", 50))

    def _apply_region_suspended(self, p: dict) -> None:
        code = p["code"]
        existing = self._regions.get(code)
        if not existing:
            return
        existing.status = RegionStatus.SUSPENDED.value
        existing.is_active = False
        existing.suspended_at = p.get("issued_at")

    def _apply_region_reactivated(self, p: dict) -> None:
        code = p["code"]
        existing = self._regions.get(code)
        if not existing:
            return
        existing.status = RegionStatus.ACTIVE.value
        existing.is_active = True
        existing.suspended_at = None

    def _apply_region_sunset(self, p: dict) -> None:
        code = p["code"]
        existing = self._regions.get(code)
        if not existing:
            return
        existing.status = RegionStatus.SUNSET.value
        existing.is_active = False
        existing.sunset_at = p.get("issued_at")

    def _apply_payment_channel_set(self, p: dict) -> None:
        code = p["region_code"]
        existing = self._regions.get(code)
        if not existing:
            return
        channel_key = p["channel_key"]
        existing.payment_channels[channel_key] = PaymentChannelConfig(
            channel_key=channel_key,
            display_name=p.get("display_name", channel_key),
            provider=p.get("provider", ""),
            channel_type=p.get("channel_type", "MOBILE_MONEY"),
            is_active=bool(p.get("is_active", True)),
            config=p.get("config", {}),
            min_amount=Decimal(str(p.get("min_amount", "0"))),
            max_amount=Decimal(str(p.get("max_amount", "999999999"))),
            settlement_delay_days=int(p.get("settlement_delay_days", 1)),
        )

    def _apply_payment_channel_removed(self, p: dict) -> None:
        code = p["region_code"]
        existing = self._regions.get(code)
        if not existing:
            return
        existing.payment_channels.pop(p["channel_key"], None)

    def _apply_settlement_set(self, p: dict) -> None:
        code = p["region_code"]
        existing = self._regions.get(code)
        if not existing:
            return
        account = SettlementAccountConfig(
            bank_name=p.get("bank_name", ""),
            account_name=p.get("account_name", ""),
            account_number=p.get("account_number", ""),
            branch_code=p.get("branch_code", ""),
            swift_code=p.get("swift_code", ""),
            currency=p.get("currency", existing.currency),
            is_primary=bool(p.get("is_primary", True)),
        )
        # Replace primary or append
        if account.is_primary:
            existing.settlement_accounts = [
                a for a in existing.settlement_accounts if not a.is_primary
            ]
        existing.settlement_accounts.append(account)

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

    def list_regions_by_status(self, status: str) -> List[RegionEntry]:
        return sorted(
            [r for r in self._regions.values() if r.status == status],
            key=lambda r: r.code,
        )

    def get_region_payment_channels(self, code: str) -> List[PaymentChannelConfig]:
        region = self._regions.get(code)
        if not region:
            return []
        return list(region.payment_channels.values())

    def get_region_settlement_accounts(self, code: str) -> List[SettlementAccountConfig]:
        region = self._regions.get(code)
        if not region:
            return []
        return list(region.settlement_accounts)

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
