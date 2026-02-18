"""
BOS Event Store - Persistence Repository
=======================================
Single low-level save helper used by persistence service.
"""

from __future__ import annotations

import uuid

from core.event_store.models import Event


def save_event(event_data: dict) -> Event:
    """
    Persist one event row via Django ORM.

    The caller (persistence service) owns all validation and transactional guards.
    """
    return Event.objects.create(**event_data)


def get_latest_event_for_business(
    business_id: uuid.UUID,
    *,
    lock: bool = False,
) -> Event | None:
    """
    Fetch the latest event for a business using deterministic ordering.

    Ordering rule:
        created_at DESC, event_id DESC

    lock=True enables row-level lock for transactional chain checks.
    """
    query = (
        Event.objects.filter(business_id=business_id)
        .order_by("-created_at", "-event_id")
    )
    if lock:
        query = query.select_for_update()
    return query.first()


def load_events_for_business(
    business_id: uuid.UUID,
) -> tuple[dict, ...]:
    """
    Load event envelopes for one business in deterministic replay order.

    Ordering rule:
        created_at ASC, event_id ASC
    """
    fields = (
        "event_id",
        "event_type",
        "event_version",
        "business_id",
        "branch_id",
        "source_engine",
        "actor_type",
        "actor_id",
        "correlation_id",
        "causation_id",
        "payload",
        "reference",
        "created_at",
        "status",
        "correction_of",
        "previous_event_hash",
        "event_hash",
    )
    rows = (
        Event.objects.filter(business_id=business_id)
        .order_by("created_at", "event_id")
        .values(*fields)
    )
    return tuple(dict(row) for row in rows)
