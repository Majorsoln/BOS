"""
BOS Admin — Dashboard Aggregation
=====================================
Read-only metrics aggregation for admin dashboards.

Combines data from multiple projections into
a unified overview for platform administrators.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.admin.tenant_manager import TenantProjection
from core.admin.settings import SettingsProjection
from core.business.models import BusinessState


# ══════════════════════════════════════════════════════════════
# DASHBOARD DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TenantSummary:
    """Summary of a single tenant for the dashboard."""
    business_id: uuid.UUID
    name: str
    state: str
    country_code: str
    branch_count: int
    open_branch_count: int


@dataclass(frozen=True)
class SystemOverview:
    """Aggregated system metrics."""
    total_tenants: int
    active_tenants: int
    suspended_tenants: int
    closed_tenants: int
    total_branches: int
    open_branches: int


@dataclass(frozen=True)
class HealthStatus:
    """System health indicators."""
    resilience_mode: str
    projection_count: int
    unhealthy_projections: List[str]
    cache_hit_rate: float
    is_healthy: bool


# ══════════════════════════════════════════════════════════════
# DASHBOARD SERVICE (read-only aggregation)
# ══════════════════════════════════════════════════════════════

class DashboardService:
    """
    Read-only dashboard aggregation service.

    Combines tenant projection, settings, and optional
    external metrics into a unified admin view.
    """

    def __init__(
        self,
        tenant_projection: TenantProjection,
        settings_projection: Optional[SettingsProjection] = None,
    ) -> None:
        self._tenants = tenant_projection
        self._settings = settings_projection

    def get_system_overview(self) -> SystemOverview:
        """Aggregate tenant counts by state."""
        businesses = self._tenants.list_businesses()
        active = sum(1 for b in businesses if b.state == BusinessState.ACTIVE)
        suspended = sum(1 for b in businesses if b.state == BusinessState.SUSPENDED)
        closed = sum(1 for b in businesses if b.state == BusinessState.CLOSED)

        total_branches = 0
        open_branches = 0
        for b in businesses:
            branches = self._tenants.get_branches(b.business_id)
            total_branches += len(branches)
            open_branches += sum(1 for br in branches if br.is_open())

        return SystemOverview(
            total_tenants=len(businesses),
            active_tenants=active,
            suspended_tenants=suspended,
            closed_tenants=closed,
            total_branches=total_branches,
            open_branches=open_branches,
        )

    def get_tenant_summaries(self) -> List[TenantSummary]:
        """List all tenants with branch counts."""
        result = []
        for biz in self._tenants.list_businesses():
            branches = self._tenants.get_branches(biz.business_id)
            result.append(TenantSummary(
                business_id=biz.business_id,
                name=biz.name,
                state=biz.state.value,
                country_code=biz.country_code,
                branch_count=len(branches),
                open_branch_count=sum(1 for b in branches if b.is_open()),
            ))
        return result

    def get_tenant_detail(
        self, business_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Get detailed info for a single tenant."""
        biz = self._tenants.get_business(business_id)
        if biz is None:
            return None

        branches = self._tenants.get_branches(business_id)
        detail: Dict[str, Any] = {
            "business_id": str(biz.business_id),
            "name": biz.name,
            "state": biz.state.value,
            "country_code": biz.country_code,
            "timezone": biz.timezone,
            "created_at": biz.created_at,
            "closed_at": biz.closed_at,
            "branches": [
                {
                    "branch_id": str(b.branch_id),
                    "name": b.name,
                    "location": b.location,
                    "is_open": b.is_open(),
                }
                for b in branches
            ],
        }

        if self._settings:
            detail["settings"] = self._settings.snapshot(business_id)

        return detail

    def get_health_status(
        self,
        resilience_mode: str = "NORMAL",
        projection_count: int = 0,
        unhealthy_projections: Optional[List[str]] = None,
        cache_hit_rate: float = 0.0,
    ) -> HealthStatus:
        """Build a health status report."""
        unhealthy = unhealthy_projections or []
        return HealthStatus(
            resilience_mode=resilience_mode,
            projection_count=projection_count,
            unhealthy_projections=unhealthy,
            cache_hit_rate=cache_hit_rate,
            is_healthy=(
                resilience_mode == "NORMAL"
                and len(unhealthy) == 0
            ),
        )
