"""
BOS Inventory Lot Engine — FIFO / LIFO / WAC Stock Valuation
=============================================================
Authority: BOS Roadmap 5.2 — "FIFO/LIFO strategy plugin"

RULES (NON-NEGOTIABLE):
- All arithmetic is integer (minor currency units — no floats)
- Lot ordering is deterministic (insertion order = receive order)
- FIFO: consume oldest lots first
- LIFO: consume newest lots first
- WAC: consume in FIFO order but cost = weighted average at time of issue
- Lots with 0 remaining quantity are retained (audit trail) but skipped in consume
- Negative stock is allowed at quantity level (backorder) but flagged

A "lot" is a batch of stock received together with a specific unit_cost.
Each stock.received event with a unit_cost creates a new lot.
Stock received without unit_cost (unit_cost=None or 0) creates an
uncosted lot — it participates in qty tracking but not valuation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class ValuationMethod(Enum):
    FIFO = "FIFO"  # First In, First Out — oldest lots consumed first
    LIFO = "LIFO"  # Last In, First Out — newest lots consumed first
    WAC = "WAC"    # Weighted Average Cost — FIFO order, avg unit cost


# ══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════

@dataclass
class _LotEntry:
    """
    Internal mutable lot entry (not exposed externally).
    quantity_remaining decreases as lots are consumed.
    """
    lot_id: str
    quantity_original: int
    quantity_remaining: int
    unit_cost: int          # minor currency units (0 = uncosted)
    received_at: str        # ISO datetime string
    reference_id: Optional[str] = None


@dataclass(frozen=True)
class StockLot:
    """Immutable snapshot of a lot (for external read queries)."""
    lot_id: str
    quantity_original: int
    quantity_remaining: int
    unit_cost: int
    received_at: str
    reference_id: Optional[str]

    @property
    def is_exhausted(self) -> bool:
        return self.quantity_remaining <= 0

    @property
    def current_value(self) -> int:
        """Current value of remaining stock in this lot (minor currency units)."""
        return self.quantity_remaining * self.unit_cost


@dataclass(frozen=True)
class ConsumedLot:
    """Record of stock consumed from a specific lot."""
    lot_id: str
    quantity_consumed: int
    unit_cost: int
    total_cost: int   # quantity_consumed × unit_cost


@dataclass(frozen=True)
class LotConsumptionResult:
    """Result of a consumption operation against a lot ledger."""
    consumed: Tuple[ConsumedLot, ...]
    total_cost: int            # Sum of all consumed lot costs
    quantity_consumed: int     # Actual qty consumed (may < requested if understock)
    quantity_unfulfilled: int  # How much could NOT be fulfilled (0 = fully fulfilled)
    method: ValuationMethod

    @property
    def fully_fulfilled(self) -> bool:
        return self.quantity_unfulfilled == 0

    @property
    def cost_per_unit(self) -> int:
        """Average cost per unit consumed (integer division)."""
        if self.quantity_consumed == 0:
            return 0
        return self.total_cost // self.quantity_consumed


# ══════════════════════════════════════════════════════════════
# LOT LEDGER
# ══════════════════════════════════════════════════════════════

class LotLedger:
    """
    Manages stock lots for a single (item_id, location_id) pair.

    Lot ordering:
    - FIFO: consume _lots[0] first (oldest)
    - LIFO: consume _lots[-1] first (newest)
    - WAC: consume in FIFO order but cost = weighted average at issue time

    All lot quantities are tracked as non-negative integers.
    Consuming more than available results in quantity_unfulfilled > 0.
    """

    def __init__(self):
        self._lots: List[_LotEntry] = []
        self._lot_sequence: int = 0

    def receive(
        self,
        lot_id: str,
        quantity: int,
        unit_cost: int,
        received_at: str,
        reference_id: Optional[str] = None,
    ) -> None:
        """Add a new lot to the ledger."""
        if quantity <= 0:
            raise ValueError(f"Lot quantity must be positive, got {quantity}.")
        if unit_cost < 0:
            raise ValueError(f"unit_cost cannot be negative, got {unit_cost}.")
        self._lot_sequence += 1
        self._lots.append(_LotEntry(
            lot_id=lot_id,
            quantity_original=quantity,
            quantity_remaining=quantity,
            unit_cost=unit_cost,
            received_at=received_at,
            reference_id=reference_id,
        ))

    def consume(
        self,
        quantity: int,
        method: ValuationMethod = ValuationMethod.FIFO,
    ) -> LotConsumptionResult:
        """
        Consume stock from lots using the specified valuation method.

        Returns a LotConsumptionResult detailing which lots were consumed
        and the total cost of consumed stock.
        """
        if quantity <= 0:
            raise ValueError(f"Consume quantity must be positive, got {quantity}.")

        # WAC: compute weighted average cost first, then consume in FIFO order
        wac = self.get_weighted_average_cost() if method == ValuationMethod.WAC else 0

        # Choose order based on method
        if method == ValuationMethod.LIFO:
            # Process newest first — work backwards
            lot_indices = list(range(len(self._lots) - 1, -1, -1))
        else:
            # FIFO and WAC: process oldest first
            lot_indices = list(range(len(self._lots)))

        remaining = quantity
        consumed_lots: List[ConsumedLot] = []

        for idx in lot_indices:
            lot = self._lots[idx]
            if remaining <= 0:
                break
            if lot.quantity_remaining <= 0:
                continue

            take = min(lot.quantity_remaining, remaining)
            lot.quantity_remaining -= take
            remaining -= take

            if method == ValuationMethod.WAC:
                # Use weighted average cost, not the lot's specific cost
                effective_cost = wac
            else:
                effective_cost = lot.unit_cost

            consumed_lots.append(ConsumedLot(
                lot_id=lot.lot_id,
                quantity_consumed=take,
                unit_cost=effective_cost,
                total_cost=take * effective_cost,
            ))

        qty_consumed = quantity - remaining
        total_cost = sum(c.total_cost for c in consumed_lots)

        return LotConsumptionResult(
            consumed=tuple(consumed_lots),
            total_cost=total_cost,
            quantity_consumed=qty_consumed,
            quantity_unfulfilled=remaining,
            method=method,
        )

    def get_total_quantity(self) -> int:
        """Total remaining stock quantity across all lots."""
        return sum(lot.quantity_remaining for lot in self._lots)

    def get_total_value(self) -> int:
        """Total stock value (quantity × unit_cost) across all lots (minor units)."""
        return sum(
            lot.quantity_remaining * lot.unit_cost
            for lot in self._lots
        )

    def get_weighted_average_cost(self) -> int:
        """
        Weighted average cost per unit (integer division).
        Returns 0 if no stock.
        """
        total_qty = self.get_total_quantity()
        if total_qty == 0:
            return 0
        return self.get_total_value() // total_qty

    def get_lots(self) -> List[StockLot]:
        """Return immutable snapshots of all lots (including exhausted ones)."""
        return [
            StockLot(
                lot_id=lot.lot_id,
                quantity_original=lot.quantity_original,
                quantity_remaining=lot.quantity_remaining,
                unit_cost=lot.unit_cost,
                received_at=lot.received_at,
                reference_id=lot.reference_id,
            )
            for lot in self._lots
        ]

    def get_active_lots(self) -> List[StockLot]:
        """Return only lots with remaining stock."""
        return [s for s in self.get_lots() if not s.is_exhausted]

    @property
    def lot_count(self) -> int:
        return len(self._lots)


# ══════════════════════════════════════════════════════════════
# LOT STORE (multi-item, multi-location)
# ══════════════════════════════════════════════════════════════

class LotStore:
    """
    Manages LotLedgers for all (item_id, location_id) pairs.
    Embedded inside InventoryProjectionStore.

    Default valuation method is FIFO.
    Per-item valuation methods can be set via set_item_method().
    """

    def __init__(self, default_method: ValuationMethod = ValuationMethod.FIFO):
        self._ledgers: Dict[Tuple[str, str], LotLedger] = {}
        self._default_method = default_method
        self._item_methods: Dict[str, ValuationMethod] = {}  # item_id → method
        self._lot_sequence: Dict[Tuple[str, str], int] = {}

    def set_item_method(self, item_id: str, method: ValuationMethod) -> None:
        """Set the valuation method for a specific item."""
        self._item_methods[item_id] = method

    def get_method(self, item_id: str) -> ValuationMethod:
        return self._item_methods.get(item_id, self._default_method)

    def _ledger(self, item_id: str, location_id: str) -> LotLedger:
        key = (item_id, location_id)
        if key not in self._ledgers:
            self._ledgers[key] = LotLedger()
        return self._ledgers[key]

    def _next_lot_id(self, item_id: str, location_id: str) -> str:
        key = (item_id, location_id)
        seq = self._lot_sequence.get(key, 0) + 1
        self._lot_sequence[key] = seq
        return f"LOT-{item_id}-{location_id}-{seq:04d}"

    def receive(
        self,
        item_id: str,
        location_id: str,
        quantity: int,
        unit_cost: int,
        received_at: str,
        reference_id: Optional[str] = None,
        lot_id: Optional[str] = None,
    ) -> str:
        """
        Receive stock into a lot. Returns the lot_id used.
        If lot_id is None, one is auto-generated deterministically.
        """
        if lot_id is None:
            lot_id = self._next_lot_id(item_id, location_id)
        ledger = self._ledger(item_id, location_id)
        ledger.receive(
            lot_id=lot_id,
            quantity=quantity,
            unit_cost=unit_cost,
            received_at=received_at,
            reference_id=reference_id,
        )
        return lot_id

    def consume(
        self,
        item_id: str,
        location_id: str,
        quantity: int,
        method: Optional[ValuationMethod] = None,
    ) -> LotConsumptionResult:
        """Consume stock from lots using FIFO/LIFO/WAC."""
        effective_method = method or self.get_method(item_id)
        ledger = self._ledger(item_id, location_id)
        return ledger.consume(quantity, effective_method)

    def get_stock_value(self, item_id: str, location_id: str) -> int:
        """Total value of stock on hand at this location."""
        return self._ledger(item_id, location_id).get_total_value()

    def get_weighted_average_cost(self, item_id: str, location_id: str) -> int:
        return self._ledger(item_id, location_id).get_weighted_average_cost()

    def get_lots(self, item_id: str, location_id: str) -> List[StockLot]:
        return self._ledger(item_id, location_id).get_lots()

    def get_active_lots(self, item_id: str, location_id: str) -> List[StockLot]:
        return self._ledger(item_id, location_id).get_active_lots()

    def total_inventory_value(self) -> int:
        """Sum of all lot values across all items and locations."""
        return sum(ledger.get_total_value() for ledger in self._ledgers.values())
