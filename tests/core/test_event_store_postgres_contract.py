from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from core.context.business_context import BusinessContext
from core.event_store.hashing.hasher import GENESIS_HASH, compute_event_hash
from core.event_store.models import Event
from core.event_store.persistence import load_events_for_business, persist_event
from core.event_store.validators.registry import EventTypeRegistry

pytestmark = pytest.mark.django_db(transaction=True)


EVENT_TYPE = "admin.feature_flag.set.v1"


def _build_registry() -> EventTypeRegistry:
    registry = EventTypeRegistry()
    registry.register(EVENT_TYPE)
    return registry


def _build_event(
    *,
    event_id: uuid.UUID,
    business_id: uuid.UUID,
    correlation_id: uuid.UUID,
    created_at: datetime,
    payload: dict | None = None,
) -> dict:
    return {
        "event_id": event_id,
        "event_type": EVENT_TYPE,
        "event_version": 1,
        "business_id": business_id,
        "branch_id": None,
        "source_engine": "admin",
        "actor_type": "SYSTEM",
        "actor_id": "test-system",
        "correlation_id": correlation_id,
        "causation_id": None,
        "payload": payload or {"flag_key": "ENABLE_DOCUMENT_DESIGNER", "status": "ENABLED"},
        "reference": {},
        "created_at": created_at,
        "status": "FINAL",
        "correction_of": None,
    }


def test_lawful_persist_event_import_path_exists_and_callable() -> None:
    assert callable(persist_event)


def test_first_persisted_event_uses_genesis_previous_hash() -> None:
    business_id = uuid.uuid4()
    context = BusinessContext(business_id=business_id)
    registry = _build_registry()
    correlation_id = uuid.uuid4()
    event = _build_event(
        event_id=uuid.uuid4(),
        business_id=business_id,
        correlation_id=correlation_id,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    result = persist_event(
        event_data=event,
        context=context,
        registry=registry,
    )

    assert result.accepted
    stored = Event.objects.get(event_id=event["event_id"])
    assert stored.previous_event_hash == GENESIS_HASH
    assert stored.event_hash == compute_event_hash(event["payload"], GENESIS_HASH)


def test_second_event_links_to_first_hash() -> None:
    business_id = uuid.uuid4()
    context = BusinessContext(business_id=business_id)
    registry = _build_registry()
    correlation_id = uuid.uuid4()
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

    first_event = _build_event(
        event_id=uuid.uuid4(),
        business_id=business_id,
        correlation_id=correlation_id,
        created_at=t0,
        payload={"step": 1},
    )
    second_event = _build_event(
        event_id=uuid.uuid4(),
        business_id=business_id,
        correlation_id=correlation_id,
        created_at=t0 + timedelta(seconds=1),
        payload={"step": 2},
    )

    first_result = persist_event(
        event_data=first_event,
        context=context,
        registry=registry,
    )
    second_result = persist_event(
        event_data=second_event,
        context=context,
        registry=registry,
    )

    assert first_result.accepted
    assert second_result.accepted

    first_row = Event.objects.get(event_id=first_event["event_id"])
    second_row = Event.objects.get(event_id=second_event["event_id"])
    assert second_row.previous_event_hash == first_row.event_hash


def test_loader_returns_deterministic_created_at_then_event_id_order() -> None:
    business_id = uuid.uuid4()
    context = BusinessContext(business_id=business_id)
    registry = _build_registry()
    correlation_id = uuid.uuid4()
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

    first_event = _build_event(
        event_id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
        business_id=business_id,
        correlation_id=correlation_id,
        created_at=t0,
        payload={"step": 1},
    )
    second_event = _build_event(
        event_id=uuid.UUID("10000000-0000-0000-0000-000000000002"),
        business_id=business_id,
        correlation_id=correlation_id,
        created_at=t0 + timedelta(seconds=1),
        payload={"step": 2},
    )
    third_event = _build_event(
        event_id=uuid.UUID("10000000-0000-0000-0000-000000000003"),
        business_id=business_id,
        correlation_id=correlation_id,
        created_at=t0 + timedelta(seconds=2),
        payload={"step": 3},
    )

    for event_data in (first_event, second_event, third_event):
        result = persist_event(
            event_data=event_data,
            context=context,
            registry=registry,
        )
        assert result.accepted

    loaded = load_events_for_business(business_id)
    loaded_ids = tuple(item["event_id"] for item in loaded)
    assert loaded_ids == (
        first_event["event_id"],
        second_event["event_id"],
        third_event["event_id"],
    )


def test_db_row_contains_expected_envelope_fields() -> None:
    business_id = uuid.uuid4()
    context = BusinessContext(business_id=business_id)
    registry = _build_registry()
    event = _build_event(
        event_id=uuid.uuid4(),
        business_id=business_id,
        correlation_id=uuid.uuid4(),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    result = persist_event(
        event_data=event,
        context=context,
        registry=registry,
    )
    assert result.accepted

    row = Event.objects.values(
        "event_id",
        "event_type",
        "event_version",
        "business_id",
        "branch_id",
        "source_engine",
        "actor_type",
        "actor_id",
        "correlation_id",
        "causation_id",
        "payload",
        "reference",
        "created_at",
        "status",
        "correction_of",
        "previous_event_hash",
        "event_hash",
    ).get(event_id=event["event_id"])

    expected_fields = {
        "event_id",
        "event_type",
        "event_version",
        "business_id",
        "branch_id",
        "source_engine",
        "actor_type",
        "actor_id",
        "correlation_id",
        "causation_id",
        "payload",
        "reference",
        "created_at",
        "status",
        "correction_of",
        "previous_event_hash",
        "event_hash",
    }
    assert set(row.keys()) == expected_fields
