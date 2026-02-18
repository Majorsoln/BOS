"""
BOS Document Issuance - Public API
==================================
"""

from core.document_issuance.commands import (
    InvoiceIssueRequest,
    QuoteIssueRequest,
    ReceiptIssueRequest,
)
from core.document_issuance.events import build_document_issued_payload
from core.document_issuance.projections import (
    DocumentIssuanceProjectionStore,
    IssuedDocumentRecord,
)
from core.document_issuance.registry import (
    DOC_INVOICE_ISSUE_REQUEST,
    DOC_INVOICE_ISSUED_V1,
    DOC_QUOTE_ISSUE_REQUEST,
    DOC_QUOTE_ISSUED_V1,
    DOC_RECEIPT_ISSUE_REQUEST,
    DOC_RECEIPT_ISSUED_V1,
    DOCUMENT_ISSUANCE_COMMAND_TYPES,
    DOCUMENT_ISSUANCE_EVENT_TYPES,
    is_document_issue_command_type,
    is_document_issuance_event_type,
    register_document_issuance_event_types,
    resolve_doc_type_for_issue_command,
    resolve_event_type_for_issue_command,
)
from core.document_issuance.repository import DocumentIssuanceRepository
from core.document_issuance.service import (
    DocumentIssuanceExecutionResult,
    DocumentIssuanceService,
)

__all__ = [
    "ReceiptIssueRequest",
    "QuoteIssueRequest",
    "InvoiceIssueRequest",
    "build_document_issued_payload",
    "IssuedDocumentRecord",
    "DocumentIssuanceProjectionStore",
    "DocumentIssuanceRepository",
    "DocumentIssuanceExecutionResult",
    "DocumentIssuanceService",
    "DOC_RECEIPT_ISSUE_REQUEST",
    "DOC_QUOTE_ISSUE_REQUEST",
    "DOC_INVOICE_ISSUE_REQUEST",
    "DOC_RECEIPT_ISSUED_V1",
    "DOC_QUOTE_ISSUED_V1",
    "DOC_INVOICE_ISSUED_V1",
    "DOCUMENT_ISSUANCE_COMMAND_TYPES",
    "DOCUMENT_ISSUANCE_EVENT_TYPES",
    "is_document_issue_command_type",
    "is_document_issuance_event_type",
    "resolve_doc_type_for_issue_command",
    "resolve_event_type_for_issue_command",
    "register_document_issuance_event_types",
]
