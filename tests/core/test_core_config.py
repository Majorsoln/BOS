"""
Tests for core.config — Admin-configurable rules.
"""

import pytest

from core.config.rules import TaxRule, ComplianceRule, InMemoryConfigStore


# ── TaxRule Tests ────────────────────────────────────────────

class TestTaxRule:
    def test_compute_tax(self):
        rule = TaxRule(country_code="KE", tax_type="VAT", rate=0.16)
        assert rule.compute_tax(1000.0) == 160.0

    def test_zero_rate(self):
        rule = TaxRule(country_code="KE", tax_type="VAT", rate=0.0)
        assert rule.compute_tax(1000.0) == 0.0

    def test_invalid_rate_too_high(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            TaxRule(country_code="KE", tax_type="VAT", rate=1.5)

    def test_invalid_rate_negative(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            TaxRule(country_code="KE", tax_type="VAT", rate=-0.1)

    def test_exemptions(self):
        rule = TaxRule(
            country_code="KE",
            tax_type="VAT",
            rate=0.16,
            applies_to=("electronics", "clothing"),
            exemptions=("food", "medicine"),
        )
        assert rule.is_exempt("food")
        assert not rule.is_exempt("electronics")

    def test_frozen_immutability(self):
        rule = TaxRule(country_code="KE", tax_type="VAT", rate=0.16)
        with pytest.raises(AttributeError):
            rule.rate = 0.18


# ── ComplianceRule Tests ─────────────────────────────────────

class TestComplianceRule:
    def test_basic_rule(self):
        rule = ComplianceRule(
            country_code="KE",
            rule_type="AUDIT_RETENTION",
            params={"years": 7},
        )
        assert rule.params["years"] == 7

    def test_frozen_immutability(self):
        rule = ComplianceRule(country_code="KE", rule_type="DATA_RESIDENCY")
        with pytest.raises(AttributeError):
            rule.country_code = "US"


# ── InMemoryConfigStore Tests ────────────────────────────────

class TestInMemoryConfigStore:
    def test_add_and_get_tax_rules(self):
        store = InMemoryConfigStore()
        rule_ke = TaxRule(country_code="KE", tax_type="VAT", rate=0.16)
        rule_tz = TaxRule(country_code="TZ", tax_type="VAT", rate=0.18)
        store.add_tax_rule(rule_ke)
        store.add_tax_rule(rule_tz)

        ke_rules = store.get_tax_rules("KE")
        assert len(ke_rules) == 1
        assert ke_rules[0].rate == 0.16

        tz_rules = store.get_tax_rules("TZ")
        assert len(tz_rules) == 1
        assert tz_rules[0].rate == 0.18

    def test_get_tax_rules_empty(self):
        store = InMemoryConfigStore()
        assert store.get_tax_rules("XX") == []

    def test_compliance_rules(self):
        store = InMemoryConfigStore()
        rule = ComplianceRule(
            country_code="KE",
            rule_type="AUDIT_RETENTION",
            params={"years": 7},
        )
        store.add_compliance_rule(rule)

        result = store.get_compliance_rule("KE", "AUDIT_RETENTION")
        assert result is not None
        assert result.params["years"] == 7

    def test_compliance_rule_not_found(self):
        store = InMemoryConfigStore()
        assert store.get_compliance_rule("KE", "NONEXISTENT") is None
