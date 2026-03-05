"""Tests for core/saas/compliance_packs.py"""
from datetime import datetime
from decimal import Decimal

import pytest

from core.saas.compliance_packs import (
    CompliancePackProjection,
    CompliancePackService,
    PublishCompliancePackRequest,
    DeprecateCompliancePackRequest,
    PinTenantPackRequest,
    UpgradeTenantPackRequest,
    COMPLIANCE_PACK_PUBLISHED_V1,
    TENANT_PACK_PINNED_V1,
    TENANT_PACK_UPGRADED_V1,
)

NOW = datetime(2026, 3, 5, 12, 0, 0)
ADMIN = "platform-admin-001"
TENANT_ID = "tenant-ke-001"
REGION = "KE"

KE_TAX_RULES = (
    {
        "tax_code": "VAT_16",
        "rate": "16",
        "description": "Standard VAT",
        "applies_to": ["GOODS", "SERVICES"],
    },
)

KE_RECEIPT_REQ = {
    "require_sequential_number": True,
    "require_tax_number": True,
    "require_customer_tax_id": False,
    "require_digital_signature": False,
    "require_qr_code": True,
    "number_prefix_format": "RCP-{YYYY}-{NNNNN}",
}

KE_DATA_RETENTION = {
    "financial_records_years": 7,
    "audit_log_years": 7,
    "personal_data_years": 5,
    "region_law_reference": "Kenya VAT Act Cap 476",
}


@pytest.fixture
def projection():
    return CompliancePackProjection()


@pytest.fixture
def service(projection):
    return CompliancePackService(projection)


def _publish(service, region=REGION, change_summary="Initial version"):
    return service.publish_pack(PublishCompliancePackRequest(
        region_code=region,
        display_name=f"{region} Compliance Pack",
        effective_date=NOW,
        tax_rules=KE_TAX_RULES,
        receipt_requirements=KE_RECEIPT_REQ,
        data_retention=KE_DATA_RETENTION,
        required_invoice_fields=("invoice_no", "customer_name", "tax_amount"),
        optional_invoice_fields=("po_ref",),
        change_summary=change_summary,
        actor_id=ADMIN,
        issued_at=NOW,
    ))


class TestPublishPack:
    def test_publish_first_version(self, service, projection):
        result = _publish(service)
        assert result["version"] == 1
        assert result["pack_ref"] == "KE:v1"
        pack = projection.get_pack(REGION, 1)
        assert pack is not None
        assert len(pack.tax_rules) == 1
        assert pack.tax_rules[0].tax_code == "VAT_16"
        assert pack.tax_rules[0].rate == Decimal("16")

    def test_version_auto_increments(self, service, projection):
        _publish(service)
        result2 = _publish(service, change_summary="Added e-signature requirement")
        assert result2["version"] == 2
        assert result2["pack_ref"] == "KE:v2"

    def test_receipt_requirements_stored(self, service, projection):
        _publish(service)
        pack = projection.get_pack(REGION, 1)
        assert pack.receipt_requirements.require_qr_code is True
        assert pack.receipt_requirements.require_sequential_number is True

    def test_data_retention_stored(self, service, projection):
        _publish(service)
        pack = projection.get_pack(REGION, 1)
        assert pack.data_retention.financial_records_years == 7
        assert "Kenya" in pack.data_retention.region_law_reference

    def test_publish_event_produced(self, service):
        result = _publish(service)
        assert result["events"][0]["event_type"] == COMPLIANCE_PACK_PUBLISHED_V1

    def test_multiple_regions_independent(self, service, projection):
        _publish(service, region="KE")
        _publish(service, region="TZ")
        ke_pack = projection.get_pack("KE", 1)
        tz_pack = projection.get_pack("TZ", 1)
        assert ke_pack is not None
        assert tz_pack is not None
        # TZ v1 is version 1 (not 2)
        assert tz_pack.version == 1


class TestDeprecation:
    def test_deprecate_old_version(self, service, projection):
        _publish(service)  # v1
        _publish(service, change_summary="v2 changes")  # v2
        err = service.deprecate_pack(DeprecateCompliancePackRequest(
            region_code=REGION, version=1, superseded_by_version=2,
            actor_id=ADMIN, issued_at=NOW,
        ))
        assert err is None
        pack = projection.get_pack(REGION, 1)
        assert pack.deprecated is True
        assert pack.superseded_by == "KE:v2"

    def test_cannot_deprecate_nonexistent(self, service):
        err = service.deprecate_pack(DeprecateCompliancePackRequest(
            region_code=REGION, version=99, superseded_by_version=100,
            actor_id=ADMIN, issued_at=NOW,
        ))
        assert err is not None
        assert err.code == "COMPLIANCE_PACK_NOT_FOUND"

    def test_cannot_deprecate_without_superseding_version(self, service):
        _publish(service)  # v1 only
        err = service.deprecate_pack(DeprecateCompliancePackRequest(
            region_code=REGION, version=1, superseded_by_version=2,
            actor_id=ADMIN, issued_at=NOW,
        ))
        assert err is not None
        assert err.code == "SUPERSEDING_PACK_NOT_FOUND"

    def test_get_latest_version_skips_deprecated(self, service, projection):
        _publish(service)  # v1
        _publish(service, change_summary="v2")  # v2
        service.deprecate_pack(DeprecateCompliancePackRequest(
            region_code=REGION, version=1, superseded_by_version=2,
            actor_id=ADMIN, issued_at=NOW,
        ))
        latest = projection.get_latest_version(REGION)
        assert latest.version == 2


class TestTenantPinning:
    def test_pin_tenant_to_pack(self, service, projection):
        _publish(service)
        err = service.pin_tenant_to_pack(PinTenantPackRequest(
            tenant_id=TENANT_ID, region_code=REGION, version=1,
            actor_id=ADMIN, issued_at=NOW,
        ))
        assert err is None
        pin = projection.get_tenant_pin(TENANT_ID, REGION)
        assert pin is not None
        assert pin.pack_ref == "KE:v1"

    def test_cannot_pin_to_nonexistent_pack(self, service):
        err = service.pin_tenant_to_pack(PinTenantPackRequest(
            tenant_id=TENANT_ID, region_code=REGION, version=99,
            actor_id=ADMIN, issued_at=NOW,
        ))
        assert err is not None
        assert err.code == "COMPLIANCE_PACK_NOT_FOUND"

    def test_auto_pin_to_latest(self, service, projection):
        _publish(service)  # v1
        _publish(service, change_summary="v2")  # v2
        result = service.auto_pin_to_latest(TENANT_ID, REGION, ADMIN, NOW)
        assert result["pinned"] is True
        assert result["version"] == 2

    def test_auto_pin_no_pack_available(self, service):
        result = service.auto_pin_to_latest(TENANT_ID, "XX", ADMIN, NOW)
        assert result["pinned"] is False

    def test_get_effective_pack(self, service, projection):
        _publish(service)
        service.pin_tenant_to_pack(PinTenantPackRequest(
            tenant_id=TENANT_ID, region_code=REGION, version=1,
            actor_id=ADMIN, issued_at=NOW,
        ))
        pack = projection.get_tenant_effective_pack(TENANT_ID, REGION)
        assert pack is not None
        assert pack.version == 1


class TestTenantUpgrade:
    def test_upgrade_tenant_to_newer_version(self, service, projection):
        _publish(service)  # v1
        _publish(service, change_summary="v2")  # v2
        service.pin_tenant_to_pack(PinTenantPackRequest(
            tenant_id=TENANT_ID, region_code=REGION, version=1,
            actor_id=ADMIN, issued_at=NOW,
        ))
        err = service.upgrade_tenant_pack(UpgradeTenantPackRequest(
            tenant_id=TENANT_ID, region_code=REGION, to_version=2,
            actor_id=ADMIN, issued_at=NOW,
        ))
        assert err is None
        pin = projection.get_tenant_pin(TENANT_ID, REGION)
        assert pin.pack_ref == "KE:v2"

    def test_cannot_downgrade_compliance_pack(self, service, projection):
        _publish(service)  # v1
        _publish(service, change_summary="v2")  # v2
        service.pin_tenant_to_pack(PinTenantPackRequest(
            tenant_id=TENANT_ID, region_code=REGION, version=2,
            actor_id=ADMIN, issued_at=NOW,
        ))
        err = service.upgrade_tenant_pack(UpgradeTenantPackRequest(
            tenant_id=TENANT_ID, region_code=REGION, to_version=1,
            actor_id=ADMIN, issued_at=NOW,
        ))
        assert err is not None
        assert err.code == "CANNOT_DOWNGRADE_COMPLIANCE_PACK"

    def test_upgrade_tenant_without_pin_rejected(self, service):
        _publish(service)  # v1
        _publish(service, change_summary="v2")  # v2
        err = service.upgrade_tenant_pack(UpgradeTenantPackRequest(
            tenant_id="no-pin-tenant", region_code=REGION, to_version=2,
            actor_id=ADMIN, issued_at=NOW,
        ))
        assert err is not None
        assert err.code == "TENANT_HAS_NO_PACK"


class TestTaxRulesResolution:
    def test_get_effective_tax_rules(self, service, projection):
        _publish(service)
        service.pin_tenant_to_pack(PinTenantPackRequest(
            tenant_id=TENANT_ID, region_code=REGION, version=1,
            actor_id=ADMIN, issued_at=NOW,
        ))
        rules = service.get_effective_tax_rules(TENANT_ID, REGION)
        assert len(rules) == 1
        assert rules[0].tax_code == "VAT_16"

    def test_tax_rules_empty_when_no_pin(self, service):
        rules = service.get_effective_tax_rules("no-pin-tenant", REGION)
        assert rules == []

    def test_receipt_requirements_resolved(self, service, projection):
        _publish(service)
        service.pin_tenant_to_pack(PinTenantPackRequest(
            tenant_id=TENANT_ID, region_code=REGION, version=1,
            actor_id=ADMIN, issued_at=NOW,
        ))
        reqs = service.get_receipt_requirements(TENANT_ID, REGION)
        assert reqs is not None
        assert reqs.require_qr_code is True

    def test_additive_only_old_tenants_keep_pinned_version(self, service, projection):
        """Old tenants must NOT automatically move to new pack version."""
        _publish(service)  # v1
        # Tenant pinned to v1
        service.pin_tenant_to_pack(PinTenantPackRequest(
            tenant_id=TENANT_ID, region_code=REGION, version=1,
            actor_id=ADMIN, issued_at=NOW,
        ))
        # New v2 published
        _publish(service, change_summary="v2 with e-signature")

        # Tenant still on v1
        pack = projection.get_tenant_effective_pack(TENANT_ID, REGION)
        assert pack.version == 1

    def test_list_versions_excludes_deprecated_by_default(self, service, projection):
        _publish(service)  # v1
        _publish(service, change_summary="v2")  # v2
        service.deprecate_pack(DeprecateCompliancePackRequest(
            region_code=REGION, version=1, superseded_by_version=2,
            actor_id=ADMIN, issued_at=NOW,
        ))
        versions = projection.list_versions(REGION)
        assert len(versions) == 1
        assert versions[0].version == 2

    def test_list_versions_includes_deprecated_when_requested(self, service, projection):
        _publish(service)  # v1
        _publish(service, change_summary="v2")  # v2
        service.deprecate_pack(DeprecateCompliancePackRequest(
            region_code=REGION, version=1, superseded_by_version=2,
            actor_id=ADMIN, issued_at=NOW,
        ))
        versions = projection.list_versions(REGION, include_deprecated=True)
        assert len(versions) == 2
