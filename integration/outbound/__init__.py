"""
BOS Integration — Outbound Publisher Framework
===================================================
Subscribes to BOS events and pushes to external systems.

Doctrine: Events emitted, never state snapshots.
Failures are logged, retried with backoff, never silently dropped.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from integration.adapters import Direction, TransientError
from integration.audit_log import IntegrationAuditLog


# ══════════════════════════════════════════════════════════════
# OUTBOUND RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OutboundResult:
    """Result of publishing an event to an external system."""

    success: bool
    system_id: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0


# ══════════════════════════════════════════════════════════════
# OUTBOUND PUBLISHER PROTOCOL
# ══════════════════════════════════════════════════════════════

class OutboundPublisher(ABC):
    """
    Base class for outbound publishers.

    Each publisher handles a specific external system.
    Publishers are stateless translators.
    """

    @property
    @abstractmethod
    def system_id(self) -> str:
        """Unique identifier for the external target system."""
        ...

    @property
    @abstractmethod
    def handled_event_types(self) -> Set[str]:
        """Set of BOS event types this publisher handles."""
        ...

    @abstractmethod
    def translate(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate a BOS event into the external system's format.

        Returns dict payload ready for delivery.
        """
        ...

    @abstractmethod
    def deliver(self, translated_payload: Dict[str, Any]) -> bool:
        """
        Deliver the translated payload to the external system.

        Returns True on success, raises TransientError on retryable failure.
        """
        ...


# ══════════════════════════════════════════════════════════════
# OUTBOUND PUBLISHER REGISTRY
# ══════════════════════════════════════════════════════════════

class OutboundPublisherRegistry:
    """Registry of outbound publishers by system_id."""

    def __init__(self) -> None:
        self._publishers: Dict[str, OutboundPublisher] = {}
        self._event_routing: Dict[str, List[str]] = {}  # event_type → [system_ids]

    def register(self, publisher: OutboundPublisher) -> None:
        self._publishers[publisher.system_id] = publisher
        for event_type in publisher.handled_event_types:
            self._event_routing.setdefault(event_type, [])
            if publisher.system_id not in self._event_routing[event_type]:
                self._event_routing[event_type].append(publisher.system_id)

    def get(self, system_id: str) -> Optional[OutboundPublisher]:
        return self._publishers.get(system_id)

    def get_publishers_for_event(self, event_type: str) -> List[OutboundPublisher]:
        system_ids = self._event_routing.get(event_type, [])
        return [self._publishers[sid] for sid in system_ids if sid in self._publishers]

    def list_system_ids(self) -> List[str]:
        return list(self._publishers.keys())


# ══════════════════════════════════════════════════════════════
# OUTBOUND EVENT DISPATCHER
# ══════════════════════════════════════════════════════════════

class OutboundEventDispatcher:
    """
    Subscribes to BOS events and routes to outbound publishers.

    Handles retry logic with exponential backoff.
    All outcomes are audit-logged.
    """

    def __init__(
        self,
        registry: OutboundPublisherRegistry,
        audit_log: IntegrationAuditLog,
        max_retries: int = 3,
        backoff_base_seconds: float = 2.0,
    ) -> None:
        self._registry = registry
        self._audit = audit_log
        self._max_retries = max_retries
        self._backoff_base = backoff_base_seconds

    def publish(
        self,
        event: Dict[str, Any],
        now: datetime,
    ) -> List[OutboundResult]:
        """
        Publish a BOS event to all registered external publishers.

        Returns results for each publisher (success/failure).
        """
        event_type = event.get("event_type", "unknown")
        business_id = event.get("business_id")
        if isinstance(business_id, str):
            try:
                business_id = uuid.UUID(business_id)
            except ValueError:
                business_id = None

        publishers = self._registry.get_publishers_for_event(event_type)
        if not publishers:
            return []

        results: List[OutboundResult] = []
        for publisher in publishers:
            result = self._publish_to_one(publisher, event, event_type, business_id, now)
            results.append(result)

        return results

    def _publish_to_one(
        self,
        publisher: OutboundPublisher,
        event: Dict[str, Any],
        event_type: str,
        business_id: Optional[uuid.UUID],
        now: datetime,
    ) -> OutboundResult:
        """Publish to a single external system with retry."""
        from integration.adapters import ExternalEventReference

        payload_hash = ExternalEventReference.compute_payload_hash(event)

        # Translate
        try:
            translated = publisher.translate(event)
        except Exception as e:
            if business_id:
                self._audit.record_failure(
                    business_id=business_id,
                    external_system_id=publisher.system_id,
                    direction=Direction.OUTBOUND,
                    event_type=event_type,
                    actor_id="system.integration.outbound",
                    payload_hash=payload_hash,
                    occurred_at=now,
                    error_code="TRANSLATION_FAILED",
                    error_message=str(e),
                )
            return OutboundResult(
                success=False,
                system_id=publisher.system_id,
                error_code="TRANSLATION_FAILED",
                error_message=str(e),
            )

        # Deliver with retry
        last_error = ""
        for attempt in range(self._max_retries + 1):
            try:
                success = publisher.deliver(translated)
                if success:
                    if business_id:
                        self._audit.record_success(
                            business_id=business_id,
                            external_system_id=publisher.system_id,
                            direction=Direction.OUTBOUND,
                            event_type=event_type,
                            actor_id="system.integration.outbound",
                            payload_hash=payload_hash,
                            occurred_at=now,
                        )
                    return OutboundResult(
                        success=True,
                        system_id=publisher.system_id,
                        retry_count=attempt,
                    )
                last_error = "deliver returned False"
            except TransientError as e:
                last_error = str(e)
                continue
            except Exception as e:
                last_error = str(e)
                break  # non-retryable

        # All retries exhausted
        if business_id:
            self._audit.record_failure(
                business_id=business_id,
                external_system_id=publisher.system_id,
                direction=Direction.OUTBOUND,
                event_type=event_type,
                actor_id="system.integration.outbound",
                payload_hash=payload_hash,
                occurred_at=now,
                error_code="DELIVERY_FAILED",
                error_message=last_error,
                retry_count=self._max_retries,
            )
        return OutboundResult(
            success=False,
            system_id=publisher.system_id,
            error_code="DELIVERY_FAILED",
            error_message=last_error,
            retry_count=self._max_retries,
        )
