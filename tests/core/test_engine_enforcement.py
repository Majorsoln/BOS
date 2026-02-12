"""
BOS Engine Registry — Enforcement Tests
==========================================
Tests for runtime contract enforcement.

Covers:
- Wrong ownership → EmissionViolation
- Cross-write attempt → EmissionViolation
- Unregistered engine → UnregisteredEngineViolation
- Unknown event type → UnknownEventTypeViolation
- Undeclared subscription → SubscriptionViolation
- Registry not locked → RegistryNotLockedError
- Enforced wrappers (persist + subscribe)
- Self-subscription override
- Happy path (valid emission + subscription)
"""

import pytest

from core.engines.contracts import EngineContract
from core.engines.registry import (
    EngineRegistry,
    RegistryNotLockedError,
)
from core.engines.enforcement import (
    EmissionViolation,
    EngineContractViolation,
    SubscriptionViolation,
    UnknownEventTypeViolation,
    UnregisteredEngineViolation,
    enforce_emission,
    enforce_subscription,
    enforced_register_subscriber,
)
from core.events.registry import SubscriberRegistry


# ══════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def engine_registry():
    """Locked registry with 3 engines for enforcement testing."""
    reg = EngineRegistry()

    reg.register_engine(EngineContract(
        engine_name="inventory",
        owned_event_types=frozenset({
            "inventory.stock.moved",
            "inventory.stock.adjusted",
        }),
        subscribed_event_types=frozenset({
            "retail.sale.completed",
        }),
    ))

    reg.register_engine(EngineContract(
        engine_name="retail",
        owned_event_types=frozenset({
            "retail.sale.completed",
            "retail.cart.created",
        }),
        subscribed_event_types=frozenset({
            "inventory.stock.moved",
        }),
    ))

    reg.register_engine(EngineContract(
        engine_name="cash",
        owned_event_types=frozenset({
            "cash.session.opened",
            "cash.session.closed",
        }),
        subscribed_event_types=frozenset({
            "retail.sale.completed",
        }),
    ))

    reg.lock()
    return reg


@pytest.fixture
def subscriber_registry():
    return SubscriberRegistry()


# ══════════════════════════════════════════════════════════════
# EMISSION ENFORCEMENT — HAPPY PATH
# ══════════════════════════════════════════════════════════════

class TestEmissionHappyPath:
    """Valid emission — engine emits its own event."""

    def test_inventory_emits_own_event(self, engine_registry):
        # Should not raise
        enforce_emission(
            source_engine="inventory",
            event_type="inventory.stock.moved",
            engine_registry=engine_registry,
        )

    def test_retail_emits_own_event(self, engine_registry):
        enforce_emission(
            source_engine="retail",
            event_type="retail.sale.completed",
            engine_registry=engine_registry,
        )

    def test_cash_emits_own_event(self, engine_registry):
        enforce_emission(
            source_engine="cash",
            event_type="cash.session.opened",
            engine_registry=engine_registry,
        )


# ══════════════════════════════════════════════════════════════
# EMISSION ENFORCEMENT — CROSS-WRITE VIOLATIONS
# ══════════════════════════════════════════════════════════════

class TestCrossWriteViolation:
    """Engine attempts to emit another engine's event → BLOCKED."""

    def test_inventory_cannot_emit_cash_event(self, engine_registry):
        with pytest.raises(EmissionViolation) as exc_info:
            enforce_emission(
                source_engine="inventory",
                event_type="cash.session.opened",
                engine_registry=engine_registry,
            )
        assert exc_info.value.source_engine == "inventory"
        assert exc_info.value.event_type == "cash.session.opened"
        assert exc_info.value.owner == "cash"

    def test_cash_cannot_emit_retail_event(self, engine_registry):
        with pytest.raises(EmissionViolation) as exc_info:
            enforce_emission(
                source_engine="cash",
                event_type="retail.sale.completed",
                engine_registry=engine_registry,
            )
        assert exc_info.value.owner == "retail"

    def test_retail_cannot_emit_inventory_event(self, engine_registry):
        with pytest.raises(EmissionViolation):
            enforce_emission(
                source_engine="retail",
                event_type="inventory.stock.moved",
                engine_registry=engine_registry,
            )

    def test_emission_violation_is_contract_violation(self, engine_registry):
        """EmissionViolation inherits from EngineContractViolation."""
        with pytest.raises(EngineContractViolation):
            enforce_emission(
                source_engine="cash",
                event_type="inventory.stock.moved",
                engine_registry=engine_registry,
            )


# ══════════════════════════════════════════════════════════════
# EMISSION ENFORCEMENT — UNREGISTERED ENGINE
# ══════════════════════════════════════════════════════════════

class TestUnregisteredEngine:
    """Unknown engine attempts to emit → BLOCKED."""

    def test_ghost_engine_emission(self, engine_registry):
        with pytest.raises(UnregisteredEngineViolation) as exc_info:
            enforce_emission(
                source_engine="ghost",
                event_type="inventory.stock.moved",
                engine_registry=engine_registry,
            )
        assert exc_info.value.engine_name == "ghost"

    def test_ghost_engine_subscription(self, engine_registry):
        with pytest.raises(UnregisteredEngineViolation):
            enforce_subscription(
                subscriber_engine="ghost",
                event_type="inventory.stock.moved",
                engine_registry=engine_registry,
            )


# ══════════════════════════════════════════════════════════════
# EMISSION ENFORCEMENT — UNKNOWN EVENT TYPE
# ══════════════════════════════════════════════════════════════

class TestUnknownEventType:
    """Engine attempts to emit/subscribe to unregistered event type."""

    def test_emit_unknown_event_type(self, engine_registry):
        with pytest.raises(UnknownEventTypeViolation) as exc_info:
            enforce_emission(
                source_engine="inventory",
                event_type="inventory.warehouse.created",
                engine_registry=engine_registry,
            )
        assert exc_info.value.event_type == "inventory.warehouse.created"

    def test_subscribe_unknown_event_type(self, engine_registry):
        with pytest.raises(UnknownEventTypeViolation):
            enforce_subscription(
                subscriber_engine="inventory",
                event_type="accounting.entry.posted",
                engine_registry=engine_registry,
            )


# ══════════════════════════════════════════════════════════════
# EMISSION ENFORCEMENT — REGISTRY NOT LOCKED
# ══════════════════════════════════════════════════════════════

class TestRegistryNotLocked:
    """Enforcement requires locked registry."""

    def test_emission_before_lock(self):
        reg = EngineRegistry()
        reg.register_engine(EngineContract(
            engine_name="test",
            owned_event_types=frozenset({"test.thing.done"}),
            subscribed_event_types=frozenset(),
        ))

        with pytest.raises(RegistryNotLockedError):
            enforce_emission(
                source_engine="test",
                event_type="test.thing.done",
                engine_registry=reg,
            )

    def test_subscription_before_lock(self):
        reg = EngineRegistry()
        reg.register_engine(EngineContract(
            engine_name="test",
            owned_event_types=frozenset({"test.thing.done"}),
            subscribed_event_types=frozenset(),
        ))

        with pytest.raises(RegistryNotLockedError):
            enforce_subscription(
                subscriber_engine="test",
                event_type="test.thing.done",
                engine_registry=reg,
            )


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION ENFORCEMENT — HAPPY PATH
# ══════════════════════════════════════════════════════════════

class TestSubscriptionHappyPath:
    """Valid subscription — engine subscribes to declared event."""

    def test_inventory_subscribes_to_retail(self, engine_registry):
        enforce_subscription(
            subscriber_engine="inventory",
            event_type="retail.sale.completed",
            engine_registry=engine_registry,
        )

    def test_retail_subscribes_to_inventory(self, engine_registry):
        enforce_subscription(
            subscriber_engine="retail",
            event_type="inventory.stock.moved",
            engine_registry=engine_registry,
        )


# ══════════════════════════════════════════════════════════════
# SUBSCRIPTION ENFORCEMENT — UNDECLARED
# ══════════════════════════════════════════════════════════════

class TestUndeclaredSubscription:
    """Engine subscribes to event not in its contract → BLOCKED."""

    def test_inventory_not_declared_cash_subscription(
        self, engine_registry
    ):
        """inventory didn't declare subscription to cash events."""
        with pytest.raises(SubscriptionViolation) as exc_info:
            enforce_subscription(
                subscriber_engine="inventory",
                event_type="cash.session.opened",
                engine_registry=engine_registry,
            )
        assert exc_info.value.subscriber_engine == "inventory"
        assert exc_info.value.event_type == "cash.session.opened"

    def test_cash_not_declared_inventory_subscription(
        self, engine_registry
    ):
        """cash didn't declare subscription to inventory events."""
        with pytest.raises(SubscriptionViolation):
            enforce_subscription(
                subscriber_engine="cash",
                event_type="inventory.stock.moved",
                engine_registry=engine_registry,
            )


# ══════════════════════════════════════════════════════════════
# ENFORCED SUBSCRIBER REGISTRATION
# ══════════════════════════════════════════════════════════════

class TestEnforcedSubscriberRegistration:
    """Enforced wrapper around SubscriberRegistry."""

    def test_valid_subscription_registered(
        self, engine_registry, subscriber_registry
    ):
        def handler(event):
            pass

        enforced_register_subscriber(
            subscriber_registry=subscriber_registry,
            engine_registry=engine_registry,
            event_type="retail.sale.completed",
            handler=handler,
            subscriber_engine="inventory",
        )

        assert subscriber_registry.has_subscribers(
            "retail.sale.completed"
        )

    def test_undeclared_subscription_blocked(
        self, engine_registry, subscriber_registry
    ):
        def handler(event):
            pass

        with pytest.raises(SubscriptionViolation):
            enforced_register_subscriber(
                subscriber_registry=subscriber_registry,
                engine_registry=engine_registry,
                event_type="cash.session.opened",
                handler=handler,
                subscriber_engine="inventory",
            )

        # Handler should NOT be registered
        assert not subscriber_registry.has_subscribers(
            "cash.session.opened"
        )

    def test_self_subscription_override(
        self, engine_registry, subscriber_registry
    ):
        """
        Self-subscription with explicit override.
        Engine subscribes to its OWN event type.
        Normally blocked by SubscriberRegistry, but allowed
        with allow_self_subscription=True.
        """
        def handler(event):
            pass

        enforced_register_subscriber(
            subscriber_registry=subscriber_registry,
            engine_registry=engine_registry,
            event_type="inventory.stock.moved",
            handler=handler,
            subscriber_engine="inventory",
            allow_self_subscription=True,
        )

        assert subscriber_registry.has_subscribers(
            "inventory.stock.moved"
        )


# ══════════════════════════════════════════════════════════════
# ERROR HIERARCHY
# ══════════════════════════════════════════════════════════════

class TestErrorHierarchy:
    """All enforcement errors inherit from EngineContractViolation."""

    def test_emission_violation_hierarchy(self):
        err = EmissionViolation("a", "b.c.d", "e")
        assert isinstance(err, EngineContractViolation)
        assert isinstance(err, Exception)

    def test_subscription_violation_hierarchy(self):
        err = SubscriptionViolation("a", "b.c.d")
        assert isinstance(err, EngineContractViolation)

    def test_unknown_event_violation_hierarchy(self):
        err = UnknownEventTypeViolation("b.c.d")
        assert isinstance(err, EngineContractViolation)

    def test_unregistered_engine_violation_hierarchy(self):
        err = UnregisteredEngineViolation("ghost")
        assert isinstance(err, EngineContractViolation)


# ══════════════════════════════════════════════════════════════
# STUB for EventTypeRegistry (avoids Django import chain)
# ══════════════════════════════════════════════════════════════

class _StubEventTypeRegistry:
    """Lightweight stub matching EventTypeRegistry interface."""

    def __init__(self):
        self._registered = set()

    def register(self, event_type: str) -> None:
        self._registered.add(event_type)

    def is_registered(self, event_type: str) -> bool:
        return event_type in self._registered

    def get_all_registered(self) -> frozenset:
        return frozenset(self._registered)


# ══════════════════════════════════════════════════════════════
# INTEGRATION: FULL FLOW
# ══════════════════════════════════════════════════════════════

class TestFullEnforcementFlow:
    """End-to-end enforcement scenario."""

    def test_complete_bootstrap_and_enforcement(self):
        """
        Simulate real bootstrap:
        1. Create registry
        2. Register engines
        3. Lock
        4. Populate EventTypeRegistry
        5. Enforce emission (valid + invalid)
        6. Enforce subscription (valid + invalid)
        """
        # ── 1. Create registries ──────────────────────────────
        engine_reg = EngineRegistry()
        event_type_reg = _StubEventTypeRegistry()
        sub_reg = SubscriberRegistry()

        # ── 2. Register engines ───────────────────────────────
        engine_reg.register_engine(EngineContract(
            engine_name="retail",
            owned_event_types=frozenset({
                "retail.sale.completed",
                "retail.cart.created",
            }),
            subscribed_event_types=frozenset({
                "inventory.stock.moved",
            }),
        ))

        engine_reg.register_engine(EngineContract(
            engine_name="inventory",
            owned_event_types=frozenset({
                "inventory.stock.moved",
                "inventory.stock.adjusted",
            }),
            subscribed_event_types=frozenset({
                "retail.sale.completed",
            }),
        ))

        # ── 3. Lock ───────────────────────────────────────────
        engine_reg.lock()
        assert engine_reg.is_locked

        # ── 4. Populate EventTypeRegistry ─────────────────────
        count = engine_reg.populate_event_type_registry(event_type_reg)
        assert count == 4
        assert event_type_reg.is_registered("retail.sale.completed")
        assert event_type_reg.is_registered("inventory.stock.moved")

        # ── 5. Enforce emission ───────────────────────────────
        # Valid
        enforce_emission("retail", "retail.sale.completed", engine_reg)

        # Invalid — cross-write
        with pytest.raises(EmissionViolation):
            enforce_emission(
                "retail", "inventory.stock.moved", engine_reg
            )

        # ── 6. Enforce subscription ───────────────────────────
        def on_sale(event):
            pass

        def on_stock(event):
            pass

        # Valid
        enforced_register_subscriber(
            subscriber_registry=sub_reg,
            engine_registry=engine_reg,
            event_type="retail.sale.completed",
            handler=on_sale,
            subscriber_engine="inventory",
        )

        # Invalid — undeclared
        with pytest.raises(SubscriptionViolation):
            enforced_register_subscriber(
                subscriber_registry=sub_reg,
                engine_registry=engine_reg,
                event_type="inventory.stock.adjusted",
                handler=on_stock,
                subscriber_engine="retail",
            )

        # Verify final state
        assert sub_reg.has_subscribers("retail.sale.completed")
        assert not sub_reg.has_subscribers("inventory.stock.adjusted")
