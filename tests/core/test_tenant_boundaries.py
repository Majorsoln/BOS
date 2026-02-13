from __future__ import annotations

import uuid
from datetime import datetime, timezone

from core.event_store.validators.event_validator import validate_event
from core.event_store.validators.errors import RejectionCode


class StubContext:
    def __init__(self, business_id: uuid.UUID, branch_id=None, active=True):
        self._business_id = business_id
        self._branch_id = branch_id
        self._active = active

    def has_active_context(self):
        return self._active

    def get_active_business_id(self):
        return self._business_id

    def get_active_branch_id(self):
        return self._branch_id

    def is_branch_in_business(self, branch_id, business_id):
        return business_id == self._business_id


class StubRegistry:
    def is_registered(self, event_type: str) -> bool:
        return event_type == "inventory.stock.moved"


def base_event_data(business_id: uuid.UUID):
    return {
        "event_id": uuid.uuid4(),
        "event_type": "inventory.stock.moved",
        "event_version": 1,
        "business_id": business_id,
        "branch_id": None,
        "source_engine": "inventory",
        "actor_type": "HUMAN",
        "actor_id": "user-1",
        "correlation_id": uuid.uuid4(),
        "payload": {"sku": "A"},
        "created_at": datetime.now(timezone.utc),
        "status": "FINAL",
        "correction_of": None,
    }


def test_event_rejected_when_branch_scope_field_missing():
    business_id = uuid.uuid4()
    context = StubContext(business_id=business_id)
    event_data = base_event_data(business_id)
    del event_data["branch_id"]

    result = validate_event(event_data, context, StubRegistry())

    assert not result.accepted
    assert result.rejection.code == RejectionCode.MISSING_FIELD


def test_event_rejected_when_branch_scope_mismatch():
    business_id = uuid.uuid4()
    branch_a = uuid.uuid4()
    branch_b = uuid.uuid4()
    context = StubContext(business_id=business_id, branch_id=branch_a)
    event_data = base_event_data(business_id)
    event_data["branch_id"] = branch_b

    result = validate_event(event_data, context, StubRegistry())

    assert not result.accepted
    assert result.rejection.code == RejectionCode.BRANCH_SCOPE_MISMATCH

