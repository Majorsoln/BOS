"""
BOS Integration — Adapter Utilities
=======================================
Shared infrastructure for inbound and outbound adapters.

Doctrine: Adapters are stateless translators.
External systems NEVER write directly to BOS core data.
All integration is event-driven and permission-based.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


# ══════════════════════════════════════════════════════════════
# ERROR HIERARCHY
# ══════════════════════════════════════════════════════════════

class IntegrationError(Exception):
    """Base error for all integration failures."""

    def __init__(self, message: str, system_id: str = "", retryable: bool = False):
        super().__init__(message)
        self.system_id = system_id
        self.retryable = retryable


class ValidationError(IntegrationError):
    """External event failed validation (bad payload, missing fields)."""

    def __init__(self, message: str, system_id: str = ""):
        super().__init__(message, system_id=system_id, retryable=False)


class TranslationError(IntegrationError):
    """Cannot map external event to BOS command."""

    def __init__(self, message: str, system_id: str = ""):
        super().__init__(message, system_id=system_id, retryable=False)


class AuthenticationError(IntegrationError):
    """Signature/auth verification failed."""

    def __init__(self, message: str, system_id: str = ""):
        super().__init__(message, system_id=system_id, retryable=False)


class TransientError(IntegrationError):
    """Temporary failure — retryable with backoff."""

    def __init__(self, message: str, system_id: str = ""):
        super().__init__(message, system_id=system_id, retryable=True)


# ══════════════════════════════════════════════════════════════
# DIRECTION ENUM
# ══════════════════════════════════════════════════════════════

class Direction(Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


# ══════════════════════════════════════════════════════════════
# EXTERNAL EVENT REFERENCE (idempotency)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ExternalEventReference:
    """
    Tracks an external system's event for idempotency.

    external_event_id: the ID the external system assigned.
    system_id: which external system sent this.
    received_at: when BOS received the event.
    """

    external_event_id: str
    system_id: str
    received_at: datetime
    business_id: uuid.UUID
    payload_hash: str = ""

    @staticmethod
    def compute_payload_hash(payload: Dict[str, Any]) -> str:
        """Deterministic hash of the payload for dedup."""
        normalized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════
# WEBHOOK SIGNATURE VERIFICATION
# ══════════════════════════════════════════════════════════════

def verify_hmac_signature(
    payload_bytes: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """
    Verify HMAC signature on an inbound webhook payload.

    Returns True if signature matches, False otherwise.
    """
    if algorithm == "sha256":
        expected = hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
    elif algorithm == "sha1":
        expected = hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha1,
        ).hexdigest()
    else:
        return False

    return hmac.compare_digest(expected, signature)


# ══════════════════════════════════════════════════════════════
# ADAPTER CONFIGURATION
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AdapterConfig:
    """
    Configuration for an external system adapter.

    business_id-scoped — each business configures its own adapters.
    """

    adapter_id: uuid.UUID
    system_id: str         # e.g. "stripe", "kds_vendor_x", "sap"
    system_type: str       # e.g. "payment_gateway", "kitchen_display", "erp"
    business_id: uuid.UUID
    enabled: bool = True
    direction: Direction = Direction.INBOUND
    endpoint_url: str = ""
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0
    metadata: Dict[str, str] = field(default_factory=dict)
