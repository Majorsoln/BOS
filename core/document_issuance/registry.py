"""
BOS Document Issuance - Command/Event Registry
==============================================
"""

from __future__ import annotations

from core.documents.models import (
    DOCUMENT_INVOICE,
    DOCUMENT_QUOTE,
    DOCUMENT_RECEIPT,
)


DOC_RECEIPT_ISSUE_REQUEST = "doc.receipt.issue.request"
DOC_QUOTE_ISSUE_REQUEST = "doc.quote.issue.request"
DOC_INVOICE_ISSUE_REQUEST = "doc.invoice.issue.request"

DOC_RECEIPT_ISSUED_V1 = "doc.receipt.issued.v1"
DOC_QUOTE_ISSUED_V1 = "doc.quote.issued.v1"
DOC_INVOICE_ISSUED_V1 = "doc.invoice.issued.v1"

DOCUMENT_ISSUANCE_COMMAND_TYPES = frozenset(
    {
        DOC_RECEIPT_ISSUE_REQUEST,
        DOC_QUOTE_ISSUE_REQUEST,
        DOC_INVOICE_ISSUE_REQUEST,
    }
)

DOCUMENT_ISSUANCE_EVENT_TYPES = frozenset(
    {
        DOC_RECEIPT_ISSUED_V1,
        DOC_QUOTE_ISSUED_V1,
        DOC_INVOICE_ISSUED_V1,
    }
)

_COMMAND_DOC_TYPE_MAP = {
    DOC_RECEIPT_ISSUE_REQUEST: DOCUMENT_RECEIPT,
    DOC_QUOTE_ISSUE_REQUEST: DOCUMENT_QUOTE,
    DOC_INVOICE_ISSUE_REQUEST: DOCUMENT_INVOICE,
}

_COMMAND_EVENT_TYPE_MAP = {
    DOC_RECEIPT_ISSUE_REQUEST: DOC_RECEIPT_ISSUED_V1,
    DOC_QUOTE_ISSUE_REQUEST: DOC_QUOTE_ISSUED_V1,
    DOC_INVOICE_ISSUE_REQUEST: DOC_INVOICE_ISSUED_V1,
}


def is_document_issue_command_type(command_type: str) -> bool:
    return command_type in DOCUMENT_ISSUANCE_COMMAND_TYPES


def is_document_issuance_event_type(event_type: str) -> bool:
    return event_type in DOCUMENT_ISSUANCE_EVENT_TYPES


def resolve_doc_type_for_issue_command(command_type: str) -> str | None:
    return _COMMAND_DOC_TYPE_MAP.get(command_type)


def resolve_event_type_for_issue_command(command_type: str) -> str | None:
    return _COMMAND_EVENT_TYPE_MAP.get(command_type)


def register_document_issuance_event_types(event_type_registry) -> None:
    for event_type in sorted(DOCUMENT_ISSUANCE_EVENT_TYPES):
        event_type_registry.register(event_type)
