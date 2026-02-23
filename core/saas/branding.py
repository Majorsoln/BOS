"""
BOS SaaS — White-Label Branding Configuration
=================================================
Per-tenant branding configuration for white-label deployments.

Stores brand identity (logo, colors, contact, custom domain)
per business. All changes are event-sourced.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# BRANDING EVENT TYPES
# ══════════════════════════════════════════════════════════════

BRANDING_CONFIGURED_V1 = "saas.branding.configured.v1"
BRANDING_RESET_V1 = "saas.branding.reset.v1"

BRANDING_EVENT_TYPES = (
    BRANDING_CONFIGURED_V1,
    BRANDING_RESET_V1,
)


# ══════════════════════════════════════════════════════════════
# BRANDING DATA MODEL
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class BrandConfig:
    """Immutable branding configuration per business."""
    business_id: uuid.UUID
    company_name: str
    logo_url: str
    primary_color: str
    secondary_color: str
    support_email: str
    custom_domain: Optional[str] = None
    tagline: Optional[str] = None
    configured_at: Optional[datetime] = None
    configured_by: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# BRANDING REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ConfigureBrandingRequest:
    business_id: uuid.UUID
    company_name: str
    logo_url: str
    primary_color: str
    secondary_color: str
    support_email: str
    actor_id: str
    issued_at: datetime
    custom_domain: Optional[str] = None
    tagline: Optional[str] = None


@dataclass(frozen=True)
class ResetBrandingRequest:
    business_id: uuid.UUID
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# BRANDING PROJECTION
# ══════════════════════════════════════════════════════════════

class BrandingProjection:
    """
    In-memory projection of branding configs per business.

    Rebuilt deterministically from branding events.
    """

    projection_name = "branding_projection"

    def __init__(self) -> None:
        self._configs: Dict[uuid.UUID, BrandConfig] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        biz_id = uuid.UUID(str(payload["business_id"]))

        if event_type == BRANDING_CONFIGURED_V1:
            self._configs[biz_id] = BrandConfig(
                business_id=biz_id,
                company_name=payload["company_name"],
                logo_url=payload.get("logo_url", ""),
                primary_color=payload.get("primary_color", "#000000"),
                secondary_color=payload.get("secondary_color", "#FFFFFF"),
                support_email=payload.get("support_email", ""),
                custom_domain=payload.get("custom_domain"),
                tagline=payload.get("tagline"),
                configured_at=payload.get("issued_at"),
                configured_by=payload.get("actor_id"),
            )

        elif event_type == BRANDING_RESET_V1:
            self._configs.pop(biz_id, None)

    def get_config(self, business_id: uuid.UUID) -> Optional[BrandConfig]:
        return self._configs.get(business_id)

    def get_by_domain(self, domain: str) -> Optional[BrandConfig]:
        """Resolve branding by custom domain."""
        for config in self._configs.values():
            if config.custom_domain == domain:
                return config
        return None

    def list_configured(self) -> List[BrandConfig]:
        return list(self._configs.values())

    def truncate(self, business_id: Optional[uuid.UUID] = None) -> None:
        if business_id:
            self._configs.pop(business_id, None)
        else:
            self._configs.clear()

    def snapshot(self, business_id: uuid.UUID) -> Dict[str, Any]:
        config = self._configs.get(business_id)
        if config is None:
            return {}
        return {
            "company_name": config.company_name,
            "logo_url": config.logo_url,
            "primary_color": config.primary_color,
            "secondary_color": config.secondary_color,
            "support_email": config.support_email,
            "custom_domain": config.custom_domain,
            "tagline": config.tagline,
        }


# ══════════════════════════════════════════════════════════════
# BRANDING SERVICE
# ══════════════════════════════════════════════════════════════

class BrandingService:
    """
    Manages white-label branding per tenant.

    All mutations produce events — no direct state writes.
    """

    def __init__(self, projection: BrandingProjection) -> None:
        self._projection = projection

    def configure(
        self, request: ConfigureBrandingRequest
    ) -> Dict[str, Any]:
        """Set or update branding for a business."""
        payload = {
            "business_id": str(request.business_id),
            "company_name": request.company_name,
            "logo_url": request.logo_url,
            "primary_color": request.primary_color,
            "secondary_color": request.secondary_color,
            "support_email": request.support_email,
            "custom_domain": request.custom_domain,
            "tagline": request.tagline,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(BRANDING_CONFIGURED_V1, payload)
        return {
            "events": [{"event_type": BRANDING_CONFIGURED_V1, "payload": payload}],
        }

    def reset(
        self, request: ResetBrandingRequest
    ) -> Optional[RejectionReason]:
        """Remove branding for a business (revert to default)."""
        existing = self._projection.get_config(request.business_id)
        if existing is None:
            return RejectionReason(
                code="NO_BRANDING_CONFIGURED",
                message="No branding configured for this business.",
                policy_name="reset_branding",
            )
        self._projection.apply(BRANDING_RESET_V1, {
            "business_id": str(request.business_id),
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None
