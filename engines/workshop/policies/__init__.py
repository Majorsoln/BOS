"""
BOS Workshop Engine — Policies
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import RejectionReason


def job_must_be_assigned_to_start_policy(
    command: Command, job_lookup=None,
) -> Optional[RejectionReason]:
    if job_lookup is None:
        return None
    if command.command_type != "workshop.job.start.request":
        return None
    job_id = command.payload.get("job_id")
    job = job_lookup(job_id)
    if job is None:
        return RejectionReason(
            code="JOB_NOT_FOUND", message=f"Job '{job_id}' not found.",
            policy_name="job_must_be_assigned_to_start_policy")
    if job.get("status") != "ASSIGNED":
        return RejectionReason(
            code="JOB_NOT_ASSIGNED",
            message=f"Job '{job_id}' is {job.get('status')}. Must be ASSIGNED to start.",
            policy_name="job_must_be_assigned_to_start_policy")
    return None
