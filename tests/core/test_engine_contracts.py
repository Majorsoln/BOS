"""
BOS Engine Registry — Contract Tests
=======================================
Tests for EngineContract validation rules.

Covers:
- Valid contract creation
- Namespace enforcement (first segment must match engine_name)
- engine.domain.action format enforcement
- Self-subscription prevention
- Frozen immutability
- Edge cases
"""

import pytest

from core.engines.contracts import (
    EngineContract,
    _validate_event_type_format,
    _validate_namespace_ownership,
)


# ══════════════════════════════════════════════════════════════
# VALID CONTRACT CREATION
# ══════════════════════════════════════════════════════════════

class TestValidContracts:
    """Happy path — valid contract creation."""

    def test_basic_contract(self):
        contract = EngineContract(
            engine_name="inventory",
            owned_event_types=frozenset({
                "inventory.stock.moved",
                "inventory.stock.adjusted",
            }),
            subscribed_event_types=frozenset({
                "procurement.order.received",
            }),
        )
        assert contract.engine_name == "inventory"
        assert len(contract.owned_event_types) == 2
        assert len(contract.subscribed_event_types) == 1

    def test_contract_with_no_subscriptions(self):
        contract = EngineContract(
            engine_name="cash",
            owned_event_types=frozenset({
                "cash.session.opened",
                "cash.session.closed",
            }),
            subscribed_event_types=frozenset(),
        )
        assert len(contract.subscribed_event_types) == 0

    def test_contract_with_empty_owned(self):
        """Engine that only subscribes (e.g. BI engine)."""
        contract = EngineContract(
            engine_name="bi",
            owned_event_types=frozenset(),
            subscribed_event_types=frozenset({
                "retail.sale.completed",
                "inventory.stock.moved",
            }),
        )
        assert len(contract.owned_event_types) == 0
        assert len(contract.subscribed_event_types) == 2

    def test_contract_is_frozen(self):
        contract = EngineContract(
            engine_name="retail",
            owned_event_types=frozenset({"retail.sale.completed"}),
            subscribed_event_types=frozenset(),
        )
        with pytest.raises(AttributeError):
            contract.engine_name = "hacked"

    def test_four_segment_event_type(self):
        """More than 3 segments is valid."""
        contract = EngineContract(
            engine_name="inventory",
            owned_event_types=frozenset({
                "inventory.stock.transfer.initiated",
            }),
            subscribed_event_types=frozenset(),
        )
        assert "inventory.stock.transfer.initiated" in contract.owned_event_types


# ══════════════════════════════════════════════════════════════
# INVALID ENGINE NAME
# ══════════════════════════════════════════════════════════════

class TestInvalidEngineName:
    """Engine name validation."""

    def test_empty_engine_name(self):
        with pytest.raises(ValueError, match="non-empty string"):
            EngineContract(
                engine_name="",
                owned_event_types=frozenset(),
                subscribed_event_types=frozenset(),
            )

    def test_none_engine_name(self):
        with pytest.raises(ValueError):
            EngineContract(
                engine_name=None,
                owned_event_types=frozenset(),
                subscribed_event_types=frozenset(),
            )

    def test_dotted_engine_name(self):
        with pytest.raises(ValueError, match="without dots"):
            EngineContract(
                engine_name="my.engine",
                owned_event_types=frozenset(),
                subscribed_event_types=frozenset(),
            )

    def test_blank_engine_name(self):
        with pytest.raises(ValueError, match="must not be blank"):
            EngineContract(
                engine_name="   ",
                owned_event_types=frozenset(),
                subscribed_event_types=frozenset(),
            )


# ══════════════════════════════════════════════════════════════
# NAMESPACE ENFORCEMENT (first segment must match engine)
# ══════════════════════════════════════════════════════════════

class TestNamespaceEnforcement:
    """First segment of event_type MUST match engine_name."""

    def test_namespace_mismatch_in_owned(self):
        """inventory engine cannot own cash.session.opened."""
        with pytest.raises(ValueError, match="namespace.*does not match"):
            EngineContract(
                engine_name="inventory",
                owned_event_types=frozenset({
                    "cash.session.opened",
                }),
                subscribed_event_types=frozenset(),
            )

    def test_namespace_match_passes(self):
        contract = EngineContract(
            engine_name="retail",
            owned_event_types=frozenset({
                "retail.sale.completed",
                "retail.cart.created",
            }),
            subscribed_event_types=frozenset(),
        )
        assert len(contract.owned_event_types) == 2

    def test_helper_namespace_validation(self):
        """Direct test of _validate_namespace_ownership."""
        # Should pass
        _validate_namespace_ownership("inventory.stock.moved", "inventory")

        # Should fail
        with pytest.raises(ValueError, match="namespace"):
            _validate_namespace_ownership("cash.session.opened", "inventory")


# ══════════════════════════════════════════════════════════════
# EVENT TYPE FORMAT ENFORCEMENT
# ══════════════════════════════════════════════════════════════

class TestEventTypeFormat:
    """engine.domain.action format enforcement."""

    def test_two_segments_rejected(self):
        with pytest.raises(ValueError, match="engine.domain.action"):
            EngineContract(
                engine_name="inventory",
                owned_event_types=frozenset({"inventory.stock"}),
                subscribed_event_types=frozenset(),
            )

    def test_one_segment_rejected(self):
        with pytest.raises(ValueError, match="engine.domain.action"):
            EngineContract(
                engine_name="inventory",
                owned_event_types=frozenset({"inventory"}),
                subscribed_event_types=frozenset(),
            )

    def test_empty_event_type_rejected(self):
        with pytest.raises(ValueError, match="non-empty string"):
            EngineContract(
                engine_name="inventory",
                owned_event_types=frozenset({""}),
                subscribed_event_types=frozenset(),
            )

    def test_bad_format_in_subscriptions(self):
        with pytest.raises(ValueError, match="engine.domain.action"):
            EngineContract(
                engine_name="inventory",
                owned_event_types=frozenset(),
                subscribed_event_types=frozenset({"bad.format"}),
            )

    def test_empty_segment_rejected(self):
        with pytest.raises(ValueError, match="empty segment"):
            EngineContract(
                engine_name="inventory",
                owned_event_types=frozenset({"inventory..moved"}),
                subscribed_event_types=frozenset(),
            )

    def test_helper_format_validation(self):
        """Direct test of _validate_event_type_format."""
        _validate_event_type_format("inventory.stock.moved")
        _validate_event_type_format("cash.session.opened")

        with pytest.raises(ValueError):
            _validate_event_type_format("twoparts.only")


# ══════════════════════════════════════════════════════════════
# SELF-SUBSCRIPTION PREVENTION
# ══════════════════════════════════════════════════════════════

class TestSelfSubscription:
    """Engine must not subscribe to its own events in contract."""

    def test_self_subscription_rejected(self):
        with pytest.raises(ValueError, match="own event types"):
            EngineContract(
                engine_name="inventory",
                owned_event_types=frozenset({
                    "inventory.stock.moved",
                }),
                subscribed_event_types=frozenset({
                    "inventory.stock.moved",
                }),
            )

    def test_partial_self_subscription_rejected(self):
        """Even one overlap is a violation."""
        with pytest.raises(ValueError, match="own event types"):
            EngineContract(
                engine_name="inventory",
                owned_event_types=frozenset({
                    "inventory.stock.moved",
                    "inventory.stock.adjusted",
                }),
                subscribed_event_types=frozenset({
                    "inventory.stock.moved",
                    "procurement.order.received",
                }),
            )

    def test_no_overlap_passes(self):
        contract = EngineContract(
            engine_name="inventory",
            owned_event_types=frozenset({
                "inventory.stock.moved",
            }),
            subscribed_event_types=frozenset({
                "procurement.order.received",
            }),
        )
        assert contract is not None


# ══════════════════════════════════════════════════════════════
# TYPE ENFORCEMENT
# ══════════════════════════════════════════════════════════════

class TestTypeEnforcement:
    """owned_event_types and subscribed_event_types must be frozensets."""

    def test_owned_not_frozenset_rejected(self):
        with pytest.raises(TypeError, match="frozenset"):
            EngineContract(
                engine_name="inventory",
                owned_event_types={"inventory.stock.moved"},
                subscribed_event_types=frozenset(),
            )

    def test_subscribed_not_frozenset_rejected(self):
        with pytest.raises(TypeError, match="frozenset"):
            EngineContract(
                engine_name="inventory",
                owned_event_types=frozenset(),
                subscribed_event_types={"cash.session.opened"},
            )
