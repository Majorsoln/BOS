"""
BOS Documents - Command to Document Type Registry
=================================================
"""

from __future__ import annotations

from core.documents.models import (
    DOCUMENT_INVOICE,
    DOCUMENT_QUOTE,
    DOCUMENT_RECEIPT,
)


COMMAND_DOCUMENT_TYPE_MAP = {
    "doc.receipt.issue.request": DOCUMENT_RECEIPT,
    "doc.quote.issue.request": DOCUMENT_QUOTE,
    "doc.invoice.issue.request": DOCUMENT_INVOICE,
}


def resolve_document_type(command_type: str) -> str | None:
    return COMMAND_DOCUMENT_TYPE_MAP.get(command_type)
