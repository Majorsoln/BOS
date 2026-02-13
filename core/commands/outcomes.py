"""
BOS Command Layer — Command Outcome Contract
===============================================
Every Command produces exactly one Outcome. No exceptions.

ACCEPTED → command intent authorized, proceed to execution.
REJECTED → command denied, reason is mandatory and auditable.

Rules:
- Exactly one outcome per command
- Outcome is immutable (frozen dataclass)
- REJECTED must contain reason (RejectionReason)
- ACCEPTED must NOT contain reason
- occurred_at is mandatory
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# COMMAND STATUS
# ══════════════════════════════════════════════════════════════

class CommandStatus(Enum):
    """Binary command decision. No middle ground."""
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


# ══════════════════════════════════════════════════════════════
# COMMAND OUTCOME
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CommandOutcome:
    """
    Deterministic result of command evaluation.

    Fields:
        command_id:  The command this outcome belongs to.
        status:      ACCEPTED or REJECTED.
        reason:      RejectionReason (mandatory if REJECTED, None if ACCEPTED).
        occurred_at: When the decision was made.

    Invariants:
        - REJECTED + reason is None → ValueError
        - ACCEPTED + reason is not None → ValueError
    """

    command_id: uuid.UUID
    status: CommandStatus
    reason: Optional[RejectionReason]
    occurred_at: datetime

    def __post_init__(self):
        if not isinstance(self.command_id, uuid.UUID):
            raise ValueError("command_id must be UUID.")

        if not isinstance(self.status, CommandStatus):
            raise ValueError(
                f"status must be CommandStatus, got {type(self.status).__name__}."
            )

        if self.status == CommandStatus.REJECTED and self.reason is None:
            raise ValueError(
                "REJECTED outcome must include a RejectionReason. "
                "No silent rejections allowed."
            )

        if self.status == CommandStatus.ACCEPTED and self.reason is not None:
            raise ValueError(
                "ACCEPTED outcome must NOT include a RejectionReason."
            )

        if not isinstance(self.occurred_at, datetime):
            raise ValueError("occurred_at must be a datetime.")

    @property
    def is_accepted(self) -> bool:
        return self.status == CommandStatus.ACCEPTED

    @property
    def is_rejected(self) -> bool:
        return self.status == CommandStatus.REJECTED
