"""
BOS Event Store — Idempotency Guard Public API
================================================
"""

from core.event_store.idempotency.errors import (
    IdempotencyRejectionCode,
    IdempotencyViolatedRule,
)
from core.event_store.idempotency.guard import (
    check_idempotency,
    handle_integrity_error,
)

__all__ = [
    "check_idempotency",
    "handle_integrity_error",
    "IdempotencyRejectionCode",
    "IdempotencyViolatedRule",
]