"""
BOS Document Issuance - Payload Builders
========================================
Envelope ownership remains external.
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.documents.hashing import compute_render_plan_hash


def build_document_issued_payload(
    *,
    command: Command,
    doc_type: str,
    render_plan: dict,
    doc_number: Optional[str] = None,
) -> dict:
    if not isinstance(render_plan, dict):
        raise ValueError("render_plan must be dict.")

    render_plan_hash = compute_render_plan_hash(render_plan)

    return {
        "business_id": command.business_id,
        "branch_id": command.branch_id,
        "actor_id": command.actor_id,
        "correlation_id": command.correlation_id,
        "document_id": command.payload["document_id"],
        "doc_type": doc_type,
        "doc_number": doc_number,
        "template_id": render_plan["template_id"],
        "template_version": render_plan["template_version"],
        "schema_version": render_plan["schema_version"],
        "render_plan": dict(render_plan),
        "render_plan_hash": render_plan_hash,
        "issued_at": command.issued_at,
        "status": "ISSUED",
    }
