"""
BOS Customer Engine — Commands
==============================
Platform-level identity + Tenant-level profiles.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

# Scope constants (mirrors core/context/scope_guard.py values)
SCOPE_BUSINESS_ALLOWED = "BUSINESS_SCOPE"
SCOPE_BRANCH_REQUIRED = "BRANCH_REQUIRED"
ACTOR_REQUIRED = "ACTOR_REQUIRED"

# Platform tenant for global customer identity
PLATFORM_BUSINESS_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


# ── Platform-Level Commands ───────────────────────────────────

@dataclass(frozen=True)
class RegisterGlobalCustomerRequest:
    """Register a new global customer identity on the platform."""
    global_customer_id: str
    phone_hash: str
    actor_id: str
    issued_at: datetime
    source_engine: str = "customer"

    def __post_init__(self):
        if not self.global_customer_id:
            raise ValueError("global_customer_id must be non-empty.")
        if not self.phone_hash:
            raise ValueError("phone_hash must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "customer.global.register.request",
            "business_id": PLATFORM_BUSINESS_ID,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "global_customer_id": self.global_customer_id,
                "phone_hash": self.phone_hash,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class RequestClientLinkRequest:
    """Business requests to link with a customer (cashier adds to My Clients)."""
    global_customer_id: str
    requesting_business_id: str
    actor_id: str
    issued_at: datetime
    source_engine: str = "customer"

    def __post_init__(self):
        if not self.global_customer_id:
            raise ValueError("global_customer_id must be non-empty.")
        if not self.requesting_business_id:
            raise ValueError("requesting_business_id must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "customer.link.request.request",
            "business_id": PLATFORM_BUSINESS_ID,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "global_customer_id": self.global_customer_id,
                "requesting_business_id": self.requesting_business_id,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class ApproveClientLinkRequest:
    """Customer approves a business link request (from customer dashboard)."""
    global_customer_id: str
    approved_business_id: str
    approved_scopes: Tuple[str, ...]
    actor_id: str
    issued_at: datetime
    source_engine: str = "customer"

    def __post_init__(self):
        if not self.global_customer_id:
            raise ValueError("global_customer_id must be non-empty.")
        if not self.approved_business_id:
            raise ValueError("approved_business_id must be non-empty.")
        if not self.approved_scopes:
            raise ValueError("approved_scopes must have at least one scope.")
        from engines.customer.events import VALID_CONSENT_SCOPES
        for scope in self.approved_scopes:
            if scope not in VALID_CONSENT_SCOPES:
                raise ValueError(f"Invalid scope: {scope}")

    def to_command(self) -> dict:
        return {
            "command_type": "customer.link.approve.request",
            "business_id": PLATFORM_BUSINESS_ID,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "global_customer_id": self.global_customer_id,
                "approved_business_id": self.approved_business_id,
                "approved_scopes": list(self.approved_scopes),
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class RevokeClientLinkRequest:
    """Customer revokes a business link."""
    global_customer_id: str
    revoked_business_id: str
    reason: str
    actor_id: str
    issued_at: datetime
    source_engine: str = "customer"

    def __post_init__(self):
        if not self.global_customer_id:
            raise ValueError("global_customer_id must be non-empty.")
        if not self.revoked_business_id:
            raise ValueError("revoked_business_id must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "customer.link.revoke.request",
            "business_id": PLATFORM_BUSINESS_ID,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "global_customer_id": self.global_customer_id,
                "revoked_business_id": self.revoked_business_id,
                "reason": self.reason,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class UpdateConsentScopesRequest:
    """Customer updates consent scopes for a linked business."""
    global_customer_id: str
    target_business_id: str
    new_scopes: Tuple[str, ...]
    actor_id: str
    issued_at: datetime
    source_engine: str = "customer"

    def __post_init__(self):
        if not self.global_customer_id:
            raise ValueError("global_customer_id must be non-empty.")
        if not self.target_business_id:
            raise ValueError("target_business_id must be non-empty.")
        from engines.customer.events import VALID_CONSENT_SCOPES
        for scope in self.new_scopes:
            if scope not in VALID_CONSENT_SCOPES:
                raise ValueError(f"Invalid scope: {scope}")

    def to_command(self) -> dict:
        return {
            "command_type": "customer.consent.update_scope.request",
            "business_id": PLATFORM_BUSINESS_ID,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "global_customer_id": self.global_customer_id,
                "target_business_id": self.target_business_id,
                "new_scopes": list(self.new_scopes),
                "issued_at": str(self.issued_at),
            },
        }


# ── Tenant-Level Commands ─────────────────────────────────────

@dataclass(frozen=True)
class CreateBusinessCustomerProfileRequest:
    """Create a customer profile within a business (after link approved)."""
    business_customer_id: str
    global_customer_id: str
    business_id: uuid.UUID
    display_name: str
    approved_scopes: Tuple[str, ...]
    actor_id: str
    issued_at: datetime
    source_engine: str = "customer"

    def __post_init__(self):
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if not self.global_customer_id:
            raise ValueError("global_customer_id must be non-empty.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")

    def to_command(self) -> dict:
        return {
            "command_type": "customer.profile.create.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "global_customer_id": self.global_customer_id,
                "display_name": self.display_name,
                "approved_scopes": list(self.approved_scopes),
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class UpdateBusinessCustomerProfileRequest:
    """Update a customer profile within a business."""
    business_customer_id: str
    business_id: uuid.UUID
    changes: dict
    actor_id: str
    issued_at: datetime
    source_engine: str = "customer"

    def __post_init__(self):
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.changes:
            raise ValueError("changes must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "customer.profile.update.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "changes": self.changes,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class AssignCustomerSegmentRequest:
    """Assign a customer to a segment within a business."""
    business_customer_id: str
    business_id: uuid.UUID
    segment: str
    actor_id: str
    issued_at: datetime
    source_engine: str = "customer"

    def __post_init__(self):
        if not self.business_customer_id:
            raise ValueError("business_customer_id must be non-empty.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not self.segment:
            raise ValueError("segment must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "customer.segment.assign.request",
            "business_id": self.business_id,
            "branch_id": None,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BUSINESS_ALLOWED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "business_customer_id": self.business_customer_id,
                "segment": self.segment,
                "issued_at": str(self.issued_at),
            },
        }
