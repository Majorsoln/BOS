"""BOS Hotel Housekeeping Engine — Projection Store + Service"""
from __future__ import annotations
from typing import Dict, List, Optional

from engines.hotel_housekeeping.events import (
    COMMAND_TO_EVENT_TYPE, PAYLOAD_BUILDERS,
    HOUSEKEEPING_TASK_ASSIGNED_V1, HOUSEKEEPING_TASK_STARTED_V1,
    HOUSEKEEPING_TASK_COMPLETED_V1, ROOM_INSPECTED_V1,
    INSPECTION_FAILED_V1, MAINTENANCE_REQUESTED_V1,
    MAINTENANCE_RESOLVED_V1, LOST_FOUND_LOGGED_V1, LOST_FOUND_CLAIMED_V1,
)


class HotelHousekeepingProjectionStore:
    def __init__(self):
        self._events:       List[dict]      = []
        self._tasks:        Dict[str, dict] = {}
        self._inspections:  Dict[str, dict] = {}
        self._maintenance:  Dict[str, dict] = {}
        self._lost_found:   Dict[str, dict] = {}

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type == HOUSEKEEPING_TASK_ASSIGNED_V1:
            self._tasks[payload["task_id"]] = dict(payload)

        elif event_type == HOUSEKEEPING_TASK_STARTED_V1:
            task = self._tasks.get(payload["task_id"])
            if task: task["status"] = "IN_PROGRESS"

        elif event_type == HOUSEKEEPING_TASK_COMPLETED_V1:
            task = self._tasks.get(payload["task_id"])
            if task:
                task["status"]       = "COMPLETED"
                task["completed_at"] = payload["completed_at"]

        elif event_type == ROOM_INSPECTED_V1:
            self._inspections[payload["inspection_id"]] = dict(payload)
            # Mark room as INSPECTED via linked task
            task_id = payload.get("task_id")
            if task_id and task_id in self._tasks:
                self._tasks[task_id]["status"] = "INSPECTED_PASS"

        elif event_type == INSPECTION_FAILED_V1:
            self._inspections[payload["inspection_id"]] = dict(payload)
            task_id = payload.get("task_id")
            if task_id and task_id in self._tasks:
                self._tasks[task_id]["status"] = "INSPECTED_FAIL"

        elif event_type == MAINTENANCE_REQUESTED_V1:
            self._maintenance[payload["maintenance_id"]] = dict(payload)

        elif event_type == MAINTENANCE_RESOLVED_V1:
            m = self._maintenance.get(payload["maintenance_id"])
            if m:
                m["status"]      = "RESOLVED"
                m["resolved_at"] = payload["resolved_at"]
                m["resolution"]  = payload.get("resolution", "")

        elif event_type == LOST_FOUND_LOGGED_V1:
            self._lost_found[payload["item_id"]] = dict(payload)

        elif event_type == LOST_FOUND_CLAIMED_V1:
            item = self._lost_found.get(payload["item_id"])
            if item:
                item["status"]      = "CLAIMED"
                item["claimed_by"]  = payload.get("claimed_by", "")
                item["released_at"] = payload["released_at"]

    def get_task(self, task_id: str) -> Optional[dict]:
        return self._tasks.get(task_id)

    def list_tasks_for_room(self, room_id: str) -> List[dict]:
        return [t for t in self._tasks.values() if t.get("room_id") == room_id]

    def list_pending_tasks(self) -> List[dict]:
        return [t for t in self._tasks.values()
                if t.get("status") in ("ASSIGNED", "IN_PROGRESS")]

    def get_maintenance(self, maintenance_id: str) -> Optional[dict]:
        return self._maintenance.get(maintenance_id)

    def list_open_maintenance(self) -> List[dict]:
        return [m for m in self._maintenance.values()
                if m.get("status") == "OPEN"]

    def get_lost_found(self, item_id: str) -> Optional[dict]:
        return self._lost_found.get(item_id)

    def list_unclaimed_items(self) -> List[dict]:
        return [i for i in self._lost_found.values()
                if i.get("status") == "UNCLAIMED"]

    @property
    def event_count(self) -> int:
        return len(self._events)

    def truncate(self):
        self._events.clear(); self._tasks.clear()
        self._inspections.clear(); self._maintenance.clear()
        self._lost_found.clear()


class HotelHousekeepingService:
    def __init__(self, *, event_factory, persist_event,
                 event_type_registry,
                 projection_store: HotelHousekeepingProjectionStore):
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
    def _store(self) -> HotelHousekeepingProjectionStore:
        return self._projection
