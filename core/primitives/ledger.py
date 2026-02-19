"""
BOS Ledger Primitive — Double-Entry Accounting Core
=====================================================
Engine: Core Primitives (Phase 4)
Authority: BOS Doctrine — Deterministic, Event-Sourced

The Ledger Primitive provides the foundational double-entry bookkeeping
abstraction used by: Accounting Engine, Cash Engine, Procurement Engine.

RULES (NON-NEGOTIABLE):
- Every journal entry must balance (total debits == total credits)
- Journal entries are immutable once created
- All amounts use integer minor units (cents/paise) — NO floats
- Currency is explicit on every monetary value
- Ledger state is derived from events only (replayable)
- Multi-tenant: every entry scoped to business_id

This file contains NO persistence logic.
Engines use these primitives and emit events to the Event Store.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class DebitCredit(Enum):
    """Ledger side. Every line is either a debit or a credit."""
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class AccountType(Enum):
    """
    Standard account classifications.
    Normal balance: ASSET/EXPENSE = DEBIT, LIABILITY/EQUITY/REVENUE = CREDIT.
    """
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


NORMAL_BALANCE: Dict[AccountType, DebitCredit] = {
    AccountType.ASSET: DebitCredit.DEBIT,
    AccountType.LIABILITY: DebitCredit.CREDIT,
    AccountType.EQUITY: DebitCredit.CREDIT,
    AccountType.REVENUE: DebitCredit.CREDIT,
    AccountType.EXPENSE: DebitCredit.DEBIT,
}


class JournalEntryStatus(Enum):
    """Journal entry lifecycle status."""
    POSTED = "POSTED"
    REVERSED = "REVERSED"


# ══════════════════════════════════════════════════════════════
# MONEY VALUE OBJECT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Money:
    """
    Monetary value in integer minor units (cents).

    Rules:
    - amount is in minor units (e.g. 1050 = $10.50)
    - currency is ISO 4217 (e.g. "USD", "KES", "TZS")
    - No floats ever. Integer arithmetic only.
    """
    amount: int
    currency: str

    def __post_init__(self):
        if not isinstance(self.amount, int):
            raise TypeError(
                f"Money amount must be int (minor units), "
                f"got {type(self.amount).__name__}. "
                f"Use cents/paise, not decimals."
            )
        if not self.currency or not isinstance(self.currency, str):
            raise ValueError("currency must be a non-empty ISO 4217 string.")
        if len(self.currency) != 3:
            raise ValueError(
                f"currency must be 3-letter ISO 4217 code, "
                f"got '{self.currency}'."
            )

    def __add__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def negate(self) -> Money:
        return Money(amount=-self.amount, currency=self.currency)

    def is_zero(self) -> bool:
        return self.amount == 0

    def _assert_same_currency(self, other: Money) -> None:
        if not isinstance(other, Money):
            raise TypeError(f"Cannot operate with {type(other).__name__}.")
        if self.currency != other.currency:
            raise ValueError(
                f"Currency mismatch: {self.currency} vs {other.currency}. "
                f"Cross-currency operations require explicit conversion."
            )

    def to_dict(self) -> dict:
        return {"amount": self.amount, "currency": self.currency}

    @classmethod
    def from_dict(cls, data: dict) -> Money:
        return cls(amount=data["amount"], currency=data["currency"])

    @classmethod
    def zero(cls, currency: str) -> Money:
        return cls(amount=0, currency=currency)


# ══════════════════════════════════════════════════════════════
# ACCOUNT IDENTIFIER
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AccountRef:
    """
    Reference to a ledger account.

    account_code: Chart of accounts code (e.g. "1000", "4100")
    account_type: Classification (ASSET, LIABILITY, etc.)
    name:         Human-readable account name
    """
    account_code: str
    account_type: AccountType
    name: str

    def __post_init__(self):
        if not self.account_code or not isinstance(self.account_code, str):
            raise ValueError("account_code must be a non-empty string.")
        if not isinstance(self.account_type, AccountType):
            raise ValueError("account_type must be an AccountType enum.")
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be a non-empty string.")

    @property
    def normal_balance(self) -> DebitCredit:
        return NORMAL_BALANCE[self.account_type]

    def to_dict(self) -> dict:
        return {
            "account_code": self.account_code,
            "account_type": self.account_type.value,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AccountRef:
        return cls(
            account_code=data["account_code"],
            account_type=AccountType(data["account_type"]),
            name=data["name"],
        )


# ══════════════════════════════════════════════════════════════
# JOURNAL LINE
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class JournalLine:
    """
    Single line in a journal entry.

    Each line debits or credits a specific account with a Money amount.
    Amount must be positive — the side (DEBIT/CREDIT) indicates direction.
    """
    account: AccountRef
    side: DebitCredit
    amount: Money
    description: str = ""

    def __post_init__(self):
        if not isinstance(self.side, DebitCredit):
            raise ValueError("side must be DebitCredit enum.")
        if not isinstance(self.amount, Money):
            raise TypeError("amount must be Money.")
        if self.amount.amount <= 0:
            raise ValueError(
                f"Journal line amount must be positive, "
                f"got {self.amount.amount}. Use side (DEBIT/CREDIT) "
                f"to indicate direction."
            )

    def to_dict(self) -> dict:
        return {
            "account": self.account.to_dict(),
            "side": self.side.value,
            "amount": self.amount.to_dict(),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> JournalLine:
        return cls(
            account=AccountRef.from_dict(data["account"]),
            side=DebitCredit(data["side"]),
            amount=Money.from_dict(data["amount"]),
            description=data.get("description", ""),
        )


# ══════════════════════════════════════════════════════════════
# JOURNAL ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class JournalEntry:
    """
    Complete double-entry journal entry.

    INVARIANT: Total debits MUST equal total credits.
    This is enforced at creation time — unbalanced entries
    are rejected deterministically.

    Fields:
        entry_id:     Unique identifier
        business_id:  Tenant boundary
        branch_id:    Branch scope (optional)
        posted_at:    When the entry was posted
        lines:        Tuple of JournalLine (immutable)
        memo:         Description of the transaction
        reference_id: Optional external reference (e.g. sale_id, PO number)
        status:       POSTED or REVERSED
    """
    entry_id: uuid.UUID
    business_id: uuid.UUID
    posted_at: datetime
    lines: Tuple[JournalLine, ...]
    memo: str
    currency: str
    branch_id: Optional[uuid.UUID] = None
    reference_id: Optional[str] = None
    status: JournalEntryStatus = JournalEntryStatus.POSTED

    def __post_init__(self):
        if not isinstance(self.entry_id, uuid.UUID):
            raise ValueError("entry_id must be UUID.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.lines, tuple):
            raise TypeError("lines must be a tuple of JournalLine.")
        if len(self.lines) < 2:
            raise ValueError(
                "Journal entry must have at least 2 lines "
                "(minimum one debit and one credit)."
            )

        # Enforce single currency
        for line in self.lines:
            if line.amount.currency != self.currency:
                raise ValueError(
                    f"All lines must use entry currency '{self.currency}', "
                    f"got '{line.amount.currency}' on account "
                    f"'{line.account.account_code}'."
                )

        # INVARIANT: debits == credits
        total_debits = sum(
            l.amount.amount for l in self.lines
            if l.side == DebitCredit.DEBIT
        )
        total_credits = sum(
            l.amount.amount for l in self.lines
            if l.side == DebitCredit.CREDIT
        )
        if total_debits != total_credits:
            raise ValueError(
                f"LEDGER INVARIANT VIOLATION: Journal entry unbalanced. "
                f"Total debits ({total_debits}) != total credits "
                f"({total_credits}). Every entry must balance."
            )

    @property
    def total_debits(self) -> Money:
        total = sum(
            l.amount.amount for l in self.lines
            if l.side == DebitCredit.DEBIT
        )
        return Money(amount=total, currency=self.currency)

    @property
    def total_credits(self) -> Money:
        total = sum(
            l.amount.amount for l in self.lines
            if l.side == DebitCredit.CREDIT
        )
        return Money(amount=total, currency=self.currency)

    @property
    def is_balanced(self) -> bool:
        return self.total_debits.amount == self.total_credits.amount

    def to_dict(self) -> dict:
        return {
            "entry_id": str(self.entry_id),
            "business_id": str(self.business_id),
            "branch_id": str(self.branch_id) if self.branch_id else None,
            "posted_at": self.posted_at.isoformat(),
            "lines": [l.to_dict() for l in self.lines],
            "memo": self.memo,
            "currency": self.currency,
            "reference_id": self.reference_id,
            "status": self.status.value,
        }


# ══════════════════════════════════════════════════════════════
# ACCOUNT BALANCE (Projection Primitive)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AccountBalance:
    """
    Computed balance for a single account (projection, not source of truth).

    Derived from replaying journal entries. Disposable and rebuildable.
    """
    account: AccountRef
    business_id: uuid.UUID
    currency: str
    total_debits: int
    total_credits: int

    @property
    def net_balance(self) -> int:
        """
        Net balance respecting normal balance side.
        ASSET/EXPENSE: debits - credits (positive = normal)
        LIABILITY/EQUITY/REVENUE: credits - debits (positive = normal)
        """
        if self.account.normal_balance == DebitCredit.DEBIT:
            return self.total_debits - self.total_credits
        return self.total_credits - self.total_debits

    @property
    def balance_money(self) -> Money:
        return Money(amount=self.net_balance, currency=self.currency)

    def to_dict(self) -> dict:
        return {
            "account": self.account.to_dict(),
            "business_id": str(self.business_id),
            "currency": self.currency,
            "total_debits": self.total_debits,
            "total_credits": self.total_credits,
            "net_balance": self.net_balance,
        }


# ══════════════════════════════════════════════════════════════
# LEDGER PROJECTION (In-Memory, Replayable)
# ══════════════════════════════════════════════════════════════

class LedgerProjection:
    """
    In-memory ledger projection that computes account balances
    from journal entries.

    This is a READ MODEL — disposable, rebuildable from events.
    Thread-safe for single-writer usage (BOS event replay pattern).
    """

    def __init__(self, business_id: uuid.UUID, currency: str):
        self._business_id = business_id
        self._currency = currency
        self._entries: List[JournalEntry] = []
        # account_code → {total_debits, total_credits}
        self._balances: Dict[str, Dict[str, int]] = {}
        # account_code → AccountRef
        self._accounts: Dict[str, AccountRef] = {}

    @property
    def business_id(self) -> uuid.UUID:
        return self._business_id

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def apply_entry(self, entry: JournalEntry) -> None:
        """Apply a journal entry to update account balances."""
        if entry.business_id != self._business_id:
            raise ValueError(
                f"Tenant isolation violation: entry business_id "
                f"{entry.business_id} != projection business_id "
                f"{self._business_id}."
            )
        if entry.currency != self._currency:
            raise ValueError(
                f"Currency mismatch: entry currency '{entry.currency}' "
                f"!= projection currency '{self._currency}'."
            )

        for line in entry.lines:
            code = line.account.account_code
            if code not in self._balances:
                self._balances[code] = {"total_debits": 0, "total_credits": 0}
                self._accounts[code] = line.account

            if line.side == DebitCredit.DEBIT:
                self._balances[code]["total_debits"] += line.amount.amount
            else:
                self._balances[code]["total_credits"] += line.amount.amount

        self._entries.append(entry)

    def get_balance(self, account_code: str) -> Optional[AccountBalance]:
        """Get computed balance for an account."""
        if account_code not in self._balances:
            return None
        bal = self._balances[account_code]
        return AccountBalance(
            account=self._accounts[account_code],
            business_id=self._business_id,
            currency=self._currency,
            total_debits=bal["total_debits"],
            total_credits=bal["total_credits"],
        )

    def get_all_balances(self) -> List[AccountBalance]:
        """Get all account balances."""
        return [
            self.get_balance(code)
            for code in sorted(self._balances.keys())
        ]

    def trial_balance(self) -> Tuple[int, int]:
        """
        Compute trial balance totals.
        Returns (total_debits, total_credits).
        Must always be equal if all entries balanced.
        """
        total_d = sum(b["total_debits"] for b in self._balances.values())
        total_c = sum(b["total_credits"] for b in self._balances.values())
        return total_d, total_c

    def is_trial_balanced(self) -> bool:
        """Trial balance check — must always pass."""
        d, c = self.trial_balance()
        return d == c
