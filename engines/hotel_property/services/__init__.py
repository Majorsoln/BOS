"""
BOS Hotel Property Engine — Projection Store + Service
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from engines.hotel_property.events import (
    COMMAND_TO_EVENT_TYPE, PAYLOAD_BUILDERS,
    PROPERTY_CONFIGURED_V1,
    ROOM_TYPE_DEFINED_V1, ROOM_TYPE_UPDATED_V1,
    ROOM_CREATED_V1, ROOM_STATUS_CHANGED_V1,
    ROOM_SET_OUT_OF_ORDER_V1, ROOM_RETURNED_TO_SERVICE_V1,
    RATE_PLAN_CREATED_V1, RATE_PLAN_UPDATED_V1,
    RATE_PLAN_DEACTIVATED_V1, SEASONAL_RATE_SET_V1,
)


# ── Projection Store ──────────────────────────────────────────

class HotelPropertyProjectionStore:
    """
    In-memory read model for hotel property configuration.
    Tracks: property config, room types, individual rooms, rate plans,
    seasonal rates.
    """

    def __init__(self):
        self._events:        List[dict]        = []
        self._property:      Optional[dict]    = None
        self._room_types:    Dict[str, dict]   = {}
        self._rooms:         Dict[str, dict]   = {}
        self._rate_plans:    Dict[str, dict]   = {}
        self._seasonal_rates: Dict[str, dict]  = {}

    # ── apply ─────────────────────────────────────────────────

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type == PROPERTY_CONFIGURED_V1:
            self._property = dict(payload)

        elif event_type == ROOM_TYPE_DEFINED_V1:
            self._room_types[payload["room_type_id"]] = dict(payload)

        elif event_type == ROOM_TYPE_UPDATED_V1:
            rt = self._room_types.get(payload["room_type_id"])
            if rt:
                rt.update(payload.get("updates", {}))

        elif event_type == ROOM_CREATED_V1:
            self._rooms[payload["room_id"]] = dict(payload)

        elif event_type == ROOM_STATUS_CHANGED_V1:
            room = self._rooms.get(payload["room_id"])
            if room:
                room["status"] = payload["new_status"]

        elif event_type == ROOM_SET_OUT_OF_ORDER_V1:
            room = self._rooms.get(payload["room_id"])
            if room:
                room["status"] = "OUT_OF_ORDER"
                room["oo_reason"]    = payload["reason"]
                room["oo_from_date"] = payload["from_date"]
                room["oo_to_date"]   = payload.get("to_date")

        elif event_type == ROOM_RETURNED_TO_SERVICE_V1:
            room = self._rooms.get(payload["room_id"])
            if room:
                room["status"]       = "AVAILABLE"
                room["oo_reason"]    = None
                room["oo_from_date"] = None
                room["oo_to_date"]   = None

        elif event_type == RATE_PLAN_CREATED_V1:
            self._rate_plans[payload["rate_plan_id"]] = dict(payload)

        elif event_type == RATE_PLAN_UPDATED_V1:
            rp = self._rate_plans.get(payload["rate_plan_id"])
            if rp:
                rp.update(payload.get("updates", {}))

        elif event_type == RATE_PLAN_DEACTIVATED_V1:
            rp = self._rate_plans.get(payload["rate_plan_id"])
            if rp:
                rp["is_active"] = False

        elif event_type == SEASONAL_RATE_SET_V1:
            self._seasonal_rates[payload["seasonal_rate_id"]] = dict(payload)

    # ── queries ───────────────────────────────────────────────

    def get_property(self) -> Optional[dict]:
        return self._property

    def get_room_type(self, room_type_id: str) -> Optional[dict]:
        return self._room_types.get(room_type_id)

    def list_room_types(self) -> List[dict]:
        return list(self._room_types.values())

    def get_room(self, room_id: str) -> Optional[dict]:
        return self._rooms.get(room_id)

    def list_rooms(self, status: Optional[str] = None) -> List[dict]:
        if status is None:
            return list(self._rooms.values())
        return [r for r in self._rooms.values() if r.get("status") == status]

    def list_rooms_by_type(self, room_type_id: str) -> List[dict]:
        return [r for r in self._rooms.values()
                if r.get("room_type_id") == room_type_id]

    def count_available_by_type(self, room_type_id: str) -> int:
        return sum(
            1 for r in self._rooms.values()
            if r.get("room_type_id") == room_type_id
            and r.get("status") == "AVAILABLE"
        )

    def get_rate_plan(self, rate_plan_id: str) -> Optional[dict]:
        return self._rate_plans.get(rate_plan_id)

    def list_active_rate_plans(self) -> List[dict]:
        return [rp for rp in self._rate_plans.values()
                if rp.get("is_active", True)]

    def get_seasonal_rate(self, seasonal_rate_id: str) -> Optional[dict]:
        return self._seasonal_rates.get(seasonal_rate_id)

    def get_rates_for_plan_and_type(
        self, rate_plan_id: str, room_type_id: str
    ) -> List[dict]:
        return [
            sr for sr in self._seasonal_rates.values()
            if sr["rate_plan_id"] == rate_plan_id
            and sr["room_type_id"] == room_type_id
        ]

    @property
    def event_count(self) -> int:
        return len(self._events)

    def truncate(self):
        self._events.clear()
        self._property      = None
        self._room_types.clear()
        self._rooms.clear()
        self._rate_plans.clear()
        self._seasonal_rates.clear()


# ── Service ───────────────────────────────────────────────────

class HotelPropertyService:
    """
    Hotel Property engine service.
    Handles property config, room type management, room CRUD,
    rate plans, and seasonal rates.
    """

    def __init__(
        self, *,
        event_factory,
        persist_event,
        event_type_registry,
        projection_store: HotelPropertyProjectionStore,
    ):
        self._event_factory    = event_factory
        self._persist_event    = persist_event
        self._registry         = event_type_registry
        self._projection       = projection_store

    def _execute_command(self, command) -> dict:
        event_type = COMMAND_TO_EVENT_TYPE.get(command.command_type)
        if event_type is None:
            raise ValueError(f"Unknown command: {command.command_type}")

        builder = PAYLOAD_BUILDERS.get(event_type)
        if builder is None:
            raise ValueError(f"No payload builder for: {event_type}")

        payload    = builder(command)
        event_data = self._event_factory.create(
            event_type, payload,
            command.business_id,
            getattr(command, "branch_id", None),
        )
        self._persist_event(event_data)
        self._projection.apply(event_type, payload)
        return {"event_type": event_type, "payload": payload}

    @property
    def _store(self) -> HotelPropertyProjectionStore:
        return self._projection
