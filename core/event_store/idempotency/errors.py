"""
BOS Event Store — Idempotency Errors
======================================
Rejection code and violated rule for duplicate event detection.
Separate from validator errors — idempotency is its own guard.
"""


class IdempotencyRejectionCode:
    """Rejection code for idempotency violations."""

    DUPLICATE_EVENT_ID = "DUPLICATE_EVENT_ID"


class IdempotencyViolatedRule:
    """Rule identifier for audit trail."""

    EVENT_IDEMPOTENCY = "EVENT_IDEMPOTENCY"