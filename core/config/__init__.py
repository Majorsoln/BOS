"""
BOS Core Config — Public API
===============================
Admin-configurable rules (tax, compliance, regional).
Doctrine: No hardcoded country codes in engine logic.
"""

from core.config.rules import (
    ComplianceRule,
    ConfigStore,
    InMemoryConfigStore,
    TaxRule,
)

__all__ = [
    "TaxRule",
    "ComplianceRule",
    "ConfigStore",
    "InMemoryConfigStore",
]
