"""
BOS Event Store — Validators Public API
=========================================
"""

from core.event_store.validators.errors import (
    Rejection,
    RejectionCode,
    ValidationResult,
    ViolatedRule,
)
from core.event_store.validators.context import BusinessContextProtocol
from core.event_store.validators.registry import EventTypeRegistry
from core.event_store.validators.event_validator import validate_event

__all__ = [
    "validate_event",
    "ValidationResult",
    "Rejection",
    "RejectionCode",
    "ViolatedRule",
    "BusinessContextProtocol",
    "EventTypeRegistry",
]
