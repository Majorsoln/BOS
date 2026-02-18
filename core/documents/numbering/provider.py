"""
BOS Documents - Numbering Provider
=====================================
Protocol + InMemory implementation for numbering policy resolution
and sequence state management.

Doctrine:
- Provider is a dependency injection point (testable, swappable).
- InMemory provider is deterministic and used in tests.
- DB provider is registered separately (adapters layer).
- Sequence state mutation is atomic per business+doc_type+branch scope.
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional, Protocol

from core.documents.numbering.engine import SequenceState
from core.documents.numbering.models import NumberingPolicy


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

class NumberingProvider(Protocol):
    def get_policy(
        self,
        *,
        business_id_str: str,
        doc_type: str,
        branch_id_str: Optional[str] = None,
    ) -> Optional[NumberingPolicy]:
        """Return the active NumberingPolicy, or None if not configured."""
        ...

    def get_and_advance(
        self,
        *,
        policy: NumberingPolicy,
        issued_at: datetime,
    ) -> str:
        """
        Atomically get the next document number and advance the sequence.

        Returns the formatted document number string.
        """
        ...


# ---------------------------------------------------------------------------
# InMemory Provider (deterministic, thread-safe for tests)
# ---------------------------------------------------------------------------

class InMemoryNumberingProvider:
    """
    Thread-safe in-memory numbering provider.
    Used in tests and bootstrap.

    Policies are registered at construction time.
    Sequence states are maintained in-memory.
    """

    def __init__(self, policies: tuple[NumberingPolicy, ...] = ()):
        self._lock = threading.Lock()
        # Key: (business_id_str, doc_type, branch_id_str or "")
        self._policies: dict[tuple[str, str, str], NumberingPolicy] = {}
        self._states: dict[str, SequenceState] = {}  # keyed by policy_id

        for policy in policies:
            key = (policy.business_id_str, policy.doc_type, policy.branch_id_str or "")
            self._policies[key] = policy
            self._states[policy.policy_id] = SequenceState(policy)

    def get_policy(
        self,
        *,
        business_id_str: str,
        doc_type: str,
        branch_id_str: Optional[str] = None,
    ) -> Optional[NumberingPolicy]:
        # Try branch-specific first
        if branch_id_str:
            key = (business_id_str, doc_type, branch_id_str)
            policy = self._policies.get(key)
            if policy is not None:
                return policy
        # Fall back to business-level
        key = (business_id_str, doc_type, "")
        return self._policies.get(key)

    def get_and_advance(
        self,
        *,
        policy: NumberingPolicy,
        issued_at: datetime,
    ) -> str:
        with self._lock:
            state = self._states.get(policy.policy_id)
            if state is None:
                state = SequenceState(policy)
            doc_number, new_state = state.next_number(issued_at)
            self._states[policy.policy_id] = new_state
            return doc_number

    def register_policy(self, policy: NumberingPolicy) -> None:
        """Register or replace a policy (used in tests)."""
        with self._lock:
            key = (policy.business_id_str, policy.doc_type, policy.branch_id_str or "")
            self._policies[key] = policy
            if policy.policy_id not in self._states:
                self._states[policy.policy_id] = SequenceState(policy)

    def current_sequence(self, policy_id: str) -> int:
        """Inspect the current sequence counter for a policy (test helper)."""
        with self._lock:
            state = self._states.get(policy_id)
            if state is None:
                return 1
            return state.current_sequence
