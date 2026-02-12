"""
BOS Event Store — Idempotency Guard
=====================================
Ensures no duplicate event_id is ever persisted.

Enforcement at TWO levels:
  A) Application Level — query DB before save
  B) Database Level — catch IntegrityError as race-condition fallback

Rules (NON-NEGOTIABLE):
- Duplicate event_id → deterministic rejection
- No payload comparison
- No silent success on duplicate
- No retry-safe merge
- No mutation of original event

The Event Store is a vault, not a merge engine.
"""

import uuid

from django.db import IntegrityError

from core.event_store.models import Event
from core.event_store.idempotency.errors import (
    IdempotencyRejectionCode,
    IdempotencyViolatedRule,
)
from core.event_store.validators.errors import Rejection, ValidationResult


def check_idempotency(event_id: uuid.UUID) -> ValidationResult:
    """
    Application-level idempotency check.
    Query the Event Store for an existing event with this event_id.

    Args:
        event_id: The UUID to check for duplicates.

    Returns:
        ValidationResult — accepted=True if no duplicate found,
        accepted=False with DUPLICATE_EVENT_ID rejection otherwise.

    This function:
    - Does NOT compare payloads
    - Does NOT return success on duplicate
    - Does NOT mutate anything
    - Is side-effect free (read-only query)
    """
    if Event.objects.filter(event_id=event_id).exists():
        return ValidationResult(
            accepted=False,
            rejection=Rejection(
                code=IdempotencyRejectionCode.DUPLICATE_EVENT_ID,
                message=f"Event with ID {event_id} already exists.",
                violated_rule=IdempotencyViolatedRule.EVENT_IDEMPOTENCY,
            ),
        )

    return ValidationResult(accepted=True)


def handle_integrity_error(event_id: uuid.UUID, exc: IntegrityError) -> ValidationResult:
    """
    Database-level fallback for race conditions.
    If a concurrent write causes IntegrityError on event_id,
    convert it into a deterministic rejection.

    This is NOT a retry mechanism. It is a safety net.

    Args:
        event_id: The event_id that caused the conflict.
        exc: The IntegrityError raised by Django/DB.

    Returns:
        ValidationResult with DUPLICATE_EVENT_ID rejection.

    Raw database exceptions must NEVER propagate to callers.
    """
    return ValidationResult(
        accepted=False,
        rejection=Rejection(
            code=IdempotencyRejectionCode.DUPLICATE_EVENT_ID,
            message=(
                f"Event with ID {event_id} already exists "
                f"(detected at database level)."
            ),
            violated_rule=IdempotencyViolatedRule.EVENT_IDEMPOTENCY,
        ),
    )