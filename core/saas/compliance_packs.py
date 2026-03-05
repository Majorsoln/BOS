"""
BOS SaaS — Versioned Compliance Packs
========================================
Compliance packs are versioned, immutable documents.

Additive-only rules:
  - A new pack version NEVER deletes or modifies the old version.
  - Existing tenants remain on their PINNED version until they
    explicitly upgrade (opt-in only, never forced).
  - Each pack version carries: tax rules, receipt requirements,
    data retention policy, invoice fields, e-signature requirements.
  - Platform admin publishes new versions. Tenant admin upgrades.

Pack versioning:
  pack_id      = stable identifier for the region's pack family (e.g. "KE", "EU")
  version      = monotonically increasing integer (v1, v2, v3…)
  pack_ref     = "{region_code}:v{version}" e.g. "KE:v2"

Tenant pinning:
  Each tenant has a pinned_pack_ref per region.
  When a tenant onboards, they receive the latest version at that time.
  Future pack versions are opt-in.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# COMPLIANCE PACK EVENT TYPES
# ══════════════════════════════════════════════════════════════

COMPLIANCE_PACK_PUBLISHED_V1   = "saas.compliance_pack.published.v1"
COMPLIANCE_PACK_DEPRECATED_V1  = "saas.compliance_pack.deprecated.v1"
TENANT_PACK_PINNED_V1          = "saas.tenant.compliance_pack.pinned.v1"
TENANT_PACK_UPGRADED_V1        = "saas.tenant.compliance_pack.upgraded.v1"

COMPLIANCE_PACK_EVENT_TYPES = (
    COMPLIANCE_PACK_PUBLISHED_V1,
    COMPLIANCE_PACK_DEPRECATED_V1,
    TENANT_PACK_PINNED_V1,
    TENANT_PACK_UPGRADED_V1,
)


# ══════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TaxRule:
    """A single tax rule within a compliance pack."""
    tax_code: str
    rate: Decimal
    description: str
    applies_to: Tuple[str, ...]    # e.g. ("GOODS", "SERVICES")
    is_compound: bool = False      # compound tax (applied on top of another)


@dataclass(frozen=True)
class ReceiptRequirement:
    """Legal requirements for receipts in this jurisdiction."""
    require_sequential_number: bool
    require_tax_number: bool        # business TIN/VAT on receipt
    require_customer_tax_id: bool   # customer VAT for B2B invoices
    require_digital_signature: bool
    require_qr_code: bool           # e.g. KRA TIMS QR code
    number_prefix_format: str       # e.g. "RCP-{YYYY}-{NNNNN}"


@dataclass(frozen=True)
class DataRetentionPolicy:
    """Statutory data retention requirements."""
    financial_records_years: int   # how long invoices/receipts must be kept
    audit_log_years: int
    personal_data_years: int
    region_law_reference: str      # e.g. "Kenya VAT Act Cap 476"


@dataclass(frozen=True)
class CompliancePackVersion:
    """
    One immutable version of a regional compliance pack.
    Published once — never modified.
    """
    region_code: str
    version: int                   # monotonically increasing
    pack_ref: str                  # "{region_code}:v{version}"
    display_name: str
    effective_date: datetime       # when this version takes legal effect
    published_at: datetime
    published_by: str
    tax_rules: Tuple[TaxRule, ...]
    receipt_requirements: ReceiptRequirement
    data_retention: DataRetentionPolicy
    required_invoice_fields: Tuple[str, ...]   # fields that MUST appear on invoices
    optional_invoice_fields: Tuple[str, ...]
    change_summary: str            # human-readable summary of changes vs previous
    deprecated: bool = False
    deprecated_at: Optional[datetime] = None
    superseded_by: Optional[str] = None       # pack_ref of replacement


@dataclass(frozen=True)
class TenantPackPin:
    """Records a tenant's pinned compliance pack version."""
    tenant_id: str
    region_code: str
    pack_ref: str
    pinned_at: datetime
    pinned_by: str


# ══════════════════════════════════════════════════════════════
# REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PublishCompliancePackRequest:
    region_code: str
    display_name: str
    effective_date: datetime
    tax_rules: Tuple[Dict[str, Any], ...]
    receipt_requirements: Dict[str, Any]
    data_retention: Dict[str, Any]
    required_invoice_fields: Tuple[str, ...]
    optional_invoice_fields: Tuple[str, ...]
    change_summary: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class DeprecateCompliancePackRequest:
    region_code: str
    version: int
    superseded_by_version: int
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class PinTenantPackRequest:
    tenant_id: str
    region_code: str
    version: int
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class UpgradeTenantPackRequest:
    tenant_id: str
    region_code: str
    to_version: int
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# PROJECTION
# ══════════════════════════════════════════════════════════════

class CompliancePackProjection:
    """
    In-memory projection of compliance pack versions and tenant pins.
    Rebuilt deterministically from compliance pack events.
    """

    projection_name = "compliance_pack_projection"

    def __init__(self) -> None:
        # "{region_code}:v{version}" → CompliancePackVersion
        self._packs: Dict[str, CompliancePackVersion] = {}
        # region_code → sorted list of versions (ascending)
        self._versions_by_region: Dict[str, List[int]] = {}
        # "{tenant_id}:{region_code}" → TenantPackPin
        self._tenant_pins: Dict[str, TenantPackPin] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == COMPLIANCE_PACK_PUBLISHED_V1:
            self._apply_published(payload)
        elif event_type == COMPLIANCE_PACK_DEPRECATED_V1:
            self._apply_deprecated(payload)
        elif event_type in (TENANT_PACK_PINNED_V1, TENANT_PACK_UPGRADED_V1):
            self._apply_pin(payload)

    def _apply_published(self, payload: Dict[str, Any]) -> None:
        region_code = payload["region_code"]
        version = int(payload["version"])
        pack_ref = f"{region_code}:v{version}"

        tax_rules = tuple(
            TaxRule(
                tax_code=t["tax_code"],
                rate=Decimal(str(t["rate"])),
                description=t.get("description", ""),
                applies_to=tuple(t.get("applies_to", [])),
                is_compound=t.get("is_compound", False),
            )
            for t in payload.get("tax_rules", [])
        )

        rr = payload.get("receipt_requirements", {})
        receipt_req = ReceiptRequirement(
            require_sequential_number=rr.get("require_sequential_number", True),
            require_tax_number=rr.get("require_tax_number", True),
            require_customer_tax_id=rr.get("require_customer_tax_id", False),
            require_digital_signature=rr.get("require_digital_signature", False),
            require_qr_code=rr.get("require_qr_code", False),
            number_prefix_format=rr.get("number_prefix_format", "RCP-{YYYY}-{NNNNN}"),
        )

        dr = payload.get("data_retention", {})
        data_ret = DataRetentionPolicy(
            financial_records_years=dr.get("financial_records_years", 7),
            audit_log_years=dr.get("audit_log_years", 7),
            personal_data_years=dr.get("personal_data_years", 5),
            region_law_reference=dr.get("region_law_reference", ""),
        )

        pack = CompliancePackVersion(
            region_code=region_code,
            version=version,
            pack_ref=pack_ref,
            display_name=payload.get("display_name", f"{region_code} Compliance Pack v{version}"),
            effective_date=payload.get("effective_date", payload.get("issued_at")),
            published_at=payload.get("issued_at"),
            published_by=payload.get("actor_id", "SYSTEM"),
            tax_rules=tax_rules,
            receipt_requirements=receipt_req,
            data_retention=data_ret,
            required_invoice_fields=tuple(payload.get("required_invoice_fields", [])),
            optional_invoice_fields=tuple(payload.get("optional_invoice_fields", [])),
            change_summary=payload.get("change_summary", ""),
        )
        self._packs[pack_ref] = pack
        versions = self._versions_by_region.setdefault(region_code, [])
        if version not in versions:
            versions.append(version)
            versions.sort()

    def _apply_deprecated(self, payload: Dict[str, Any]) -> None:
        region_code = payload["region_code"]
        version = int(payload["version"])
        pack_ref = f"{region_code}:v{version}"
        old = self._packs.get(pack_ref)
        if old is None:
            return
        superseded_version = payload.get("superseded_by_version")
        superseded_by = (
            f"{region_code}:v{superseded_version}"
            if superseded_version else None
        )
        self._packs[pack_ref] = CompliancePackVersion(
            region_code=old.region_code,
            version=old.version,
            pack_ref=old.pack_ref,
            display_name=old.display_name,
            effective_date=old.effective_date,
            published_at=old.published_at,
            published_by=old.published_by,
            tax_rules=old.tax_rules,
            receipt_requirements=old.receipt_requirements,
            data_retention=old.data_retention,
            required_invoice_fields=old.required_invoice_fields,
            optional_invoice_fields=old.optional_invoice_fields,
            change_summary=old.change_summary,
            deprecated=True,
            deprecated_at=payload.get("issued_at"),
            superseded_by=superseded_by,
        )

    def _apply_pin(self, payload: Dict[str, Any]) -> None:
        tenant_id = payload["tenant_id"]
        region_code = payload["region_code"]
        version = int(payload["version"])
        pack_ref = f"{region_code}:v{version}"
        key = f"{tenant_id}:{region_code}"
        self._tenant_pins[key] = TenantPackPin(
            tenant_id=tenant_id,
            region_code=region_code,
            pack_ref=pack_ref,
            pinned_at=payload.get("issued_at"),
            pinned_by=payload.get("actor_id", "SYSTEM"),
        )

    # ── queries ───────────────────────────────────────────────

    def get_pack(self, region_code: str, version: int) -> Optional[CompliancePackVersion]:
        return self._packs.get(f"{region_code}:v{version}")

    def get_pack_by_ref(self, pack_ref: str) -> Optional[CompliancePackVersion]:
        return self._packs.get(pack_ref)

    def get_latest_version(self, region_code: str) -> Optional[CompliancePackVersion]:
        """Return the newest (highest version number) non-deprecated pack for a region."""
        versions = self._versions_by_region.get(region_code, [])
        for version in reversed(versions):
            pack = self._packs.get(f"{region_code}:v{version}")
            if pack and not pack.deprecated:
                return pack
        # If all deprecated, return latest anyway
        if versions:
            return self._packs.get(f"{region_code}:v{versions[-1]}")
        return None

    def list_versions(
        self, region_code: str, include_deprecated: bool = False
    ) -> List[CompliancePackVersion]:
        versions = self._versions_by_region.get(region_code, [])
        packs = [
            self._packs[f"{region_code}:v{v}"]
            for v in versions
            if f"{region_code}:v{v}" in self._packs
        ]
        if not include_deprecated:
            packs = [p for p in packs if not p.deprecated]
        return packs

    def get_tenant_pin(
        self, tenant_id: str, region_code: str
    ) -> Optional[TenantPackPin]:
        return self._tenant_pins.get(f"{tenant_id}:{region_code}")

    def get_tenant_effective_pack(
        self, tenant_id: str, region_code: str
    ) -> Optional[CompliancePackVersion]:
        """Return the pack version currently effective for a tenant."""
        pin = self.get_tenant_pin(tenant_id, region_code)
        if pin is None:
            return None
        return self._packs.get(pin.pack_ref)

    def truncate(self) -> None:
        self._packs.clear()
        self._versions_by_region.clear()
        self._tenant_pins.clear()


# ══════════════════════════════════════════════════════════════
# COMPLIANCE PACK SERVICE
# ══════════════════════════════════════════════════════════════

class CompliancePackService:
    """
    Manages versioned compliance packs and tenant pack pins.

    Additive-only: new versions are published alongside existing ones.
    Existing tenants keep their pinned version. Upgrade is explicit.
    """

    def __init__(self, projection: CompliancePackProjection) -> None:
        self._projection = projection

    def publish_pack(
        self, request: PublishCompliancePackRequest
    ) -> Dict[str, Any]:
        """
        Publish a new compliance pack version for a region.
        Version number is auto-incremented from the latest existing version.
        """
        latest = self._projection.get_latest_version(request.region_code)
        new_version = (latest.version + 1) if latest else 1

        pack_ref = f"{request.region_code}:v{new_version}"
        payload: Dict[str, Any] = {
            "region_code": request.region_code,
            "version": new_version,
            "pack_ref": pack_ref,
            "display_name": request.display_name,
            "effective_date": request.effective_date,
            "tax_rules": [
                {
                    "tax_code": t.get("tax_code", ""),
                    "rate": str(t.get("rate", "0")),
                    "description": t.get("description", ""),
                    "applies_to": t.get("applies_to", []),
                    "is_compound": t.get("is_compound", False),
                }
                for t in request.tax_rules
            ],
            "receipt_requirements": request.receipt_requirements,
            "data_retention": request.data_retention,
            "required_invoice_fields": list(request.required_invoice_fields),
            "optional_invoice_fields": list(request.optional_invoice_fields),
            "change_summary": request.change_summary,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(COMPLIANCE_PACK_PUBLISHED_V1, payload)
        return {
            "pack_ref": pack_ref,
            "version": new_version,
            "events": [{"event_type": COMPLIANCE_PACK_PUBLISHED_V1, "payload": payload}],
        }

    def deprecate_pack(
        self, request: DeprecateCompliancePackRequest
    ) -> Optional[RejectionReason]:
        """Mark an old pack version as deprecated (superseded by a newer version)."""
        pack = self._projection.get_pack(request.region_code, request.version)
        if pack is None:
            return RejectionReason(
                code="COMPLIANCE_PACK_NOT_FOUND",
                message=f"Pack {request.region_code}:v{request.version} not found.",
                policy_name="deprecate_compliance_pack",
            )
        if pack.deprecated:
            return RejectionReason(
                code="COMPLIANCE_PACK_ALREADY_DEPRECATED",
                message=f"Pack {pack.pack_ref} is already deprecated.",
                policy_name="deprecate_compliance_pack",
            )
        # Verify superseding version exists
        superseding = self._projection.get_pack(
            request.region_code, request.superseded_by_version
        )
        if superseding is None:
            return RejectionReason(
                code="SUPERSEDING_PACK_NOT_FOUND",
                message=f"Superseding pack v{request.superseded_by_version} does not exist.",
                policy_name="deprecate_compliance_pack",
            )
        self._projection.apply(COMPLIANCE_PACK_DEPRECATED_V1, {
            "region_code": request.region_code,
            "version": request.version,
            "superseded_by_version": request.superseded_by_version,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def pin_tenant_to_pack(
        self, request: PinTenantPackRequest
    ) -> Optional[RejectionReason]:
        """
        Pin a tenant to a specific compliance pack version.
        Called automatically during onboarding (latest version at that time).
        """
        pack = self._projection.get_pack(request.region_code, request.version)
        if pack is None:
            return RejectionReason(
                code="COMPLIANCE_PACK_NOT_FOUND",
                message=f"Pack {request.region_code}:v{request.version} not found.",
                policy_name="pin_tenant_pack",
            )
        self._projection.apply(TENANT_PACK_PINNED_V1, {
            "tenant_id": request.tenant_id,
            "region_code": request.region_code,
            "version": request.version,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def upgrade_tenant_pack(
        self, request: UpgradeTenantPackRequest
    ) -> Optional[RejectionReason]:
        """
        Upgrade a tenant to a newer compliance pack version.
        Tenant explicitly opts in — never forced.
        """
        current_pin = self._projection.get_tenant_pin(
            request.tenant_id, request.region_code
        )
        if current_pin is None:
            return RejectionReason(
                code="TENANT_HAS_NO_PACK",
                message="Tenant is not pinned to any compliance pack for this region.",
                policy_name="upgrade_tenant_pack",
            )

        target_pack = self._projection.get_pack(request.region_code, request.to_version)
        if target_pack is None:
            return RejectionReason(
                code="COMPLIANCE_PACK_NOT_FOUND",
                message=f"Target pack {request.region_code}:v{request.to_version} not found.",
                policy_name="upgrade_tenant_pack",
            )

        # Extract current version number from pack_ref  e.g. "KE:v2" → 2
        current_version = int(current_pin.pack_ref.split(":v")[-1])
        if request.to_version <= current_version:
            return RejectionReason(
                code="CANNOT_DOWNGRADE_COMPLIANCE_PACK",
                message=(
                    f"Cannot downgrade from v{current_version} to v{request.to_version}. "
                    "Compliance packs are additive-only."
                ),
                policy_name="upgrade_tenant_pack",
            )

        self._projection.apply(TENANT_PACK_UPGRADED_V1, {
            "tenant_id": request.tenant_id,
            "region_code": request.region_code,
            "version": request.to_version,
            "previous_version": current_version,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def auto_pin_to_latest(
        self, tenant_id: str, region_code: str, actor_id: str, issued_at: datetime
    ) -> Dict[str, Any]:
        """
        Pin a new tenant to the latest available compliance pack version.
        Called automatically during onboarding.
        """
        latest = self._projection.get_latest_version(region_code)
        if latest is None:
            return {
                "pinned": False,
                "reason": f"No compliance pack found for region {region_code}.",
            }
        result = self.pin_tenant_to_pack(PinTenantPackRequest(
            tenant_id=tenant_id,
            region_code=region_code,
            version=latest.version,
            actor_id=actor_id,
            issued_at=issued_at,
        ))
        if result:
            return {"pinned": False, "reason": result.message}
        return {
            "pinned": True,
            "pack_ref": latest.pack_ref,
            "version": latest.version,
        }

    def get_effective_tax_rules(
        self, tenant_id: str, region_code: str
    ) -> List[TaxRule]:
        """Return tax rules from the tenant's currently pinned compliance pack."""
        pack = self._projection.get_tenant_effective_pack(tenant_id, region_code)
        if pack is None:
            return []
        return list(pack.tax_rules)

    def get_receipt_requirements(
        self, tenant_id: str, region_code: str
    ) -> Optional[ReceiptRequirement]:
        """Return receipt requirements from the tenant's pinned compliance pack."""
        pack = self._projection.get_tenant_effective_pack(tenant_id, region_code)
        return pack.receipt_requirements if pack else None
