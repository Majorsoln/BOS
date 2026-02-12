"""
BOS Engine Registry — System Governance Layer
===============================================
Controls which engines exist, what they own, and what they subscribe to.

Event Store protects history.
Event Bus protects flow.
Engine Registry protects discipline.

Without contract enforcement, future chaos is guaranteed.
"""

from core.engines.contracts import EngineContract
from core.engines.registry import (
    EngineRegistry,
    EngineRegistryError,
    DuplicateEngineError,
    DuplicateEventOwnerError,
    RegistryLockedError,
    RegistryNotLockedError,
)
from core.engines.enforcement import (
    EngineContractViolation,
    EmissionViolation,
    SubscriptionViolation,
    UnknownEventTypeViolation,
    UnregisteredEngineViolation,
    enforce_emission,
    enforce_subscription,
    enforced_persist_event,
    enforced_register_subscriber,
)

__all__ = [
    # ── Contract ──────────────────────────────────────────────
    "EngineContract",
    # ── Registry ──────────────────────────────────────────────
    "EngineRegistry",
    "EngineRegistryError",
    "DuplicateEngineError",
    "DuplicateEventOwnerError",
    "RegistryLockedError",
    "RegistryNotLockedError",
    # ── Enforcement ───────────────────────────────────────────
    "EngineContractViolation",
    "EmissionViolation",
    "SubscriptionViolation",
    "UnknownEventTypeViolation",
    "UnregisteredEngineViolation",
    "enforce_emission",
    "enforce_subscription",
    "enforced_persist_event",
    "enforced_register_subscriber",
]
