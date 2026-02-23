"""
Tests for BOS SaaS — White-Label Branding Configuration
"""

import uuid
from datetime import datetime

import pytest

from core.saas.branding import (
    BRANDING_CONFIGURED_V1,
    BRANDING_RESET_V1,
    BrandConfig,
    BrandingProjection,
    BrandingService,
    ConfigureBrandingRequest,
    ResetBrandingRequest,
)


NOW = datetime(2025, 6, 1, 12, 0, 0)
BIZ_ID = uuid.uuid4()


@pytest.fixture
def projection():
    return BrandingProjection()


@pytest.fixture
def service(projection):
    return BrandingService(projection)


def _configure(service, biz_id=None):
    return service.configure(ConfigureBrandingRequest(
        business_id=biz_id or BIZ_ID,
        company_name="Acme Corp",
        logo_url="https://acme.co/logo.png",
        primary_color="#FF6600",
        secondary_color="#333333",
        support_email="support@acme.co",
        actor_id="admin-1",
        issued_at=NOW,
        custom_domain="app.acme.co",
        tagline="Building the future",
    ))


class TestBrandingConfiguration:
    def test_configure_emits_event(self, service):
        result = _configure(service)
        assert len(result["events"]) == 1
        assert result["events"][0]["event_type"] == BRANDING_CONFIGURED_V1

    def test_config_stored_in_projection(self, service, projection):
        _configure(service)
        config = projection.get_config(BIZ_ID)
        assert config is not None
        assert config.company_name == "Acme Corp"
        assert config.logo_url == "https://acme.co/logo.png"
        assert config.primary_color == "#FF6600"
        assert config.custom_domain == "app.acme.co"
        assert config.tagline == "Building the future"

    def test_overwrite_branding(self, service, projection):
        _configure(service)
        service.configure(ConfigureBrandingRequest(
            business_id=BIZ_ID,
            company_name="Acme Inc",
            logo_url="https://acme.co/new-logo.png",
            primary_color="#0066FF",
            secondary_color="#FFFFFF",
            support_email="help@acme.co",
            actor_id="admin-1",
            issued_at=NOW,
        ))
        config = projection.get_config(BIZ_ID)
        assert config.company_name == "Acme Inc"
        assert config.primary_color == "#0066FF"

    def test_domain_lookup(self, service, projection):
        _configure(service)
        config = projection.get_by_domain("app.acme.co")
        assert config is not None
        assert config.business_id == BIZ_ID

    def test_domain_lookup_not_found(self, service, projection):
        _configure(service)
        assert projection.get_by_domain("unknown.domain.com") is None


class TestBrandingReset:
    def test_reset_branding(self, service, projection):
        _configure(service)
        rejection = service.reset(ResetBrandingRequest(
            business_id=BIZ_ID, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is None
        assert projection.get_config(BIZ_ID) is None

    def test_reset_no_branding_rejected(self, service):
        rejection = service.reset(ResetBrandingRequest(
            business_id=uuid.uuid4(), actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "NO_BRANDING_CONFIGURED"


class TestBrandingProjectionQueries:
    def test_list_configured(self, service, projection):
        _configure(service)
        biz2 = uuid.uuid4()
        _configure(service, biz_id=biz2)
        assert len(projection.list_configured()) == 2

    def test_snapshot(self, service, projection):
        _configure(service)
        snap = projection.snapshot(BIZ_ID)
        assert snap["company_name"] == "Acme Corp"
        assert snap["primary_color"] == "#FF6600"
        assert snap["custom_domain"] == "app.acme.co"

    def test_snapshot_empty(self, projection):
        snap = projection.snapshot(uuid.uuid4())
        assert snap == {}

    def test_truncate_specific(self, service, projection):
        _configure(service)
        projection.truncate(BIZ_ID)
        assert projection.get_config(BIZ_ID) is None

    def test_truncate_all(self, service, projection):
        _configure(service)
        projection.truncate()
        assert len(projection.list_configured()) == 0
