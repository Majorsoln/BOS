# BOS Engine Development Guide

> Version: 1.0
> Audience: Developers creating new business engines

---

## 1. What Is an Engine?

An engine is a self-contained business domain module that:
- Handles a specific business function (retail, accounting, HR, etc.)
- Communicates with other engines **only via events**
- Maintains its own projection store (in-memory read model)
- Enforces scope guards (business/branch isolation)
- Is wrapped behind a feature flag

---

## 2. Canonical Engine Structure

```
engines/<name>/
├── __init__.py              # Empty
├── events.py                # Event type constants + payload builders
├── commands/
│   └── __init__.py          # Frozen request dataclasses with to_command()
├── services/
│   └── __init__.py          # <Name>Service + <Name>ProjectionStore
├── policies/
│   └── __init__.py          # Policy functions → Optional[RejectionReason]
└── subscriptions.py         # Cross-engine event subscriptions
```

---

## 3. Step-by-Step: Creating a New Engine

### 3.1 Define Event Types (`events.py`)

```python
"""
BOS <Name> Engine — Event Types
"""

# Event type constants (format: engine.domain.action.vN)
ORDER_CREATED_V1 = "logistics.order.created.v1"
ORDER_DISPATCHED_V1 = "logistics.order.dispatched.v1"
ORDER_DELIVERED_V1 = "logistics.order.delivered.v1"

ALL_EVENT_TYPES = (
    ORDER_CREATED_V1,
    ORDER_DISPATCHED_V1,
    ORDER_DELIVERED_V1,
)


def _order_created_payload(data: dict) -> dict:
    return {
        "order_id": data["order_id"],
        "business_id": data["business_id"],
        "branch_id": data.get("branch_id"),
        "items": data.get("items", []),
        "created_at": data["issued_at"],
    }


# Event type → payload builder mapping
PAYLOAD_BUILDERS = {
    ORDER_CREATED_V1: _order_created_payload,
    ORDER_DISPATCHED_V1: lambda d: d,
    ORDER_DELIVERED_V1: lambda d: d,
}


def register_logistics_event_types(registry):
    """Register all event types with the global registry."""
    for event_type, builder in PAYLOAD_BUILDERS.items():
        registry.register(event_type, builder)


def resolve_logistics_event_type(name: str):
    """Resolve event type name to payload builder."""
    return PAYLOAD_BUILDERS.get(name)
```

**Naming Convention:** `engine.domain.action.vN`
- `retail.sale.completed.v1`
- `accounting.journal.posted.v1`
- `hr.employee.onboarded.v1`

### 3.2 Define Commands (`commands/__init__.py`)

```python
"""
BOS <Name> Engine — Commands
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple


@dataclass(frozen=True)
class CreateOrderRequest:
    """Intent to create a logistics order."""
    business_id: uuid.UUID
    branch_id: uuid.UUID           # BRANCH_REQUIRED scope
    items: Tuple[dict, ...]
    actor_id: str
    issued_at: datetime
    source_engine: str = "logistics"

    def __post_init__(self):
        if not self.items:
            raise ValueError("Order must have at least one item.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")

    def to_command(self) -> dict:
        """Convert to Command Bus payload."""
        return {
            "command_type": "logistics.order.create.request",
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "payload": {
                "items": list(self.items),
            },
        }
```

**Rules:**
- All commands are `@dataclass(frozen=True)` — immutable
- Include `source_engine` field
- Command type format: `engine.domain.action.request`
- Include `__post_init__` validation

### 3.3 Implement Service Layer (`services/__init__.py`)

```python
"""
BOS <Name> Engine — Service Layer
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.commands.rejection import RejectionReason
from core.context.scope_guard import enforce_scope, ScopeRequirement

from engines.logistics.events import (
    ORDER_CREATED_V1,
    ORDER_DISPATCHED_V1,
    ORDER_DELIVERED_V1,
)


# ── Projection Store ──────────────────────────────────

@dataclass(frozen=True)
class OrderRecord:
    order_id: uuid.UUID
    business_id: uuid.UUID
    branch_id: uuid.UUID
    status: str
    items: tuple
    created_at: datetime


class LogisticsProjectionStore:
    """In-memory projection of logistics orders."""

    def __init__(self):
        self._orders: Dict[uuid.UUID, OrderRecord] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == ORDER_CREATED_V1:
            order_id = uuid.UUID(str(payload["order_id"]))
            self._orders[order_id] = OrderRecord(
                order_id=order_id,
                business_id=uuid.UUID(str(payload["business_id"])),
                branch_id=uuid.UUID(str(payload["branch_id"])),
                status="CREATED",
                items=tuple(payload.get("items", [])),
                created_at=payload.get("created_at"),
            )
        elif event_type == ORDER_DISPATCHED_V1:
            order_id = uuid.UUID(str(payload["order_id"]))
            old = self._orders.get(order_id)
            if old:
                self._orders[order_id] = OrderRecord(
                    order_id=old.order_id,
                    business_id=old.business_id,
                    branch_id=old.branch_id,
                    status="DISPATCHED",
                    items=old.items,
                    created_at=old.created_at,
                )

    def get_order(self, order_id: uuid.UUID) -> Optional[OrderRecord]:
        return self._orders.get(order_id)

    def list_orders(self, business_id: uuid.UUID) -> List[OrderRecord]:
        return [o for o in self._orders.values() if o.business_id == business_id]

    def truncate(self):
        self._orders.clear()


# ── Service ───────────────────────────────────────────

class LogisticsService:
    """
    Logistics engine service.

    All mutations produce events.
    Scope guard is enforced first.
    """

    SCOPE_REQUIREMENT = ScopeRequirement.BRANCH_REQUIRED

    def __init__(
        self,
        *,
        event_factory,
        persist_event,
        event_type_registry,
        projection_store: LogisticsProjectionStore,
        feature_flag_evaluator=None,
    ):
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection = projection_store
        self._feature_flags = feature_flag_evaluator

    def _execute_command(self, command) -> dict:
        # SCOPE GUARD — always first
        enforce_scope(command, self.SCOPE_REQUIREMENT)

        handler = self._resolve_handler(command.command_type)
        if handler is None:
            return {"rejected": RejectionReason(
                code="UNKNOWN_COMMAND",
                message=f"Unknown command: {command.command_type}",
                policy_name="_execute_command",
            )}
        return handler(command)

    def _resolve_handler(self, command_type: str):
        handlers = {
            "logistics.order.create.request": self._handle_create_order,
        }
        return handlers.get(command_type)

    def _handle_create_order(self, command) -> dict:
        order_id = uuid.uuid4()
        event_data = {
            "order_id": str(order_id),
            "business_id": str(command.business_id),
            "branch_id": str(command.branch_id),
            "items": command.payload.get("items", []),
            "issued_at": command.issued_at,
        }
        event = self._event_factory.create(
            ORDER_CREATED_V1, event_data,
            command.business_id, command.branch_id,
        )
        self._persist_event(event)
        self._projection.apply(ORDER_CREATED_V1, event_data)
        return {"order_id": order_id, "status": "CREATED"}
```

**Critical Rules:**
1. `enforce_scope()` is **always the first call** in `_execute_command()`
2. Service receives dependencies via constructor injection
3. Events are persisted via `persist_event` (single write path)
4. Projection is updated after event is persisted

### 3.4 Define Policies (`policies/__init__.py`)

```python
"""
BOS <Name> Engine — Policies
"""

from typing import Optional
from core.commands.rejection import RejectionReason


def check_order_not_already_dispatched(
    order_status: str,
) -> Optional[RejectionReason]:
    """Order can only be dispatched once."""
    if order_status == "DISPATCHED":
        return RejectionReason(
            code="ORDER_ALREADY_DISPATCHED",
            message="Order has already been dispatched.",
            policy_name="check_order_not_already_dispatched",
        )
    return None
```

**Rules:**
- Policies return `Optional[RejectionReason]` — `None` means pass
- `policy_name` must match the function name
- Policies must NOT mutate state

### 3.5 Wire Subscriptions (`subscriptions.py`)

```python
"""
BOS <Name> Engine — Cross-Engine Subscriptions
"""

SUBSCRIPTIONS = {
    # React to inventory events
    "inventory.stock.received.v1": "on_stock_received",
}


class LogisticsSubscriptionHandler:
    """Handles events from other engines."""

    def __init__(self, projection_store):
        self._projection = projection_store

    def on_stock_received(self, event):
        """React to inventory receiving stock."""
        # Update local projection, emit follow-up events, etc.
        pass
```

### 3.6 Register Feature Flag

In your engine initialization:

```python
# Feature flag key convention: ENABLE_<ENGINE>_ENGINE
FEATURE_FLAG_KEY = "ENABLE_LOGISTICS_ENGINE"
```

Check flag before command execution:

```python
if self._feature_flags and not self._feature_flags.is_enabled(
    FEATURE_FLAG_KEY, command.business_id
):
    return {"rejected": RejectionReason(
        code="FEATURE_DISABLED",
        message="Logistics engine is not enabled.",
        policy_name="feature_flag_check",
    )}
```

---

## 4. Testing Your Engine

### 4.1 Test Structure

```
tests/engines/test_logistics_engine.py
```

### 4.2 Test Pattern

```python
import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from engines.logistics.events import register_logistics_event_types
from engines.logistics.services import LogisticsService, LogisticsProjectionStore


# ── Test Doubles ──

class StubEventTypeRegistry:
    def __init__(self): self._types = {}
    def register(self, name, factory): self._types[name] = factory
    def resolve(self, name): return self._types.get(name)

class StubEventFactory:
    def __init__(self, registry): self._registry = registry
    def create(self, event_type, payload, business_id, branch_id=None, actor_id=None):
        return {"event_type": event_type, "payload": payload, "business_id": business_id}

class StubPersistEvent:
    def __init__(self): self.events = []
    def __call__(self, event): self.events.append(event)


# ── Fixtures ──

BIZ_ID = uuid.uuid4()
BRANCH_ID = uuid.uuid4()
NOW = datetime(2025, 6, 1, 12, 0, 0)

@pytest.fixture
def service():
    registry = StubEventTypeRegistry()
    register_logistics_event_types(registry)
    projection = LogisticsProjectionStore()
    return LogisticsService(
        event_factory=StubEventFactory(registry),
        persist_event=StubPersistEvent(),
        event_type_registry=registry,
        projection_store=projection,
    )


# ── Tests ──

class TestLogisticsEngine:
    def test_create_order(self, service):
        command = MagicMock(
            command_type="logistics.order.create.request",
            business_id=BIZ_ID,
            branch_id=BRANCH_ID,
            payload={"items": [{"name": "Widget", "qty": 5}]},
            issued_at=NOW,
        )
        result = service._execute_command(command)
        assert "order_id" in result
        assert result["status"] == "CREATED"
```

### 4.3 What to Test

- Command execution produces events
- Projection updates correctly
- Invalid transitions are rejected
- Scope guard enforces branch requirements
- Feature flag blocks when disabled
- Deterministic replay (same inputs → same outputs)
- Tenant isolation (events scoped to business_id)

---

## 5. Scope Requirements

Determine if your engine operations need branch scope:

| Scope | When to Use | Example |
|-------|-------------|---------|
| `BUSINESS_SCOPE` | Administrative, aggregated ops | Journal entries, supplier registry |
| `BRANCH_REQUIRED` | Physical/operational ops | POS sale, cash drawer, stock movement |

Operations requiring `BRANCH_REQUIRED` (from scope-policy.md):
- Cash: drawer create, CashIn/CashOut, reconciliation
- Inventory: stock movements, transfers
- Retail: POS sale, refund
- Restaurant: table/order/kitchen/split billing
- Workshop: cutting optimization, material consumption

---

## 6. Naming Conventions

| Item | Pattern | Example |
|------|---------|---------|
| Event type | `engine.domain.action.vN` | `retail.sale.completed.v1` |
| Command type | `engine.domain.action.request` | `retail.sale.complete.request` |
| Feature flag | `ENABLE_<ENGINE>_ENGINE` | `ENABLE_RETAIL_ENGINE` |
| Module path | `engines/<name>/` | `engines/retail/` |
| Test file | `tests/engines/test_<name>_engine.py` | `tests/engines/test_retail_engine.py` |

---

## 7. Checklist Before Submitting a New Engine

- [ ] Events defined with versioned names (`*.v1`)
- [ ] Commands are frozen dataclasses with `__post_init__` validation
- [ ] Service has scope guard as first statement
- [ ] Feature flag wraps engine activation
- [ ] Policies return `Optional[RejectionReason]` with `policy_name`
- [ ] Projection store has `apply()`, `truncate()`, and query methods
- [ ] All tests pass
- [ ] Determinism verified (no `datetime.now()`, no `random()`)
- [ ] Multi-tenant isolation verified (`business_id` in every event)

---

*"Engines are isolated. Events are truth. Projections are disposable."*
