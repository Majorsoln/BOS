"""
BOS Documents - Verification Portal
======================================
Verifies the integrity of an issued document by checking its render_plan hash.

Doctrine:
- Verification is read-only. It does not mutate state.
- A document is VALID iff its stored hash matches hash(render_plan).
- TAMPERED if a document is found but hash does not match.
- NOT_FOUND if no document exists for the given identifier.
- Cross-tenant access must fail deterministically (business_id check).
- Replay-safe: verification result is derived from stored event data only.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from core.documents.hashing import verify_render_plan_hash


# ---------------------------------------------------------------------------
# Verification status codes
# ---------------------------------------------------------------------------

VERIFICATION_VALID = "VALID"
VERIFICATION_TAMPERED = "TAMPERED"
VERIFICATION_NOT_FOUND = "NOT_FOUND"

VALID_VERIFICATION_STATUSES = frozenset({
    VERIFICATION_VALID,
    VERIFICATION_TAMPERED,
    VERIFICATION_NOT_FOUND,
})


# ---------------------------------------------------------------------------
# Verification result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VerificationResult:
    status: str                       # VALID | TAMPERED | NOT_FOUND
    document_id: Optional[str]        # str(uuid) or None
    doc_type: Optional[str]
    doc_number: Optional[str]
    business_id: Optional[str]
    branch_id: Optional[str]
    issued_at: Optional[str]
    actor_id: Optional[str]
    stored_hash: Optional[str]        # the hash stored at issuance
    computed_hash: Optional[str]      # hash computed now from render_plan
    message: str = ""

    def is_valid(self) -> bool:
        return self.status == VERIFICATION_VALID

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "document_id": self.document_id,
            "doc_type": self.doc_type,
            "doc_number": self.doc_number,
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "issued_at": self.issued_at,
            "actor_id": self.actor_id,
            "stored_hash": self.stored_hash,
            "computed_hash": self.computed_hash,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# Document record protocol
# ---------------------------------------------------------------------------

class VerifiableRecord:
    """
    Minimal interface expected from a projection record for verification.

    Concrete implementations (from DocumentIssuanceProjectionStore or DB)
    must provide these attributes.
    """
    document_id: uuid.UUID
    doc_type: str
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID]
    issued_at: object
    actor_id: str
    render_plan: dict           # the full render_plan stored in the event
    render_plan_hash: str       # the SHA-256 hash stored at issuance
    doc_number: Optional[str]   # the formatted document number (if any)


# ---------------------------------------------------------------------------
# Verification service
# ---------------------------------------------------------------------------

def verify_document(
    *,
    document_id: uuid.UUID,
    business_id: uuid.UUID,
    record: Optional[VerifiableRecord],
) -> VerificationResult:
    """
    Verify the integrity of an issued document.

    Args:
        document_id: UUID of the document to verify
        business_id: the requesting business (tenant boundary check)
        record: the stored document record (or None if not found)

    Returns:
        VerificationResult with status VALID | TAMPERED | NOT_FOUND
    """
    if record is None:
        return VerificationResult(
            status=VERIFICATION_NOT_FOUND,
            document_id=str(document_id),
            doc_type=None,
            doc_number=None,
            business_id=str(business_id),
            branch_id=None,
            issued_at=None,
            actor_id=None,
            stored_hash=None,
            computed_hash=None,
            message="Document not found.",
        )

    # Cross-tenant boundary check
    if record.business_id != business_id:
        return VerificationResult(
            status=VERIFICATION_NOT_FOUND,
            document_id=str(document_id),
            doc_type=None,
            doc_number=None,
            business_id=str(business_id),
            branch_id=None,
            issued_at=None,
            actor_id=None,
            stored_hash=None,
            computed_hash=None,
            message="Document not found.",  # Do not leak cross-tenant existence
        )

    stored_hash = getattr(record, "render_plan_hash", None)
    render_plan = getattr(record, "render_plan", None)
    doc_number = getattr(record, "doc_number", None)

    if not stored_hash or not isinstance(stored_hash, str):
        return VerificationResult(
            status=VERIFICATION_TAMPERED,
            document_id=str(record.document_id),
            doc_type=record.doc_type,
            doc_number=doc_number,
            business_id=str(record.business_id),
            branch_id=str(record.branch_id) if record.branch_id else None,
            issued_at=str(record.issued_at),
            actor_id=record.actor_id,
            stored_hash=None,
            computed_hash=None,
            message="No stored hash found — document integrity cannot be confirmed.",
        )

    if not isinstance(render_plan, dict):
        return VerificationResult(
            status=VERIFICATION_TAMPERED,
            document_id=str(record.document_id),
            doc_type=record.doc_type,
            doc_number=doc_number,
            business_id=str(record.business_id),
            branch_id=str(record.branch_id) if record.branch_id else None,
            issued_at=str(record.issued_at),
            actor_id=record.actor_id,
            stored_hash=stored_hash,
            computed_hash=None,
            message="Render plan not available for hash verification.",
        )

    from core.documents.hashing import compute_render_plan_hash
    computed_hash = compute_render_plan_hash(render_plan)
    is_valid = verify_render_plan_hash(render_plan, stored_hash)

    if is_valid:
        return VerificationResult(
            status=VERIFICATION_VALID,
            document_id=str(record.document_id),
            doc_type=record.doc_type,
            doc_number=doc_number,
            business_id=str(record.business_id),
            branch_id=str(record.branch_id) if record.branch_id else None,
            issued_at=str(record.issued_at),
            actor_id=record.actor_id,
            stored_hash=stored_hash,
            computed_hash=computed_hash,
            message="Document hash verified. Integrity confirmed.",
        )
    else:
        return VerificationResult(
            status=VERIFICATION_TAMPERED,
            document_id=str(record.document_id),
            doc_type=record.doc_type,
            doc_number=doc_number,
            business_id=str(record.business_id),
            branch_id=str(record.branch_id) if record.branch_id else None,
            issued_at=str(record.issued_at),
            actor_id=record.actor_id,
            stored_hash=stored_hash,
            computed_hash=computed_hash,
            message="Document hash mismatch — possible tampering detected.",
        )
