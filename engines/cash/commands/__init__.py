"""
BOS Cash Engine — Request Commands
=====================================
Typed cash management requests that convert into canonical Command objects.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.commands.base import Command
from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.identity.requirements import ACTOR_REQUIRED


# ══════════════════════════════════════════════════════════════
# COMMAND TYPE CONSTANTS
# ══════════════════════════════════════════════════════════════

CASH_SESSION_OPEN_REQUEST = "cash.session.open.request"
CASH_SESSION_CLOSE_REQUEST = "cash.session.close.request"
CASH_PAYMENT_RECORD_REQUEST = "cash.payment.record.request"
CASH_DEPOSIT_RECORD_REQUEST = "cash.deposit.record.request"
CASH_WITHDRAWAL_RECORD_REQUEST = "cash.withdrawal.record.request"

CASH_COMMAND_TYPES = frozenset({
    CASH_SESSION_OPEN_REQUEST,
    CASH_SESSION_CLOSE_REQUEST,
    CASH_PAYMENT_RECORD_REQUEST,
    CASH_DEPOSIT_RECORD_REQUEST,
    CASH_WITHDRAWAL_RECORD_REQUEST,
})

VALID_PAYMENT_METHODS = frozenset({
    "CASH", "CARD", "MOBILE", "BANK_TRANSFER", "CHEQUE",
})
VALID_DEPOSIT_REASONS = frozenset({
    "FLOAT_ADD", "CHANGE_REPLENISH", "TRANSFER_IN",
})
VALID_WITHDRAWAL_REASONS = frozenset({
    "BANK_DEPOSIT", "SAFE_TRANSFER", "EXPENSE_PAYOUT", "TRANSFER_OUT",
})


# ══════════════════════════════════════════════════════════════
# REQUEST COMMANDS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SessionOpenRequest:
    """Request to open a cash session / drawer."""
    session_id: str
    drawer_id: str
    opening_balance: int
    currency: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.session_id:
            raise ValueError("session_id must be non-empty.")
        if not self.drawer_id:
            raise ValueError("drawer_id must be non-empty.")
        if not isinstance(self.opening_balance, int) or self.opening_balance < 0:
            raise ValueError("opening_balance must be non-negative integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")

    def to_command(
        self,
        *,
        business_id: uuid.UUID,
        actor_type: str,
        actor_id: str,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ) -> Command:
        return Command(
            command_id=command_id,
            command_type=CASH_SESSION_OPEN_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "session_id": self.session_id,
                "drawer_id": self.drawer_id,
                "opening_balance": self.opening_balance,
                "currency": self.currency,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="cash",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class SessionCloseRequest:
    """Request to close a cash session / drawer."""
    session_id: str
    drawer_id: str
    closing_balance: int
    currency: str
    expected_balance: Optional[int] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.session_id:
            raise ValueError("session_id must be non-empty.")
        if not self.drawer_id:
            raise ValueError("drawer_id must be non-empty.")
        if not isinstance(self.closing_balance, int) or self.closing_balance < 0:
            raise ValueError("closing_balance must be non-negative integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")

    @property
    def difference(self) -> int:
        if self.expected_balance is None:
            return 0
        return self.closing_balance - self.expected_balance

    def to_command(
        self,
        *,
        business_id: uuid.UUID,
        actor_type: str,
        actor_id: str,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ) -> Command:
        return Command(
            command_id=command_id,
            command_type=CASH_SESSION_CLOSE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "session_id": self.session_id,
                "drawer_id": self.drawer_id,
                "closing_balance": self.closing_balance,
                "expected_balance": self.expected_balance,
                "currency": self.currency,
                "difference": self.difference,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="cash",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class PaymentRecordRequest:
    """Request to record a payment received."""
    payment_id: str
    session_id: str
    drawer_id: str
    amount: int
    currency: str
    payment_method: str
    reference_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.payment_id:
            raise ValueError("payment_id must be non-empty.")
        if not self.session_id:
            raise ValueError("session_id must be non-empty.")
        if not self.drawer_id:
            raise ValueError("drawer_id must be non-empty.")
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError("amount must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")
        if self.payment_method not in VALID_PAYMENT_METHODS:
            raise ValueError(f"payment_method '{self.payment_method}' not valid.")

    def to_command(
        self,
        *,
        business_id: uuid.UUID,
        actor_type: str,
        actor_id: str,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ) -> Command:
        return Command(
            command_id=command_id,
            command_type=CASH_PAYMENT_RECORD_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "payment_id": self.payment_id,
                "session_id": self.session_id,
                "drawer_id": self.drawer_id,
                "amount": self.amount,
                "currency": self.currency,
                "payment_method": self.payment_method,
                "reference_id": self.reference_id,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="cash",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class DepositRecordRequest:
    """Request to record a cash deposit into the drawer."""
    deposit_id: str
    session_id: str
    drawer_id: str
    amount: int
    currency: str
    reason: str = "FLOAT_ADD"
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.deposit_id:
            raise ValueError("deposit_id must be non-empty.")
        if not self.session_id:
            raise ValueError("session_id must be non-empty.")
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError("amount must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")
        if self.reason not in VALID_DEPOSIT_REASONS:
            raise ValueError(f"reason '{self.reason}' not valid.")

    def to_command(
        self,
        *,
        business_id: uuid.UUID,
        actor_type: str,
        actor_id: str,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ) -> Command:
        return Command(
            command_id=command_id,
            command_type=CASH_DEPOSIT_RECORD_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "deposit_id": self.deposit_id,
                "session_id": self.session_id,
                "drawer_id": self.drawer_id,
                "amount": self.amount,
                "currency": self.currency,
                "reason": self.reason,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="cash",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class WithdrawalRecordRequest:
    """Request to record a cash withdrawal from the drawer."""
    withdrawal_id: str
    session_id: str
    drawer_id: str
    amount: int
    currency: str
    reason: str = "BANK_DEPOSIT"
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.withdrawal_id:
            raise ValueError("withdrawal_id must be non-empty.")
        if not self.session_id:
            raise ValueError("session_id must be non-empty.")
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError("amount must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")
        if self.reason not in VALID_WITHDRAWAL_REASONS:
            raise ValueError(f"reason '{self.reason}' not valid.")

    def to_command(
        self,
        *,
        business_id: uuid.UUID,
        actor_type: str,
        actor_id: str,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ) -> Command:
        return Command(
            command_id=command_id,
            command_type=CASH_WITHDRAWAL_RECORD_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "withdrawal_id": self.withdrawal_id,
                "session_id": self.session_id,
                "drawer_id": self.drawer_id,
                "amount": self.amount,
                "currency": self.currency,
                "reason": self.reason,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="cash",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )
