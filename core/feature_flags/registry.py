"""
BOS Feature Flags - Command to Flag Registry
============================================
"""

from __future__ import annotations


FLAG_ENABLE_COMPLIANCE_ENGINE = "ENABLE_COMPLIANCE_ENGINE"
FLAG_ENABLE_ADVANCED_POLICY_ESCALATION = "ENABLE_ADVANCED_POLICY_ESCALATION"
FLAG_ENABLE_DOCUMENT_DESIGNER = "ENABLE_DOCUMENT_DESIGNER"
FLAG_ENABLE_DOCUMENT_RENDER_PLAN = "ENABLE_DOCUMENT_RENDER_PLAN"
FLAG_ENABLE_WORKSHOP_ENGINE = "ENABLE_WORKSHOP_ENGINE"


COMMAND_FLAG_MAP = {
    "compliance.profile.assign.request": FLAG_ENABLE_COMPLIANCE_ENGINE,
    "policy.escalation.advanced.request": FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
    "document.template.design.request": FLAG_ENABLE_DOCUMENT_DESIGNER,
    "workshop.production.execute.request": FLAG_ENABLE_WORKSHOP_ENGINE,
    "test.x.y.request": FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
}


def resolve_flag_for_command(command_type: str) -> str | None:
    return COMMAND_FLAG_MAP.get(command_type)
