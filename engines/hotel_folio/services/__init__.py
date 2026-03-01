"""BOS Hotel Folio Engine — Projection Store + Service"""
from __future__ import annotations
from typing import Dict, List, Optional

from engines.hotel_folio.events import (
    COMMAND_TO_EVENT_TYPE, PAYLOAD_BUILDERS,
    FOLIO_OPENED_V1, FOLIO_CHARGE_POSTED_V1,
    FOLIO_PAYMENT_RECEIVED_V1, FOLIO_CREDIT_APPLIED_V1,
    FOLIO_ADJUSTED_V1, FOLIO_SETTLED_V1,
    NIGHT_AUDIT_RUN_V1, ROOM_NIGHT_CHARGE_POSTED_V1,
    FOLIO_TRANSFERRED_V1,
)


class HotelFolioProjectionStore:
    """
    In-memory projection of guest folios.
    Each folio tracks charges, payments, credits, and running balance.
    Night audit auto-posts ROOM_NIGHT charges for all open folios.
    """

    def __init__(self):
        self._events:  List[dict]      = []
        self._folios:  Dict[str, dict] = {}

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type == FOLIO_OPENED_V1:
            fid = payload["folio_id"]
            self._folios[fid] = {
                **payload,
                "status":   "OPEN",
                "charges":  [],
                "payments": [],
                "credits":  [],
                "balance":  0,
            }

        elif event_type == FOLIO_CHARGE_POSTED_V1:
            folio = self._folios.get(payload["folio_id"])
            if folio:
                folio["charges"].append(payload)
                folio["balance"] += payload["amount"]

        elif event_type == ROOM_NIGHT_CHARGE_POSTED_V1:
            folio = self._folios.get(payload["folio_id"])
            if folio:
                charge = {**payload, "charge_type": "ROOM_NIGHT"}
                folio["charges"].append(charge)
                folio["balance"] += payload["nightly_rate"]

        elif event_type == FOLIO_PAYMENT_RECEIVED_V1:
            folio = self._folios.get(payload["folio_id"])
            if folio:
                folio["payments"].append(payload)
                folio["balance"] -= payload["amount"]

        elif event_type == FOLIO_CREDIT_APPLIED_V1:
            folio = self._folios.get(payload["folio_id"])
            if folio:
                folio["credits"].append(payload)
                folio["balance"] -= payload["amount"]

        elif event_type == FOLIO_ADJUSTED_V1:
            folio = self._folios.get(payload["folio_id"])
            if folio:
                if payload["adjustment_type"] == "CREDIT":
                    folio["balance"] -= payload["amount"]
                else:
                    folio["balance"] += payload["amount"]

        elif event_type == FOLIO_TRANSFERRED_V1:
            # Debit source folio, credit destination folio
            src = self._folios.get(payload["from_folio_id"])
            dst = self._folios.get(payload["to_folio_id"])
            amount = payload["amount"]
            if src: src["balance"] -= amount
            if dst: dst["balance"] += amount

        elif event_type == FOLIO_SETTLED_V1:
            folio = self._folios.get(payload["folio_id"])
            if folio:
                folio["status"]         = "SETTLED"
                folio["total_charges"]  = payload["total_charges"]
                folio["total_payments"] = payload["total_payments"]
                folio["balance"]        = payload["balance_due"]
                folio["balance_due"]    = payload["balance_due"]

        elif event_type == NIGHT_AUDIT_RUN_V1:
            pass  # audit summary — charges posted separately

    def get_folio(self, folio_id: str) -> Optional[dict]:
        return self._folios.get(folio_id)

    def get_balance(self, folio_id: str) -> int:
        folio = self._folios.get(folio_id)
        return folio["balance"] if folio else 0

    def list_open_folios(self) -> List[dict]:
        return [f for f in self._folios.values() if f.get("status") == "OPEN"]

    def total_charges(self, folio_id: str) -> int:
        folio = self._folios.get(folio_id)
        if not folio: return 0
        return sum(c.get("amount") or c.get("nightly_rate", 0)
                   for c in folio["charges"])

    @property
    def event_count(self) -> int:
        return len(self._events)

    def truncate(self):
        self._events.clear()
        self._folios.clear()


class HotelFolioService:
    def __init__(self, *, event_factory, persist_event,
                 event_type_registry,
                 projection_store: HotelFolioProjectionStore):
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._registry      = event_type_registry
        self._projection    = projection_store

    def _execute_command(self, command) -> dict:
        event_type = COMMAND_TO_EVENT_TYPE.get(command.command_type)
        if event_type is None:
            raise ValueError(f"Unknown command: {command.command_type}")
        builder    = PAYLOAD_BUILDERS[event_type]
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
    def _store(self) -> HotelFolioProjectionStore:
        return self._projection
