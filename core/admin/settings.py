"""
BOS Admin — System Settings
===============================
Event-sourced system configuration management.

Tax rules, compliance rules, and global system properties.
All changes produce events — no direct config mutations.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


# ══════════════════════════════════════════════════════════════
# SETTINGS EVENT TYPES
# ══════════════════════════════════════════════════════════════

SETTINGS_TAX_RULE_CONFIGURED_V1 = "admin.tax_rule.configured.v1"
SETTINGS_SYSTEM_PROPERTY_SET_V1 = "admin.system_property.set.v1"

SETTINGS_EVENT_TYPES = (
    SETTINGS_TAX_RULE_CONFIGURED_V1,
    SETTINGS_SYSTEM_PROPERTY_SET_V1,
)


# ══════════════════════════════════════════════════════════════
# SETTINGS REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SetTaxRuleRequest:
    business_id: uuid.UUID
    tax_code: str          # e.g. "VAT", "SALES_TAX"
    rate: Decimal          # e.g. 0.18 for 18%
    description: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class SetSystemPropertyRequest:
    business_id: uuid.UUID
    property_key: str      # e.g. "audit.retention_days", "rate_limit.max_per_minute"
    property_value: str    # stored as string, interpreted by consumer
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# SETTINGS PROJECTION
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TaxRuleEntry:
    tax_code: str
    rate: Decimal
    description: str
    configured_at: datetime
    configured_by: str


@dataclass(frozen=True)
class SystemPropertyEntry:
    property_key: str
    property_value: str
    set_at: datetime
    set_by: str


class SettingsProjection:
    """
    In-memory projection of system settings per business.

    Rebuilt deterministically from settings events.
    """

    projection_name = "settings_projection"

    def __init__(self) -> None:
        # { business_id: { tax_code: TaxRuleEntry } }
        self._tax_rules: Dict[uuid.UUID, Dict[str, TaxRuleEntry]] = defaultdict(dict)
        # { business_id: { property_key: SystemPropertyEntry } }
        self._properties: Dict[uuid.UUID, Dict[str, SystemPropertyEntry]] = defaultdict(dict)

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        biz_id = payload.get("business_id")
        if isinstance(biz_id, str):
            biz_id = uuid.UUID(biz_id)
        if biz_id is None:
            return

        if event_type == SETTINGS_TAX_RULE_CONFIGURED_V1:
            entry = TaxRuleEntry(
                tax_code=payload["tax_code"],
                rate=Decimal(str(payload["rate"])),
                description=payload.get("description", ""),
                configured_at=payload.get("issued_at"),
                configured_by=payload.get("actor_id", ""),
            )
            self._tax_rules[biz_id][entry.tax_code] = entry

        elif event_type == SETTINGS_SYSTEM_PROPERTY_SET_V1:
            entry = SystemPropertyEntry(
                property_key=payload["property_key"],
                property_value=payload["property_value"],
                set_at=payload.get("issued_at"),
                set_by=payload.get("actor_id", ""),
            )
            self._properties[biz_id][entry.property_key] = entry

    def get_tax_rule(
        self, business_id: uuid.UUID, tax_code: str
    ) -> Optional[TaxRuleEntry]:
        return self._tax_rules.get(business_id, {}).get(tax_code)

    def list_tax_rules(self, business_id: uuid.UUID) -> List[TaxRuleEntry]:
        return list(self._tax_rules.get(business_id, {}).values())

    def get_property(
        self, business_id: uuid.UUID, key: str
    ) -> Optional[str]:
        entry = self._properties.get(business_id, {}).get(key)
        return entry.property_value if entry else None

    def list_properties(self, business_id: uuid.UUID) -> List[SystemPropertyEntry]:
        return list(self._properties.get(business_id, {}).values())

    def truncate(self, business_id: Optional[uuid.UUID] = None) -> None:
        if business_id:
            self._tax_rules.pop(business_id, None)
            self._properties.pop(business_id, None)
        else:
            self._tax_rules.clear()
            self._properties.clear()

    def snapshot(self, business_id: uuid.UUID) -> Dict[str, Any]:
        return {
            "tax_rules": {
                code: {"rate": str(r.rate), "description": r.description}
                for code, r in self._tax_rules.get(business_id, {}).items()
            },
            "properties": {
                k: v.property_value
                for k, v in self._properties.get(business_id, {}).items()
            },
        }
