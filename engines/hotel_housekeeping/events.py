"""
BOS Hotel Housekeeping Engine — Event Types and Payload Builders
================================================================
Engine: hotel_housekeeping
Scope:  Room cleaning lifecycle: task assignment, progress tracking,
        supervisor inspection, maintenance requests, lost & found.
        Integrates with hotel_property (room status) and
        hotel_reservation (departure triggers task creation).
"""
from __future__ import annotations

HOUSEKEEPING_TASK_ASSIGNED_V1   = "hotel.housekeeping.task_assigned.v1"
HOUSEKEEPING_TASK_STARTED_V1    = "hotel.housekeeping.task_started.v1"
HOUSEKEEPING_TASK_COMPLETED_V1  = "hotel.housekeeping.task_completed.v1"
ROOM_INSPECTED_V1               = "hotel.room.inspected.v1"
INSPECTION_FAILED_V1            = "hotel.room.inspection_failed.v1"
MAINTENANCE_REQUESTED_V1        = "hotel.maintenance.requested.v1"
MAINTENANCE_RESOLVED_V1         = "hotel.maintenance.resolved.v1"
LOST_FOUND_LOGGED_V1            = "hotel.lost_found.logged.v1"
LOST_FOUND_CLAIMED_V1           = "hotel.lost_found.claimed.v1"

HOTEL_HOUSEKEEPING_EVENT_TYPES = (
    HOUSEKEEPING_TASK_ASSIGNED_V1, HOUSEKEEPING_TASK_STARTED_V1,
    HOUSEKEEPING_TASK_COMPLETED_V1, ROOM_INSPECTED_V1,
    INSPECTION_FAILED_V1, MAINTENANCE_REQUESTED_V1,
    MAINTENANCE_RESOLVED_V1, LOST_FOUND_LOGGED_V1, LOST_FOUND_CLAIMED_V1,
)

COMMAND_TO_EVENT_TYPE = {
    "hotel.housekeeping.assign_task.request":     HOUSEKEEPING_TASK_ASSIGNED_V1,
    "hotel.housekeeping.start_task.request":      HOUSEKEEPING_TASK_STARTED_V1,
    "hotel.housekeeping.complete_task.request":   HOUSEKEEPING_TASK_COMPLETED_V1,
    "hotel.housekeeping.inspect_room.request":    ROOM_INSPECTED_V1,
    "hotel.housekeeping.fail_inspection.request": INSPECTION_FAILED_V1,
    "hotel.maintenance.request.create":           MAINTENANCE_REQUESTED_V1,
    "hotel.maintenance.resolve.request":          MAINTENANCE_RESOLVED_V1,
    "hotel.lost_found.log.request":               LOST_FOUND_LOGGED_V1,
    "hotel.lost_found.claim.request":             LOST_FOUND_CLAIMED_V1,
}

VALID_TASK_TYPES = frozenset({
    "DEPARTURE_CLEAN", "STAYOVER_CLEAN", "TURNDOWN",
    "DEEP_CLEAN", "TOUCH_UP", "INSPECTION",
})
VALID_TASK_PRIORITIES = frozenset({"NORMAL", "URGENT", "RUSH"})
VALID_MAINTENANCE_CATEGORIES = frozenset({
    "PLUMBING", "ELECTRICAL", "HVAC", "FURNITURE",
    "APPLIANCE", "DOOR_LOCK", "INTERNET", "OTHER",
})


def build_task_assigned_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "task_id":       p["task_id"],
        "room_id":       p["room_id"],
        "room_number":   p.get("room_number", ""),
        "task_type":     p["task_type"],
        "housekeeper_id": p.get("housekeeper_id"),
        "priority":      p.get("priority", "NORMAL"),
        "notes":         p.get("notes", ""),
        "assigned_by":   cmd.actor_id,
        "assigned_at":   cmd.issued_at,
        "status":        "ASSIGNED",
    }


def build_task_started_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "task_id":    p["task_id"],
        "room_id":    p["room_id"],
        "started_by": cmd.actor_id,
        "started_at": cmd.issued_at,
    }


def build_task_completed_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "task_id":      p["task_id"],
        "room_id":      p["room_id"],
        "notes":        p.get("notes", ""),
        "completed_by": cmd.actor_id,
        "completed_at": cmd.issued_at,
    }


def build_room_inspected_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "inspection_id": p["inspection_id"],
        "room_id":       p["room_id"],
        "task_id":       p.get("task_id"),
        "result":        "PASS",
        "notes":         p.get("notes", ""),
        "inspected_by":  cmd.actor_id,
        "inspected_at":  cmd.issued_at,
    }


def build_inspection_failed_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "inspection_id":    p["inspection_id"],
        "room_id":          p["room_id"],
        "task_id":          p.get("task_id"),
        "result":           "FAIL",
        "failure_reasons":  list(p.get("failure_reasons", [])),
        "notes":            p.get("notes", ""),
        "inspected_by":     cmd.actor_id,
        "inspected_at":     cmd.issued_at,
    }


def build_maintenance_requested_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "maintenance_id": p["maintenance_id"],
        "room_id":        p["room_id"],
        "category":       p["category"],
        "description":    p["description"],
        "priority":       p.get("priority", "NORMAL"),
        "reported_by":    cmd.actor_id,
        "reported_at":    cmd.issued_at,
        "status":         "OPEN",
    }


def build_maintenance_resolved_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "maintenance_id": p["maintenance_id"],
        "resolution":     p.get("resolution", ""),
        "resolved_by":    cmd.actor_id,
        "resolved_at":    cmd.issued_at,
    }


def build_lost_found_logged_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "item_id":       p["item_id"],
        "room_id":       p.get("room_id", ""),
        "description":   p["description"],
        "found_by":      cmd.actor_id,
        "found_at":      cmd.issued_at,
        "storage_loc":   p.get("storage_loc", "FRONT_DESK"),
        "status":        "UNCLAIMED",
    }


def build_lost_found_claimed_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "item_id":     p["item_id"],
        "claimed_by":  p.get("claimed_by", ""),
        "id_verified": p.get("id_verified", False),
        "released_by": cmd.actor_id,
        "released_at": cmd.issued_at,
    }


PAYLOAD_BUILDERS = {
    HOUSEKEEPING_TASK_ASSIGNED_V1:  build_task_assigned_payload,
    HOUSEKEEPING_TASK_STARTED_V1:   build_task_started_payload,
    HOUSEKEEPING_TASK_COMPLETED_V1: build_task_completed_payload,
    ROOM_INSPECTED_V1:              build_room_inspected_payload,
    INSPECTION_FAILED_V1:           build_inspection_failed_payload,
    MAINTENANCE_REQUESTED_V1:       build_maintenance_requested_payload,
    MAINTENANCE_RESOLVED_V1:        build_maintenance_resolved_payload,
    LOST_FOUND_LOGGED_V1:           build_lost_found_logged_payload,
    LOST_FOUND_CLAIMED_V1:          build_lost_found_claimed_payload,
}
