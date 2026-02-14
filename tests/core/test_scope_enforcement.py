from __future__ import annotations

import sys
import types
import uuid
from datetime import datetime, timezone

models_stub = types.ModuleType("core.event_store.models")


class ActorType:
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"
    DEVICE = "DEVICE"
    AI = "AI"
    choices = (
        (HUMAN, "Human"),
        (SYSTEM, "System"),
        (DEVICE, "Device"),
        (AI, "AI"),
    )


class EventStatus:
    FINAL = "FINAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    choices = (
        (FINAL, "Final"),
        (REVIEW_REQUIRED, "Review Required"),
    )


models_stub.ActorType = ActorType
models_stub.EventStatus = EventStatus
sys.modules["core.event_store.models"] = models_stub

from core.context.scope import (
    SCOPE_BRANCH_REQUIRED,
    SCOPE_BUSINESS_ALLOWED,
)
from core.event_store.validators.event_validator import validate_event
from core.event_store.validators.registry import EventTypeRegistry


BUSINESS_ID = uuid.uuid4()
OTHER_BUSINESS_ID = uuid.uuid4()
CONTEXT_BRANCH_ID = uuid.uuid4()
EVENT_BRANCH_ID = uuid.uuid4()


class StubContext:
    def __init__(
        self,
        active: bool = True,
        business_id: uuid.UUID = BUSINESS_ID,
        branch_id: uuid.UUID | None = CONTEXT_BRANCH_ID,
    ):
        self._active = active
        self._business_id = business_id
        self._branch_id = branch_id

    def has_active_context(self) -> bool:
        return self._active

    def get_active_business_id(self):
        return self._business_id

    def get_active_branch_id(self):
        return self._branch_id

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        return True


def _event_data(
    business_id: uuid.UUID = BUSINESS_ID,
    branch_id: uuid.UUID | None = EVENT_BRANCH_ID,
) -> dict:
    return {
        "event_id": uuid.uuid4(),
        "event_type": "inventory.stock.moved",
        "event_version": 1,
        "business_id": business_id,
        "branch_id": branch_id,
        "source_engine": "inventory",
        "actor_type": "HUMAN",
        "actor_id": "user-1",
        "correlation_id": uuid.uuid4(),
        "payload": {"sku": "A", "qty": 1},
        "created_at": datetime.now(timezone.utc),
    }


def _registry() -> EventTypeRegistry:
    registry = EventTypeRegistry()
    registry.register("inventory.stock.moved")
    return registry


def test_event_without_business_id_rejected():
    event_data = _event_data()
    event_data.pop("business_id")

    result = validate_event(
        event_data=event_data,
        context=StubContext(),
        registry=_registry(),
        scope_requirement=SCOPE_BUSINESS_ALLOWED,
    )

    assert not result.accepted
    assert result.rejection.code == "MISSING_FIELD"


def test_cross_business_event_rejected():
    result = validate_event(
        event_data=_event_data(business_id=OTHER_BUSINESS_ID),
        context=StubContext(business_id=BUSINESS_ID),
        registry=_registry(),
        scope_requirement=SCOPE_BUSINESS_ALLOWED,
    )

    assert not result.accepted
    assert result.rejection.code == "BUSINESS_ID_MISMATCH"


def test_branch_required_missing_rejected():
    result = validate_event(
        event_data=_event_data(branch_id=None),
        context=StubContext(branch_id=CONTEXT_BRANCH_ID),
        registry=_registry(),
        scope_requirement=SCOPE_BRANCH_REQUIRED,
    )

    assert not result.accepted
    assert result.rejection.code == "BRANCH_REQUIRED_MISSING"


def test_branch_required_mismatch_rejected():
    result = validate_event(
        event_data=_event_data(branch_id=EVENT_BRANCH_ID),
        context=StubContext(branch_id=CONTEXT_BRANCH_ID),
        registry=_registry(),
        scope_requirement=SCOPE_BRANCH_REQUIRED,
    )

    assert not result.accepted
    assert result.rejection.code == "BRANCH_SCOPE_MISMATCH"


def test_business_allowed_does_not_enforce_branch_equality():
    result = validate_event(
        event_data=_event_data(branch_id=EVENT_BRANCH_ID),
        context=StubContext(branch_id=CONTEXT_BRANCH_ID),
        registry=_registry(),
        scope_requirement=SCOPE_BUSINESS_ALLOWED,
    )

    assert result.accepted
