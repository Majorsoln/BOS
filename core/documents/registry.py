"""
BOS Documents - Command to Document Type Registry
=================================================
Delegates to the issuance registry as the single source of truth for
command_type → doc_type mapping.
"""

from __future__ import annotations

from core.document_issuance.registry import resolve_doc_type_for_issue_command


def resolve_document_type(command_type: str) -> str | None:
    return resolve_doc_type_for_issue_command(command_type)
