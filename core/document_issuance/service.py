"""
BOS Document Issuance - Application Service
===========================================
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Protocol

from core.commands.base import Command
from core.context.actor_context import ActorContext
from core.document_issuance.commands import (
    CancellationNoteIssueRequest,
    CompletionCertificateIssueRequest,
    CreditNoteIssueRequest,
    CuttingListIssueRequest,
    DebitNoteIssueRequest,
    DeliveryNoteIssueRequest,
    FolioIssueRequest,
    GoodsReceiptNoteIssueRequest,
    InvoiceIssueRequest,
    KitchenOrderTicketIssueRequest,
    MaterialRequisitionIssueRequest,
    PaymentVoucherIssueRequest,
    PettyCashVoucherIssueRequest,
    ProformaInvoiceIssueRequest,
    PurchaseOrderIssueRequest,
    QuoteIssueRequest,
    ReceiptIssueRequest,
    RefundNoteIssueRequest,
    RegistrationCardIssueRequest,
    ReservationConfirmationIssueRequest,
    SalesOrderIssueRequest,
    CashSessionReconciliationIssueRequest,
    StatementIssueRequest,
    StockAdjustmentNoteIssueRequest,
    StockTransferNoteIssueRequest,
    WorkOrderIssueRequest,
)
from core.document_issuance.events import build_document_issued_payload
from core.document_issuance.projections import DocumentIssuanceProjectionStore
from core.document_issuance.registry import (
    DOCUMENT_ISSUANCE_COMMAND_TYPES,
    register_document_issuance_event_types,
    resolve_doc_type_for_issue_command,
    resolve_event_type_for_issue_command,
)
from core.documents.builder import DocumentBuilder
from core.documents.registry import resolve_document_type
from core.documents.numbering.provider import NumberingProvider


class EventFactoryProtocol(Protocol):
    def __call__(
        self,
        *,
        command: Command,
        event_type: str,
        payload: dict,
    ) -> dict:
        ...


class PersistEventProtocol(Protocol):
    def __call__(
        self,
        *,
        event_data: dict,
        context: Any,
        registry: Any,
        **kwargs: Any,
    ) -> Any:
        ...


@dataclass(frozen=True)
class DocumentIssuanceExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


class _DocumentIssuanceCommandHandler:
    def __init__(self, service: "DocumentIssuanceService"):
        self._service = service

    def execute(self, command: Command) -> DocumentIssuanceExecutionResult:
        return self._service._execute_issue_command(command)


class DocumentIssuanceService:
    def __init__(
        self,
        *,
        business_context,
        dispatcher,
        command_bus,
        event_factory: EventFactoryProtocol,
        persist_event: PersistEventProtocol,
        event_type_registry,
        projection_store: DocumentIssuanceProjectionStore | None = None,
        document_provider=None,
        numbering_provider: NumberingProvider | None = None,
    ):
        self._business_context = business_context
        self._dispatcher = dispatcher
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or DocumentIssuanceProjectionStore()
        self._document_provider = document_provider
        self._numbering_provider = numbering_provider

        register_document_issuance_event_types(self._event_type_registry)
        self._register_handlers()

    def _register_handlers(self) -> None:
        handler = _DocumentIssuanceCommandHandler(self)
        for command_type in sorted(DOCUMENT_ISSUANCE_COMMAND_TYPES):
            self._command_bus.register_handler(command_type, handler)

    def _is_persist_accepted(self, persist_result: Any) -> bool:
        if hasattr(persist_result, "accepted"):
            return bool(getattr(persist_result, "accepted"))
        if isinstance(persist_result, dict):
            return bool(persist_result.get("accepted"))
        return bool(persist_result)

    def _execute_issue_command(
        self,
        command: Command,
    ) -> DocumentIssuanceExecutionResult:
        doc_type = resolve_doc_type_for_issue_command(command.command_type)
        if doc_type is None:
            raise ValueError(
                f"Unsupported document issue command type: {command.command_type}"
            )

        mapped_doc_type = resolve_document_type(command.command_type)
        if mapped_doc_type != doc_type:
            raise ValueError(
                "Document type mapping mismatch between issuance registry "
                "and document registry."
            )

        event_type = resolve_event_type_for_issue_command(command.command_type)
        if event_type is None:
            raise ValueError(
                f"Unsupported document issue command type: {command.command_type}"
            )

        render_plan = DocumentBuilder.build_for_command(
            command=command,
            doc_type=doc_type,
            provider=self._document_provider,
        )

        # Assign document number from numbering provider if configured
        doc_number: Optional[str] = None
        if self._numbering_provider is not None:
            policy = self._numbering_provider.get_policy(
                business_id_str=str(command.business_id),
                doc_type=doc_type,
                branch_id_str=str(command.branch_id) if command.branch_id else None,
            )
            if policy is not None:
                doc_number = self._numbering_provider.get_and_advance(
                    policy=policy,
                    issued_at=command.issued_at,
                )

        payload = build_document_issued_payload(
            command=command,
            doc_type=doc_type,
            render_plan=render_plan,
            doc_number=doc_number,
        )

        event_data = self._event_factory(
            command=command,
            event_type=event_type,
            payload=payload,
        )
        persist_result = self._persist_event(
            event_data=event_data,
            context=self._business_context,
            registry=self._event_type_registry,
            scope_requirement=command.scope_requirement,
        )

        applied = False
        if self._is_persist_accepted(persist_result):
            self._projection_store.apply(event_type=event_type, payload=payload)
            applied = True

        return DocumentIssuanceExecutionResult(
            event_type=event_type,
            event_data=event_data,
            persist_result=persist_result,
            projection_applied=applied,
        )

    def issue_receipt(
        self,
        *,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None,
        document_id: uuid.UUID,
        payload: dict,
        actor_context: ActorContext,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ):
        request = ReceiptIssueRequest(
            business_id=business_id,
            branch_id=branch_id,
            document_id=document_id,
            payload=payload,
        )
        command = request.to_command(
            command_id=command_id,
            correlation_id=correlation_id,
            issued_at=issued_at,
            actor_context=actor_context,
        )
        return self._command_bus.handle(command)

    def issue_quote(
        self,
        *,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None,
        document_id: uuid.UUID,
        payload: dict,
        actor_context: ActorContext,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ):
        request = QuoteIssueRequest(
            business_id=business_id,
            branch_id=branch_id,
            document_id=document_id,
            payload=payload,
        )
        command = request.to_command(
            command_id=command_id,
            correlation_id=correlation_id,
            issued_at=issued_at,
            actor_context=actor_context,
        )
        return self._command_bus.handle(command)

    def issue_invoice(
        self,
        *,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None,
        document_id: uuid.UUID,
        payload: dict,
        actor_context: ActorContext,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ):
        request = InvoiceIssueRequest(
            business_id=business_id,
            branch_id=branch_id,
            document_id=document_id,
            payload=payload,
        )
        command = request.to_command(
            command_id=command_id,
            correlation_id=correlation_id,
            issued_at=issued_at,
            actor_context=actor_context,
        )
        return self._command_bus.handle(command)

    def _issue(
        self,
        request_cls,
        *,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None,
        document_id: uuid.UUID,
        payload: dict,
        actor_context: ActorContext,
        command_id: uuid.UUID,
        correlation_id: uuid.UUID,
        issued_at: datetime,
    ):
        """Generic issue helper — reduces boilerplate for all document types."""
        request = request_cls(
            business_id=business_id,
            branch_id=branch_id,
            document_id=document_id,
            payload=payload,
        )
        command = request.to_command(
            command_id=command_id,
            correlation_id=correlation_id,
            issued_at=issued_at,
            actor_context=actor_context,
        )
        return self._command_bus.handle(command)

    def _issue_kwargs(self, request_cls, **kw):
        """Thin wrapper: unpack common kwargs and delegate to _issue."""
        return self._issue(request_cls, **kw)

    # ── Public issue_* surface (one per document type) ────────────

    def issue_proforma_invoice(self, *, business_id, branch_id, document_id, payload,
                               actor_context, command_id, correlation_id, issued_at):
        return self._issue(ProformaInvoiceIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_delivery_note(self, *, business_id, branch_id, document_id, payload,
                            actor_context, command_id, correlation_id, issued_at):
        return self._issue(DeliveryNoteIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_credit_note(self, *, business_id, branch_id, document_id, payload,
                          actor_context, command_id, correlation_id, issued_at):
        return self._issue(CreditNoteIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_debit_note(self, *, business_id, branch_id, document_id, payload,
                         actor_context, command_id, correlation_id, issued_at):
        return self._issue(DebitNoteIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_purchase_order(self, *, business_id, branch_id, document_id, payload,
                             actor_context, command_id, correlation_id, issued_at):
        return self._issue(PurchaseOrderIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_goods_receipt_note(self, *, business_id, branch_id, document_id, payload,
                                 actor_context, command_id, correlation_id, issued_at):
        return self._issue(GoodsReceiptNoteIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_sales_order(self, *, business_id, branch_id, document_id, payload,
                          actor_context, command_id, correlation_id, issued_at):
        return self._issue(SalesOrderIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_refund_note(self, *, business_id, branch_id, document_id, payload,
                          actor_context, command_id, correlation_id, issued_at):
        return self._issue(RefundNoteIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_work_order(self, *, business_id, branch_id, document_id, payload,
                         actor_context, command_id, correlation_id, issued_at):
        return self._issue(WorkOrderIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_material_requisition(self, *, business_id, branch_id, document_id, payload,
                                   actor_context, command_id, correlation_id, issued_at):
        return self._issue(MaterialRequisitionIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_cutting_list(self, *, business_id, branch_id, document_id, payload,
                           actor_context, command_id, correlation_id, issued_at):
        return self._issue(CuttingListIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_completion_certificate(self, *, business_id, branch_id, document_id, payload,
                                     actor_context, command_id, correlation_id, issued_at):
        return self._issue(CompletionCertificateIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_kitchen_order_ticket(self, *, business_id, branch_id, document_id, payload,
                                   actor_context, command_id, correlation_id, issued_at):
        return self._issue(KitchenOrderTicketIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_folio(self, *, business_id, branch_id, document_id, payload,
                    actor_context, command_id, correlation_id, issued_at):
        return self._issue(FolioIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_reservation_confirmation(self, *, business_id, branch_id, document_id, payload,
                                       actor_context, command_id, correlation_id, issued_at):
        return self._issue(ReservationConfirmationIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_registration_card(self, *, business_id, branch_id, document_id, payload,
                                actor_context, command_id, correlation_id, issued_at):
        return self._issue(RegistrationCardIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_cancellation_note(self, *, business_id, branch_id, document_id, payload,
                                actor_context, command_id, correlation_id, issued_at):
        return self._issue(CancellationNoteIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_payment_voucher(self, *, business_id, branch_id, document_id, payload,
                              actor_context, command_id, correlation_id, issued_at):
        return self._issue(PaymentVoucherIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_petty_cash_voucher(self, *, business_id, branch_id, document_id, payload,
                                 actor_context, command_id, correlation_id, issued_at):
        return self._issue(PettyCashVoucherIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_stock_transfer_note(self, *, business_id, branch_id, document_id, payload,
                                  actor_context, command_id, correlation_id, issued_at):
        return self._issue(StockTransferNoteIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_stock_adjustment_note(self, *, business_id, branch_id, document_id, payload,
                                    actor_context, command_id, correlation_id, issued_at):
        return self._issue(StockAdjustmentNoteIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_statement(self, *, business_id, branch_id, document_id, payload,
                        actor_context, command_id, correlation_id, issued_at):
        return self._issue(StatementIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    def issue_cash_session_reconciliation(self, *, business_id, branch_id, document_id, payload,
                                          actor_context, command_id, correlation_id, issued_at):
        return self._issue(CashSessionReconciliationIssueRequest, business_id=business_id,
                           branch_id=branch_id, document_id=document_id, payload=payload,
                           actor_context=actor_context, command_id=command_id,
                           correlation_id=correlation_id, issued_at=issued_at)

    @property
    def projection_store(self) -> DocumentIssuanceProjectionStore:
        return self._projection_store
