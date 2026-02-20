"""
BOS HR Engine — Request Commands
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.commands.base import Command
from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.identity.requirements import ACTOR_REQUIRED

HR_EMPLOYEE_ONBOARD_REQUEST = "hr.employee.onboard.request"
HR_EMPLOYEE_TERMINATE_REQUEST = "hr.employee.terminate.request"
HR_SHIFT_START_REQUEST = "hr.shift.start.request"
HR_SHIFT_END_REQUEST = "hr.shift.end.request"
HR_LEAVE_REQUEST_REQUEST = "hr.leave.request.request"

HR_COMMAND_TYPES = frozenset({
    HR_EMPLOYEE_ONBOARD_REQUEST,
    HR_EMPLOYEE_TERMINATE_REQUEST,
    HR_SHIFT_START_REQUEST,
    HR_SHIFT_END_REQUEST,
    HR_LEAVE_REQUEST_REQUEST,
})

VALID_LEAVE_TYPES = frozenset({"ANNUAL", "SICK", "MATERNITY", "PATERNITY", "UNPAID"})
VALID_TERMINATE_REASONS = frozenset({
    "RESIGNATION", "DISMISSAL", "CONTRACT_END", "REDUNDANCY",
})


def _cmd(ct, payload, *, business_id, actor_type, actor_id,
         command_id, correlation_id, issued_at, branch_id=None):
    return Command(
        command_id=command_id, command_type=ct,
        business_id=business_id, branch_id=branch_id,
        actor_type=actor_type, actor_id=actor_id,
        payload=payload, issued_at=issued_at,
        correlation_id=correlation_id, source_engine="hr",
        scope_requirement=SCOPE_BUSINESS_ALLOWED,
        actor_requirement=ACTOR_REQUIRED,
    )


@dataclass(frozen=True)
class EmployeeOnboardRequest:
    employee_id: str
    full_name: str
    role: str
    start_date: str
    department: str = ""
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.employee_id:
            raise ValueError("employee_id must be non-empty.")
        if not self.full_name:
            raise ValueError("full_name must be non-empty.")
        if not self.role:
            raise ValueError("role must be non-empty.")

    def to_command(self, **kw) -> Command:
        return _cmd(HR_EMPLOYEE_ONBOARD_REQUEST, {
            "employee_id": self.employee_id, "full_name": self.full_name,
            "role": self.role, "department": self.department,
            "start_date": self.start_date,
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class EmployeeTerminateRequest:
    employee_id: str
    reason: str
    effective_date: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.employee_id:
            raise ValueError("employee_id must be non-empty.")
        if self.reason not in VALID_TERMINATE_REASONS:
            raise ValueError(f"reason '{self.reason}' not valid.")

    def to_command(self, **kw) -> Command:
        return _cmd(HR_EMPLOYEE_TERMINATE_REQUEST, {
            "employee_id": self.employee_id, "reason": self.reason,
            "effective_date": self.effective_date,
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class ShiftStartRequest:
    shift_id: str
    employee_id: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.shift_id:
            raise ValueError("shift_id must be non-empty.")
        if not self.employee_id:
            raise ValueError("employee_id must be non-empty.")

    def to_command(self, **kw) -> Command:
        return _cmd(HR_SHIFT_START_REQUEST, {
            "shift_id": self.shift_id, "employee_id": self.employee_id,
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class ShiftEndRequest:
    shift_id: str
    employee_id: str
    hours_worked: int
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.shift_id:
            raise ValueError("shift_id must be non-empty.")
        if not self.employee_id:
            raise ValueError("employee_id must be non-empty.")
        if not isinstance(self.hours_worked, int) or self.hours_worked <= 0:
            raise ValueError("hours_worked must be positive integer.")

    def to_command(self, **kw) -> Command:
        return _cmd(HR_SHIFT_END_REQUEST, {
            "shift_id": self.shift_id, "employee_id": self.employee_id,
            "hours_worked": self.hours_worked,
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class LeaveRequestRequest:
    leave_id: str
    employee_id: str
    leave_type: str
    start_date: str
    end_date: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.leave_id:
            raise ValueError("leave_id must be non-empty.")
        if not self.employee_id:
            raise ValueError("employee_id must be non-empty.")
        if self.leave_type not in VALID_LEAVE_TYPES:
            raise ValueError(f"leave_type '{self.leave_type}' not valid.")

    def to_command(self, **kw) -> Command:
        return _cmd(HR_LEAVE_REQUEST_REQUEST, {
            "leave_id": self.leave_id, "employee_id": self.employee_id,
            "leave_type": self.leave_type,
            "start_date": self.start_date, "end_date": self.end_date,
        }, branch_id=self.branch_id, **kw)
