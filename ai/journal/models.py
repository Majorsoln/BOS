"""
BOS Decision Journal — Immutable Decision Records
=====================================================
Every AI advisory output is logged as a DecisionEntry.
These are append-only — never modified, never deleted.

Schema from BOS_MASTER_REFERENCE §4:
  decision_id, tenant_id, engine, advice, mode, outcome, actor, occurred_at
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


# ══════════════════════════════════════════════════════════════
# DECISION MODE
# ══════════════════════════════════════════════════════════════

class DecisionMode(Enum):
    """AI decision simulation mode."""
    ADVISORY = "advisory"                    # AI analyzes, human decides
    ASSISTED_EXECUTION = "assisted"          # AI prepares, human approves
    LIMITED_AUTOMATION = "limited_automation" # AI executes (policy-gated)


# ══════════════════════════════════════════════════════════════
# DECISION OUTCOME
# ══════════════════════════════════════════════════════════════

class DecisionOutcome(Enum):
    """Human review state of AI advice."""
    PENDING = "PENDING"      # Awaiting human review
    ACCEPTED = "ACCEPTED"    # Human accepted the advice
    REJECTED = "REJECTED"    # Human rejected the advice
    EXPIRED = "EXPIRED"      # Advice timed out without review


# ══════════════════════════════════════════════════════════════
# DECISION ENTRY (frozen, append-only)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class DecisionEntry:
    """
    Immutable record of an AI advisory output.

    Every AI recommendation, simulation result, or anomaly flag
    produces a DecisionEntry for full audit trail.
    """

    decision_id: uuid.UUID
    tenant_id: uuid.UUID      # business_id — AI is tenant-scoped
    engine: str               # which engine the advice relates to
    advice_type: str          # reorder_suggestion | anomaly_flag | simulation_result
    advice: Dict[str, Any]    # structured recommendation payload
    mode: DecisionMode
    outcome: DecisionOutcome
    actor_type: str           # AI model/service identifier
    actor_id: str             # specific AI instance
    occurred_at: datetime
    reviewed_by: Optional[str] = None     # human who reviewed (if applicable)
    reviewed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, uuid.UUID):
            raise ValueError("tenant_id must be UUID.")
        if not self.engine:
            raise ValueError("engine must be non-empty string.")

    def is_pending(self) -> bool:
        return self.outcome == DecisionOutcome.PENDING

    def is_resolved(self) -> bool:
        return self.outcome in (DecisionOutcome.ACCEPTED, DecisionOutcome.REJECTED)
