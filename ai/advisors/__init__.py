"""
BOS AI Advisors — Public API
================================
Domain-specific advisory modules.
"""

from ai.advisors.base import Advisor, Advisory
from ai.advisors.inventory_advisor import InventoryAdvisor
from ai.advisors.cash_advisor import CashAdvisor
from ai.advisors.procurement_advisor import ProcurementAdvisor

__all__ = [
    "Advisor",
    "Advisory",
    "InventoryAdvisor",
    "CashAdvisor",
    "ProcurementAdvisor",
]
