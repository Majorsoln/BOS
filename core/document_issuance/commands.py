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
    DOC_INVOICE_ISSUE_REQUEST,
    DOC_QUOTE_ISSUE_REQUEST,
    DOC_RECEIPT_ISSUE_REQUEST,
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
