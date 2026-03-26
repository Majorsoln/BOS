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
# TAX CATEGORIES — Multi-Category Tax Support
# ══════════════════════════════════════════════════════════════

class TaxCategory:
    """Tax classification categories per governance memo."""
    STANDARD = "STANDARD"           # Normal taxable rate (e.g. 16% VAT Kenya)
    ZERO_RATED = "ZERO_RATED"       # 0% but still VAT-registered (exports, basic foods)
    EXEMPT = "EXEMPT"               # Not subject to VAT at all (financial services, education)
    REVERSE_CHARGE = "REVERSE_CHARGE"  # Buyer accounts for VAT (B2B cross-border)
    REDUCED = "REDUCED"             # Lower rate for specific goods (e.g. 8% in some EU)
    WITHHOLDING = "WITHHOLDING"     # Tax withheld at source

TAX_CATEGORIES = frozenset({
    TaxCategory.STANDARD,
    TaxCategory.ZERO_RATED,
    TaxCategory.EXEMPT,
    TaxCategory.REVERSE_CHARGE,
    TaxCategory.REDUCED,
    TaxCategory.WITHHOLDING,
})


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
    """
    A single tax rule within a compliance pack.

    Enhanced with multi-category support per governance memo:
    - category: STANDARD, ZERO_RATED, EXEMPT, REVERSE_CHARGE, REDUCED, WITHHOLDING
    - threshold_amount: VAT registration threshold (0 = always required)
    - exemption_codes: specific product/service codes exempt under this rule
    - effective_from / effective_until: temporal validity for rate changes
    """
    tax_code: str
    rate: Decimal
    description: str
    applies_to: Tuple[str, ...]    # e.g. ("GOODS", "SERVICES")
    is_compound: bool = False      # compound tax (applied on top of another)
    # ── Governance Memo Additions ──
    category: str = "STANDARD"     # TaxCategory value
    threshold_amount: Decimal = Decimal("0")  # VAT registration threshold in local currency
    exemption_codes: Tuple[str, ...] = ()     # product/service codes exempt under this rule
    reverse_charge_applicable: bool = False   # whether reverse charge applies (B2B cross-border)
    withholding_rate: Decimal = Decimal("0")  # withholding tax rate if applicable
    effective_from: Optional[datetime] = None # when this rate starts applying
    effective_until: Optional[datetime] = None  # when this rate expires (None = indefinite)


@dataclass(frozen=True)
class EInvoicingRequirement:
    """
    E-invoicing mandate configuration per jurisdiction.

    Covers: KRA eTIMS (Kenya), TRA EFDMS (Tanzania), URA EFRIS (Uganda),
    FIRS MBS (Nigeria), ZRA Smart Invoice (Zambia), etc.
    """
    mandate_active: bool                    # is e-invoicing mandatory?
    system_name: str                        # e.g. "eTIMS", "EFDMS", "EFRIS"
    regulatory_body: str                    # e.g. "KRA", "TRA", "URA"
    api_endpoint_ref: str = ""              # reference key for API config (not the actual URL)
    transmission_mode: str = "REAL_TIME"    # REAL_TIME | BATCH | ON_DEMAND
    requires_device_registration: bool = False  # fiscal device required?
    device_type: str = ""                   # e.g. "ETR", "EFD", "VIRTUAL"
    qr_code_required: bool = False          # must invoice carry QR?
    digital_signature_required: bool = False
    invoice_number_format: str = ""         # regex or pattern from authority
    max_offline_hours: int = 48             # hours allowed offline before sync
    penalty_reference: str = ""             # law section for non-compliance penalty


@dataclass(frozen=True)
class InvoiceFormatRules:
    """
    Invoice content and format rules per jurisdiction.

    Defines what fields are legally required on different document types
    and formatting constraints (language, decimal places, date format, etc.).
    """
    required_header_fields: Tuple[str, ...] = ()    # e.g. ("business_name", "tax_id", "address")
    required_line_fields: Tuple[str, ...] = ()       # e.g. ("description", "qty", "unit_price", "tax_rate")
    required_footer_fields: Tuple[str, ...] = ()     # e.g. ("total_tax", "grand_total")
    document_language: str = "en"                     # ISO 639-1 primary language
    secondary_language: str = ""                      # bilingual requirement
    currency_decimal_places: int = 2
    date_format: str = "YYYY-MM-DD"                  # ISO 8601 default
    tax_breakdown_required: bool = True               # must show per-line tax?
    credit_note_must_reference_invoice: bool = True   # CN must cite original invoice number
    pro_forma_legally_binding: bool = False            # is proforma legally binding?
    max_payment_terms_days: int = 0                   # 0 = no statutory limit


@dataclass(frozen=True)
class CrossBorderRules:
    """
    Cross-border transaction rules per jurisdiction.

    Governs: reverse charge, withholding, transfer pricing documentation.
    """
    reverse_charge_on_imports: bool = False       # buyer accounts for VAT on B2B imports
    reverse_charge_threshold: Decimal = Decimal("0")  # above this amount, reverse charge kicks in
    withholding_on_foreign_services: bool = False
    withholding_rate: Decimal = Decimal("0")
    transfer_pricing_doc_required: bool = False   # must keep TP documentation?
    permanent_establishment_rules: str = ""       # reference to PE rules
    double_tax_treaty_countries: Tuple[str, ...] = ()  # countries with DTAs


@dataclass(frozen=True)
class DigitalSignatureRules:
    """Digital signature and document authentication requirements."""
    require_digital_signature: bool = False
    signature_algorithm: str = "SHA256withRSA"    # default algorithm
    certificate_authority: str = ""               # approved CA
    timestamp_required: bool = False              # RFC 3161 timestamp
    signature_visible_on_pdf: bool = False        # visible signature mark on PDF


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
    # ── Governance Memo Additions ──
    consent_records_years: int = 7          # how long to keep consent evidence
    tax_records_years: int = 0              # specific tax record retention (0 = same as financial)
    employee_records_years: int = 0         # HR/payroll records
    destruction_method: str = "SECURE_DELETE"  # SECURE_DELETE | ANONYMIZE | ARCHIVE


@dataclass(frozen=True)
class CompliancePackVersion:
    """
    One immutable version of a regional compliance pack.
    Published once — never modified.

    Enhanced per governance memo with:
    - Multi-category tax rules (STANDARD/ZERO_RATED/EXEMPT/REVERSE_CHARGE)
    - E-invoicing mandates (eTIMS, EFDMS, EFRIS, etc.)
    - Invoice format rules (per-jurisdiction legal requirements)
    - Cross-border transaction rules
    - Digital signature requirements
    - Fiscal year and reporting frequency configuration
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
    # ── Governance Memo Additions ──
    e_invoicing: Optional[EInvoicingRequirement] = None     # e-invoicing mandate config
    invoice_format: Optional[InvoiceFormatRules] = None     # invoice content/format rules
    cross_border: Optional[CrossBorderRules] = None         # cross-border transaction rules
    digital_signature: Optional[DigitalSignatureRules] = None  # digital signature requirements
    fiscal_year_start_month: int = 1                        # 1=Jan, 7=Jul (Kenya/Tanzania)
    reporting_frequency: str = "MONTHLY"                    # MONTHLY | QUARTERLY | ANNUAL
    vat_return_frequency: str = "MONTHLY"                   # MONTHLY | QUARTERLY
    currency_code: str = ""                                 # ISO 4217 for this jurisdiction
    law_reference_url: str = ""                             # link to relevant tax authority


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
    # ── Governance Memo Additions ──
    e_invoicing: Optional[Dict[str, Any]] = None
    invoice_format: Optional[Dict[str, Any]] = None
    cross_border: Optional[Dict[str, Any]] = None
    digital_signature: Optional[Dict[str, Any]] = None
    fiscal_year_start_month: int = 1
    reporting_frequency: str = "MONTHLY"
    vat_return_frequency: str = "MONTHLY"
    currency_code: str = ""
    law_reference_url: str = ""


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
                category=t.get("category", "STANDARD"),
                threshold_amount=Decimal(str(t.get("threshold_amount", "0"))),
                exemption_codes=tuple(t.get("exemption_codes", [])),
                reverse_charge_applicable=t.get("reverse_charge_applicable", False),
                withholding_rate=Decimal(str(t.get("withholding_rate", "0"))),
                effective_from=t.get("effective_from"),
                effective_until=t.get("effective_until"),
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
            consent_records_years=dr.get("consent_records_years", 7),
            tax_records_years=dr.get("tax_records_years", 0),
            employee_records_years=dr.get("employee_records_years", 0),
            destruction_method=dr.get("destruction_method", "SECURE_DELETE"),
        )

        # E-invoicing mandate
        ei_data = payload.get("e_invoicing")
        e_invoicing = None
        if ei_data:
            e_invoicing = EInvoicingRequirement(
                mandate_active=ei_data.get("mandate_active", False),
                system_name=ei_data.get("system_name", ""),
                regulatory_body=ei_data.get("regulatory_body", ""),
                api_endpoint_ref=ei_data.get("api_endpoint_ref", ""),
                transmission_mode=ei_data.get("transmission_mode", "REAL_TIME"),
                requires_device_registration=ei_data.get("requires_device_registration", False),
                device_type=ei_data.get("device_type", ""),
                qr_code_required=ei_data.get("qr_code_required", False),
                digital_signature_required=ei_data.get("digital_signature_required", False),
                invoice_number_format=ei_data.get("invoice_number_format", ""),
                max_offline_hours=ei_data.get("max_offline_hours", 48),
                penalty_reference=ei_data.get("penalty_reference", ""),
            )

        # Invoice format rules
        if_data = payload.get("invoice_format")
        invoice_format = None
        if if_data:
            invoice_format = InvoiceFormatRules(
                required_header_fields=tuple(if_data.get("required_header_fields", [])),
                required_line_fields=tuple(if_data.get("required_line_fields", [])),
                required_footer_fields=tuple(if_data.get("required_footer_fields", [])),
                document_language=if_data.get("document_language", "en"),
                secondary_language=if_data.get("secondary_language", ""),
                currency_decimal_places=if_data.get("currency_decimal_places", 2),
                date_format=if_data.get("date_format", "YYYY-MM-DD"),
                tax_breakdown_required=if_data.get("tax_breakdown_required", True),
                credit_note_must_reference_invoice=if_data.get("credit_note_must_reference_invoice", True),
                pro_forma_legally_binding=if_data.get("pro_forma_legally_binding", False),
                max_payment_terms_days=if_data.get("max_payment_terms_days", 0),
            )

        # Cross-border rules
        cb_data = payload.get("cross_border")
        cross_border = None
        if cb_data:
            cross_border = CrossBorderRules(
                reverse_charge_on_imports=cb_data.get("reverse_charge_on_imports", False),
                reverse_charge_threshold=Decimal(str(cb_data.get("reverse_charge_threshold", "0"))),
                withholding_on_foreign_services=cb_data.get("withholding_on_foreign_services", False),
                withholding_rate=Decimal(str(cb_data.get("withholding_rate", "0"))),
                transfer_pricing_doc_required=cb_data.get("transfer_pricing_doc_required", False),
                permanent_establishment_rules=cb_data.get("permanent_establishment_rules", ""),
                double_tax_treaty_countries=tuple(cb_data.get("double_tax_treaty_countries", [])),
            )

        # Digital signature rules
        ds_data = payload.get("digital_signature")
        digital_signature = None
        if ds_data:
            digital_signature = DigitalSignatureRules(
                require_digital_signature=ds_data.get("require_digital_signature", False),
                signature_algorithm=ds_data.get("signature_algorithm", "SHA256withRSA"),
                certificate_authority=ds_data.get("certificate_authority", ""),
                timestamp_required=ds_data.get("timestamp_required", False),
                signature_visible_on_pdf=ds_data.get("signature_visible_on_pdf", False),
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
            e_invoicing=e_invoicing,
            invoice_format=invoice_format,
            cross_border=cross_border,
            digital_signature=digital_signature,
            fiscal_year_start_month=int(payload.get("fiscal_year_start_month", 1)),
            reporting_frequency=payload.get("reporting_frequency", "MONTHLY"),
            vat_return_frequency=payload.get("vat_return_frequency", "MONTHLY"),
            currency_code=payload.get("currency_code", ""),
            law_reference_url=payload.get("law_reference_url", ""),
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
                    "category": t.get("category", "STANDARD"),
                    "threshold_amount": str(t.get("threshold_amount", "0")),
                    "exemption_codes": t.get("exemption_codes", []),
                    "reverse_charge_applicable": t.get("reverse_charge_applicable", False),
                    "withholding_rate": str(t.get("withholding_rate", "0")),
                    "effective_from": t.get("effective_from"),
                    "effective_until": t.get("effective_until"),
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
            "e_invoicing": request.e_invoicing,
            "invoice_format": request.invoice_format,
            "cross_border": request.cross_border,
            "digital_signature": request.digital_signature,
            "fiscal_year_start_month": request.fiscal_year_start_month,
            "reporting_frequency": request.reporting_frequency,
            "vat_return_frequency": request.vat_return_frequency,
            "currency_code": request.currency_code,
            "law_reference_url": request.law_reference_url,
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

    def get_e_invoicing_requirements(
        self, tenant_id: str, region_code: str
    ) -> Optional[EInvoicingRequirement]:
        """Return e-invoicing requirements from the tenant's pinned compliance pack."""
        pack = self._projection.get_tenant_effective_pack(tenant_id, region_code)
        return pack.e_invoicing if pack else None

    def get_invoice_format_rules(
        self, tenant_id: str, region_code: str
    ) -> Optional[InvoiceFormatRules]:
        """Return invoice format rules from the tenant's pinned compliance pack."""
        pack = self._projection.get_tenant_effective_pack(tenant_id, region_code)
        return pack.invoice_format if pack else None

    def get_cross_border_rules(
        self, tenant_id: str, region_code: str
    ) -> Optional[CrossBorderRules]:
        """Return cross-border rules from the tenant's pinned compliance pack."""
        pack = self._projection.get_tenant_effective_pack(tenant_id, region_code)
        return pack.cross_border if pack else None


# ══════════════════════════════════════════════════════════════
# TAX DECISION ENGINE
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TaxDecisionResult:
    """Result of a tax computation from the Tax Decision Engine."""
    tax_code: str
    category: str              # TaxCategory value
    rate: Decimal
    tax_amount: Decimal        # computed tax amount
    base_amount: Decimal       # amount tax was computed on
    description: str
    is_exempt: bool = False
    is_reverse_charge: bool = False
    withholding_amount: Decimal = Decimal("0")


@dataclass(frozen=True)
class TaxDecisionRequest:
    """Request to the Tax Decision Engine."""
    tenant_id: str
    region_code: str
    transaction_type: str      # SALE, PURCHASE, SERVICE, IMPORT, EXPORT
    customer_type: str         # B2B, B2C
    product_category: str      # product/service category code
    base_amount: Decimal       # pre-tax amount
    is_cross_border: bool = False
    counterparty_country: str = ""  # for cross-border: other party's country
    is_digital_service: bool = False


class TaxDecisionEngine:
    """
    Multi-category tax computation engine.

    Doctrine: BOS does not hardcode tax rates. The Tax Decision Engine
    reads rules from the tenant's pinned compliance pack and applies them.

    Supports: standard VAT, zero-rated, exempt, reverse charge,
    reduced rates, withholding, and compound taxes.
    """

    def __init__(self, pack_service: CompliancePackService) -> None:
        self._pack_service = pack_service

    def compute_tax(self, request: TaxDecisionRequest) -> List[TaxDecisionResult]:
        """
        Compute applicable taxes for a transaction.

        Returns a list of TaxDecisionResult — one per applicable tax rule.
        Empty list means no tax applies (exempt or no rules found).
        """
        rules = self._pack_service.get_effective_tax_rules(
            request.tenant_id, request.region_code
        )
        if not rules:
            return []

        # Check cross-border rules
        cross_border = self._pack_service.get_cross_border_rules(
            request.tenant_id, request.region_code
        )

        results: List[TaxDecisionResult] = []
        compound_base = request.base_amount

        for rule in rules:
            # Skip expired rules
            if rule.effective_until and isinstance(rule.effective_until, datetime):
                if datetime.utcnow() > rule.effective_until:
                    continue

            # Skip rules that haven't started yet
            if rule.effective_from and isinstance(rule.effective_from, datetime):
                if datetime.utcnow() < rule.effective_from:
                    continue

            # Check if product category is in applies_to
            if rule.applies_to and request.product_category not in rule.applies_to:
                if request.transaction_type not in rule.applies_to:
                    continue

            # Check exemptions
            if rule.exemption_codes and request.product_category in rule.exemption_codes:
                results.append(TaxDecisionResult(
                    tax_code=rule.tax_code,
                    category=TaxCategory.EXEMPT,
                    rate=Decimal("0"),
                    tax_amount=Decimal("0"),
                    base_amount=request.base_amount,
                    description=f"Exempt: {rule.description}",
                    is_exempt=True,
                ))
                continue

            # Handle reverse charge for cross-border B2B
            if (request.is_cross_border
                    and request.customer_type == "B2B"
                    and rule.reverse_charge_applicable):
                results.append(TaxDecisionResult(
                    tax_code=rule.tax_code,
                    category=TaxCategory.REVERSE_CHARGE,
                    rate=rule.rate,
                    tax_amount=Decimal("0"),  # buyer accounts for this
                    base_amount=request.base_amount,
                    description=f"Reverse charge: {rule.description}",
                    is_reverse_charge=True,
                ))
                continue

            # Handle cross-border withholding
            if (request.is_cross_border
                    and cross_border
                    and cross_border.withholding_on_foreign_services
                    and request.transaction_type == "SERVICE"):
                wh_rate = cross_border.withholding_rate or rule.withholding_rate
                if wh_rate > 0:
                    wh_amount = (request.base_amount * wh_rate).quantize(Decimal("0.01"))
                    results.append(TaxDecisionResult(
                        tax_code=f"{rule.tax_code}_WHT",
                        category=TaxCategory.WITHHOLDING,
                        rate=wh_rate,
                        tax_amount=Decimal("0"),
                        base_amount=request.base_amount,
                        description=f"Withholding tax: {rule.description}",
                        withholding_amount=wh_amount,
                    ))

            # Standard / zero-rated / reduced computation
            if rule.category == TaxCategory.ZERO_RATED:
                results.append(TaxDecisionResult(
                    tax_code=rule.tax_code,
                    category=TaxCategory.ZERO_RATED,
                    rate=Decimal("0"),
                    tax_amount=Decimal("0"),
                    base_amount=request.base_amount,
                    description=f"Zero-rated: {rule.description}",
                ))
            else:
                # Standard or reduced rate
                base = compound_base if rule.is_compound else request.base_amount
                tax_amount = (base * rule.rate).quantize(Decimal("0.01"))
                results.append(TaxDecisionResult(
                    tax_code=rule.tax_code,
                    category=rule.category,
                    rate=rule.rate,
                    tax_amount=tax_amount,
                    base_amount=base,
                    description=rule.description,
                ))
                if rule.is_compound:
                    compound_base += tax_amount

        return results

    def compute_total_tax(self, request: TaxDecisionRequest) -> Decimal:
        """Convenience: sum of all tax amounts for a transaction."""
        results = self.compute_tax(request)
        return sum((r.tax_amount for r in results), Decimal("0"))
