"""
BOS Core Config — Admin-Configurable Rules
=============================================
Doctrine: No hardcoded country codes in engine logic.
Tax rates, compliance rules, and regional settings come
from admin-configurable data, not from source code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, Tuple


# ══════════════════════════════════════════════════════════════
# TAX RULE
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TaxRule:
    """
    Tax calculation rule (VAT, GST, sales tax, etc).

    Rates and applicability are admin-defined per country,
    never hardcoded in engine logic.
    """

    country_code: str
    tax_type: str  # VAT | GST | SALES_TAX | WITHHOLDING
    rate: float  # 0.16 means 16%
    applies_to: Tuple[str, ...] = ()  # product categories
    exemptions: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.rate <= 1:
            raise ValueError(f"Tax rate must be between 0 and 1, got {self.rate}.")

    def compute_tax(self, amount: float) -> float:
        """Compute tax amount for a given base amount."""
        return round(amount * self.rate, 2)

    def is_exempt(self, category: str) -> bool:
        """Check if a category is exempt from this tax."""
        return category in self.exemptions


# ══════════════════════════════════════════════════════════════
# COMPLIANCE RULE
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ComplianceRule:
    """Regional compliance configuration."""

    country_code: str
    rule_type: str  # AUDIT_RETENTION | EXPORT_CONTROL | DATA_RESIDENCY
    params: Dict[str, Any] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════
# CONFIG STORE PROTOCOL
# ══════════════════════════════════════════════════════════════

class ConfigStore(Protocol):
    """
    Protocol for admin-configured rule storage.

    Implementations may back this with a database, file, or in-memory store.
    """

    def get_tax_rules(self, country_code: str) -> list[TaxRule]:
        """Fetch all tax rules for a country."""
        ...  # pragma: no cover

    def get_compliance_rule(
        self, country_code: str, rule_type: str
    ) -> Optional[ComplianceRule]:
        """Fetch a specific compliance rule."""
        ...  # pragma: no cover


# ══════════════════════════════════════════════════════════════
# IN-MEMORY CONFIG STORE (for testing / bootstrap)
# ══════════════════════════════════════════════════════════════

class InMemoryConfigStore:
    """Simple in-memory config store for testing and bootstrap."""

    def __init__(self) -> None:
        self._tax_rules: list[TaxRule] = []
        self._compliance_rules: list[ComplianceRule] = []

    def add_tax_rule(self, rule: TaxRule) -> None:
        self._tax_rules.append(rule)

    def add_compliance_rule(self, rule: ComplianceRule) -> None:
        self._compliance_rules.append(rule)

    def get_tax_rules(self, country_code: str) -> list[TaxRule]:
        return [r for r in self._tax_rules if r.country_code == country_code]

    def get_compliance_rule(
        self, country_code: str, rule_type: str
    ) -> Optional[ComplianceRule]:
        for r in self._compliance_rules:
            if r.country_code == country_code and r.rule_type == rule_type:
                return r
        return None
