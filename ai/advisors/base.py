"""
BOS AI Advisors — Base Advisor Protocol
==========================================
All domain advisors implement this protocol.
Advisors are read-only — they consume projections and
produce advisory outputs logged to the Decision Journal.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from ai.journal.models import DecisionEntry, DecisionMode, DecisionOutcome


# ══════════════════════════════════════════════════════════════
# ADVISORY OUTPUT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Advisory:
    """
    Structured AI recommendation.

    This is the output of an advisor — it gets recorded in the
    Decision Journal and optionally presented for human review.
    """

    engine: str               # which engine this relates to
    advice_type: str          # reorder_suggestion | anomaly_flag | forecast | optimization
    title: str                # human-readable summary
    description: str          # detailed explanation
    confidence: float         # 0.0 to 1.0
    recommended_action: Optional[str] = None  # what the AI suggests
    data: Dict[str, Any] = field(default_factory=dict)  # supporting evidence

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}.")

    def to_advice_payload(self) -> Dict[str, Any]:
        """Serialize for Decision Journal storage."""
        return {
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "recommended_action": self.recommended_action,
            "data": self.data,
        }


# ══════════════════════════════════════════════════════════════
# ADVISOR PROTOCOL
# ══════════════════════════════════════════════════════════════

class Advisor(ABC):
    """
    Base class for domain-specific AI advisors.

    Subclasses implement `analyze()` which reads from projections
    and returns a list of Advisory outputs.
    """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Which engine this advisor covers."""
        ...

    @abstractmethod
    def analyze(
        self,
        tenant_id: uuid.UUID,
        context: Dict[str, Any],
        now: datetime,
    ) -> List[Advisory]:
        """
        Analyze current state and produce advisories.

        Args:
            tenant_id: Business scope (AI is tenant-scoped)
            context: Read-model / projection data to analyze
            now: Current time (explicit, not datetime.now())

        Returns:
            List of Advisory outputs to be journaled
        """
        ...

    def create_decision_entry(
        self,
        advisory: Advisory,
        tenant_id: uuid.UUID,
        mode: DecisionMode,
        now: datetime,
        actor_id: str = "ai-advisor",
    ) -> DecisionEntry:
        """Convert an Advisory into a DecisionEntry for journaling."""
        return DecisionEntry(
            decision_id=uuid.uuid4(),
            tenant_id=tenant_id,
            engine=advisory.engine,
            advice_type=advisory.advice_type,
            advice=advisory.to_advice_payload(),
            mode=mode,
            outcome=DecisionOutcome.PENDING,
            actor_type="AI",
            actor_id=actor_id,
            occurred_at=now,
        )
