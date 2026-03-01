"""
BOS Customer Engine — Service Layer
====================================
Platform identity service + Tenant profile service + Projection stores.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from core.commands.rejection import RejectionReason

from engines.customer.events import (
    GLOBAL_CUSTOMER_REGISTERED_V1,
    CLIENT_LINK_REQUESTED_V1,
    CLIENT_LINK_APPROVED_V1,
    CLIENT_LINK_REVOKED_V1,
    CONSENT_SCOPE_UPDATED_V1,
    BUSINESS_CUSTOMER_PROFILE_CREATED_V1,
    BUSINESS_CUSTOMER_PROFILE_UPDATED_V1,
    BUSINESS_CUSTOMER_SEGMENT_ASSIGNED_V1,
    COMMAND_TO_EVENT_TYPE,
    PAYLOAD_BUILDERS,
)


# ── Data Records ──────────────────────────────────────────────

@dataclass(frozen=True)
class GlobalCustomerRecord:
    global_customer_id: str
    phone_hash: str
    status: str  # ACTIVE / SUSPENDED
    registered_at: str


@dataclass(frozen=True)
class LinkRecord:
    global_customer_id: str
    business_id: str
    status: str  # PENDING / APPROVED / REVOKED
    approved_scopes: tuple
    requested_at: str
    approved_at: Optional[str] = None
    revoked_at: Optional[str] = None


@dataclass(frozen=True)
class BusinessCustomerProfileRecord:
    business_customer_id: str
    global_customer_id: str
    business_id: str
    display_name: str
    segment: str
    approved_scopes: tuple
    created_at: str


# ── Platform Projection Store ─────────────────────────────────

class CustomerPlatformProjectionStore:
    """In-memory projection of global customer identities and links."""

    def __init__(self):
        self._events: List[dict] = []
        self._customers: Dict[str, GlobalCustomerRecord] = {}
        self._by_phone_hash: Dict[str, str] = {}  # phone_hash → global_customer_id
        self._links: Dict[str, Dict[str, LinkRecord]] = {}  # global_cid → {biz_id → link}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type == GLOBAL_CUSTOMER_REGISTERED_V1:
            gcid = payload["global_customer_id"]
            self._customers[gcid] = GlobalCustomerRecord(
                global_customer_id=gcid,
                phone_hash=payload["phone_hash"],
                status="ACTIVE",
                registered_at=payload.get("registered_at", ""),
            )
            self._by_phone_hash[payload["phone_hash"]] = gcid

        elif event_type == CLIENT_LINK_REQUESTED_V1:
            gcid = payload["global_customer_id"]
            biz = payload["requesting_business_id"]
            if gcid not in self._links:
                self._links[gcid] = {}
            self._links[gcid][biz] = LinkRecord(
                global_customer_id=gcid,
                business_id=biz,
                status="PENDING",
                approved_scopes=(),
                requested_at=payload.get("requested_at", ""),
            )

        elif event_type == CLIENT_LINK_APPROVED_V1:
            gcid = payload["global_customer_id"]
            biz = payload["approved_business_id"]
            if gcid in self._links and biz in self._links[gcid]:
                old = self._links[gcid][biz]
                self._links[gcid][biz] = LinkRecord(
                    global_customer_id=gcid,
                    business_id=biz,
                    status="APPROVED",
                    approved_scopes=tuple(payload.get("approved_scopes", [])),
                    requested_at=old.requested_at,
                    approved_at=payload.get("approved_at", ""),
                )

        elif event_type == CLIENT_LINK_REVOKED_V1:
            gcid = payload["global_customer_id"]
            biz = payload["revoked_business_id"]
            if gcid in self._links and biz in self._links[gcid]:
                old = self._links[gcid][biz]
                self._links[gcid][biz] = LinkRecord(
                    global_customer_id=gcid,
                    business_id=biz,
                    status="REVOKED",
                    approved_scopes=(),
                    requested_at=old.requested_at,
                    approved_at=old.approved_at,
                    revoked_at=payload.get("revoked_at", ""),
                )

        elif event_type == CONSENT_SCOPE_UPDATED_V1:
            gcid = payload["global_customer_id"]
            biz = payload["target_business_id"]
            if gcid in self._links and biz in self._links[gcid]:
                old = self._links[gcid][biz]
                self._links[gcid][biz] = LinkRecord(
                    global_customer_id=gcid,
                    business_id=biz,
                    status=old.status,
                    approved_scopes=tuple(payload.get("new_scopes", [])),
                    requested_at=old.requested_at,
                    approved_at=old.approved_at,
                    revoked_at=old.revoked_at,
                )

    def get_customer(self, global_customer_id: str) -> Optional[GlobalCustomerRecord]:
        return self._customers.get(global_customer_id)

    def lookup_by_phone_hash(self, phone_hash: str) -> Optional[str]:
        return self._by_phone_hash.get(phone_hash)

    def get_link(self, global_customer_id: str, business_id: str) -> Optional[LinkRecord]:
        return self._links.get(global_customer_id, {}).get(business_id)

    def get_links_for_customer(self, global_customer_id: str) -> List[LinkRecord]:
        return list(self._links.get(global_customer_id, {}).values())

    def get_approved_links(self, global_customer_id: str) -> List[LinkRecord]:
        return [l for l in self.get_links_for_customer(global_customer_id) if l.status == "APPROVED"]

    @property
    def customer_count(self) -> int:
        return len(self._customers)

    @property
    def event_count(self) -> int:
        return len(self._events)

    def truncate(self):
        self._events.clear()
        self._customers.clear()
        self._by_phone_hash.clear()
        self._links.clear()


# ── Business Profile Projection Store ─────────────────────────

class CustomerProfileProjectionStore:
    """In-memory projection of business customer profiles (tenant-scoped)."""

    def __init__(self):
        self._events: List[dict] = []
        self._profiles: Dict[str, BusinessCustomerProfileRecord] = {}
        self._by_global_id: Dict[str, str] = {}  # global_cid → business_customer_id

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type == BUSINESS_CUSTOMER_PROFILE_CREATED_V1:
            bcid = payload["business_customer_id"]
            gcid = payload["global_customer_id"]
            self._profiles[bcid] = BusinessCustomerProfileRecord(
                business_customer_id=bcid,
                global_customer_id=gcid,
                business_id=str(payload.get("business_id", "")),
                display_name=payload.get("display_name", ""),
                segment="",
                approved_scopes=tuple(payload.get("approved_scopes", [])),
                created_at=payload.get("created_at", ""),
            )
            self._by_global_id[gcid] = bcid

        elif event_type == BUSINESS_CUSTOMER_PROFILE_UPDATED_V1:
            bcid = payload["business_customer_id"]
            old = self._profiles.get(bcid)
            if old:
                changes = payload.get("changes", {})
                self._profiles[bcid] = BusinessCustomerProfileRecord(
                    business_customer_id=bcid,
                    global_customer_id=old.global_customer_id,
                    business_id=old.business_id,
                    display_name=changes.get("display_name", old.display_name),
                    segment=old.segment,
                    approved_scopes=old.approved_scopes,
                    created_at=old.created_at,
                )

        elif event_type == BUSINESS_CUSTOMER_SEGMENT_ASSIGNED_V1:
            bcid = payload["business_customer_id"]
            old = self._profiles.get(bcid)
            if old:
                self._profiles[bcid] = BusinessCustomerProfileRecord(
                    business_customer_id=bcid,
                    global_customer_id=old.global_customer_id,
                    business_id=old.business_id,
                    display_name=old.display_name,
                    segment=payload["segment"],
                    approved_scopes=old.approved_scopes,
                    created_at=old.created_at,
                )

    def get_profile(self, business_customer_id: str) -> Optional[BusinessCustomerProfileRecord]:
        return self._profiles.get(business_customer_id)

    def get_profile_by_global_id(self, global_customer_id: str) -> Optional[BusinessCustomerProfileRecord]:
        bcid = self._by_global_id.get(global_customer_id)
        return self._profiles.get(bcid) if bcid else None

    def list_profiles(self) -> List[BusinessCustomerProfileRecord]:
        return list(self._profiles.values())

    @property
    def profile_count(self) -> int:
        return len(self._profiles)

    @property
    def event_count(self) -> int:
        return len(self._events)

    def truncate(self):
        self._events.clear()
        self._profiles.clear()
        self._by_global_id.clear()


# ── Customer Identity Service (Platform) ──────────────────────

class CustomerIdentityService:
    """Manages global customer identities and consent links."""

    def __init__(
        self,
        *,
        event_factory,
        persist_event,
        event_type_registry,
        projection_store: CustomerPlatformProjectionStore,
        feature_flag_evaluator=None,
    ):
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection = projection_store
        self._feature_flags = feature_flag_evaluator

    def _execute_command(self, command) -> dict:
        event_type = COMMAND_TO_EVENT_TYPE.get(command.command_type)
        if event_type is None:
            return {"rejected": RejectionReason(
                code="UNKNOWN_COMMAND",
                message=f"Unknown command: {command.command_type}",
                policy_name="_execute_command",
            )}

        builder = PAYLOAD_BUILDERS.get(event_type)
        if builder is None:
            return {"rejected": RejectionReason(
                code="NO_PAYLOAD_BUILDER",
                message=f"No payload builder for: {event_type}",
                policy_name="_execute_command",
            )}

        payload = builder(command)
        event_data = self._event_factory.create(
            event_type, payload, command.business_id,
            getattr(command, "branch_id", None),
        )
        self._persist_event(event_data)
        self._projection.apply(event_type, payload)
        return {"event_type": event_type, "payload": payload}


# ── Customer Profile Service (Tenant) ─────────────────────────

class CustomerProfileService:
    """Manages business customer profiles within a tenant."""

    def __init__(
        self,
        *,
        event_factory,
        persist_event,
        event_type_registry,
        projection_store: CustomerProfileProjectionStore,
        feature_flag_evaluator=None,
    ):
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection = projection_store
        self._feature_flags = feature_flag_evaluator

    def _execute_command(self, command) -> dict:
        event_type = COMMAND_TO_EVENT_TYPE.get(command.command_type)
        if event_type is None:
            return {"rejected": RejectionReason(
                code="UNKNOWN_COMMAND",
                message=f"Unknown command: {command.command_type}",
                policy_name="_execute_command",
            )}

        builder = PAYLOAD_BUILDERS.get(event_type)
        if builder is None:
            return {"rejected": RejectionReason(
                code="NO_PAYLOAD_BUILDER",
                message=f"No payload builder for: {event_type}",
                policy_name="_execute_command",
            )}

        payload = builder(command)
        event_data = self._event_factory.create(
            event_type, payload, command.business_id,
            getattr(command, "branch_id", None),
        )
        self._persist_event(event_data)
        self._projection.apply(event_type, payload)
        return {"event_type": event_type, "payload": payload}
