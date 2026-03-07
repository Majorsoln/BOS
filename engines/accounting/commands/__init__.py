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
ACCOUNTING_STATEMENT_GENERATE_REQUEST = "accounting.statement.generate.request"
ACCOUNTING_AR_AGING_SNAPSHOT_REQUEST = "accounting.ar_aging.snapshot.request"

ACCOUNTING_COMMAND_TYPES = frozenset({
    ACCOUNTING_JOURNAL_POST_REQUEST,
    ACCOUNTING_JOURNAL_REVERSE_REQUEST,
    ACCOUNTING_ACCOUNT_CREATE_REQUEST,
    ACCOUNTING_OBLIGATION_CREATE_REQUEST,
    ACCOUNTING_OBLIGATION_FULFILL_REQUEST,
    ACCOUNTING_STATEMENT_GENERATE_REQUEST,
    ACCOUNTING_AR_AGING_SNAPSHOT_REQUEST,
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


@dataclass(frozen=True)
class StatementGenerateRequest:
    """
    On-demand request to generate a Statement of Account for a customer.

    The caller is responsible for pre-computing the line_items from the
    customer's transaction history for the given period.
    On success the accounting engine emits accounting.statement.generated.v1
    which the DocumentSubscriptionHandler converts into a STATEMENT document.
    """
    statement_id: str
    period_from: str          # ISO date string e.g. "2026-01-01"
    period_to: str            # ISO date string e.g. "2026-01-31"
    currency: str
    customer_id: Optional[str] = None
    line_items: tuple = ()    # list of {date, description, debit, credit, balance}
    opening_balance: int = 0
    total_debit: int = 0
    total_credit: int = 0
    closing_balance: int = 0
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.statement_id:
            raise ValueError("statement_id must be non-empty.")
        if not self.period_from:
            raise ValueError("period_from must be non-empty.")
        if not self.period_to:
            raise ValueError("period_to must be non-empty.")
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
            command_type=ACCOUNTING_STATEMENT_GENERATE_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "statement_id":    self.statement_id,
                "customer_id":     self.customer_id,
                "period_from":     self.period_from,
                "period_to":       self.period_to,
                "line_items":      list(self.line_items),
                "opening_balance": self.opening_balance,
                "total_debit":     self.total_debit,
                "total_credit":    self.total_credit,
                "closing_balance": self.closing_balance,
                "currency":        self.currency,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="accounting",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class ArAgingSnapshotRequest:
    """
    On-demand or scheduled request to compute AR aging buckets.

    The caller pre-computes the aging data from obligation records.
    On success the accounting engine emits accounting.ar_aging.snapshot.v1
    which the ReportingSubscriptionHandler records as KPIs.
    """
    snapshot_id: str
    snapshot_date: str            # ISO date string e.g. "2026-03-07"
    currency: str
    current: int = 0              # Not yet due (minor currency)
    aging_0_30: int = 0           # 0-30 days overdue
    aging_30_60: int = 0          # 30-60 days overdue
    aging_60_90: int = 0          # 60-90 days overdue
    aging_90_plus: int = 0        # 90+ days overdue
    total_outstanding: int = 0    # Total AR outstanding
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.snapshot_id:
            raise ValueError("snapshot_id must be non-empty.")
        if not self.snapshot_date:
            raise ValueError("snapshot_date must be non-empty.")
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
            command_type=ACCOUNTING_AR_AGING_SNAPSHOT_REQUEST,
            business_id=business_id,
            branch_id=self.branch_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "snapshot_id":       self.snapshot_id,
                "snapshot_date":     self.snapshot_date,
                "currency":          self.currency,
                "current":           self.current,
                "aging_0_30":        self.aging_0_30,
                "aging_30_60":       self.aging_30_60,
                "aging_60_90":       self.aging_60_90,
                "aging_90_plus":     self.aging_90_plus,
                "total_outstanding": self.total_outstanding,
            },
            issued_at=issued_at,
            correlation_id=correlation_id,
            source_engine="accounting",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )
