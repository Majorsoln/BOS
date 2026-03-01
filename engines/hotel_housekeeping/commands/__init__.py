"""BOS Hotel Housekeeping Engine — Request Commands"""
from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple
from engines.hotel_housekeeping.events import (
    VALID_TASK_TYPES, VALID_TASK_PRIORITIES, VALID_MAINTENANCE_CATEGORIES,
)

HOTEL_HK_ASSIGN_TASK_REQUEST     = "hotel.housekeeping.assign_task.request"
HOTEL_HK_START_TASK_REQUEST      = "hotel.housekeeping.start_task.request"
HOTEL_HK_COMPLETE_TASK_REQUEST   = "hotel.housekeeping.complete_task.request"
HOTEL_HK_INSPECT_ROOM_REQUEST    = "hotel.housekeeping.inspect_room.request"
HOTEL_HK_FAIL_INSPECTION_REQUEST = "hotel.housekeeping.fail_inspection.request"
HOTEL_MAINTENANCE_CREATE_REQUEST = "hotel.maintenance.request.create"
HOTEL_MAINTENANCE_RESOLVE_REQUEST= "hotel.maintenance.resolve.request"
HOTEL_LOST_FOUND_LOG_REQUEST     = "hotel.lost_found.log.request"
HOTEL_LOST_FOUND_CLAIM_REQUEST   = "hotel.lost_found.claim.request"

HOTEL_HOUSEKEEPING_COMMAND_TYPES = frozenset({
    HOTEL_HK_ASSIGN_TASK_REQUEST, HOTEL_HK_START_TASK_REQUEST,
    HOTEL_HK_COMPLETE_TASK_REQUEST, HOTEL_HK_INSPECT_ROOM_REQUEST,
    HOTEL_HK_FAIL_INSPECTION_REQUEST, HOTEL_MAINTENANCE_CREATE_REQUEST,
    HOTEL_MAINTENANCE_RESOLVE_REQUEST, HOTEL_LOST_FOUND_LOG_REQUEST,
    HOTEL_LOST_FOUND_CLAIM_REQUEST,
})


class _Cmd:
    __slots__ = ("command_type","payload","business_id","branch_id","actor_id","issued_at")
    def __init__(self,command_type,payload,*,business_id,branch_id,actor_id,issued_at):
        self.command_type=command_type; self.payload=payload
        self.business_id=business_id; self.branch_id=branch_id
        self.actor_id=actor_id; self.issued_at=issued_at


@dataclass(frozen=True)
class AssignHousekeepingTaskRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    task_id:        str
    room_id:        str
    task_type:      str
    actor_id:       str
    issued_at:      datetime
    housekeeper_id: Optional[str] = None
    priority:       str = "NORMAL"
    notes:          str = ""
    room_number:    str = ""

    def __post_init__(self):
        if not self.task_id: raise ValueError("task_id must be non-empty.")
        if not self.room_id: raise ValueError("room_id must be non-empty.")
        if self.task_type not in VALID_TASK_TYPES:
            raise ValueError(f"task_type must be one of {sorted(VALID_TASK_TYPES)}.")
        if self.priority not in VALID_TASK_PRIORITIES:
            raise ValueError(f"priority must be one of {sorted(VALID_TASK_PRIORITIES)}.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_HK_ASSIGN_TASK_REQUEST, {
            "task_id": self.task_id, "room_id": self.room_id,
            "room_number": self.room_number, "task_type": self.task_type,
            "housekeeper_id": self.housekeeper_id,
            "priority": self.priority, "notes": self.notes,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class CompleteHousekeepingTaskRequest:
    business_id: uuid.UUID
    branch_id:   uuid.UUID
    task_id:     str
    room_id:     str
    actor_id:    str
    issued_at:   datetime
    notes:       str = ""

    def __post_init__(self):
        if not self.task_id: raise ValueError("task_id must be non-empty.")
        if not self.room_id: raise ValueError("room_id must be non-empty.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_HK_COMPLETE_TASK_REQUEST, {
            "task_id": self.task_id, "room_id": self.room_id, "notes": self.notes,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class InspectRoomRequest:
    business_id:   uuid.UUID
    branch_id:     uuid.UUID
    inspection_id: str
    room_id:       str
    actor_id:      str
    issued_at:     datetime
    task_id:       Optional[str] = None
    notes:         str = ""

    def __post_init__(self):
        if not self.inspection_id: raise ValueError("inspection_id must be non-empty.")
        if not self.room_id:       raise ValueError("room_id must be non-empty.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_HK_INSPECT_ROOM_REQUEST, {
            "inspection_id": self.inspection_id, "room_id": self.room_id,
            "task_id": self.task_id, "notes": self.notes,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class FailInspectionRequest:
    business_id:     uuid.UUID
    branch_id:       uuid.UUID
    inspection_id:   str
    room_id:         str
    failure_reasons: Tuple[str, ...]
    actor_id:        str
    issued_at:       datetime
    task_id:         Optional[str] = None
    notes:           str = ""

    def __post_init__(self):
        if not self.inspection_id:   raise ValueError("inspection_id must be non-empty.")
        if not self.room_id:         raise ValueError("room_id must be non-empty.")
        if not self.failure_reasons: raise ValueError("failure_reasons must be non-empty.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_HK_FAIL_INSPECTION_REQUEST, {
            "inspection_id": self.inspection_id, "room_id": self.room_id,
            "task_id": self.task_id,
            "failure_reasons": list(self.failure_reasons), "notes": self.notes,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class RequestMaintenanceRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    maintenance_id: str
    room_id:        str
    category:       str
    description:    str
    actor_id:       str
    issued_at:      datetime
    priority:       str = "NORMAL"

    def __post_init__(self):
        if not self.maintenance_id: raise ValueError("maintenance_id must be non-empty.")
        if not self.room_id:        raise ValueError("room_id must be non-empty.")
        if not self.description:    raise ValueError("description must be non-empty.")
        if self.category not in VALID_MAINTENANCE_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(VALID_MAINTENANCE_CATEGORIES)}.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_MAINTENANCE_CREATE_REQUEST, {
            "maintenance_id": self.maintenance_id, "room_id": self.room_id,
            "category": self.category, "description": self.description,
            "priority": self.priority,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)
