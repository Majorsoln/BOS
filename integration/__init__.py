"""
BOS Integration Layer — Public API
======================================
Controlled gateway for external system communication.

Doctrine: External systems NEVER write directly to BOS core data.
All integration is event-driven and permission-based.

Inbound:  External event → validate → translate → BOS command bus
Outbound: BOS event → translate → push to external system
"""

from integration.adapters import (
    AdapterConfig,
    AuthenticationError,
    Direction,
    ExternalEventReference,
    IntegrationError,
    TransientError,
    TranslationError,
    ValidationError,
    verify_hmac_signature,
)
from integration.audit_log import IntegrationAuditEntry, IntegrationAuditLog
from integration.inbound import (
    InboundAdapter,
    InboundAdapterRegistry,
    InboundDispatcher,
    InboundResult,
)
from integration.outbound import (
    OutboundEventDispatcher,
    OutboundPublisher,
    OutboundPublisherRegistry,
    OutboundResult,
)
from integration.permissions import (
    INTEGRATION_CONFIGURE,
    INTEGRATION_DISABLE,
    INTEGRATION_ENABLE,
    INTEGRATION_TEST,
    INTEGRATION_VIEW_AUDIT,
    IntegrationGrant,
    IntegrationPermissionChecker,
)

__all__ = [
    # Adapters
    "AdapterConfig",
    "Direction",
    "ExternalEventReference",
    "verify_hmac_signature",
    # Errors
    "IntegrationError",
    "ValidationError",
    "TranslationError",
    "AuthenticationError",
    "TransientError",
    # Audit
    "IntegrationAuditEntry",
    "IntegrationAuditLog",
    # Inbound
    "InboundAdapter",
    "InboundAdapterRegistry",
    "InboundDispatcher",
    "InboundResult",
    # Outbound
    "OutboundPublisher",
    "OutboundPublisherRegistry",
    "OutboundEventDispatcher",
    "OutboundResult",
    # Permissions
    "IntegrationGrant",
    "IntegrationPermissionChecker",
    "INTEGRATION_CONFIGURE",
    "INTEGRATION_ENABLE",
    "INTEGRATION_DISABLE",
    "INTEGRATION_TEST",
    "INTEGRATION_VIEW_AUDIT",
]
