"""
BOS Hotel Reservation Engine — Projection Store + Service
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from engines.hotel_reservation.events import (
    COMMAND_TO_EVENT_TYPE, PAYLOAD_BUILDERS,
    RESERVATION_CREATED_V1, RESERVATION_CONFIRMED_V1,
    RESERVATION_MODIFIED_V1, RESERVATION_CANCELLED_V1,
    RESERVATION_NO_SHOW_V1, GUEST_CHECKED_IN_V1,
    GUEST_CHECKED_OUT_V1, STAY_EXTENDED_V1,
    EARLY_DEPARTURE_V1, ROOM_MOVED_V1,
)


class HotelReservationProjectionStore:
    """
    In-memory read model for reservations.
    Tracks reservation lifecycle, room assignments, folio links.
    Also maintains an external_id → reservation_id index for
    idempotent OTA ingestion.
    """

    def __init__(self):
        self._events:       List[dict]      = []
        self._reservations: Dict[str, dict] = {}
        self._ext_index:    Dict[str, str]  = {}   # external_id → reservation_id

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type == RESERVATION_CREATED_V1:
            rid = payload["reservation_id"]
            self._reservations[rid] = dict(payload)
            if payload.get("external_id"):
                self._ext_index[payload["external_id"]] = rid

        elif event_type == RESERVATION_CONFIRMED_V1:
            res = self._reservations.get(payload["reservation_id"])
            if res:
                res["status"] = "CONFIRMED"
                res["deposit_paid"] = payload.get("deposit_paid", 0)
                res["payment_ref"]  = payload.get("payment_ref", "")

        elif event_type == RESERVATION_MODIFIED_V1:
            res = self._reservations.get(payload["reservation_id"])
            if res:
                res.update(payload.get("changes", {}))

        elif event_type == RESERVATION_CANCELLED_V1:
            res = self._reservations.get(payload["reservation_id"])
            if res:
                res["status"]              = "CANCELLED"
                res["cancel_reason"]       = payload["reason"]
                res["cancellation_charge"] = payload.get("cancellation_charge", 0)
                res["refund_amount"]       = payload.get("refund_amount", 0)

        elif event_type == RESERVATION_NO_SHOW_V1:
            res = self._reservations.get(payload["reservation_id"])
            if res:
                res["status"]         = "NO_SHOW"
                res["no_show_charge"] = payload.get("no_show_charge", 0)

        elif event_type == GUEST_CHECKED_IN_V1:
            res = self._reservations.get(payload["reservation_id"])
            if res:
                res["status"]      = "CHECKED_IN"
                res["room_id"]     = payload["room_id"]
                res["room_number"] = payload.get("room_number", "")
                res["folio_id"]    = payload["folio_id"]

        elif event_type == GUEST_CHECKED_OUT_V1:
            res = self._reservations.get(payload["reservation_id"])
            if res:
                res["status"]      = "CHECKED_OUT"
                res["folio_total"] = payload.get("folio_total", 0)

        elif event_type == STAY_EXTENDED_V1:
            res = self._reservations.get(payload["reservation_id"])
            if res:
                res["departure_date"] = payload["new_departure_date"]
                res["nights"] = res.get("nights", 0) + payload.get("extra_nights", 0)
                res["total_amount"] = res.get("total_amount", 0) + payload.get("extra_amount", 0)

        elif event_type == EARLY_DEPARTURE_V1:
            res = self._reservations.get(payload["reservation_id"])
            if res:
                res["departure_date"] = payload["actual_departure"]

        elif event_type == ROOM_MOVED_V1:
            res = self._reservations.get(payload["reservation_id"])
            if res:
                res["room_id"]     = payload["new_room_id"]
                res["room_number"] = payload.get("new_room_number", "")

    # ── queries ───────────────────────────────────────────────

    def get_reservation(self, reservation_id: str) -> Optional[dict]:
        return self._reservations.get(reservation_id)

    def get_by_external_id(self, external_id: str) -> Optional[dict]:
        rid = self._ext_index.get(external_id)
        return self._reservations.get(rid) if rid else None

    def external_id_exists(self, external_id: str) -> bool:
        return external_id in self._ext_index

    def list_by_status(self, status: str) -> List[dict]:
        return [r for r in self._reservations.values()
                if r.get("status") == status]

    def list_arrivals(self, date: str) -> List[dict]:
        return [r for r in self._reservations.values()
                if r.get("arrival_date") == date
                and r.get("status") in ("PENDING", "CONFIRMED")]

    def list_departures(self, date: str) -> List[dict]:
        return [r for r in self._reservations.values()
                if r.get("departure_date") == date
                and r.get("status") == "CHECKED_IN"]

    def list_in_house(self) -> List[dict]:
        return self.list_by_status("CHECKED_IN")

    @property
    def event_count(self) -> int:
        return len(self._events)

    def truncate(self):
        self._events.clear()
        self._reservations.clear()
        self._ext_index.clear()


class HotelReservationService:
    def __init__(self, *, event_factory, persist_event,
                 event_type_registry,
                 projection_store: HotelReservationProjectionStore):
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._registry      = event_type_registry
        self._projection    = projection_store

    def _execute_command(self, command) -> dict:
        event_type = COMMAND_TO_EVENT_TYPE.get(command.command_type)
        if event_type is None:
            raise ValueError(f"Unknown command: {command.command_type}")
        builder = PAYLOAD_BUILDERS[event_type]
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
    def _store(self) -> HotelReservationProjectionStore:
        return self._projection
