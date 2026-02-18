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
    InvoiceIssueRequest,
    QuoteIssueRequest,
    ReceiptIssueRequest,
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
    ):
        self._business_context = business_context
        self._dispatcher = dispatcher
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or DocumentIssuanceProjectionStore()
        self._document_provider = document_provider

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
        payload = build_document_issued_payload(
            command=command,
            doc_type=doc_type,
            render_plan=render_plan,
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

    @property
    def projection_store(self) -> DocumentIssuanceProjectionStore:
        return self._projection_store
