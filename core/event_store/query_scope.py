"""
BOS Event Store — Query Scope Guards
====================================
Default-safe helpers for tenant-scoped reads.
"""

from __future__ import annotations



def scoped_events_for_context(context):
    """
    Return Event queryset scoped to the active business context.

    Fails fast if context is missing/inactive.
    """
    if context is None or not context.has_active_context():
        raise ValueError("Active BusinessContext is required for event reads.")

    from core.event_store.models import Event

    business_id = context.get_active_business_id()
    qs = Event.objects.filter(business_id=business_id)

    branch_id = context.get_active_branch_id()
    if branch_id is not None:
        qs = qs.filter(branch_id=branch_id)

    return qs
