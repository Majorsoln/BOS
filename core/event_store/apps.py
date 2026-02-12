"""
BOS Core — Event Store App Configuration
==========================================
The Event Store is BOS's first and most fundamental module.
It is the immutable vault of truth. All state in BOS originates here.

This app:
- Validates event structure
- Enforces idempotency
- Maintains hash-chain integrity
- Persists immutable events

This app does NOT:
- Interpret event meaning
- Write business state
- Make decisions
- Dispatch events (that is core.events responsibility)
"""

from django.apps import AppConfig


class EventStoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.event_store"
    label = "event_store"
    verbose_name = "BOS Event Store"
