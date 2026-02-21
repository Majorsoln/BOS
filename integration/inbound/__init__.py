"""
BOS Integration — Inbound Adapter Framework
================================================
Receives events from external systems, validates, translates
to BOS commands, and dispatches to the command bus.

Doctrine: External systems NEVER bypass command validation.
All inbound data goes through: validate → translate → dispatch.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, Tuple

from integration.adapters import (
    AuthenticationError,
    Direction,
    ExternalEventReference,
    IntegrationError,
    TranslationError,
    ValidationError,
)
from integration.audit_log import IntegrationAuditLog


# ══════════════════════════════════════════════════════════════
# INBOUND RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class InboundResult:
    """Result of processing an inbound external event."""

    success: bool
    command: Optional[Dict[str, Any]] = None  # translated BOS command dict
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    external_event_id: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# INBOUND ADAPTER PROTOCOL
# ══════════════════════════════════════════════════════════════

class InboundAdapter(ABC):
    """
    Base class for inbound integration adapters.

    Subclasses implement system-specific validation and translation.
    Adapters are stateless — no internal mutable state.
    """

    @property
    @abstractmethod
    def system_id(self) -> str:
        """Unique identifier for the external system."""
        ...

    @property
    @abstractmethod
    def system_type(self) -> str:
        """Type category (payment_gateway, erp, kds, etc.)."""
        ...

    @abstractmethod
    def validate(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate the external event payload.

        Returns (is_valid, error_message).
        Must check: required fields, data types, business_id present.
        """
        ...

    @abstractmethod
    def translate_to_command(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Translate external event to a BOS command dict.

        Returns a dict with at minimum:
          command_type, business_id, payload, actor_id
        """
        ...

    def extract_event_id(self, payload: Dict[str, Any]) -> Optional[str]:
        """Extract the external system's event ID for idempotency."""
        return payload.get("event_id") or payload.get("id")


# ══════════════════════════════════════════════════════════════
# INBOUND ADAPTER REGISTRY
# ══════════════════════════════════════════════════════════════

class InboundAdapterRegistry:
    """Registry of inbound adapters by system_id."""

    def __init__(self) -> None:
        self._adapters: Dict[str, InboundAdapter] = {}

    def register(self, adapter: InboundAdapter) -> None:
        self._adapters[adapter.system_id] = adapter

    def get(self, system_id: str) -> Optional[InboundAdapter]:
        return self._adapters.get(system_id)

    def list_system_ids(self) -> List[str]:
        return list(self._adapters.keys())


# ══════════════════════════════════════════════════════════════
# INBOUND DISPATCHER
# ══════════════════════════════════════════════════════════════

class CommandDispatchPort(Protocol):
    """Port for dispatching commands to BOS command bus."""

    def dispatch(self, command: Dict[str, Any]) -> Any:
        ...


class InboundDispatcher:
    """
    Receives external events, routes to the correct adapter,
    validates, translates, and dispatches to the BOS command bus.

    All interactions are audit-logged.
    """

    def __init__(
        self,
        registry: InboundAdapterRegistry,
        command_dispatch: CommandDispatchPort,
        audit_log: IntegrationAuditLog,
    ) -> None:
        self._registry = registry
        self._dispatch = command_dispatch
        self._audit = audit_log

    def process(
        self,
        system_id: str,
        payload: Dict[str, Any],
        received_at: datetime,
    ) -> InboundResult:
        """
        Process an inbound external event end-to-end.

        1. Find adapter
        2. Validate payload
        3. Translate to BOS command
        4. Dispatch to command bus
        5. Log audit trail
        """
        adapter = self._registry.get(system_id)
        if adapter is None:
            return InboundResult(
                success=False,
                error_code="UNKNOWN_SYSTEM",
                error_message=f"No adapter registered for system '{system_id}'.",
            )

        external_event_id = adapter.extract_event_id(payload)
        payload_hash = ExternalEventReference.compute_payload_hash(payload)
        business_id = payload.get("business_id")

        # Tenant isolation: business_id MUST be present
        if business_id is None:
            return InboundResult(
                success=False,
                error_code="MISSING_BUSINESS_ID",
                error_message="Inbound event must include business_id.",
                external_event_id=external_event_id,
            )

        if isinstance(business_id, str):
            try:
                business_id = uuid.UUID(business_id)
            except ValueError:
                return InboundResult(
                    success=False,
                    error_code="INVALID_BUSINESS_ID",
                    error_message="business_id must be a valid UUID.",
                    external_event_id=external_event_id,
                )

        # Step 1: Validate
        try:
            is_valid, error_msg = adapter.validate(payload)
            if not is_valid:
                self._audit.record_failure(
                    business_id=business_id,
                    external_system_id=system_id,
                    direction=Direction.INBOUND,
                    event_type=payload.get("event_type", "unknown"),
                    actor_id=f"system.integration.{system_id}",
                    payload_hash=payload_hash,
                    occurred_at=received_at,
                    error_code="VALIDATION_FAILED",
                    error_message=error_msg or "Validation failed.",
                    external_event_id=external_event_id,
                )
                return InboundResult(
                    success=False,
                    error_code="VALIDATION_FAILED",
                    error_message=error_msg,
                    external_event_id=external_event_id,
                )
        except IntegrationError as e:
            self._audit.record_failure(
                business_id=business_id,
                external_system_id=system_id,
                direction=Direction.INBOUND,
                event_type=payload.get("event_type", "unknown"),
                actor_id=f"system.integration.{system_id}",
                payload_hash=payload_hash,
                occurred_at=received_at,
                error_code=type(e).__name__,
                error_message=str(e),
                external_event_id=external_event_id,
            )
            return InboundResult(
                success=False,
                error_code=type(e).__name__,
                error_message=str(e),
                external_event_id=external_event_id,
            )

        # Step 2: Translate
        try:
            command = adapter.translate_to_command(payload)
        except IntegrationError as e:
            self._audit.record_failure(
                business_id=business_id,
                external_system_id=system_id,
                direction=Direction.INBOUND,
                event_type=payload.get("event_type", "unknown"),
                actor_id=f"system.integration.{system_id}",
                payload_hash=payload_hash,
                occurred_at=received_at,
                error_code="TRANSLATION_FAILED",
                error_message=str(e),
                external_event_id=external_event_id,
            )
            return InboundResult(
                success=False,
                error_code="TRANSLATION_FAILED",
                error_message=str(e),
                external_event_id=external_event_id,
            )

        # Step 3: Dispatch to BOS command bus
        try:
            self._dispatch.dispatch(command)
        except Exception as e:
            self._audit.record_failure(
                business_id=business_id,
                external_system_id=system_id,
                direction=Direction.INBOUND,
                event_type=payload.get("event_type", "unknown"),
                actor_id=f"system.integration.{system_id}",
                payload_hash=payload_hash,
                occurred_at=received_at,
                error_code="DISPATCH_FAILED",
                error_message=str(e),
                external_event_id=external_event_id,
            )
            return InboundResult(
                success=False,
                error_code="DISPATCH_FAILED",
                error_message=str(e),
                external_event_id=external_event_id,
            )

        # Step 4: Audit success
        self._audit.record_success(
            business_id=business_id,
            external_system_id=system_id,
            direction=Direction.INBOUND,
            event_type=payload.get("event_type", "unknown"),
            actor_id=f"system.integration.{system_id}",
            payload_hash=payload_hash,
            occurred_at=received_at,
            external_event_id=external_event_id,
        )

        return InboundResult(
            success=True,
            command=command,
            external_event_id=external_event_id,
        )
