"""
BOS Phase 4 — Business Primitives Test Suite
==============================================
Tests for: Ledger, Item, Inventory, Party, Obligation primitives.

Tests verify:
- Determinism (same input → same output)
- Immutability (frozen dataclasses)
- Multi-tenant isolation
- Invariant enforcement (balanced entries, positive quantities)
- Projection correctness (balances, stock levels, lookups)
- Serialization round-trips (to_dict / from_dict)
"""

import uuid
from datetime import datetime, timezone, timedelta

import pytest

# ══════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════

BIZ_A = uuid.uuid4()
BIZ_B = uuid.uuid4()
BRANCH_1 = uuid.uuid4()
NOW = datetime(2026, 2, 19, 12, 0, 0, tzinfo=timezone.utc)
YESTERDAY = NOW - timedelta(days=1)
TOMORROW = NOW + timedelta(days=1)
NEXT_WEEK = NOW + timedelta(days=7)


# ══════════════════════════════════════════════════════════════
# MONEY TESTS
# ══════════════════════════════════════════════════════════════

class TestMoney:
    """Tests for Money value object."""

    def test_create_money(self):
        from core.primitives.ledger import Money
        m = Money(amount=1050, currency="USD")
        assert m.amount == 1050
        assert m.currency == "USD"

    def test_money_must_be_int(self):
        from core.primitives.ledger import Money
        with pytest.raises(TypeError, match="int"):
            Money(amount=10.50, currency="USD")

    def test_money_currency_must_be_3_chars(self):
        from core.primitives.ledger import Money
        with pytest.raises(ValueError, match="3-letter"):
            Money(amount=100, currency="US")

    def test_money_addition(self):
        from core.primitives.ledger import Money
        a = Money(amount=500, currency="KES")
        b = Money(amount=300, currency="KES")
        c = a + b
        assert c.amount == 800
        assert c.currency == "KES"

    def test_money_subtraction(self):
        from core.primitives.ledger import Money
        a = Money(amount=500, currency="TZS")
        b = Money(amount=200, currency="TZS")
        c = a - b
        assert c.amount == 300

    def test_money_cross_currency_fails(self):
        from core.primitives.ledger import Money
        a = Money(amount=100, currency="USD")
        b = Money(amount=100, currency="KES")
        with pytest.raises(ValueError, match="Currency mismatch"):
            a + b

    def test_money_negate(self):
        from core.primitives.ledger import Money
        m = Money(amount=500, currency="USD")
        neg = m.negate()
        assert neg.amount == -500

    def test_money_zero(self):
        from core.primitives.ledger import Money
        z = Money.zero("USD")
        assert z.is_zero()
        assert z.amount == 0

    def test_money_serialization(self):
        from core.primitives.ledger import Money
        m = Money(amount=9999, currency="EUR")
        d = m.to_dict()
        m2 = Money.from_dict(d)
        assert m == m2

    def test_money_immutable(self):
        from core.primitives.ledger import Money
        m = Money(amount=100, currency="USD")
        with pytest.raises(AttributeError):
            m.amount = 200


# ══════════════════════════════════════════════════════════════
# LEDGER TESTS
# ══════════════════════════════════════════════════════════════

class TestLedger:
    """Tests for double-entry ledger primitives."""

    def _make_accounts(self):
        from core.primitives.ledger import AccountRef, AccountType
        cash = AccountRef(
            account_code="1000",
            account_type=AccountType.ASSET,
            name="Cash",
        )
        revenue = AccountRef(
            account_code="4000",
            account_type=AccountType.REVENUE,
            name="Sales Revenue",
        )
        expense = AccountRef(
            account_code="5000",
            account_type=AccountType.EXPENSE,
            name="Cost of Goods Sold",
        )
        payable = AccountRef(
            account_code="2000",
            account_type=AccountType.LIABILITY,
            name="Accounts Payable",
        )
        return cash, revenue, expense, payable

    def test_balanced_journal_entry(self):
        from core.primitives.ledger import (
            JournalEntry, JournalLine, DebitCredit, Money,
        )
        cash, revenue, _, _ = self._make_accounts()
        entry = JournalEntry(
            entry_id=uuid.uuid4(),
            business_id=BIZ_A,
            posted_at=NOW,
            currency="KES",
            memo="Cash sale",
            lines=(
                JournalLine(
                    account=cash,
                    side=DebitCredit.DEBIT,
                    amount=Money(amount=5000, currency="KES"),
                ),
                JournalLine(
                    account=revenue,
                    side=DebitCredit.CREDIT,
                    amount=Money(amount=5000, currency="KES"),
                ),
            ),
        )
        assert entry.is_balanced
        assert entry.total_debits.amount == 5000
        assert entry.total_credits.amount == 5000

    def test_unbalanced_entry_rejected(self):
        from core.primitives.ledger import (
            JournalEntry, JournalLine, DebitCredit, Money, AccountRef,
            AccountType,
        )
        cash, revenue, _, _ = self._make_accounts()
        with pytest.raises(ValueError, match="LEDGER INVARIANT VIOLATION"):
            JournalEntry(
                entry_id=uuid.uuid4(),
                business_id=BIZ_A,
                posted_at=NOW,
                currency="KES",
                memo="Bad entry",
                lines=(
                    JournalLine(
                        account=cash,
                        side=DebitCredit.DEBIT,
                        amount=Money(amount=5000, currency="KES"),
                    ),
                    JournalLine(
                        account=revenue,
                        side=DebitCredit.CREDIT,
                        amount=Money(amount=3000, currency="KES"),
                    ),
                ),
            )

    def test_entry_needs_minimum_two_lines(self):
        from core.primitives.ledger import (
            JournalEntry, JournalLine, DebitCredit, Money,
        )
        cash, _, _, _ = self._make_accounts()
        with pytest.raises(ValueError, match="at least 2 lines"):
            JournalEntry(
                entry_id=uuid.uuid4(),
                business_id=BIZ_A,
                posted_at=NOW,
                currency="KES",
                memo="Single line",
                lines=(
                    JournalLine(
                        account=cash,
                        side=DebitCredit.DEBIT,
                        amount=Money(amount=1000, currency="KES"),
                    ),
                ),
            )

    def test_journal_line_must_be_positive(self):
        from core.primitives.ledger import JournalLine, DebitCredit, Money
        cash, _, _, _ = self._make_accounts()
        with pytest.raises(ValueError, match="positive"):
            JournalLine(
                account=cash,
                side=DebitCredit.DEBIT,
                amount=Money(amount=-100, currency="KES"),
            )

    def test_mixed_currency_entry_rejected(self):
        from core.primitives.ledger import (
            JournalEntry, JournalLine, DebitCredit, Money,
        )
        cash, revenue, _, _ = self._make_accounts()
        with pytest.raises(ValueError, match="entry currency"):
            JournalEntry(
                entry_id=uuid.uuid4(),
                business_id=BIZ_A,
                posted_at=NOW,
                currency="KES",
                memo="Mixed currencies",
                lines=(
                    JournalLine(
                        account=cash,
                        side=DebitCredit.DEBIT,
                        amount=Money(amount=5000, currency="USD"),
                    ),
                    JournalLine(
                        account=revenue,
                        side=DebitCredit.CREDIT,
                        amount=Money(amount=5000, currency="KES"),
                    ),
                ),
            )

    def test_multi_line_entry(self):
        from core.primitives.ledger import (
            JournalEntry, JournalLine, DebitCredit, Money,
        )
        cash, revenue, expense, _ = self._make_accounts()
        entry = JournalEntry(
            entry_id=uuid.uuid4(),
            business_id=BIZ_A,
            posted_at=NOW,
            currency="USD",
            memo="Sale with COGS",
            lines=(
                JournalLine(
                    account=cash,
                    side=DebitCredit.DEBIT,
                    amount=Money(amount=10000, currency="USD"),
                ),
                JournalLine(
                    account=revenue,
                    side=DebitCredit.CREDIT,
                    amount=Money(amount=10000, currency="USD"),
                ),
                JournalLine(
                    account=expense,
                    side=DebitCredit.DEBIT,
                    amount=Money(amount=6000, currency="USD"),
                ),
                JournalLine(
                    account=cash,
                    side=DebitCredit.CREDIT,
                    amount=Money(amount=6000, currency="USD"),
                ),
            ),
        )
        assert entry.is_balanced
        assert entry.total_debits.amount == 16000
        assert entry.total_credits.amount == 16000

    def test_account_normal_balance(self):
        from core.primitives.ledger import AccountRef, AccountType, DebitCredit
        asset = AccountRef("1000", AccountType.ASSET, "Cash")
        assert asset.normal_balance == DebitCredit.DEBIT
        liability = AccountRef("2000", AccountType.LIABILITY, "Payable")
        assert liability.normal_balance == DebitCredit.CREDIT
        revenue = AccountRef("4000", AccountType.REVENUE, "Sales")
        assert revenue.normal_balance == DebitCredit.CREDIT
        expense = AccountRef("5000", AccountType.EXPENSE, "COGS")
        assert expense.normal_balance == DebitCredit.DEBIT

    def test_account_ref_serialization(self):
        from core.primitives.ledger import AccountRef, AccountType
        acc = AccountRef("1000", AccountType.ASSET, "Cash")
        d = acc.to_dict()
        acc2 = AccountRef.from_dict(d)
        assert acc == acc2

    def test_journal_entry_immutable(self):
        from core.primitives.ledger import (
            JournalEntry, JournalLine, DebitCredit, Money,
        )
        cash, revenue, _, _ = self._make_accounts()
        entry = JournalEntry(
            entry_id=uuid.uuid4(),
            business_id=BIZ_A,
            posted_at=NOW,
            currency="KES",
            memo="Test",
            lines=(
                JournalLine(
                    account=cash,
                    side=DebitCredit.DEBIT,
                    amount=Money(amount=1000, currency="KES"),
                ),
                JournalLine(
                    account=revenue,
                    side=DebitCredit.CREDIT,
                    amount=Money(amount=1000, currency="KES"),
                ),
            ),
        )
        with pytest.raises(AttributeError):
            entry.memo = "Changed"

    def test_ledger_projection(self):
        from core.primitives.ledger import (
            LedgerProjection, JournalEntry, JournalLine,
            DebitCredit, Money,
        )
        cash, revenue, _, _ = self._make_accounts()
        proj = LedgerProjection(business_id=BIZ_A, currency="KES")

        entry = JournalEntry(
            entry_id=uuid.uuid4(),
            business_id=BIZ_A,
            posted_at=NOW,
            currency="KES",
            memo="Sale 1",
            lines=(
                JournalLine(
                    account=cash,
                    side=DebitCredit.DEBIT,
                    amount=Money(amount=5000, currency="KES"),
                ),
                JournalLine(
                    account=revenue,
                    side=DebitCredit.CREDIT,
                    amount=Money(amount=5000, currency="KES"),
                ),
            ),
        )
        proj.apply_entry(entry)

        assert proj.entry_count == 1
        assert proj.is_trial_balanced()

        cash_bal = proj.get_balance("1000")
        assert cash_bal is not None
        assert cash_bal.net_balance == 5000  # Asset, debit side

        rev_bal = proj.get_balance("4000")
        assert rev_bal is not None
        assert rev_bal.net_balance == 5000  # Revenue, credit side

    def test_ledger_projection_tenant_isolation(self):
        from core.primitives.ledger import (
            LedgerProjection, JournalEntry, JournalLine,
            DebitCredit, Money,
        )
        cash, revenue, _, _ = self._make_accounts()
        proj = LedgerProjection(business_id=BIZ_A, currency="KES")

        bad_entry = JournalEntry(
            entry_id=uuid.uuid4(),
            business_id=BIZ_B,  # Different tenant!
            posted_at=NOW,
            currency="KES",
            memo="Cross-tenant",
            lines=(
                JournalLine(
                    account=cash,
                    side=DebitCredit.DEBIT,
                    amount=Money(amount=1000, currency="KES"),
                ),
                JournalLine(
                    account=revenue,
                    side=DebitCredit.CREDIT,
                    amount=Money(amount=1000, currency="KES"),
                ),
            ),
        )
        with pytest.raises(ValueError, match="Tenant isolation"):
            proj.apply_entry(bad_entry)

    def test_trial_balance_always_balances(self):
        from core.primitives.ledger import (
            LedgerProjection, JournalEntry, JournalLine,
            DebitCredit, Money,
        )
        cash, revenue, expense, payable = self._make_accounts()
        proj = LedgerProjection(business_id=BIZ_A, currency="USD")

        # Multiple entries
        for i in range(5):
            entry = JournalEntry(
                entry_id=uuid.uuid4(),
                business_id=BIZ_A,
                posted_at=NOW,
                currency="USD",
                memo=f"Entry {i}",
                lines=(
                    JournalLine(
                        account=cash,
                        side=DebitCredit.DEBIT,
                        amount=Money(amount=1000 * (i + 1), currency="USD"),
                    ),
                    JournalLine(
                        account=revenue,
                        side=DebitCredit.CREDIT,
                        amount=Money(amount=1000 * (i + 1), currency="USD"),
                    ),
                ),
            )
            proj.apply_entry(entry)

        assert proj.is_trial_balanced()
        assert proj.entry_count == 5
        d, c = proj.trial_balance()
        assert d == c == 15000  # 1000+2000+3000+4000+5000

    def test_ledger_determinism(self):
        """Same entries in same order → identical projection state."""
        from core.primitives.ledger import (
            LedgerProjection, JournalEntry, JournalLine,
            DebitCredit, Money,
        )
        cash, revenue, _, _ = self._make_accounts()
        entry_id = uuid.uuid4()

        def build_projection():
            proj = LedgerProjection(business_id=BIZ_A, currency="KES")
            entry = JournalEntry(
                entry_id=entry_id,
                business_id=BIZ_A,
                posted_at=NOW,
                currency="KES",
                memo="Deterministic",
                lines=(
                    JournalLine(
                        account=cash,
                        side=DebitCredit.DEBIT,
                        amount=Money(amount=7777, currency="KES"),
                    ),
                    JournalLine(
                        account=revenue,
                        side=DebitCredit.CREDIT,
                        amount=Money(amount=7777, currency="KES"),
                    ),
                ),
            )
            proj.apply_entry(entry)
            return proj

        p1 = build_projection()
        p2 = build_projection()
        assert p1.get_balance("1000").net_balance == p2.get_balance("1000").net_balance
        assert p1.trial_balance() == p2.trial_balance()


# ══════════════════════════════════════════════════════════════
# ITEM TESTS
# ══════════════════════════════════════════════════════════════

class TestItem:
    """Tests for item/product primitives."""

    def _make_item(self, **overrides):
        from core.primitives.item import (
            ItemDefinition, ItemType, UnitOfMeasure, PriceEntry,
            PriceType, TaxCategoryRef,
        )
        from core.primitives.ledger import Money

        defaults = dict(
            item_id=uuid.uuid4(),
            business_id=BIZ_A,
            sku="ITEM-001",
            name="Widget",
            item_type=ItemType.PRODUCT,
            unit_of_measure=UnitOfMeasure.PIECE,
            version=1,
            tax_category=TaxCategoryRef(
                category_code="VAT_STD",
                name="Standard VAT",
            ),
            prices=(
                PriceEntry(
                    price_type=PriceType.SELLING,
                    amount=Money(amount=2500, currency="KES"),
                    effective_from=YESTERDAY,
                ),
            ),
        )
        defaults.update(overrides)
        return ItemDefinition(**defaults)

    def test_create_item(self):
        item = self._make_item()
        assert item.sku == "ITEM-001"
        assert item.name == "Widget"
        assert item.version == 1

    def test_item_immutable(self):
        item = self._make_item()
        with pytest.raises(AttributeError):
            item.name = "Changed"

    def test_item_requires_sku(self):
        from core.primitives.item import ItemDefinition
        with pytest.raises(ValueError, match="sku"):
            self._make_item(sku="")

    def test_item_version_must_be_positive(self):
        with pytest.raises(ValueError, match="positive"):
            self._make_item(version=0)

    def test_price_resolution(self):
        from core.primitives.item import PriceType
        item = self._make_item()
        price = item.get_active_price(PriceType.SELLING, at=NOW)
        assert price is not None
        assert price.amount.amount == 2500

    def test_price_not_yet_effective(self):
        from core.primitives.item import PriceEntry, PriceType
        from core.primitives.ledger import Money

        item = self._make_item(
            prices=(
                PriceEntry(
                    price_type=PriceType.SELLING,
                    amount=Money(amount=3000, currency="KES"),
                    effective_from=TOMORROW,
                ),
            ),
        )
        price = item.get_active_price(PriceType.SELLING, at=NOW)
        assert price is None  # Not yet effective

    def test_price_expired(self):
        from core.primitives.item import PriceEntry, PriceType
        from core.primitives.ledger import Money

        item = self._make_item(
            prices=(
                PriceEntry(
                    price_type=PriceType.SELLING,
                    amount=Money(amount=2000, currency="KES"),
                    effective_from=YESTERDAY - timedelta(days=10),
                    effective_until=YESTERDAY,
                ),
            ),
        )
        price = item.get_active_price(PriceType.SELLING, at=NOW)
        assert price is None  # Expired

    def test_quantity_based_pricing(self):
        from core.primitives.item import PriceEntry, PriceType
        from core.primitives.ledger import Money

        item = self._make_item(
            prices=(
                PriceEntry(
                    price_type=PriceType.SELLING,
                    amount=Money(amount=2500, currency="KES"),
                    effective_from=YESTERDAY,
                    min_quantity=1,
                ),
                PriceEntry(
                    price_type=PriceType.SELLING,
                    amount=Money(amount=2000, currency="KES"),
                    effective_from=YESTERDAY,
                    min_quantity=10,
                ),
            ),
        )
        # qty=1 → base price
        p1 = item.get_active_price(PriceType.SELLING, at=NOW, quantity=1)
        assert p1.amount.amount == 2500

        # qty=10 → bulk price
        p10 = item.get_active_price(PriceType.SELLING, at=NOW, quantity=10)
        assert p10.amount.amount == 2000

        # qty=50 → still bulk price (highest qualifying)
        p50 = item.get_active_price(PriceType.SELLING, at=NOW, quantity=50)
        assert p50.amount.amount == 2000

    def test_item_serialization(self):
        item = self._make_item()
        d = item.to_dict()
        assert d["sku"] == "ITEM-001"
        assert d["item_type"] == "PRODUCT"
        assert d["tax_category"]["category_code"] == "VAT_STD"
        assert len(d["prices"]) == 1

    def test_item_catalog_projection(self):
        from core.primitives.item import ItemCatalog
        catalog = ItemCatalog(business_id=BIZ_A)

        item = self._make_item()
        catalog.apply_item(item)

        assert catalog.item_count == 1
        assert catalog.get_by_sku("ITEM-001") is not None
        assert catalog.get_by_id(item.item_id) is not None
        assert len(catalog.list_active()) == 1

    def test_item_catalog_sku_uniqueness(self):
        from core.primitives.item import ItemCatalog
        catalog = ItemCatalog(business_id=BIZ_A)

        item1 = self._make_item(item_id=uuid.uuid4(), sku="DUP-001")
        item2 = self._make_item(item_id=uuid.uuid4(), sku="DUP-001")

        catalog.apply_item(item1)
        with pytest.raises(ValueError, match="SKU.*already assigned"):
            catalog.apply_item(item2)

    def test_item_catalog_tenant_isolation(self):
        from core.primitives.item import ItemCatalog
        catalog = ItemCatalog(business_id=BIZ_A)
        bad_item = self._make_item(business_id=BIZ_B)
        with pytest.raises(ValueError, match="Tenant isolation"):
            catalog.apply_item(bad_item)

    def test_price_entry_negative_rejected(self):
        from core.primitives.item import PriceEntry, PriceType
        from core.primitives.ledger import Money
        with pytest.raises(ValueError, match="negative"):
            PriceEntry(
                price_type=PriceType.SELLING,
                amount=Money(amount=-100, currency="KES"),
                effective_from=NOW,
            )


# ══════════════════════════════════════════════════════════════
# INVENTORY TESTS
# ══════════════════════════════════════════════════════════════

class TestInventory:
    """Tests for inventory movement primitives."""

    def _make_location(self, name="Main Warehouse"):
        from core.primitives.inventory import LocationRef
        return LocationRef(location_id=uuid.uuid4(), name=name)

    def _make_movement(self, **overrides):
        from core.primitives.inventory import (
            StockMovement, MovementType, MovementReason,
        )
        loc = self._make_location()
        defaults = dict(
            movement_id=uuid.uuid4(),
            business_id=BIZ_A,
            item_id=uuid.uuid4(),
            sku="ITEM-001",
            movement_type=MovementType.RECEIVE,
            reason=MovementReason.PURCHASE,
            quantity=100,
            occurred_at=NOW,
            location_to=loc,
        )
        defaults.update(overrides)
        return StockMovement(**defaults)

    def test_receive_movement(self):
        movement = self._make_movement()
        assert movement.net_quantity_change == 100

    def test_issue_movement(self):
        from core.primitives.inventory import (
            StockMovement, MovementType, MovementReason,
        )
        loc = self._make_location()
        movement = StockMovement(
            movement_id=uuid.uuid4(),
            business_id=BIZ_A,
            item_id=uuid.uuid4(),
            sku="ITEM-001",
            movement_type=MovementType.ISSUE,
            reason=MovementReason.SALE,
            quantity=30,
            occurred_at=NOW,
            location_from=loc,
        )
        assert movement.net_quantity_change == -30

    def test_transfer_movement(self):
        from core.primitives.inventory import (
            StockMovement, MovementType, MovementReason,
        )
        loc_a = self._make_location("Warehouse A")
        loc_b = self._make_location("Warehouse B")
        movement = StockMovement(
            movement_id=uuid.uuid4(),
            business_id=BIZ_A,
            item_id=uuid.uuid4(),
            sku="ITEM-001",
            movement_type=MovementType.TRANSFER,
            reason=MovementReason.BRANCH_TRANSFER,
            quantity=20,
            occurred_at=NOW,
            location_from=loc_a,
            location_to=loc_b,
        )
        assert movement.net_quantity_change == 0  # Net zero at biz level

    def test_transfer_requires_both_locations(self):
        from core.primitives.inventory import (
            StockMovement, MovementType, MovementReason,
        )
        with pytest.raises(ValueError, match="both.*location"):
            StockMovement(
                movement_id=uuid.uuid4(),
                business_id=BIZ_A,
                item_id=uuid.uuid4(),
                sku="ITEM-001",
                movement_type=MovementType.TRANSFER,
                reason=MovementReason.BRANCH_TRANSFER,
                quantity=10,
                occurred_at=NOW,
                location_from=self._make_location(),
                # Missing location_to!
            )

    def test_issue_requires_location_from(self):
        from core.primitives.inventory import (
            StockMovement, MovementType, MovementReason,
        )
        with pytest.raises(ValueError, match="location_from"):
            StockMovement(
                movement_id=uuid.uuid4(),
                business_id=BIZ_A,
                item_id=uuid.uuid4(),
                sku="ITEM-001",
                movement_type=MovementType.ISSUE,
                reason=MovementReason.SALE,
                quantity=10,
                occurred_at=NOW,
                # Missing location_from!
            )

    def test_receive_requires_location_to(self):
        from core.primitives.inventory import (
            StockMovement, MovementType, MovementReason,
        )
        with pytest.raises(ValueError, match="location_to"):
            StockMovement(
                movement_id=uuid.uuid4(),
                business_id=BIZ_A,
                item_id=uuid.uuid4(),
                sku="ITEM-001",
                movement_type=MovementType.RECEIVE,
                reason=MovementReason.PURCHASE,
                quantity=10,
                occurred_at=NOW,
                # Missing location_to!
            )

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValueError, match="positive"):
            self._make_movement(quantity=0)
        with pytest.raises(ValueError, match="positive"):
            self._make_movement(quantity=-5)

    def test_movement_immutable(self):
        movement = self._make_movement()
        with pytest.raises(AttributeError):
            movement.quantity = 200

    def test_inventory_projection(self):
        from core.primitives.inventory import (
            InventoryProjection, StockMovement, MovementType,
            MovementReason, LocationRef,
        )
        proj = InventoryProjection(business_id=BIZ_A)
        item_id = uuid.uuid4()
        loc = LocationRef(location_id=uuid.uuid4(), name="Main")

        # Receive 100
        proj.apply_movement(StockMovement(
            movement_id=uuid.uuid4(),
            business_id=BIZ_A,
            item_id=item_id,
            sku="WIDGET",
            movement_type=MovementType.RECEIVE,
            reason=MovementReason.PURCHASE,
            quantity=100,
            occurred_at=NOW,
            location_to=loc,
        ))

        # Issue 30
        proj.apply_movement(StockMovement(
            movement_id=uuid.uuid4(),
            business_id=BIZ_A,
            item_id=item_id,
            sku="WIDGET",
            movement_type=MovementType.ISSUE,
            reason=MovementReason.SALE,
            quantity=30,
            occurred_at=NOW,
            location_from=loc,
        ))

        assert proj.movement_count == 2
        level = proj.get_stock_level(item_id, loc.location_id)
        assert level is not None
        assert level.quantity_on_hand == 70
        assert level.total_received == 100
        assert level.total_issued == 30
        assert level.is_in_stock

    def test_inventory_projection_transfer(self):
        from core.primitives.inventory import (
            InventoryProjection, StockMovement, MovementType,
            MovementReason, LocationRef,
        )
        proj = InventoryProjection(business_id=BIZ_A)
        item_id = uuid.uuid4()
        loc_a = LocationRef(location_id=uuid.uuid4(), name="Warehouse A")
        loc_b = LocationRef(location_id=uuid.uuid4(), name="Warehouse B")

        # Receive 50 at A
        proj.apply_movement(StockMovement(
            movement_id=uuid.uuid4(),
            business_id=BIZ_A,
            item_id=item_id,
            sku="BOLT",
            movement_type=MovementType.RECEIVE,
            reason=MovementReason.PURCHASE,
            quantity=50,
            occurred_at=NOW,
            location_to=loc_a,
        ))

        # Transfer 20 from A → B
        proj.apply_movement(StockMovement(
            movement_id=uuid.uuid4(),
            business_id=BIZ_A,
            item_id=item_id,
            sku="BOLT",
            movement_type=MovementType.TRANSFER,
            reason=MovementReason.BRANCH_TRANSFER,
            quantity=20,
            occurred_at=NOW,
            location_from=loc_a,
            location_to=loc_b,
        ))

        level_a = proj.get_stock_level(item_id, loc_a.location_id)
        level_b = proj.get_stock_level(item_id, loc_b.location_id)
        assert level_a.quantity_on_hand == 30
        assert level_b.quantity_on_hand == 20
        assert proj.get_total_stock(item_id) == 50  # Total unchanged

    def test_inventory_projection_tenant_isolation(self):
        from core.primitives.inventory import InventoryProjection
        proj = InventoryProjection(business_id=BIZ_A)
        bad_movement = self._make_movement(business_id=BIZ_B)
        with pytest.raises(ValueError, match="Tenant isolation"):
            proj.apply_movement(bad_movement)

    def test_location_serialization(self):
        from core.primitives.inventory import LocationRef
        loc = LocationRef(location_id=uuid.uuid4(), name="Shelf B2")
        d = loc.to_dict()
        loc2 = LocationRef.from_dict(d)
        assert loc == loc2


# ══════════════════════════════════════════════════════════════
# PARTY TESTS
# ══════════════════════════════════════════════════════════════

class TestParty:
    """Tests for party/stakeholder primitives."""

    def _make_party(self, **overrides):
        from core.primitives.party import (
            PartyDefinition, PartyType, ContactEntry, ContactType,
            TaxIdentification,
        )
        defaults = dict(
            party_id=uuid.uuid4(),
            business_id=BIZ_A,
            party_type=PartyType.CUSTOMER,
            name="John Doe",
            code="CUST-001",
            version=1,
            contacts=(
                ContactEntry(
                    contact_type=ContactType.PHONE,
                    value="+254700123456",
                    is_primary=True,
                ),
                ContactEntry(
                    contact_type=ContactType.EMAIL,
                    value="john@example.com",
                ),
            ),
            tax_ids=(
                TaxIdentification(
                    tax_id_type="TIN",
                    tax_id_value="A123456789",
                ),
            ),
            tags=("vip", "retail"),
        )
        defaults.update(overrides)
        return PartyDefinition(**defaults)

    def test_create_party(self):
        party = self._make_party()
        assert party.name == "John Doe"
        assert party.code == "CUST-001"
        assert party.version == 1

    def test_party_immutable(self):
        party = self._make_party()
        with pytest.raises(AttributeError):
            party.name = "Changed"

    def test_party_primary_contact(self):
        from core.primitives.party import ContactType
        party = self._make_party()
        phone = party.get_primary_contact(ContactType.PHONE)
        assert phone is not None
        assert phone.value == "+254700123456"
        assert phone.is_primary

    def test_party_has_tag(self):
        party = self._make_party()
        assert party.has_tag("vip")
        assert not party.has_tag("wholesale")

    def test_party_requires_name(self):
        with pytest.raises(ValueError, match="name"):
            self._make_party(name="")

    def test_party_requires_code(self):
        with pytest.raises(ValueError, match="code"):
            self._make_party(code="")

    def test_party_version_positive(self):
        with pytest.raises(ValueError, match="positive"):
            self._make_party(version=0)

    def test_party_registry(self):
        from core.primitives.party import PartyRegistry, PartyType
        registry = PartyRegistry(business_id=BIZ_A)

        customer = self._make_party()
        registry.apply_party(customer)

        assert registry.party_count == 1
        assert registry.get_by_code("CUST-001") is not None
        assert registry.get_by_id(customer.party_id) is not None
        assert len(registry.list_by_type(PartyType.CUSTOMER)) == 1

    def test_party_registry_code_uniqueness(self):
        from core.primitives.party import PartyRegistry
        registry = PartyRegistry(business_id=BIZ_A)

        p1 = self._make_party(party_id=uuid.uuid4(), code="DUP-001")
        p2 = self._make_party(party_id=uuid.uuid4(), code="DUP-001")

        registry.apply_party(p1)
        with pytest.raises(ValueError, match="code.*already assigned"):
            registry.apply_party(p2)

    def test_party_registry_tenant_isolation(self):
        from core.primitives.party import PartyRegistry
        registry = PartyRegistry(business_id=BIZ_A)
        bad_party = self._make_party(business_id=BIZ_B)
        with pytest.raises(ValueError, match="Tenant isolation"):
            registry.apply_party(bad_party)

    def test_party_registry_list_active(self):
        from core.primitives.party import PartyRegistry, PartyStatus
        registry = PartyRegistry(business_id=BIZ_A)

        active = self._make_party(
            party_id=uuid.uuid4(), code="A-001",
        )
        inactive = self._make_party(
            party_id=uuid.uuid4(), code="I-001",
            status=PartyStatus.INACTIVE,
        )
        registry.apply_party(active)
        registry.apply_party(inactive)

        assert len(registry.list_active()) == 1

    def test_party_registry_list_by_tag(self):
        from core.primitives.party import PartyRegistry
        registry = PartyRegistry(business_id=BIZ_A)

        vip = self._make_party(
            party_id=uuid.uuid4(), code="V-001",
            tags=("vip",),
        )
        regular = self._make_party(
            party_id=uuid.uuid4(), code="R-001",
            tags=("regular",),
        )
        registry.apply_party(vip)
        registry.apply_party(regular)

        assert len(registry.list_by_tag("vip")) == 1

    def test_party_serialization(self):
        party = self._make_party()
        d = party.to_dict()
        assert d["party_type"] == "CUSTOMER"
        assert d["code"] == "CUST-001"
        assert len(d["contacts"]) == 2
        assert len(d["tax_ids"]) == 1

    def test_tax_identification_serialization(self):
        from core.primitives.party import TaxIdentification
        tid = TaxIdentification(tax_id_type="VAT", tax_id_value="V12345")
        d = tid.to_dict()
        tid2 = TaxIdentification.from_dict(d)
        assert tid == tid2

    def test_contact_entry_serialization(self):
        from core.primitives.party import ContactEntry, ContactType
        c = ContactEntry(
            contact_type=ContactType.EMAIL,
            value="test@example.com",
            label="Work",
            is_primary=True,
        )
        d = c.to_dict()
        c2 = ContactEntry.from_dict(d)
        assert c == c2


# ══════════════════════════════════════════════════════════════
# OBLIGATION TESTS
# ══════════════════════════════════════════════════════════════

class TestObligation:
    """Tests for obligation/commitment primitives."""

    def _make_obligation(self, **overrides):
        from core.primitives.obligation import (
            ObligationDefinition, ObligationType,
        )
        from core.primitives.ledger import Money

        defaults = dict(
            obligation_id=uuid.uuid4(),
            business_id=BIZ_A,
            obligation_type=ObligationType.RECEIVABLE,
            party_id=uuid.uuid4(),
            total_amount=Money(amount=50000, currency="KES"),
            due_date=NEXT_WEEK,
            created_at=NOW,
            description="Invoice #1001",
        )
        defaults.update(overrides)
        return ObligationDefinition(**defaults)

    def test_create_obligation(self):
        obl = self._make_obligation()
        assert obl.amount_remaining.amount == 50000
        assert obl.fulfillment_percentage == 0
        assert not obl.is_fully_fulfilled

    def test_obligation_immutable(self):
        obl = self._make_obligation()
        with pytest.raises(AttributeError):
            obl.description = "Changed"

    def test_obligation_requires_positive_amount(self):
        from core.primitives.ledger import Money
        with pytest.raises(ValueError, match="positive"):
            self._make_obligation(
                total_amount=Money(amount=0, currency="KES"),
            )

    def test_partial_fulfillment(self):
        from core.primitives.obligation import FulfillmentRecord, FulfillmentType
        from core.primitives.ledger import Money

        obl = self._make_obligation()

        record = FulfillmentRecord(
            fulfillment_id=uuid.uuid4(),
            fulfillment_type=FulfillmentType.PAYMENT_CASH,
            amount=Money(amount=20000, currency="KES"),
            fulfilled_at=NOW,
        )

        updated = obl.with_fulfillment(record)
        assert updated.is_partially_fulfilled
        assert not updated.is_fully_fulfilled
        assert updated.amount_fulfilled.amount == 20000
        assert updated.amount_remaining.amount == 30000
        assert updated.fulfillment_percentage == 40

    def test_full_fulfillment(self):
        from core.primitives.obligation import (
            FulfillmentRecord, FulfillmentType, ObligationStatus,
        )
        from core.primitives.ledger import Money

        obl = self._make_obligation()

        record = FulfillmentRecord(
            fulfillment_id=uuid.uuid4(),
            fulfillment_type=FulfillmentType.PAYMENT_CASH,
            amount=Money(amount=50000, currency="KES"),
            fulfilled_at=NOW,
        )

        updated = obl.with_fulfillment(record)
        assert updated.is_fully_fulfilled
        assert updated.status == ObligationStatus.FULFILLED
        assert updated.fulfillment_percentage == 100

    def test_multi_payment_fulfillment(self):
        from core.primitives.obligation import (
            FulfillmentRecord, FulfillmentType, ObligationStatus,
        )
        from core.primitives.ledger import Money

        obl = self._make_obligation()

        # Payment 1: 15000
        obl = obl.with_fulfillment(FulfillmentRecord(
            fulfillment_id=uuid.uuid4(),
            fulfillment_type=FulfillmentType.PAYMENT_CASH,
            amount=Money(amount=15000, currency="KES"),
            fulfilled_at=NOW,
        ))
        assert obl.status == ObligationStatus.PARTIALLY_FULFILLED

        # Payment 2: 15000
        obl = obl.with_fulfillment(FulfillmentRecord(
            fulfillment_id=uuid.uuid4(),
            fulfillment_type=FulfillmentType.PAYMENT_MOBILE,
            amount=Money(amount=15000, currency="KES"),
            fulfilled_at=NOW,
        ))
        assert obl.status == ObligationStatus.PARTIALLY_FULFILLED
        assert obl.fulfillment_percentage == 60

        # Payment 3: 20000 (completes)
        obl = obl.with_fulfillment(FulfillmentRecord(
            fulfillment_id=uuid.uuid4(),
            fulfillment_type=FulfillmentType.PAYMENT_BANK,
            amount=Money(amount=20000, currency="KES"),
            fulfilled_at=NOW,
        ))
        assert obl.status == ObligationStatus.FULFILLED
        assert len(obl.fulfillments) == 3

    def test_overdue_detection(self):
        obl = self._make_obligation(due_date=YESTERDAY)
        assert obl.is_overdue_at(NOW)

    def test_not_overdue_before_due(self):
        obl = self._make_obligation(due_date=NEXT_WEEK)
        assert not obl.is_overdue_at(NOW)

    def test_fulfilled_not_overdue(self):
        from core.primitives.obligation import (
            ObligationDefinition, ObligationType, ObligationStatus,
        )
        from core.primitives.ledger import Money
        obl = ObligationDefinition(
            obligation_id=uuid.uuid4(),
            business_id=BIZ_A,
            obligation_type=ObligationType.RECEIVABLE,
            party_id=uuid.uuid4(),
            total_amount=Money(amount=10000, currency="KES"),
            due_date=YESTERDAY,
            created_at=YESTERDAY - timedelta(days=7),
            status=ObligationStatus.FULFILLED,
        )
        assert not obl.is_overdue_at(NOW)

    def test_obligation_tracker(self):
        from core.primitives.obligation import (
            ObligationTracker, ObligationType,
        )

        tracker = ObligationTracker(business_id=BIZ_A)
        obl = self._make_obligation()
        tracker.apply_obligation(obl)

        assert tracker.obligation_count == 1
        assert tracker.get_by_id(obl.obligation_id) is not None
        assert len(tracker.list_by_type(ObligationType.RECEIVABLE)) == 1

    def test_tracker_apply_fulfillment(self):
        from core.primitives.obligation import (
            ObligationTracker, FulfillmentRecord, FulfillmentType,
        )
        from core.primitives.ledger import Money

        tracker = ObligationTracker(business_id=BIZ_A)
        obl = self._make_obligation()
        tracker.apply_obligation(obl)

        record = FulfillmentRecord(
            fulfillment_id=uuid.uuid4(),
            fulfillment_type=FulfillmentType.PAYMENT_CASH,
            amount=Money(amount=25000, currency="KES"),
            fulfilled_at=NOW,
        )
        updated = tracker.apply_fulfillment(obl.obligation_id, record)
        assert updated.is_partially_fulfilled

    def test_tracker_tenant_isolation(self):
        from core.primitives.obligation import ObligationTracker
        tracker = ObligationTracker(business_id=BIZ_A)
        bad_obl = self._make_obligation(business_id=BIZ_B)
        with pytest.raises(ValueError, match="Tenant isolation"):
            tracker.apply_obligation(bad_obl)

    def test_tracker_total_outstanding(self):
        from core.primitives.obligation import (
            ObligationTracker, ObligationType,
        )
        from core.primitives.ledger import Money

        tracker = ObligationTracker(business_id=BIZ_A)

        tracker.apply_obligation(self._make_obligation(
            obligation_id=uuid.uuid4(),
            total_amount=Money(amount=10000, currency="KES"),
        ))
        tracker.apply_obligation(self._make_obligation(
            obligation_id=uuid.uuid4(),
            total_amount=Money(amount=25000, currency="KES"),
        ))

        total = tracker.total_outstanding(ObligationType.RECEIVABLE, "KES")
        assert total.amount == 35000

    def test_tracker_list_overdue(self):
        from core.primitives.obligation import ObligationTracker
        tracker = ObligationTracker(business_id=BIZ_A)

        overdue = self._make_obligation(
            obligation_id=uuid.uuid4(), due_date=YESTERDAY,
        )
        current = self._make_obligation(
            obligation_id=uuid.uuid4(), due_date=NEXT_WEEK,
        )
        tracker.apply_obligation(overdue)
        tracker.apply_obligation(current)

        overdue_list = tracker.list_overdue_at(NOW)
        assert len(overdue_list) == 1

    def test_fulfillment_record_serialization(self):
        from core.primitives.obligation import (
            FulfillmentRecord, FulfillmentType,
        )
        from core.primitives.ledger import Money

        record = FulfillmentRecord(
            fulfillment_id=uuid.uuid4(),
            fulfillment_type=FulfillmentType.PAYMENT_CASH,
            amount=Money(amount=5000, currency="KES"),
            fulfilled_at=NOW,
            reference_id="PAY-001",
        )
        d = record.to_dict()
        r2 = FulfillmentRecord.from_dict(d)
        assert record == r2

    def test_obligation_serialization(self):
        obl = self._make_obligation()
        d = obl.to_dict()
        assert d["obligation_type"] == "RECEIVABLE"
        assert d["total_amount"]["amount"] == 50000
        assert d["fulfillment_percentage"] == 0

    def test_fulfillment_must_be_positive(self):
        from core.primitives.obligation import (
            FulfillmentRecord, FulfillmentType,
        )
        from core.primitives.ledger import Money
        with pytest.raises(ValueError, match="positive"):
            FulfillmentRecord(
                fulfillment_id=uuid.uuid4(),
                fulfillment_type=FulfillmentType.PAYMENT_CASH,
                amount=Money(amount=-100, currency="KES"),
                fulfilled_at=NOW,
            )


# ══════════════════════════════════════════════════════════════
# CROSS-PRIMITIVE INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════

class TestCrossPrimitiveIntegration:
    """
    Tests that primitives work together correctly.
    Simulates real business flows using multiple primitives.
    """

    def test_sale_flow_ledger_inventory_obligation(self):
        """
        Full sale flow:
        1. Item exists in catalog
        2. Stock is issued (inventory)
        3. Journal entry posted (ledger)
        4. Obligation created (receivable)
        5. Payment received (fulfillment)
        """
        from core.primitives.ledger import (
            Money, JournalEntry, JournalLine, DebitCredit,
            AccountRef, AccountType, LedgerProjection,
        )
        from core.primitives.item import (
            ItemDefinition, ItemType, UnitOfMeasure, ItemCatalog,
            PriceEntry, PriceType,
        )
        from core.primitives.inventory import (
            InventoryProjection, StockMovement, MovementType,
            MovementReason, LocationRef,
        )
        from core.primitives.party import (
            PartyDefinition, PartyType, PartyRegistry,
        )
        from core.primitives.obligation import (
            ObligationTracker, ObligationDefinition, ObligationType,
            FulfillmentRecord, FulfillmentType, ObligationStatus,
        )

        # Setup
        item_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        warehouse = LocationRef(location_id=uuid.uuid4(), name="Main")

        # 1. Register item in catalog
        catalog = ItemCatalog(business_id=BIZ_A)
        item = ItemDefinition(
            item_id=item_id,
            business_id=BIZ_A,
            sku="LAPTOP-001",
            name="Laptop Pro 15",
            item_type=ItemType.PRODUCT,
            unit_of_measure=UnitOfMeasure.PIECE,
            version=1,
            prices=(
                PriceEntry(
                    price_type=PriceType.SELLING,
                    amount=Money(amount=150000, currency="KES"),
                    effective_from=YESTERDAY,
                ),
            ),
        )
        catalog.apply_item(item)

        # 2. Register customer
        registry = PartyRegistry(business_id=BIZ_A)
        customer = PartyDefinition(
            party_id=customer_id,
            business_id=BIZ_A,
            party_type=PartyType.CUSTOMER,
            name="Acme Corp",
            code="CUST-ACME",
            version=1,
        )
        registry.apply_party(customer)

        # 3. Receive stock first
        inv_proj = InventoryProjection(business_id=BIZ_A)
        inv_proj.apply_movement(StockMovement(
            movement_id=uuid.uuid4(),
            business_id=BIZ_A,
            item_id=item_id,
            sku="LAPTOP-001",
            movement_type=MovementType.RECEIVE,
            reason=MovementReason.PURCHASE,
            quantity=10,
            occurred_at=YESTERDAY,
            location_to=warehouse,
        ))

        # 4. Issue 2 units for sale
        inv_proj.apply_movement(StockMovement(
            movement_id=uuid.uuid4(),
            business_id=BIZ_A,
            item_id=item_id,
            sku="LAPTOP-001",
            movement_type=MovementType.ISSUE,
            reason=MovementReason.SALE,
            quantity=2,
            occurred_at=NOW,
            location_from=warehouse,
        ))
        stock = inv_proj.get_stock_level(item_id, warehouse.location_id)
        assert stock.quantity_on_hand == 8

        # 5. Post journal entry (sale at 150000 x 2 = 300000)
        sale_amount = 300000
        ar = AccountRef("1200", AccountType.ASSET, "Accounts Receivable")
        revenue = AccountRef("4000", AccountType.REVENUE, "Sales Revenue")

        ledger = LedgerProjection(business_id=BIZ_A, currency="KES")
        ledger.apply_entry(JournalEntry(
            entry_id=uuid.uuid4(),
            business_id=BIZ_A,
            posted_at=NOW,
            currency="KES",
            memo="Sale to Acme Corp - 2x Laptop Pro 15",
            lines=(
                JournalLine(
                    account=ar,
                    side=DebitCredit.DEBIT,
                    amount=Money(amount=sale_amount, currency="KES"),
                ),
                JournalLine(
                    account=revenue,
                    side=DebitCredit.CREDIT,
                    amount=Money(amount=sale_amount, currency="KES"),
                ),
            ),
        ))
        assert ledger.is_trial_balanced()

        # 6. Create obligation (receivable)
        tracker = ObligationTracker(business_id=BIZ_A)
        obl = ObligationDefinition(
            obligation_id=uuid.uuid4(),
            business_id=BIZ_A,
            obligation_type=ObligationType.RECEIVABLE,
            party_id=customer_id,
            total_amount=Money(amount=sale_amount, currency="KES"),
            due_date=NEXT_WEEK,
            created_at=NOW,
            description="INV-1001: 2x Laptop Pro 15",
        )
        tracker.apply_obligation(obl)

        # 7. Customer pays
        updated = tracker.apply_fulfillment(
            obl.obligation_id,
            FulfillmentRecord(
                fulfillment_id=uuid.uuid4(),
                fulfillment_type=FulfillmentType.PAYMENT_MOBILE,
                amount=Money(amount=sale_amount, currency="KES"),
                fulfilled_at=NOW,
            ),
        )
        assert updated.status == ObligationStatus.FULFILLED
        assert updated.amount_remaining.amount == 0

        # Verify everything is consistent
        assert catalog.get_by_sku("LAPTOP-001") is not None
        assert registry.get_by_code("CUST-ACME") is not None
        assert ledger.get_balance("1200").net_balance == sale_amount
        assert ledger.get_balance("4000").net_balance == sale_amount

    def test_determinism_across_primitives(self):
        """
        Same operations in same order → identical state.
        Core BOS guarantee.
        """
        from core.primitives.ledger import (
            Money, JournalEntry, JournalLine, DebitCredit,
            AccountRef, AccountType, LedgerProjection,
        )
        from core.primitives.inventory import (
            InventoryProjection, StockMovement, MovementType,
            MovementReason, LocationRef,
        )

        entry_id = uuid.uuid4()
        mov_id = uuid.uuid4()
        item_id = uuid.uuid4()
        loc_id = uuid.uuid4()

        def run_scenario():
            cash = AccountRef("1000", AccountType.ASSET, "Cash")
            rev = AccountRef("4000", AccountType.REVENUE, "Revenue")
            loc = LocationRef(location_id=loc_id, name="Warehouse")

            ledger = LedgerProjection(business_id=BIZ_A, currency="KES")
            ledger.apply_entry(JournalEntry(
                entry_id=entry_id,
                business_id=BIZ_A,
                posted_at=NOW,
                currency="KES",
                memo="Test",
                lines=(
                    JournalLine(
                        account=cash,
                        side=DebitCredit.DEBIT,
                        amount=Money(amount=5000, currency="KES"),
                    ),
                    JournalLine(
                        account=rev,
                        side=DebitCredit.CREDIT,
                        amount=Money(amount=5000, currency="KES"),
                    ),
                ),
            ))

            inv = InventoryProjection(business_id=BIZ_A)
            inv.apply_movement(StockMovement(
                movement_id=mov_id,
                business_id=BIZ_A,
                item_id=item_id,
                sku="TEST",
                movement_type=MovementType.RECEIVE,
                reason=MovementReason.PURCHASE,
                quantity=100,
                occurred_at=NOW,
                location_to=loc,
            ))

            return (
                ledger.get_balance("1000").net_balance,
                ledger.get_balance("4000").net_balance,
                ledger.trial_balance(),
                inv.get_total_stock(item_id),
            )

        r1 = run_scenario()
        r2 = run_scenario()
        assert r1 == r2  # Deterministic
