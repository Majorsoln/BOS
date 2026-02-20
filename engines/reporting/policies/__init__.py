"""
BOS Reporting Engine — Domain Policies
=======================================
Policies guard against invalid reporting operations.
All policies return Optional[RejectionReason] — None = allowed.
"""

from __future__ import annotations

from core.commands.base import Command
from core.commands.rejection import RejectionReason


def report_period_must_be_valid_policy(
    command: Command,
) -> RejectionReason | None:
    """
    Report period_start must not be after period_end.
    """
    payload = command.payload
    period_start = payload.get("period_start", "")
    period_end = payload.get("period_end", "")

    if period_start and period_end and period_start > period_end:
        return RejectionReason(
            code="INVALID_PERIOD",
            message=f"period_start '{period_start}' is after period_end '{period_end}'.",
            policy_name="report_period_must_be_valid_policy",
        )
    return None


def snapshot_id_must_be_unique_policy(
    command: Command,
    snapshot_lookup,
) -> RejectionReason | None:
    """
    A snapshot_id must not already exist in the projection store.
    """
    snapshot_id = command.payload.get("snapshot_id", "")
    if snapshot_id and snapshot_lookup(snapshot_id) is not None:
        return RejectionReason(
            code="DUPLICATE_SNAPSHOT",
            message=f"Snapshot '{snapshot_id}' already recorded.",
            policy_name="snapshot_id_must_be_unique_policy",
        )
    return None


def report_must_have_sections_policy(
    command: Command,
) -> RejectionReason | None:
    """
    A generated report must have at least one section.
    """
    sections = command.payload.get("sections", [])
    if not sections:
        return RejectionReason(
            code="REPORT_NO_SECTIONS",
            message="Report must have at least one section.",
            policy_name="report_must_have_sections_policy",
        )
    return None
