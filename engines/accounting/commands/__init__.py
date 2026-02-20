"""
BOS Accounting Engine — Request Commands
==========================================
Typed accounting requests that convert into canonical Command objects.
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

ACCOUNTING_JOURNAL_POST_REQUEST = "accounting.journal.post.request"
ACCOUNTING_JOURNAL_REVERSE_REQUEST = "accounting.journal.reverse.request"
ACCOUNTING_ACCOUNT_CREATE_REQUEST = "accounting.account.create.request"
ACCOUNTING_OBLIGATION_CREATE_REQUEST = "accounting.obligation.create.request"
ACCOUNTING_OBLIGATION_FULFILL_REQUEST = "accounting.obligation.fulfill.request"

ACCOUNTING_COMMAND_TYPES = frozenset({
    ACCOUNTING_JOURNAL_POST_REQUEST,
    ACCOUNTING_JOURNAL_REVERSE_REQUEST,
    ACCOUNTING_ACCOUNT_CREATE_REQUEST,
    ACCOUNTING_OBLIGATION_CREATE_REQUEST,
    ACCOUNTING_OBLIGATION_FULFILL_REQUEST,
})

VALID_ACCOUNT_TYPES = frozenset({
    "ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE",
})
VALID_OBLIGATION_TYPES = frozenset({
    "PAYABLE", "RECEIVABLE",
})
VALID_FULFILLMENT_TYPES = frozenset({
    "PAYMENT_CASH", "PAYMENT_CARD", "PAYMENT_BANK",
    "PAYMENT_MOBILE", "CREDIT_NOTE", "WRITE_OFF",
})


# ══════════════════════════════════════════════════════════════
# REQUEST COMMANDS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class JournalPostRequest:
    """Request to post a journal entry."""
    entry_id: str
    lines: tuple
    memo: str
    currency: str
    reference_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.entry_id:
            raise ValueError("entry_id must be non-empty.")
        if not isinstance(self.lines, tuple) or len(self.lines) < 2:
            raise ValueError("lines must be a tuple with at least 2 entries.")
        if not self.memo:
            raise ValueError("memo must be non-empty.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")

        # Validate balance: total debits == total credits
        total_debits = sum(
            l["amount"] for l in self.lines if l["side"] == "DEBIT"
        )
        total_credits = sum(
            l["amount"] for l in self.lines if l["side"] == "CREDIT"
        )
        if total_debits != total_credits:
            raise ValueError(
                f"Journal entry unbalanced: debits ({total_debits}) "
                f"!= credits ({total_credits})."
            )

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
            command_type=ACCOUNTING_JOURNAL_POST_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "entry_id": self.entry_id,
                "lines": list(self.lines),
                "memo": self.memo,
                "currency": self.currency,
                "reference_id": self.reference_id,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="accounting",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class JournalReverseRequest:
    """Request to reverse a posted journal entry."""
    original_entry_id: str
    reversal_entry_id: str
    reason: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.original_entry_id:
            raise ValueError("original_entry_id must be non-empty.")
        if not self.reversal_entry_id:
            raise ValueError("reversal_entry_id must be non-empty.")
        if not self.reason:
            raise ValueError("reason must be non-empty.")

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
            command_type=ACCOUNTING_JOURNAL_REVERSE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "original_entry_id": self.original_entry_id,
                "reversal_entry_id": self.reversal_entry_id,
                "reason": self.reason,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="accounting",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class AccountCreateRequest:
    """Request to create a new chart of accounts entry."""
    account_code: str
    account_type: str
    name: str
    parent_code: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.account_code:
            raise ValueError("account_code must be non-empty.")
        if self.account_type not in VALID_ACCOUNT_TYPES:
            raise ValueError(f"account_type '{self.account_type}' not valid.")
        if not self.name:
            raise ValueError("name must be non-empty.")

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
            command_type=ACCOUNTING_ACCOUNT_CREATE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "account_code": self.account_code,
                "account_type": self.account_type,
                "name": self.name,
                "parent_code": self.parent_code,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="accounting",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class ObligationCreateRequest:
    """Request to create a payment obligation (payable/receivable)."""
    obligation_id: str
    obligation_type: str
    party_id: str
    total_amount: int
    currency: str
    due_date: str
    reference_id: Optional[str] = None
    description: str = ""
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.obligation_id:
            raise ValueError("obligation_id must be non-empty.")
        if self.obligation_type not in VALID_OBLIGATION_TYPES:
            raise ValueError(f"obligation_type '{self.obligation_type}' not valid.")
        if not self.party_id:
            raise ValueError("party_id must be non-empty.")
        if not isinstance(self.total_amount, int) or self.total_amount <= 0:
            raise ValueError("total_amount must be positive integer.")
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
            command_type=ACCOUNTING_OBLIGATION_CREATE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "obligation_id": self.obligation_id,
                "obligation_type": self.obligation_type,
                "party_id": self.party_id,
                "total_amount": self.total_amount,
                "currency": self.currency,
                "due_date": self.due_date,
                "reference_id": self.reference_id,
                "description": self.description,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="accounting",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class ObligationFulfillRequest:
    """Request to record a fulfillment against an obligation."""
    obligation_id: str
    fulfillment_id: str
    fulfillment_type: str
    amount: int
    currency: str
    reference_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.obligation_id:
            raise ValueError("obligation_id must be non-empty.")
        if not self.fulfillment_id:
            raise ValueError("fulfillment_id must be non-empty.")
        if self.fulfillment_type not in VALID_FULFILLMENT_TYPES:
            raise ValueError(f"fulfillment_type '{self.fulfillment_type}' not valid.")
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError("amount must be positive integer.")
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
            command_type=ACCOUNTING_OBLIGATION_FULFILL_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "obligation_id": self.obligation_id,
                "fulfillment_id": self.fulfillment_id,
                "fulfillment_type": self.fulfillment_type,
                "amount": self.amount,
                "currency": self.currency,
                "reference_id": self.reference_id,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="accounting",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )
