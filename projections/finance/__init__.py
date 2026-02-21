"""
BOS Projections — Finance Read Model
=========================================
Cross-engine read model aggregating accounting journals,
cash positions, and obligations.

Built from events:
- accounting.journal.posted.v1
- accounting.correction.posted.v1
- cash.session.opened.v1
- cash.session.closed.v1
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class AccountBalance:
    account_code: str
    debit_total: Decimal = Decimal(0)
    credit_total: Decimal = Decimal(0)

    @property
    def balance(self) -> Decimal:
        return self.debit_total - self.credit_total


class FinanceReadModel:
    """
    Aggregated finance read model for trial balance,
    P&L summaries, and cash position tracking.

    Implements ProjectionProtocol for rebuild support.
    """

    projection_name = "finance_read_model"

    def __init__(self) -> None:
        # { business_id: { account_code: AccountBalance } }
        self._balances: Dict[uuid.UUID, Dict[str, AccountBalance]] = defaultdict(dict)
        self._journal_count: Dict[uuid.UUID, int] = defaultdict(int)
        self._cash_position: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        biz_id = payload.get("business_id")
        if isinstance(biz_id, str):
            biz_id = uuid.UUID(biz_id)
        if biz_id is None:
            return

        if event_type in ("accounting.journal.posted.v1", "accounting.correction.posted.v1"):
            lines = payload.get("lines", [])
            for line in lines:
                code = line.get("account_code", "")
                debit = Decimal(str(line.get("debit", 0)))
                credit = Decimal(str(line.get("credit", 0)))
                bal = self._balances[biz_id].setdefault(
                    code, AccountBalance(account_code=code)
                )
                bal.debit_total += debit
                bal.credit_total += credit
            self._journal_count[biz_id] += 1

        elif event_type == "cash.session.closed.v1":
            closing = Decimal(str(payload.get("closing_balance", 0)))
            self._cash_position[biz_id] = closing

    def get_trial_balance(self, business_id: uuid.UUID) -> Dict[str, AccountBalance]:
        return dict(self._balances.get(business_id, {}))

    def get_account_balance(
        self, business_id: uuid.UUID, account_code: str
    ) -> Optional[AccountBalance]:
        return self._balances.get(business_id, {}).get(account_code)

    def get_journal_count(self, business_id: uuid.UUID) -> int:
        return self._journal_count.get(business_id, 0)

    def get_cash_position(self, business_id: uuid.UUID) -> Decimal:
        return self._cash_position.get(business_id, Decimal(0))

    def truncate(self, business_id: Optional[uuid.UUID] = None) -> None:
        if business_id:
            self._balances.pop(business_id, None)
            self._journal_count.pop(business_id, None)
            self._cash_position.pop(business_id, None)
        else:
            self._balances.clear()
            self._journal_count.clear()
            self._cash_position.clear()

    def snapshot(self, business_id: uuid.UUID) -> Dict[str, Any]:
        trial = self.get_trial_balance(business_id)
        return {
            "journal_count": self.get_journal_count(business_id),
            "cash_position": str(self.get_cash_position(business_id)),
            "account_count": len(trial),
            "total_debits": str(sum(b.debit_total for b in trial.values())),
            "total_credits": str(sum(b.credit_total for b in trial.values())),
        }
