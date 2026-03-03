"""
BOS Document Issuance - Request to Command
==========================================
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.commands.base import Command
from core.context.actor_context import ActorContext
from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.document_issuance.registry import (
    DOC_CANCELLATION_NOTE_ISSUE_REQUEST,
    DOC_COMPLETION_CERTIFICATE_ISSUE_REQUEST,
    DOC_CREDIT_NOTE_ISSUE_REQUEST,
    DOC_CUTTING_LIST_ISSUE_REQUEST,
    DOC_DEBIT_NOTE_ISSUE_REQUEST,
    DOC_DELIVERY_NOTE_ISSUE_REQUEST,
    DOC_FOLIO_ISSUE_REQUEST,
    DOC_GOODS_RECEIPT_NOTE_ISSUE_REQUEST,
    DOC_INVOICE_ISSUE_REQUEST,
    DOC_KITCHEN_ORDER_TICKET_ISSUE_REQUEST,
    DOC_MATERIAL_REQUISITION_ISSUE_REQUEST,
    DOC_PAYMENT_VOUCHER_ISSUE_REQUEST,
    DOC_PETTY_CASH_VOUCHER_ISSUE_REQUEST,
    DOC_PROFORMA_INVOICE_ISSUE_REQUEST,
    DOC_PURCHASE_ORDER_ISSUE_REQUEST,
    DOC_QUOTE_ISSUE_REQUEST,
    DOC_RECEIPT_ISSUE_REQUEST,
    DOC_REFUND_NOTE_ISSUE_REQUEST,
    DOC_REGISTRATION_CARD_ISSUE_REQUEST,
    DOC_RESERVATION_CONFIRMATION_ISSUE_REQUEST,
    DOC_SALES_ORDER_ISSUE_REQUEST,
    DOC_STATEMENT_ISSUE_REQUEST,
    DOC_STOCK_ADJUSTMENT_NOTE_ISSUE_REQUEST,
    DOC_STOCK_TRANSFER_NOTE_ISSUE_REQUEST,
    DOC_WORK_ORDER_ISSUE_REQUEST,
    resolve_doc_type_for_issue_command,
)
from core.identity.requirements import ACTOR_REQUIRED


def _validate_request_fields(
    *,
    business_id: uuid.UUID,
    branch_id: Optional[uuid.UUID],
    document_id: uuid.UUID,
    payload: dict,
) -> None:
    if not isinstance(business_id, uuid.UUID):
        raise ValueError("business_id must be UUID.")
    if branch_id is not None and not isinstance(branch_id, uuid.UUID):
        raise ValueError("branch_id must be UUID or None.")
    if not isinstance(document_id, uuid.UUID):
        raise ValueError("document_id must be UUID.")
    if not isinstance(payload, dict):
        raise ValueError("payload must be dict.")


def _build_issue_command(
    *,
    command_type: str,
    business_id: uuid.UUID,
    branch_id: Optional[uuid.UUID],
    document_id: uuid.UUID,
    payload: dict,
    command_id: uuid.UUID,
    correlation_id: uuid.UUID,
    issued_at: datetime,
    actor_context: ActorContext,
) -> Command:
    if not isinstance(command_id, uuid.UUID):
        raise ValueError("command_id must be UUID.")
    if not isinstance(correlation_id, uuid.UUID):
        raise ValueError("correlation_id must be UUID.")
    if not isinstance(issued_at, datetime):
        raise ValueError("issued_at must be datetime.")
    if not isinstance(actor_context, ActorContext):
        raise ValueError("actor_context must be ActorContext.")

    doc_type = resolve_doc_type_for_issue_command(command_type)
    if doc_type is None:
        raise ValueError(f"Unsupported command type: {command_type}")

    return Command(
        command_id=command_id,
        command_type=command_type,
        business_id=business_id,
        branch_id=branch_id,
        actor_type=actor_context.actor_type,
        actor_id=actor_context.actor_id,
        actor_context=actor_context,
        payload={
            "document_id": document_id,
            "doc_type": doc_type,
            "render_inputs": dict(payload),
        },
        issued_at=issued_at,
        correlation_id=correlation_id,
        source_engine="doc",
        scope_requirement=SCOPE_BUSINESS_ALLOWED,
        actor_requirement=ACTOR_REQUIRED,
    )


@dataclass(frozen=True)
class ReceiptIssueRequest:
    business_id: uuid.UUID
    document_id: uuid.UUID
    payload: dict
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        _validate_request_fields(
            business_id=self.business_id,
            branch_id=self.branch_id,
            document_id=self.document_id,
            payload=self.payload,
        )

    def to_command(
        self,
        *,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
        actor_context: ActorContext,
    ) -> Command:
        return _build_issue_command(
            command_type=DOC_RECEIPT_ISSUE_REQUEST,
            business_id=self.business_id,
            branch_id=self.branch_id,
            document_id=self.document_id,
            payload=self.payload,
            command_id=command_id,
            correlation_id=correlation_id,
            issued_at=issued_at,
            actor_context=actor_context,
        )


@dataclass(frozen=True)
class QuoteIssueRequest:
    business_id: uuid.UUID
    document_id: uuid.UUID
    payload: dict
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        _validate_request_fields(
            business_id=self.business_id,
            branch_id=self.branch_id,
            document_id=self.document_id,
            payload=self.payload,
        )

    def to_command(
        self,
        *,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
        actor_context: ActorContext,
    ) -> Command:
        return _build_issue_command(
            command_type=DOC_QUOTE_ISSUE_REQUEST,
            business_id=self.business_id,
            branch_id=self.branch_id,
            document_id=self.document_id,
            payload=self.payload,
            command_id=command_id,
            correlation_id=correlation_id,
            issued_at=issued_at,
            actor_context=actor_context,
        )


@dataclass(frozen=True)
class InvoiceIssueRequest:
    business_id: uuid.UUID
    document_id: uuid.UUID
    payload: dict
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        _validate_request_fields(
            business_id=self.business_id,
            branch_id=self.branch_id,
            document_id=self.document_id,
            payload=self.payload,
        )

    def to_command(
        self,
        *,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
        actor_context: ActorContext,
    ) -> Command:
        return _build_issue_command(
            command_type=DOC_INVOICE_ISSUE_REQUEST,
            business_id=self.business_id,
            branch_id=self.branch_id,
            document_id=self.document_id,
            payload=self.payload,
            command_id=command_id,
            correlation_id=correlation_id,
            issued_at=issued_at,
            actor_context=actor_context,
        )


# ── Generic base for all additional document issue requests ───────────────────

def _make_issue_request(command_type_const: str):
    """
    Factory that returns an IssueRequest dataclass bound to a specific command type.
    All document issue requests are structurally identical; only the command type differs.
    """
    @dataclass(frozen=True)
    class _IssueRequest:
        business_id: uuid.UUID
        document_id: uuid.UUID
        payload: dict
        branch_id: Optional[uuid.UUID] = None

        def __post_init__(self):
            _validate_request_fields(
                business_id=self.business_id,
                branch_id=self.branch_id,
                document_id=self.document_id,
                payload=self.payload,
            )

        def to_command(
            self,
            *,
            command_id: uuid.UUID,
            correlation_id: uuid.UUID,
            issued_at: datetime,
            actor_context: ActorContext,
        ) -> Command:
            return _build_issue_command(
                command_type=command_type_const,
                business_id=self.business_id,
                branch_id=self.branch_id,
                document_id=self.document_id,
                payload=self.payload,
                command_id=command_id,
                correlation_id=correlation_id,
                issued_at=issued_at,
                actor_context=actor_context,
            )

    return _IssueRequest


ProformaInvoiceIssueRequest          = _make_issue_request(DOC_PROFORMA_INVOICE_ISSUE_REQUEST)
DeliveryNoteIssueRequest             = _make_issue_request(DOC_DELIVERY_NOTE_ISSUE_REQUEST)
CreditNoteIssueRequest               = _make_issue_request(DOC_CREDIT_NOTE_ISSUE_REQUEST)
DebitNoteIssueRequest                = _make_issue_request(DOC_DEBIT_NOTE_ISSUE_REQUEST)
PurchaseOrderIssueRequest            = _make_issue_request(DOC_PURCHASE_ORDER_ISSUE_REQUEST)
GoodsReceiptNoteIssueRequest         = _make_issue_request(DOC_GOODS_RECEIPT_NOTE_ISSUE_REQUEST)
SalesOrderIssueRequest               = _make_issue_request(DOC_SALES_ORDER_ISSUE_REQUEST)
RefundNoteIssueRequest               = _make_issue_request(DOC_REFUND_NOTE_ISSUE_REQUEST)
WorkOrderIssueRequest                = _make_issue_request(DOC_WORK_ORDER_ISSUE_REQUEST)
MaterialRequisitionIssueRequest      = _make_issue_request(DOC_MATERIAL_REQUISITION_ISSUE_REQUEST)
CuttingListIssueRequest              = _make_issue_request(DOC_CUTTING_LIST_ISSUE_REQUEST)
CompletionCertificateIssueRequest    = _make_issue_request(DOC_COMPLETION_CERTIFICATE_ISSUE_REQUEST)
KitchenOrderTicketIssueRequest       = _make_issue_request(DOC_KITCHEN_ORDER_TICKET_ISSUE_REQUEST)
FolioIssueRequest                    = _make_issue_request(DOC_FOLIO_ISSUE_REQUEST)
ReservationConfirmationIssueRequest  = _make_issue_request(DOC_RESERVATION_CONFIRMATION_ISSUE_REQUEST)
RegistrationCardIssueRequest         = _make_issue_request(DOC_REGISTRATION_CARD_ISSUE_REQUEST)
CancellationNoteIssueRequest         = _make_issue_request(DOC_CANCELLATION_NOTE_ISSUE_REQUEST)
PaymentVoucherIssueRequest           = _make_issue_request(DOC_PAYMENT_VOUCHER_ISSUE_REQUEST)
PettyCashVoucherIssueRequest         = _make_issue_request(DOC_PETTY_CASH_VOUCHER_ISSUE_REQUEST)
StockTransferNoteIssueRequest        = _make_issue_request(DOC_STOCK_TRANSFER_NOTE_ISSUE_REQUEST)
StockAdjustmentNoteIssueRequest      = _make_issue_request(DOC_STOCK_ADJUSTMENT_NOTE_ISSUE_REQUEST)
StatementIssueRequest                = _make_issue_request(DOC_STATEMENT_ISSUE_REQUEST)
