"""
BOS Event Store - Persistence Repository
=======================================
Single low-level save helper used by persistence service.
"""

from __future__ import annotations

from core.event_store.models import Event


def save_event(event_data: dict) -> Event:
    """
    Persist one event row via Django ORM.

    The caller (persistence service) owns all validation and transactional guards.
    """
    return Event.objects.create(**event_data)

