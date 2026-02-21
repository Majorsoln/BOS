"""
Tests — Dashboard Aggregation
=================================
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from core.admin.dashboard import DashboardService, SystemOverview, TenantSummary, HealthStatus
from core.admin.tenant_manager import (
    ActivateTenantRequest,
    CloseTenantRequest,
    CreateTenantRequest,
    SuspendTenantRequest,
    TenantManager,
    TenantProjection,
)
from core.admin.settings import SettingsProjection, SETTINGS_TAX_RULE_CONFIGURED_V1


T0 = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _setup():
    proj = TenantProjection()
    settings = SettingsProjection()
    mgr = TenantManager(proj)
    dash = DashboardService(proj, settings)
    return mgr, dash, settings


class TestSystemOverview:
    def test_empty_system(self):
        _, dash, _ = _setup()
        overview = dash.get_system_overview()
        assert overview.total_tenants == 0
        assert overview.active_tenants == 0

    def test_counts_by_state(self):
        mgr, dash, _ = _setup()
        # Create 3 tenants
        r1 = mgr.create_tenant(CreateTenantRequest(
            business_name="A", country_code="US", timezone="UTC",
            actor_id="a", issued_at=T0, initial_branch_name="B1",
        ))
        r2 = mgr.create_tenant(CreateTenantRequest(
            business_name="B", country_code="KE", timezone="UTC",
            actor_id="a", issued_at=T0,
        ))
        r3 = mgr.create_tenant(CreateTenantRequest(
            business_name="C", country_code="UK", timezone="UTC",
            actor_id="a", issued_at=T0,
        ))
        # Activate A, suspend it, close C
        mgr.activate_tenant(ActivateTenantRequest(
            business_id=r1["business_id"], actor_id="a", issued_at=T0,
        ))
        mgr.activate_tenant(ActivateTenantRequest(
            business_id=r2["business_id"], actor_id="a", issued_at=T0,
        ))
        mgr.suspend_tenant(SuspendTenantRequest(
            business_id=r1["business_id"], actor_id="a", issued_at=T0,
        ))
        mgr.close_tenant(CloseTenantRequest(
            business_id=r3["business_id"], actor_id="a", issued_at=T0,
        ))

        overview = dash.get_system_overview()
        assert overview.total_tenants == 3
        assert overview.active_tenants == 1   # B
        assert overview.suspended_tenants == 1  # A
        assert overview.closed_tenants == 1   # C

    def test_branch_counts(self):
        mgr, dash, _ = _setup()
        mgr.create_tenant(CreateTenantRequest(
            business_name="A", country_code="US", timezone="UTC",
            actor_id="a", issued_at=T0,
            initial_branch_name="HQ",
        ))
        overview = dash.get_system_overview()
        assert overview.total_branches == 1
        assert overview.open_branches == 1


class TestTenantSummaries:
    def test_returns_summaries(self):
        mgr, dash, _ = _setup()
        mgr.create_tenant(CreateTenantRequest(
            business_name="Acme", country_code="US", timezone="UTC",
            actor_id="a", issued_at=T0, initial_branch_name="HQ",
        ))
        summaries = dash.get_tenant_summaries()
        assert len(summaries) == 1
        assert summaries[0].name == "Acme"
        assert summaries[0].branch_count == 1
        assert summaries[0].state == "CREATED"


class TestTenantDetail:
    def test_returns_detail_with_settings(self):
        mgr, dash, settings = _setup()
        result = mgr.create_tenant(CreateTenantRequest(
            business_name="Acme", country_code="KE", timezone="Africa/Nairobi",
            actor_id="a", issued_at=T0, initial_branch_name="HQ",
        ))
        biz_id = result["business_id"]
        settings.apply(SETTINGS_TAX_RULE_CONFIGURED_V1, {
            "business_id": str(biz_id), "tax_code": "VAT",
            "rate": "0.16", "description": "KE VAT",
            "actor_id": "a", "issued_at": T0,
        })
        detail = dash.get_tenant_detail(biz_id)
        assert detail is not None
        assert detail["name"] == "Acme"
        assert len(detail["branches"]) == 1
        assert "VAT" in detail["settings"]["tax_rules"]

    def test_not_found(self):
        _, dash, _ = _setup()
        assert dash.get_tenant_detail(uuid.uuid4()) is None


class TestHealthStatus:
    def test_healthy_system(self):
        _, dash, _ = _setup()
        health = dash.get_health_status(
            resilience_mode="NORMAL",
            projection_count=10,
            cache_hit_rate=0.95,
        )
        assert health.is_healthy is True
        assert health.resilience_mode == "NORMAL"

    def test_unhealthy_when_degraded(self):
        _, dash, _ = _setup()
        health = dash.get_health_status(
            resilience_mode="DEGRADED",
            projection_count=10,
        )
        assert health.is_healthy is False

    def test_unhealthy_with_broken_projections(self):
        _, dash, _ = _setup()
        health = dash.get_health_status(
            resilience_mode="NORMAL",
            projection_count=10,
            unhealthy_projections=["retail_rm"],
        )
        assert health.is_healthy is False
