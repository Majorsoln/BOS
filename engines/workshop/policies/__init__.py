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


# ── Phase 16: Style Registry Policies ────────────────────────────────────────

def style_must_exist_to_quote_policy(
    command: Command, style_lookup=None,
) -> Optional[RejectionReason]:
    """
    A quote cannot be generated for a style that does not exist in the catalog.
    style_lookup(style_id) must return the style record or None.
    """
    if style_lookup is None:
        return None
    if command.command_type != "workshop.quote.generate.request":
        return None
    style_id = command.payload.get("style_id")
    style = style_lookup(style_id)
    if style is None:
        return RejectionReason(
            code="STYLE_NOT_FOUND",
            message=f"Style '{style_id}' not found. Register it before generating a quote.",
            policy_name="style_must_exist_to_quote_policy")
    return None


def style_must_be_active_to_quote_policy(
    command: Command, style_lookup=None,
) -> Optional[RejectionReason]:
    """
    A quote cannot be generated for a deactivated style.
    style_lookup(style_id) must return the style record (with .status) or None.
    """
    if style_lookup is None:
        return None
    if command.command_type != "workshop.quote.generate.request":
        return None
    style_id = command.payload.get("style_id")
    style = style_lookup(style_id)
    if style is None:
        return None  # existence check is handled by style_must_exist_to_quote_policy
    if getattr(style, "status", None) != "ACTIVE":
        return RejectionReason(
            code="STYLE_INACTIVE",
            message=f"Style '{style_id}' is {getattr(style, 'status', 'UNKNOWN')}. "
                    "Only ACTIVE styles can be used for quotes.",
            policy_name="style_must_be_active_to_quote_policy")
    return None


def style_id_must_not_exist_to_register_policy(
    command: Command, style_lookup=None,
) -> Optional[RejectionReason]:
    """
    Prevent registering a style with a duplicate style_id.
    style_lookup(style_id) returns the existing record or None.
    """
    if style_lookup is None:
        return None
    if command.command_type != "workshop.style.register.request":
        return None
    style_id = command.payload.get("style_id")
    existing = style_lookup(style_id)
    if existing is not None:
        return RejectionReason(
            code="STYLE_ALREADY_EXISTS",
            message=f"Style '{style_id}' already exists. Use update instead.",
            policy_name="style_id_must_not_exist_to_register_policy")
    return None
