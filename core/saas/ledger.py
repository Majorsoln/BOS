"""
BOS Revenue Ledger — Source of Truth for Revenue Distribution.

OPERATING LAW: BOS holds truth. RLA holds money.
BOS must never silently mutate truth.

Every sale produces a LedgerEntry with full breakdown:
  Gross sale → Tax → Gateway fee → Net distributable → Shares → Holds

Settlement lifecycle:
  RECORDED → SETTLED → PAYABLE → PAID / REVERSED
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EntryStatus(Enum):
    """Settlement lifecycle: record → settle → payable → paid."""
    RECORDED = "RECORDED"       # Sale recorded, not yet settled by provider
    SETTLED = "SETTLED"         # Provider confirmed, funds with RLA
    PAYABLE = "PAYABLE"         # Hold period passed, shares are payable
    PAID = "PAID"               # All shares disbursed
    REVERSED = "REVERSED"       # Refund / chargeback reversed the entry
    DISPUTED = "DISPUTED"       # Under investigation


class ShareType(Enum):
    PLATFORM_ROYALTY = "PLATFORM_ROYALTY"
    RLA_SHARE = "RLA_SHARE"
    REMOTE_AGENT_SHARE = "REMOTE_AGENT_SHARE"
    TAX_COLLECTED = "TAX_COLLECTED"
    GATEWAY_FEE = "GATEWAY_FEE"
    RESERVE_HOLD = "RESERVE_HOLD"


class TaxTreatment(Enum):
    INCLUSIVE = "INCLUSIVE"      # Tax included in gross
    EXCLUSIVE = "EXCLUSIVE"     # Tax added on top
    EXEMPT = "EXEMPT"           # No tax applicable
    ZERO_RATED = "ZERO_RATED"   # Zero-rated (tax applies but at 0%)


# ---------------------------------------------------------------------------
# Core Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ShareLine:
    """One line in the distribution of a sale."""
    share_type: str             # ShareType value
    party_id: str               # Who receives this (platform, RLA UUID, agent UUID)
    party_name: str             # Human-readable
    rate_pct: Decimal           # Percentage used (for audit trail)
    amount: int                 # Amount in minor currency units
    currency: str
    rule_version: str           # Which rule version calculated this
    notes: str = ""


@dataclass(frozen=True)
class LedgerEntry:
    """
    Immutable record of a single sale's financial truth.

    Operating Law #7: Historical sales never recalculate under new rules
    unless a correction event is posted.
    """
    entry_id: str                       # UUID
    created_at: str                     # ISO datetime

    # --- Attribution (Operating Law #4) ---
    tenant_id: str                      # Who paid
    tenant_name: str
    region_code: str                    # Where
    rla_id: str                         # Which RLA collected
    rla_name: str
    remote_agent_id: str                # Which agent caused the sale (empty if direct)
    remote_agent_name: str
    sale_reference: str                 # Original sale/invoice/subscription ID

    # --- Contract version (Operating Law #7) ---
    contract_version: str               # RLA contract version at time of sale
    commission_rule_version: str        # Agent commission rules version

    # --- Amounts ---
    gross_amount: int                   # Total amount charged to tenant (minor units)
    currency: str
    tax_treatment: str                  # TaxTreatment value
    tax_amount: int                     # Tax component
    gateway_provider: str               # e.g. "stripe", "mpesa", "bank_transfer"
    gateway_fee: int                    # Provider processing fee
    net_distributable: int              # gross - tax - gateway_fee

    # --- Distribution shares ---
    shares: Tuple[ShareLine, ...]       # Immutable breakdown

    # --- Settlement lifecycle ---
    status: str                         # EntryStatus value
    settled_at: str                     # When provider confirmed
    hold_until: str                     # Date after which shares become payable
    payable_at: str                     # When shares were released
    paid_at: str                        # When all payouts completed

    # --- Reversal ---
    reversal_reason: str                # If reversed: "refund", "chargeback", etc.
    reversal_entry_id: str              # Points to the corrective entry

    # --- Metadata ---
    period: str                         # Billing period e.g. "2026-03"
    notes: str


@dataclass(frozen=True)
class RemittanceRecord:
    """
    Tracks RLA remittance of platform share.

    Operating Law: No reseller payout before owner-remittance condition
    is satisfied, unless centrally approved as advance.
    """
    remittance_id: str
    rla_id: str
    rla_name: str
    region_code: str
    period: str                         # Settlement period
    currency: str
    expected_amount: int                # What BOS calculated RLA owes
    remitted_amount: int                # What RLA actually sent
    variance: int                       # expected - remitted
    settlement_statement_id: str        # Links to the statement
    exchange_rate: str                  # If currency conversion happened
    remitted_at: str                    # When RLA sent
    confirmed_at: str                   # When platform confirmed receipt
    status: str                         # PENDING, CONFIRMED, PARTIAL, OVERDUE, DISPUTED
    sale_references: Tuple[str, ...]    # List of entry_ids covered
    notes: str


@dataclass(frozen=True)
class PeriodStatement:
    """
    Operating Law #8: Statements are period-based and immutable once
    finalized, except by corrective events.
    """
    statement_id: str
    party_id: str                       # RLA or agent UUID
    party_name: str
    party_role: str                     # "RLA" or "REMOTE_AGENT"
    region_code: str
    period: str                         # e.g. "2026-03"
    currency: str

    # Breakdown
    gross_sales: int
    total_tax: int
    total_gateway_fees: int
    net_distributable: int
    party_share: int                    # What this party earned
    platform_share: int                 # What platform earned
    holds: int                          # Amount still on hold
    released: int                       # Amount released for payout
    paid: int                           # Amount actually paid out
    reversals: int                      # Refunds/chargebacks deducted

    # Entries
    entry_count: int
    entry_ids: Tuple[str, ...]

    # State
    status: str                         # DRAFT, FINALIZED, CORRECTED
    finalized_at: str
    notes: str


# ---------------------------------------------------------------------------
# Distribution Engine
# ---------------------------------------------------------------------------

@dataclass
class DistributionRules:
    """
    Active rules for calculating shares.
    Operating Law #7: versioned — historical sales use their version.
    """
    version: str                        # e.g. "v2026.03.28"
    created_at: str

    # Platform royalty
    default_platform_royalty_pct: Decimal    # e.g. 70 (platform gets 70% of net)

    # Hold period
    hold_period_days: int               # Days before shares become payable (default 7)

    # Gateway fee handling
    gateway_fee_bearer: str             # "PLATFORM", "RLA", "SPLIT"

    # Reserve/withhold percentage
    reserve_pct: Decimal                # % withheld as reserve (default 0)

    # Tax handling
    tax_deducted_before_split: bool     # True = split net-of-tax, False = split gross


class DistributionEngine:
    """
    Calculates the distribution of a sale into shares.

    Operating Law #1: Money never becomes payable by record alone.
    Operating Law #2: BOS calculates entitlements, not legal custody.
    """

    def calculate_distribution(
        self,
        *,
        gross_amount: int,
        currency: str,
        tax_treatment: str,
        tax_amount: int,
        gateway_fee: int,
        rla_id: str,
        rla_name: str,
        rla_market_share_pct: Decimal,
        remote_agent_id: str,
        remote_agent_name: str,
        remote_agent_commission_pct: Decimal,
        rules: DistributionRules,
    ) -> Tuple[int, List[ShareLine]]:
        """
        Returns (net_distributable, list_of_share_lines).

        The formula:
          1. Gross amount
          2. - Tax (if deducted before split)
          3. - Gateway fee
          4. = Net distributable base
          5. RLA share = net × rla_market_share_pct%
          6. Remote agent share = net × remote_agent_commission_pct%
          7. Reserve = net × reserve_pct%
          8. Platform royalty = net - RLA share - agent share - reserve
        """
        shares: List[ShareLine] = []

        # Tax line
        if tax_amount > 0:
            shares.append(ShareLine(
                share_type=ShareType.TAX_COLLECTED.value,
                party_id="TAX_AUTHORITY",
                party_name="Tax Authority",
                rate_pct=Decimal("0"),
                amount=tax_amount,
                currency=currency,
                rule_version=rules.version,
                notes=f"Tax treatment: {tax_treatment}",
            ))

        # Gateway fee line
        if gateway_fee > 0:
            shares.append(ShareLine(
                share_type=ShareType.GATEWAY_FEE.value,
                party_id="GATEWAY",
                party_name="Payment Gateway",
                rate_pct=Decimal("0"),
                amount=gateway_fee,
                currency=currency,
                rule_version=rules.version,
            ))

        # Net distributable
        if rules.tax_deducted_before_split:
            net = gross_amount - tax_amount - gateway_fee
        else:
            net = gross_amount - gateway_fee

        if net < 0:
            net = 0

        # RLA share
        rla_share = int(net * rla_market_share_pct / Decimal("100"))
        shares.append(ShareLine(
            share_type=ShareType.RLA_SHARE.value,
            party_id=rla_id,
            party_name=rla_name,
            rate_pct=rla_market_share_pct,
            amount=rla_share,
            currency=currency,
            rule_version=rules.version,
        ))

        # Remote agent share (only if an agent is attributed)
        agent_share = 0
        if remote_agent_id:
            agent_share = int(net * remote_agent_commission_pct / Decimal("100"))
            shares.append(ShareLine(
                share_type=ShareType.REMOTE_AGENT_SHARE.value,
                party_id=remote_agent_id,
                party_name=remote_agent_name,
                rate_pct=remote_agent_commission_pct,
                amount=agent_share,
                currency=currency,
                rule_version=rules.version,
            ))

        # Reserve
        reserve = 0
        if rules.reserve_pct > 0:
            reserve = int(net * rules.reserve_pct / Decimal("100"))
            shares.append(ShareLine(
                share_type=ShareType.RESERVE_HOLD.value,
                party_id="RESERVE",
                party_name="Platform Reserve",
                rate_pct=rules.reserve_pct,
                amount=reserve,
                currency=currency,
                rule_version=rules.version,
            ))

        # Platform royalty = remainder
        platform_share = net - rla_share - agent_share - reserve
        if platform_share < 0:
            platform_share = 0
        shares.append(ShareLine(
            share_type=ShareType.PLATFORM_ROYALTY.value,
            party_id="PLATFORM",
            party_name="BOS Platform",
            rate_pct=Decimal("100") - rla_market_share_pct - remote_agent_commission_pct - rules.reserve_pct,
            amount=platform_share,
            currency=currency,
            rule_version=rules.version,
        ))

        return net, shares

    def create_ledger_entry(
        self,
        *,
        tenant_id: str,
        tenant_name: str,
        region_code: str,
        rla_id: str,
        rla_name: str,
        remote_agent_id: str = "",
        remote_agent_name: str = "",
        sale_reference: str,
        gross_amount: int,
        currency: str,
        tax_treatment: str,
        tax_amount: int,
        gateway_provider: str,
        gateway_fee: int,
        rla_market_share_pct: Decimal,
        remote_agent_commission_pct: Decimal = Decimal("0"),
        contract_version: str = "",
        rules: DistributionRules,
        period: str = "",
        notes: str = "",
    ) -> LedgerEntry:
        """Create an immutable ledger entry with full distribution."""
        now = datetime.utcnow()
        hold_until = now + timedelta(days=rules.hold_period_days)

        net, shares = self.calculate_distribution(
            gross_amount=gross_amount,
            currency=currency,
            tax_treatment=tax_treatment,
            tax_amount=tax_amount,
            gateway_fee=gateway_fee,
            rla_id=rla_id,
            rla_name=rla_name,
            rla_market_share_pct=rla_market_share_pct,
            remote_agent_id=remote_agent_id,
            remote_agent_name=remote_agent_name,
            remote_agent_commission_pct=remote_agent_commission_pct,
            rules=rules,
        )

        return LedgerEntry(
            entry_id=str(uuid.uuid4()),
            created_at=now.isoformat(),
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            region_code=region_code,
            rla_id=rla_id,
            rla_name=rla_name,
            remote_agent_id=remote_agent_id,
            remote_agent_name=remote_agent_name,
            sale_reference=sale_reference,
            contract_version=contract_version,
            commission_rule_version=rules.version,
            gross_amount=gross_amount,
            currency=currency,
            tax_treatment=tax_treatment,
            tax_amount=tax_amount,
            gateway_provider=gateway_provider,
            gateway_fee=gateway_fee,
            net_distributable=net,
            shares=tuple(shares),
            status=EntryStatus.RECORDED.value,
            settled_at="",
            hold_until=hold_until.isoformat(),
            payable_at="",
            paid_at="",
            reversal_reason="",
            reversal_entry_id="",
            period=period or now.strftime("%Y-%m"),
            notes=notes,
        )

    def create_reversal_entry(
        self,
        original: LedgerEntry,
        reason: str,
        rules: DistributionRules,
    ) -> LedgerEntry:
        """
        Operating Law #6: Refunds, chargebacks, and reversals must create
        negative ledger entries, never silent edits.
        """
        now = datetime.utcnow()
        reversed_shares = tuple(
            ShareLine(
                share_type=s.share_type,
                party_id=s.party_id,
                party_name=s.party_name,
                rate_pct=s.rate_pct,
                amount=-s.amount,
                currency=s.currency,
                rule_version=s.rule_version,
                notes=f"REVERSAL: {reason}",
            )
            for s in original.shares
        )

        return LedgerEntry(
            entry_id=str(uuid.uuid4()),
            created_at=now.isoformat(),
            tenant_id=original.tenant_id,
            tenant_name=original.tenant_name,
            region_code=original.region_code,
            rla_id=original.rla_id,
            rla_name=original.rla_name,
            remote_agent_id=original.remote_agent_id,
            remote_agent_name=original.remote_agent_name,
            sale_reference=original.sale_reference,
            contract_version=original.contract_version,
            commission_rule_version=original.commission_rule_version,
            gross_amount=-original.gross_amount,
            currency=original.currency,
            tax_treatment=original.tax_treatment,
            tax_amount=-original.tax_amount,
            gateway_provider=original.gateway_provider,
            gateway_fee=-original.gateway_fee,
            net_distributable=-original.net_distributable,
            shares=reversed_shares,
            status=EntryStatus.REVERSED.value,
            settled_at="",
            hold_until="",
            payable_at="",
            paid_at="",
            reversal_reason=reason,
            reversal_entry_id=original.entry_id,
            period=original.period,
            notes=f"Reversal of {original.entry_id}: {reason}",
        )


# ---------------------------------------------------------------------------
# Ledger Service
# ---------------------------------------------------------------------------

# Operating Laws stored as system constants
OPERATING_LAWS = (
    {
        "number": 1,
        "law": "Money never becomes payable by record alone",
        "detail": "Entitlements become payable only after settlement confirmation + hold period expiry.",
    },
    {
        "number": 2,
        "law": "BOS calculates entitlements, not legal custody",
        "detail": "BOS is a system of record. Real money is held by RLA or payment provider.",
    },
    {
        "number": 3,
        "law": "Each RLA collects only within approved territory and approved payment setup",
        "detail": "RLA must have KYC/KYB, merchant account, and contractual authorization for their region.",
    },
    {
        "number": 4,
        "law": "Every sale must carry full attribution",
        "detail": "Region, RLA, remote agent, contract version, and tax status must be recorded on every entry.",
    },
    {
        "number": 5,
        "law": "No agent payout before owner-remittance condition is satisfied",
        "detail": "Remote agent share is not payable until RLA has remitted platform share, unless centrally approved as advance.",
    },
    {
        "number": 6,
        "law": "Reversals create negative entries, never silent edits",
        "detail": "Refunds, chargebacks, and corrections are recorded as new entries with negative amounts.",
    },
    {
        "number": 7,
        "law": "Historical sales never recalculate under new rules",
        "detail": "Commission rules are versioned. A sale uses the rules active at time of sale, not current rules.",
    },
    {
        "number": 8,
        "law": "Statements are period-based and immutable once finalized",
        "detail": "Corrections after finalization require a new corrective event, not editing the statement.",
    },
    {
        "number": 9,
        "law": "All payout recipients must pass minimum verification",
        "detail": "KYC/KYB, bank account verification, and sanctions screening required before first payout.",
    },
    {
        "number": 10,
        "law": "Dashboard must show exact formula and source values behind every share",
        "detail": "Every party sees the full breakdown: gross, tax, fees, net basis, percentage, and resulting amount.",
    },
)


class LedgerService:
    """
    In-memory revenue ledger service.

    In production this would be backed by an immutable append-only store.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, LedgerEntry] = {}
        self._remittances: Dict[str, RemittanceRecord] = {}
        self._statements: Dict[str, PeriodStatement] = {}
        self._distribution_rules: Optional[DistributionRules] = None
        self._rules_history: List[DistributionRules] = []
        self._engine = DistributionEngine()

    # --- Rules ---

    def get_active_rules(self) -> DistributionRules:
        if self._distribution_rules is None:
            self._distribution_rules = DistributionRules(
                version="v2026.03.28",
                created_at=datetime.utcnow().isoformat(),
                default_platform_royalty_pct=Decimal("70"),
                hold_period_days=7,
                gateway_fee_bearer="RLA",
                reserve_pct=Decimal("0"),
                tax_deducted_before_split=True,
            )
        return self._distribution_rules

    def set_rules(self, rules: DistributionRules) -> None:
        """Operating Law #7: old rules kept in history."""
        if self._distribution_rules:
            self._rules_history.append(self._distribution_rules)
        self._distribution_rules = rules

    def get_rules_history(self) -> List[DistributionRules]:
        result = list(self._rules_history)
        if self._distribution_rules:
            result.append(self._distribution_rules)
        return result

    # --- Entries ---

    def record_sale(self, **kwargs: Any) -> LedgerEntry:
        """Record a sale and compute distribution."""
        rules = self.get_active_rules()
        kwargs.setdefault("rules", rules)
        entry = self._engine.create_ledger_entry(**kwargs)
        self._entries[entry.entry_id] = entry
        return entry

    def reverse_entry(self, entry_id: str, reason: str) -> LedgerEntry:
        """Operating Law #6: create reversal entry."""
        original = self._entries.get(entry_id)
        if not original:
            raise ValueError(f"Entry {entry_id} not found")
        rules = self.get_active_rules()
        reversal = self._engine.create_reversal_entry(original, reason, rules)
        self._entries[reversal.entry_id] = reversal
        return reversal

    def settle_entry(self, entry_id: str) -> LedgerEntry:
        """Mark entry as settled by provider."""
        entry = self._entries.get(entry_id)
        if not entry:
            raise ValueError(f"Entry {entry_id} not found")
        # Frozen dataclass — create new with updated status
        updated = LedgerEntry(
            **{
                **{f: getattr(entry, f) for f in entry.__dataclass_fields__},
                "status": EntryStatus.SETTLED.value,
                "settled_at": datetime.utcnow().isoformat(),
            }
        )
        self._entries[entry_id] = updated
        return updated

    def get_entry(self, entry_id: str) -> Optional[LedgerEntry]:
        return self._entries.get(entry_id)

    def list_entries(
        self,
        region_code: str = "",
        rla_id: str = "",
        period: str = "",
        status: str = "",
        limit: int = 100,
    ) -> List[LedgerEntry]:
        entries = list(self._entries.values())
        if region_code:
            entries = [e for e in entries if e.region_code == region_code]
        if rla_id:
            entries = [e for e in entries if e.rla_id == rla_id]
        if period:
            entries = [e for e in entries if e.period == period]
        if status:
            entries = [e for e in entries if e.status == status]
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]

    # --- Remittance ---

    def record_remittance(self, remittance: RemittanceRecord) -> None:
        self._remittances[remittance.remittance_id] = remittance

    def list_remittances(self, rla_id: str = "", period: str = "") -> List[RemittanceRecord]:
        rems = list(self._remittances.values())
        if rla_id:
            rems = [r for r in rems if r.rla_id == rla_id]
        if period:
            rems = [r for r in rems if r.period == period]
        return rems

    # --- Statements ---

    def get_statement(self, statement_id: str) -> Optional[PeriodStatement]:
        return self._statements.get(statement_id)

    def list_statements(self, party_id: str = "", period: str = "") -> List[PeriodStatement]:
        stmts = list(self._statements.values())
        if party_id:
            stmts = [s for s in stmts if s.party_id == party_id]
        if period:
            stmts = [s for s in stmts if s.period == period]
        return stmts

    # --- Summary ---

    def get_period_summary(self, period: str) -> Dict[str, Any]:
        """Get aggregate numbers for a period."""
        entries = [e for e in self._entries.values() if e.period == period]
        gross = sum(e.gross_amount for e in entries)
        tax = sum(e.tax_amount for e in entries)
        fees = sum(e.gateway_fee for e in entries)
        net = sum(e.net_distributable for e in entries)

        platform_share = 0
        rla_share = 0
        agent_share = 0
        reserve = 0
        for e in entries:
            for s in e.shares:
                if s.share_type == ShareType.PLATFORM_ROYALTY.value:
                    platform_share += s.amount
                elif s.share_type == ShareType.RLA_SHARE.value:
                    rla_share += s.amount
                elif s.share_type == ShareType.REMOTE_AGENT_SHARE.value:
                    agent_share += s.amount
                elif s.share_type == ShareType.RESERVE_HOLD.value:
                    reserve += s.amount

        return {
            "period": period,
            "entry_count": len(entries),
            "gross_total": gross,
            "tax_total": tax,
            "gateway_fees_total": fees,
            "net_distributable_total": net,
            "platform_share": platform_share,
            "rla_share": rla_share,
            "agent_share": agent_share,
            "reserve": reserve,
        }
