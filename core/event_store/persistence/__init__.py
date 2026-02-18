"""
BOS Event Store Persistence public API.
"""

from core.event_store.persistence.service import persist_event
from core.event_store.persistence.repository import load_events_for_business

__all__ = ["persist_event", "load_events_for_business"]
