"""
BOS HR Engine — Event Types and Payload Builders
===================================================
Engine: HR (Employee & Attendance Management)
"""

from __future__ import annotations

from core.commands.base import Command

HR_EMPLOYEE_ONBOARDED_V1 = "hr.employee.onboarded.v1"
HR_EMPLOYEE_TERMINATED_V1 = "hr.employee.terminated.v1"
HR_SHIFT_STARTED_V1 = "hr.shift.started.v1"
HR_SHIFT_ENDED_V1 = "hr.shift.ended.v1"
HR_LEAVE_REQUESTED_V1 = "hr.leave.requested.v1"

HR_EVENT_TYPES = (
    HR_EMPLOYEE_ONBOARDED_V1,
    HR_EMPLOYEE_TERMINATED_V1,
    HR_SHIFT_STARTED_V1,
    HR_SHIFT_ENDED_V1,
    HR_LEAVE_REQUESTED_V1,
)

COMMAND_TO_EVENT_TYPE = {
    "hr.employee.onboard.request": HR_EMPLOYEE_ONBOARDED_V1,
    "hr.employee.terminate.request": HR_EMPLOYEE_TERMINATED_V1,
    "hr.shift.start.request": HR_SHIFT_STARTED_V1,
    "hr.shift.end.request": HR_SHIFT_ENDED_V1,
    "hr.leave.request.request": HR_LEAVE_REQUESTED_V1,
}


def resolve_hr_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_hr_event_types(event_type_registry) -> None:
    for et in sorted(HR_EVENT_TYPES):
        event_type_registry.register(et)


def _base_payload(command: Command) -> dict:
    return {
        "business_id": command.business_id, "branch_id": command.branch_id,
        "actor_id": command.actor_id, "actor_type": command.actor_type,
        "correlation_id": command.correlation_id, "command_id": command.command_id,
    }


def build_employee_onboarded_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "employee_id": command.payload["employee_id"],
        "full_name": command.payload["full_name"],
        "role": command.payload["role"],
        "department": command.payload.get("department", ""),
        "start_date": command.payload["start_date"],
        "onboarded_at": command.issued_at,
    })
    return p


def build_employee_terminated_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "employee_id": command.payload["employee_id"],
        "reason": command.payload["reason"],
        "effective_date": command.payload["effective_date"],
        "terminated_at": command.issued_at,
    })
    return p


def build_shift_started_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "shift_id": command.payload["shift_id"],
        "employee_id": command.payload["employee_id"],
        "started_at": command.issued_at,
    })
    return p


def build_shift_ended_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "shift_id": command.payload["shift_id"],
        "employee_id": command.payload["employee_id"],
        "hours_worked": command.payload["hours_worked"],
        "ended_at": command.issued_at,
    })
    return p


def build_leave_requested_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "leave_id": command.payload["leave_id"],
        "employee_id": command.payload["employee_id"],
        "leave_type": command.payload["leave_type"],
        "start_date": command.payload["start_date"],
        "end_date": command.payload["end_date"],
        "requested_at": command.issued_at,
    })
    return p
