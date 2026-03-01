"""
Tests — System Settings
==========================
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from core.admin.settings import (
    SETTINGS_SYSTEM_PROPERTY_SET_V1,
    SETTINGS_TAX_RULE_CONFIGURED_V1,
    SetSystemPropertyRequest,
    SetTaxRuleRequest,
    SettingsProjection,
)


BIZ = uuid.uuid4()
T0 = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestSettingsProjection:
    def test_apply_tax_rule(self):
        sp = SettingsProjection()
        sp.apply(SETTINGS_TAX_RULE_CONFIGURED_V1, {
            "business_id": str(BIZ),
            "tax_code": "VAT",
            "rate": "0.18",
            "description": "Value Added Tax 18%",
            "actor_id": "admin-1",
            "issued_at": T0,
        })
        rule = sp.get_tax_rule(BIZ, "VAT")
        assert rule is not None
        assert rule.rate == Decimal("0.18")
        assert rule.description == "Value Added Tax 18%"

    def test_list_tax_rules(self):
        sp = SettingsProjection()
        sp.apply(SETTINGS_TAX_RULE_CONFIGURED_V1, {
            "business_id": str(BIZ), "tax_code": "VAT",
            "rate": "0.18", "description": "VAT",
            "actor_id": "a", "issued_at": T0,
        })
        sp.apply(SETTINGS_TAX_RULE_CONFIGURED_V1, {
            "business_id": str(BIZ), "tax_code": "SALES_TAX",
            "rate": "0.07", "description": "Sales Tax",
            "actor_id": "a", "issued_at": T0,
        })
        rules = sp.list_tax_rules(BIZ)
        assert len(rules) == 2

    def test_overwrite_tax_rule(self):
        sp = SettingsProjection()
        sp.apply(SETTINGS_TAX_RULE_CONFIGURED_V1, {
            "business_id": str(BIZ), "tax_code": "VAT",
            "rate": "0.16", "description": "old",
            "actor_id": "a", "issued_at": T0,
        })
        sp.apply(SETTINGS_TAX_RULE_CONFIGURED_V1, {
            "business_id": str(BIZ), "tax_code": "VAT",
            "rate": "0.18", "description": "new",
            "actor_id": "a", "issued_at": T0,
        })
        rule = sp.get_tax_rule(BIZ, "VAT")
        assert rule.rate == Decimal("0.18")

    def test_apply_system_property(self):
        sp = SettingsProjection()
        sp.apply(SETTINGS_SYSTEM_PROPERTY_SET_V1, {
            "business_id": str(BIZ),
            "property_key": "audit.retention_days",
            "property_value": "365",
            "actor_id": "admin-1",
            "issued_at": T0,
        })
        assert sp.get_property(BIZ, "audit.retention_days") == "365"

    def test_list_properties(self):
        sp = SettingsProjection()
        sp.apply(SETTINGS_SYSTEM_PROPERTY_SET_V1, {
            "business_id": str(BIZ), "property_key": "k1",
            "property_value": "v1", "actor_id": "a", "issued_at": T0,
        })
        sp.apply(SETTINGS_SYSTEM_PROPERTY_SET_V1, {
            "business_id": str(BIZ), "property_key": "k2",
            "property_value": "v2", "actor_id": "a", "issued_at": T0,
        })
        props = sp.list_properties(BIZ)
        assert len(props) == 2

    def test_tenant_isolation(self):
        sp = SettingsProjection()
        biz2 = uuid.uuid4()
        sp.apply(SETTINGS_TAX_RULE_CONFIGURED_V1, {
            "business_id": str(BIZ), "tax_code": "VAT",
            "rate": "0.18", "description": "x",
            "actor_id": "a", "issued_at": T0,
        })
        assert sp.get_tax_rule(biz2, "VAT") is None

    def test_truncate(self):
        sp = SettingsProjection()
        sp.apply(SETTINGS_TAX_RULE_CONFIGURED_V1, {
            "business_id": str(BIZ), "tax_code": "VAT",
            "rate": "0.18", "description": "x",
            "actor_id": "a", "issued_at": T0,
        })
        sp.truncate(BIZ)
        assert sp.list_tax_rules(BIZ) == []

    def test_snapshot(self):
        sp = SettingsProjection()
        sp.apply(SETTINGS_TAX_RULE_CONFIGURED_V1, {
            "business_id": str(BIZ), "tax_code": "VAT",
            "rate": "0.18", "description": "VAT",
            "actor_id": "a", "issued_at": T0,
        })
        sp.apply(SETTINGS_SYSTEM_PROPERTY_SET_V1, {
            "business_id": str(BIZ), "property_key": "k1",
            "property_value": "v1", "actor_id": "a", "issued_at": T0,
        })
        snap = sp.snapshot(BIZ)
        assert "VAT" in snap["tax_rules"]
        assert snap["properties"]["k1"] == "v1"
