"""
BOS Documents - Numbering Engine
===================================
Deterministic document number generation from a NumberingPolicy + sequence state.

Doctrine:
- Stateless engine: given the same inputs, always produces the same output.
- Sequence state is managed externally (provider/event store).
- Time is passed explicitly — never read from system clock here.
- No random(), no mutable global state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from core.documents.numbering.models import (
    RESET_DAILY,
    RESET_MONTHLY,
    RESET_NEVER,
    RESET_YEARLY,
    NumberingPolicy,
)


# ---------------------------------------------------------------------------
# Period key helpers
# ---------------------------------------------------------------------------

def period_key(policy: NumberingPolicy, issued_at: datetime) -> str:
    """
    Return a string key identifying the current reset period for issued_at.

    This key changes when the sequence should reset:
    - NEVER   → "" (constant)
    - DAILY   → "2026-02-18"
    - MONTHLY → "2026-02"
    - YEARLY  → "2026"
    """
    if policy.reset_period == RESET_NEVER:
        return ""
    # Normalise to UTC
    if issued_at.tzinfo is None:
        issued_at = issued_at.replace(tzinfo=timezone.utc)
    else:
        issued_at = issued_at.astimezone(timezone.utc)

    if policy.reset_period == RESET_DAILY:
        return issued_at.strftime("%Y-%m-%d")
    if policy.reset_period == RESET_MONTHLY:
        return issued_at.strftime("%Y-%m")
    if policy.reset_period == RESET_YEARLY:
        return issued_at.strftime("%Y")
    return ""


# ---------------------------------------------------------------------------
# Sequence state
# ---------------------------------------------------------------------------

class SequenceState:
    """
    Tracks the current sequence counter for one policy.

    - current_period_key: the period key when the counter was last updated
    - current_sequence: the next sequence number to issue
    """

    def __init__(
        self,
        policy: NumberingPolicy,
        *,
        current_period_key: str = "",
        current_sequence: int | None = None,
    ):
        self._policy = policy
        self._current_period_key = current_period_key
        self._current_sequence = current_sequence if current_sequence is not None else policy.start_at

    @property
    def policy(self) -> NumberingPolicy:
        return self._policy

    @property
    def current_sequence(self) -> int:
        return self._current_sequence

    @property
    def current_period_key(self) -> str:
        return self._current_period_key

    def next_number(self, issued_at: datetime) -> tuple[str, "SequenceState"]:
        """
        Return (doc_number, new_state) for issued_at.

        Resets counter if the period key has changed.
        Returns a new SequenceState (immutable pattern).
        """
        new_period_key = period_key(self._policy, issued_at)
        if new_period_key != self._current_period_key:
            # Period rolled over: reset counter
            next_seq = self._policy.start_at
        else:
            next_seq = self._current_sequence

        doc_number = self._policy.format_number(next_seq)
        new_state = SequenceState(
            self._policy,
            current_period_key=new_period_key,
            current_sequence=next_seq + 1,
        )
        return doc_number, new_state


# ---------------------------------------------------------------------------
# Numbering Engine (stateless, functional)
# ---------------------------------------------------------------------------

def generate_document_number(
    *,
    policy: NumberingPolicy,
    sequence: int,
    issued_at: datetime,
) -> str:
    """
    Generate a document number deterministically.

    Args:
        policy: the NumberingPolicy for this doc_type/business/branch
        sequence: the 1-based sequence position within the current period
        issued_at: the document issuance datetime (used to build suffix if needed)

    Returns:
        formatted document number string
    """
    if not isinstance(sequence, int) or sequence < 1:
        raise ValueError("sequence must be int >= 1.")
    if not isinstance(issued_at, datetime):
        raise ValueError("issued_at must be datetime.")
    return policy.format_number(sequence)


def build_suffix_for_period(policy: NumberingPolicy, issued_at: datetime) -> str:
    """
    Build a dynamic suffix incorporating the period (e.g. "/2026" for yearly).
    Caller is responsible for setting policy.suffix to an empty string and using
    this value to override if dynamic suffixes are desired.

    Used when policy.suffix contains a format template token like '{year}'.
    If policy.suffix does not contain '{year}', '{month}', or '{day}',
    returns policy.suffix unchanged.
    """
    suffix = policy.suffix
    if "{" not in suffix:
        return suffix

    if issued_at.tzinfo is None:
        dt = issued_at.replace(tzinfo=timezone.utc)
    else:
        dt = issued_at.astimezone(timezone.utc)

    suffix = suffix.replace("{year}", dt.strftime("%Y"))
    suffix = suffix.replace("{month}", dt.strftime("%m"))
    suffix = suffix.replace("{day}", dt.strftime("%d"))
    return suffix
