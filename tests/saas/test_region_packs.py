"""
Tests for BOS SaaS — Regional Configuration Packs
"""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from core.saas.region_packs import (
    REGION_PACK_APPLIED_V1,
    REGION_PACK_REGISTERED_V1,
    ApplyRegionPackRequest,
    RegionPackProjection,
    RegionPackService,
    RegisterRegionPackRequest,
    TaxPreset,
)


NOW = datetime(2025, 6, 1, 12, 0, 0)
BIZ_ID = uuid.uuid4()


@pytest.fixture
def projection():
    return RegionPackProjection()


@pytest.fixture
def service(projection):
    return RegionPackService(projection)


def _register_tz_pack(service):
    return service.register_pack(RegisterRegionPackRequest(
        region_code="TZ",
        region_name="Tanzania",
        default_currency="TZS",
        default_timezone="Africa/Dar_es_Salaam",
        date_format="DD/MM/YYYY",
        tax_presets=(
            {"tax_code": "VAT", "rate": "0.18", "description": "Value Added Tax 18%"},
            {"tax_code": "SDL", "rate": "0.045", "description": "Skills Development Levy 4.5%"},
        ),
        compliance_tags=("TRA_EFD", "TIN_REQUIRED"),
        actor_id="platform-admin",
        issued_at=NOW,
    ))


def _register_ke_pack(service):
    return service.register_pack(RegisterRegionPackRequest(
        region_code="KE",
        region_name="Kenya",
        default_currency="KES",
        default_timezone="Africa/Nairobi",
        date_format="DD/MM/YYYY",
        tax_presets=(
            {"tax_code": "VAT", "rate": "0.16", "description": "Value Added Tax 16%"},
        ),
        compliance_tags=("KRA_ETIMS",),
        actor_id="platform-admin",
        issued_at=NOW,
    ))


class TestRegionPackRegistration:
    def test_register_returns_pack_id(self, service):
        result = _register_tz_pack(service)
        assert "pack_id" in result
        assert isinstance(result["pack_id"], uuid.UUID)

    def test_register_emits_event(self, service):
        result = _register_tz_pack(service)
        assert result["events"][0]["event_type"] == REGION_PACK_REGISTERED_V1

    def test_pack_in_projection(self, service, projection):
        _register_tz_pack(service)
        pack = projection.get_pack("TZ")
        assert pack is not None
        assert pack.region_name == "Tanzania"
        assert pack.default_currency == "TZS"
        assert pack.date_format == "DD/MM/YYYY"

    def test_tax_presets_stored(self, service, projection):
        _register_tz_pack(service)
        pack = projection.get_pack("TZ")
        assert len(pack.tax_presets) == 2
        vat = next(t for t in pack.tax_presets if t.tax_code == "VAT")
        assert vat.rate == Decimal("0.18")

    def test_compliance_tags_stored(self, service, projection):
        _register_tz_pack(service)
        pack = projection.get_pack("TZ")
        assert "TRA_EFD" in pack.compliance_tags
        assert "TIN_REQUIRED" in pack.compliance_tags

    def test_overwrite_region_pack(self, service, projection):
        _register_tz_pack(service)
        service.register_pack(RegisterRegionPackRequest(
            region_code="TZ",
            region_name="Tanzania (Updated)",
            default_currency="TZS",
            default_timezone="Africa/Dar_es_Salaam",
            date_format="YYYY-MM-DD",
            tax_presets=(
                {"tax_code": "VAT", "rate": "0.18", "description": "VAT 18%"},
            ),
            compliance_tags=("TRA_EFD",),
            actor_id="platform-admin",
            issued_at=NOW,
        ))
        pack = projection.get_pack("TZ")
        assert pack.region_name == "Tanzania (Updated)"
        assert pack.date_format == "YYYY-MM-DD"
        assert len(pack.tax_presets) == 1

    def test_multiple_region_packs(self, service, projection):
        _register_tz_pack(service)
        _register_ke_pack(service)
        assert len(projection.list_packs()) == 2


class TestRegionPackApplication:
    def test_apply_pack_to_business(self, service, projection):
        _register_tz_pack(service)
        rejection = service.apply_pack(ApplyRegionPackRequest(
            business_id=BIZ_ID, region_code="TZ",
            actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is None
        app = projection.get_application(BIZ_ID)
        assert app is not None
        assert app.region_code == "TZ"

    def test_apply_nonexistent_pack_rejected(self, service):
        rejection = service.apply_pack(ApplyRegionPackRequest(
            business_id=BIZ_ID, region_code="XX",
            actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "REGION_PACK_NOT_FOUND"

    def test_get_tax_presets_for_business(self, service):
        _register_tz_pack(service)
        service.apply_pack(ApplyRegionPackRequest(
            business_id=BIZ_ID, region_code="TZ",
            actor_id="admin-1", issued_at=NOW,
        ))
        presets = service.get_tax_presets_for_business(BIZ_ID)
        assert len(presets) == 2
        assert any(t.tax_code == "VAT" for t in presets)

    def test_tax_presets_no_application(self, service):
        presets = service.get_tax_presets_for_business(uuid.uuid4())
        assert presets == []


class TestRegionPackDefaults:
    def test_get_region_defaults(self, service):
        _register_tz_pack(service)
        defaults = service.get_region_defaults("TZ")
        assert defaults is not None
        assert defaults["default_currency"] == "TZS"
        assert defaults["default_timezone"] == "Africa/Dar_es_Salaam"
        assert len(defaults["tax_presets"]) == 2

    def test_get_region_defaults_not_found(self, service):
        assert service.get_region_defaults("XX") is None


class TestRegionPackProjectionQueries:
    def test_truncate(self, service, projection):
        _register_tz_pack(service)
        service.apply_pack(ApplyRegionPackRequest(
            business_id=BIZ_ID, region_code="TZ",
            actor_id="admin-1", issued_at=NOW,
        ))
        projection.truncate()
        assert len(projection.list_packs()) == 0
        assert projection.get_application(BIZ_ID) is None
