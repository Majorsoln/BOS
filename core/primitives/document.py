"""
BOS Document Primitive — Lightweight Document Reference
=======================================================
Phase 4: Business Primitive Layer
Authority: BOS Core Technical Appendix, Document Engine HOW

The Document Primitive is a lightweight reference pointing to
a document produced by the Document Engine.

It does NOT contain the document content — it contains a verifiable
reference to it (hash, ID, number). The Document Engine holds
the full template + render logic.

Used by:
    Procurement Engine — Purchase Order documents, GRN receipts
    Retail Engine      — Sale receipts, refund notes
    Restaurant Engine  — Bills, receipts
    Workshop Engine    — Quotes, job completion certificates
    HR Engine          — Employment contracts, payslip references
    Accounting Engine  — Journal references, statements

RULES (NON-NEGOTIABLE):
- Document references are immutable once issued
- Document hash is the source of truth for verification
- Corrections = new document with correction_of reference
- Multi-tenant: scoped to business_id
- Past documents can never be altered

This file contains NO persistence logic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class DocumentType(Enum):
    """Classification of BOS documents."""
    SALES_RECEIPT = "SALES_RECEIPT"
    REFUND_NOTE = "REFUND_NOTE"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    GOODS_RECEIPT_NOTE = "GOODS_RECEIPT_NOTE"
    INVOICE = "INVOICE"
    CREDIT_NOTE = "CREDIT_NOTE"
    QUOTE = "QUOTE"
    JOB_SHEET = "JOB_SHEET"
    PAYSLIP = "PAYSLIP"
    EMPLOYMENT_CONTRACT = "EMPLOYMENT_CONTRACT"
    JOURNAL_VOUCHER = "JOURNAL_VOUCHER"
    STATEMENT = "STATEMENT"
    CUSTOM = "CUSTOM"


class DocumentStatus(Enum):
    """Lifecycle status of a document."""
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    VOID = "VOID"          # Voided, superseded by a correction
    CORRECTED = "CORRECTED"  # A correction was issued, this is original


# ══════════════════════════════════════════════════════════════
# DOCUMENT REFERENCE
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class DocumentReference:
    """
    A verifiable reference to a BOS document.

    This is embedded in events and commands — it is NOT the document
    itself, but an immutable pointer to one.

    Fields:
        document_id:    Unique identifier
        business_id:    Tenant boundary
        document_type:  Classification of document
        document_number: Human-readable sequential number (e.g. "INV-00042")
        document_hash:  SHA-256 hash of rendered content (hex string)
        issued_at:      When the document was officially issued
        subject_id:     The subject of this document (e.g. sale_id, po_id)
        subject_type:   Type of the subject (e.g. "Sale", "PurchaseOrder")
        template_id:    Which template produced this document
        status:         Current lifecycle status
        correction_of:  If this corrects another document, its document_id
        branch_id:      Branch scope (optional)
        metadata:       Additional key-value metadata
    """
    document_id: uuid.UUID
    business_id: uuid.UUID
    document_type: DocumentType
    document_number: str
    document_hash: str
    issued_at: datetime
    subject_id: str
    subject_type: str
    template_id: str
    status: DocumentStatus = DocumentStatus.ISSUED
    correction_of: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    metadata: Optional[dict] = None

    def __post_init__(self):
        if not isinstance(self.document_id, uuid.UUID):
            raise ValueError("document_id must be UUID.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.document_type, DocumentType):
            raise ValueError("document_type must be DocumentType enum.")
        if not self.document_number or not isinstance(self.document_number, str):
            raise ValueError("document_number must be non-empty string.")
        if not self.document_hash or not isinstance(self.document_hash, str):
            raise ValueError("document_hash must be non-empty string.")
        if not isinstance(self.issued_at, datetime):
            raise TypeError("issued_at must be datetime.")
        if not self.subject_id or not isinstance(self.subject_id, str):
            raise ValueError("subject_id must be non-empty string.")
        if not self.template_id or not isinstance(self.template_id, str):
            raise ValueError("template_id must be non-empty string.")

    @property
    def is_correction(self) -> bool:
        return self.correction_of is not None

    @property
    def is_voided(self) -> bool:
        return self.status == DocumentStatus.VOID

    def verify(self, rendered_hash: str) -> bool:
        """
        Verify this document reference matches a rendered output.
        Returns True if hashes match (document is authentic).
        """
        return self.document_hash == rendered_hash

    def to_dict(self) -> dict:
        return {
            "document_id": str(self.document_id),
            "business_id": str(self.business_id),
            "branch_id": str(self.branch_id) if self.branch_id else None,
            "document_type": self.document_type.value,
            "document_number": self.document_number,
            "document_hash": self.document_hash,
            "issued_at": self.issued_at.isoformat(),
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "template_id": self.template_id,
            "status": self.status.value,
            "correction_of": str(self.correction_of) if self.correction_of else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DocumentReference:
        return cls(
            document_id=uuid.UUID(data["document_id"]),
            business_id=uuid.UUID(data["business_id"]),
            branch_id=uuid.UUID(data["branch_id"]) if data.get("branch_id") else None,
            document_type=DocumentType(data["document_type"]),
            document_number=data["document_number"],
            document_hash=data["document_hash"],
            issued_at=datetime.fromisoformat(data["issued_at"]),
            subject_id=data["subject_id"],
            subject_type=data["subject_type"],
            template_id=data["template_id"],
            status=DocumentStatus(data.get("status", DocumentStatus.ISSUED.value)),
            correction_of=uuid.UUID(data["correction_of"]) if data.get("correction_of") else None,
            metadata=data.get("metadata"),
        )
