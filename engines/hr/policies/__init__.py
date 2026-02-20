"""
BOS HR Engine — Policies
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import RejectionReason


def employee_must_be_active_policy(
    command: Command, employee_lookup=None,
) -> Optional[RejectionReason]:
    if employee_lookup is None:
        return None
    if command.command_type not in (
        "hr.shift.start.request", "hr.shift.end.request",
        "hr.leave.request.request",
    ):
        return None
    eid = command.payload.get("employee_id")
    emp = employee_lookup(eid)
    if emp is None:
        return RejectionReason(
            code="EMPLOYEE_NOT_FOUND", message=f"Employee '{eid}' not found.",
            policy_name="employee_must_be_active_policy")
    if emp.get("status") != "ACTIVE":
        return RejectionReason(
            code="EMPLOYEE_NOT_ACTIVE",
            message=f"Employee '{eid}' is {emp.get('status')}.",
            policy_name="employee_must_be_active_policy")
    return None
