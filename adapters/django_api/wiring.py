"""
BOS Django Adapter Wiring
=========================
Constructs HttpApiDependencies for local/staging live runs.

This module is adapter-only glue:
- no core contract changes
- no replay/event-store logic changes
- in-memory persistence/projections for phase smoke usage
"""

from __future__ import annotations

import copy
import threading
import uuid
from typing import Any

from core.admin.projections import AdminProjectionStore
from core.admin.repository import (
    AdminRepository,
    RepositoryComplianceProvider,
    RepositoryDocumentProvider,
    RepositoryFeatureFlagProvider,
)
from core.admin.service import AdminDataService
from core.commands.bus import CommandBus
from core.commands.dispatcher import CommandDispatcher
from core.context.business_context import BusinessContext
from core.event_store.hashing.hasher import GENESIS_HASH, compute_event_hash
from core.event_store.validators.registry import EventTypeRegistry
from core.http_api.auth import AuthPrincipal, InMemoryAuthProvider
from core.http_api.dependencies import HttpApiDependencies, UtcClock, UuidIdProvider
from core.permissions import (
    InMemoryPermissionProvider,
    PERMISSION_ADMIN_CONFIGURE,
    Role,
    ScopeGrant,
)


DEV_ADMIN_API_KEY = "dev-admin-key"
DEV_CASHIER_API_KEY = "dev-cashier-key"

DEV_BUSINESS_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DEV_ADMIN_BRANCH_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEV_CASHIER_BRANCH_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

_DEV_ADMIN_ACTOR_ID = "live-admin-user"
_DEV_CASHIER_ACTOR_ID = "live-cashier-user"

_DEPENDENCIES_LOCK = threading.Lock()
_DEPENDENCIES: HttpApiDependencies | None = None


class _InMemoryEventLedger:
    def __init__(self):
        self._events: list[dict[str, Any]] = []
        self._last_hash_by_business: dict[uuid.UUID, str] = {}
        self._lock = threading.Lock()

    def previous_hash_for_business(self, business_id: uuid.UUID) -> str:
        with self._lock:
            return self._last_hash_by_business.get(business_id, GENESIS_HASH)

    def record(self, event_data: dict[str, Any]) -> None:
        with self._lock:
            stored = copy.deepcopy(event_data)
            self._events.append(stored)
            business_id = stored.get("business_id")
            event_hash = stored.get("event_hash")
            if isinstance(business_id, uuid.UUID) and isinstance(event_hash, str):
                self._last_hash_by_business[business_id] = event_hash

    def all_events(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(copy.deepcopy(self._events))


class _InMemoryPersistEvent:
    """
    Adapter-level persistence stub for live smoke usage.
    Core persist_event path remains unchanged and unmodified.
    """

    def __init__(self, ledger: _InMemoryEventLedger):
        self._ledger = ledger

    def __call__(self, event_data: dict[str, Any], context, registry, **kwargs):
        self._ledger.record(event_data)
        return {"accepted": True}


def _build_business_context() -> BusinessContext:
    known_branches = frozenset({DEV_ADMIN_BRANCH_ID, DEV_CASHIER_BRANCH_ID})

    def _branch_checker(branch_id: uuid.UUID, business_id: uuid.UUID) -> bool:
        return business_id == DEV_BUSINESS_ID and branch_id in known_branches

    return BusinessContext(
        business_id=DEV_BUSINESS_ID,
        branch_id=None,
        _branch_ownership_checker=_branch_checker,
    )


def _build_permission_provider() -> InMemoryPermissionProvider:
    admin_role = Role(
        role_id="live-admin-configure",
        permissions=(PERMISSION_ADMIN_CONFIGURE,),
    )
    admin_grant = ScopeGrant(
        actor_id=_DEV_ADMIN_ACTOR_ID,
        role_id=admin_role.role_id,
        business_id=DEV_BUSINESS_ID,
    )
    return InMemoryPermissionProvider(
        roles=(admin_role,),
        grants=(admin_grant,),
    )


def _build_auth_provider() -> InMemoryAuthProvider:
    admin_principal = AuthPrincipal(
        actor_id=_DEV_ADMIN_ACTOR_ID,
        actor_type="USER",
        allowed_business_ids=(str(DEV_BUSINESS_ID),),
        allowed_branch_ids_by_business={
            str(DEV_BUSINESS_ID): (
                str(DEV_ADMIN_BRANCH_ID),
                str(DEV_CASHIER_BRANCH_ID),
            )
        },
    )
    cashier_principal = AuthPrincipal(
        actor_id=_DEV_CASHIER_ACTOR_ID,
        actor_type="USER",
        allowed_business_ids=(str(DEV_BUSINESS_ID),),
        allowed_branch_ids_by_business={
            str(DEV_BUSINESS_ID): (str(DEV_CASHIER_BRANCH_ID),)
        },
    )
    return InMemoryAuthProvider(
        {
            DEV_ADMIN_API_KEY: admin_principal,
            DEV_CASHIER_API_KEY: cashier_principal,
        }
    )


def _build_event_factory(ledger: _InMemoryEventLedger):
    def _event_factory(*, command, event_type: str, payload: dict) -> dict[str, Any]:
        previous_hash = ledger.previous_hash_for_business(command.business_id)
        event_hash = compute_event_hash(payload, previous_hash)
        return {
            "event_id": command.command_id,
            "event_type": event_type,
            "event_version": 1,
            "business_id": command.business_id,
            "branch_id": command.branch_id,
            "source_engine": command.source_engine,
            "actor_type": command.actor_type,
            "actor_id": command.actor_id,
            "correlation_id": command.correlation_id,
            "causation_id": None,
            "payload": dict(payload),
            "reference": {},
            "created_at": command.issued_at,
            "status": "FINAL",
            "correction_of": None,
            "previous_event_hash": previous_hash,
            "event_hash": event_hash,
        }

    return _event_factory


def _create_dependencies() -> HttpApiDependencies:
    projection_store = AdminProjectionStore()
    repository = AdminRepository(projection_store)
    event_ledger = _InMemoryEventLedger()
    persist_event = _InMemoryPersistEvent(event_ledger)

    business_context = _build_business_context()
    permission_provider = _build_permission_provider()
    feature_flag_provider = RepositoryFeatureFlagProvider(repository)
    compliance_provider = RepositoryComplianceProvider(repository)
    document_provider = RepositoryDocumentProvider(repository)

    dispatcher = CommandDispatcher(
        context=business_context,
        permission_provider=permission_provider,
        feature_flag_provider=feature_flag_provider,
        compliance_provider=compliance_provider,
        document_provider=document_provider,
    )
    event_type_registry = EventTypeRegistry()
    command_bus = CommandBus(
        dispatcher=dispatcher,
        persist_event=persist_event,
        context=business_context,
        event_type_registry=event_type_registry,
    )
    admin_service = AdminDataService(
        business_context=business_context,
        dispatcher=dispatcher,
        command_bus=command_bus,
        event_factory=_build_event_factory(event_ledger),
        persist_event=persist_event,
        event_type_registry=event_type_registry,
        projection_store=projection_store,
    )

    return HttpApiDependencies(
        admin_service=admin_service,
        admin_repository=repository,
        id_provider=UuidIdProvider(),
        clock=UtcClock(),
        auth_provider=_build_auth_provider(),
    )


def build_dependencies() -> HttpApiDependencies:
    """
    Lazy singleton wiring for adapter runtime.
    """
    global _DEPENDENCIES
    with _DEPENDENCIES_LOCK:
        if _DEPENDENCIES is None:
            _DEPENDENCIES = _create_dependencies()
        return _DEPENDENCIES

