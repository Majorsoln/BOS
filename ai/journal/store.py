"""
BOS Decision Journal — In-Memory Store
=========================================
Append-only storage for DecisionEntry records.
Production would back this with event store; this is the in-memory
implementation for testing and development.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from ai.journal.models import DecisionEntry, DecisionMode, DecisionOutcome


class DecisionJournal:
    """
    Append-only decision journal.

    Records are indexed by decision_id and queryable by tenant_id.
    No deletion is permitted.
    """

    def __init__(self) -> None:
        self._entries: Dict[uuid.UUID, DecisionEntry] = {}
        self._by_tenant: Dict[uuid.UUID, List[uuid.UUID]] = {}

    def record(self, entry: DecisionEntry) -> None:
        """Append a decision entry. Duplicate decision_id raises ValueError."""
        if entry.decision_id in self._entries:
            raise ValueError(
                f"Decision {entry.decision_id} already exists — journal is append-only."
            )
        self._entries[entry.decision_id] = entry
        self._by_tenant.setdefault(entry.tenant_id, []).append(entry.decision_id)

    def get(self, decision_id: uuid.UUID) -> Optional[DecisionEntry]:
        """Retrieve a decision by ID."""
        return self._entries.get(decision_id)

    def list_by_tenant(
        self, tenant_id: uuid.UUID, engine: Optional[str] = None
    ) -> List[DecisionEntry]:
        """List all decisions for a tenant, optionally filtered by engine."""
        ids = self._by_tenant.get(tenant_id, [])
        entries = [self._entries[did] for did in ids]
        if engine:
            entries = [e for e in entries if e.engine == engine]
        return entries

    def list_pending(self, tenant_id: uuid.UUID) -> List[DecisionEntry]:
        """List all pending decisions awaiting human review."""
        return [
            e for e in self.list_by_tenant(tenant_id)
            if e.is_pending()
        ]

    def resolve(
        self,
        decision_id: uuid.UUID,
        outcome: DecisionOutcome,
        reviewed_by: str,
        reviewed_at: datetime,
    ) -> DecisionEntry:
        """
        Mark a pending decision as ACCEPTED or REJECTED.

        Creates a new DecisionEntry (immutable) with the outcome set.
        The original entry remains in the journal for audit trail.
        """
        original = self._entries.get(decision_id)
        if original is None:
            raise ValueError(f"Decision {decision_id} not found.")
        if not original.is_pending():
            raise ValueError(
                f"Decision {decision_id} is already {original.outcome.value}, cannot re-resolve."
            )
        if outcome not in (DecisionOutcome.ACCEPTED, DecisionOutcome.REJECTED):
            raise ValueError(f"Resolution outcome must be ACCEPTED or REJECTED, got {outcome}.")

        resolved = DecisionEntry(
            decision_id=original.decision_id,
            tenant_id=original.tenant_id,
            engine=original.engine,
            advice_type=original.advice_type,
            advice=original.advice,
            mode=original.mode,
            outcome=outcome,
            actor_type=original.actor_type,
            actor_id=original.actor_id,
            occurred_at=original.occurred_at,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            metadata=original.metadata,
        )
        # Replace in journal (same ID, resolved version)
        self._entries[decision_id] = resolved
        return resolved

    @property
    def count(self) -> int:
        return len(self._entries)
