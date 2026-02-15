from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.admin.projections import AdminProjectionStore
from core.admin.repository import AdminRepository
from core.admin.service import AdminDataService
from core.commands.bus import CommandBus
from core.commands.rejection import RejectionReason
from core.context.actor_context import ActorContext
from core.http_api.auth import (
    AuthPrincipal,
    InMemoryAuthProvider,
    resolve_actor_context,
    resolve_business_context,
    resolve_request_context,
)
from core.http_api.contracts import (
    ActorMetadata,
    BusinessReadRequest,
    FeatureFlagSetHttpRequest,
)
from core.http_api.dependencies import HttpApiDependencies
from core.http_api.handlers import list_feature_flags, post_feature_flag_set
from core.permissions import (
    InMemoryPermissionProvider,
    PERMISSION_ADMIN_CONFIGURE,
    Role,
    ScopeGrant,
)
from core.commands.dispatcher import CommandDispatcher
from core.feature_flags.models import FEATURE_ENABLED


BUSINESS_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-auth-business")
OTHER_BUSINESS_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-auth-other-business")
BRANCH_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-auth-branch")
OTHER_BRANCH_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-auth-other-branch")
ACTOR_ID = "auth-user-1"
FIXED_ISSUED_AT = datetime(2026, 2, 2, 8, 0, tzinfo=timezone.utc)
LEGACY_ACTOR = ActorMetadata(actor_type="HUMAN", actor_id=ACTOR_ID)


class StubContext:
    def __init__(self, business_id=BUSINESS_ID, branches=None):
        self._business_id = business_id
        self._branches = set(branches or {BRANCH_ID, OTHER_BRANCH_ID})

    def has_active_context(self) -> bool:
        return True

    def get_active_business_id(self):
        return self._business_id

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        return branch_id in self._branches

    def get_business_lifecycle_state(self) -> str:
        return "ACTIVE"


class StubEventTypeRegistry:
    def __init__(self):
        self._registered = set()

    def register(self, event_type: str) -> None:
        self._registered.add(event_type)

    def is_registered(self, event_type: str) -> bool:
        return event_type in self._registered


class PersistEventStub:
    def __init__(self):
        self.persisted_events = []

    def __call__(self, event_data: dict, context, registry, **kwargs):
        self.persisted_events.append(event_data)
        return {"accepted": True}


class FixedIdProvider:
    def __init__(self):
        self._command_counter = 0
        self._correlation_counter = 0

    def new_command_id(self) -> uuid.UUID:
        value = uuid.uuid5(
            uuid.NAMESPACE_URL, f"bos-http-auth:command:{self._command_counter}"
        )
        self._command_counter += 1
        return value

    def new_correlation_id(self) -> uuid.UUID:
        value = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"bos-http-auth:correlation:{self._correlation_counter}",
        )
        self._correlation_counter += 1
        return value


class FixedClock:
    def now_issued_at(self) -> datetime:
        return FIXED_ISSUED_AT


def _admin_permission_provider() -> InMemoryPermissionProvider:
    role = Role(
        role_id="admin-role",
        permissions=(PERMISSION_ADMIN_CONFIGURE,),
    )
    grant = ScopeGrant(
        actor_id=ACTOR_ID,
        role_id="admin-role",
        business_id=BUSINESS_ID,
    )
    return InMemoryPermissionProvider(roles=(role,), grants=(grant,))


def _deterministic_event_factory(*, command, event_type: str, payload: dict) -> dict:
    return {
        "event_id": command.command_id,
        "event_type": event_type,
        "business_id": command.business_id,
        "branch_id": command.branch_id,
        "correlation_id": command.correlation_id,
        "actor_id": command.actor_id,
        "payload": payload,
        "issued_at": command.issued_at,
    }


def _build_dependencies(*, auth_provider=None, permission_provider=None):
    projection_store = AdminProjectionStore()
    repository = AdminRepository(projection_store)
    context = StubContext()
    permission_provider = permission_provider or _admin_permission_provider()
    persist_stub = PersistEventStub()
    registry = StubEventTypeRegistry()

    dispatcher = CommandDispatcher(
        context=context,
        permission_provider=permission_provider,
    )
    command_bus = CommandBus(
        dispatcher=dispatcher,
        persist_event=persist_stub,
        context=context,
        event_type_registry=registry,
    )
    admin_service = AdminDataService(
        business_context=context,
        dispatcher=dispatcher,
        command_bus=command_bus,
        event_factory=_deterministic_event_factory,
        persist_event=persist_stub,
        event_type_registry=registry,
        projection_store=projection_store,
    )

    dependencies = HttpApiDependencies(
        admin_service=admin_service,
        admin_repository=repository,
        id_provider=FixedIdProvider(),
        clock=FixedClock(),
        auth_provider=auth_provider,
    )
    return dependencies


def _headers(api_key: str | None, business_id: uuid.UUID, branch_id=None) -> dict[str, str]:
    data = {"X-BUSINESS-ID": str(business_id)}
    if api_key is not None:
        data["X-API-KEY"] = api_key
    if branch_id is not None:
        data["X-BRANCH-ID"] = str(branch_id)
    return data


def _principal(
    *,
    businesses: tuple[uuid.UUID, ...] = (BUSINESS_ID,),
    branches_by_business=None,
    actor_type: str = "USER",
) -> AuthPrincipal:
    normalized_map = {}
    for business_id, branch_ids in (branches_by_business or {}).items():
        normalized_map[str(business_id)] = tuple(str(item) for item in branch_ids)
    return AuthPrincipal(
        actor_id=ACTOR_ID,
        actor_type=actor_type,
        allowed_business_ids=tuple(str(item) for item in businesses),
        allowed_branch_ids_by_business=normalized_map,
    )


def _request(*, business_id=BUSINESS_ID, actor=LEGACY_ACTOR, branch_id=None):
    return FeatureFlagSetHttpRequest(
        business_id=business_id,
        actor=actor,
        flag_key="ENABLE_DOCUMENT_DESIGNER",
        status=FEATURE_ENABLED,
        branch_id=branch_id,
    )


def test_missing_api_key_rejected():
    auth_provider = InMemoryAuthProvider({"valid": _principal()})
    dependencies = _build_dependencies(auth_provider=auth_provider)

    response = post_feature_flag_set(
        _request(actor=None),
        dependencies,
        headers=_headers(None, BUSINESS_ID),
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "ACTOR_REQUIRED_MISSING"


def test_invalid_api_key_rejected():
    auth_provider = InMemoryAuthProvider({"valid": _principal()})
    dependencies = _build_dependencies(auth_provider=auth_provider)

    response = post_feature_flag_set(
        _request(actor=None),
        dependencies,
        headers=_headers("invalid", BUSINESS_ID),
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "ACTOR_INVALID"


def test_valid_key_but_disallowed_business_rejected():
    auth_provider = InMemoryAuthProvider(
        {"valid": _principal(businesses=(OTHER_BUSINESS_ID,))}
    )
    dependencies = _build_dependencies(auth_provider=auth_provider)

    response = post_feature_flag_set(
        _request(actor=None),
        dependencies,
        headers=_headers("valid", BUSINESS_ID),
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "ACTOR_UNAUTHORIZED_BUSINESS"


def test_valid_key_and_allowed_business_passes_write_handler():
    auth_provider = InMemoryAuthProvider({"valid": _principal()})
    dependencies = _build_dependencies(auth_provider=auth_provider)

    response = post_feature_flag_set(
        _request(actor=None),
        dependencies,
        headers=_headers("valid", BUSINESS_ID),
    )

    assert response["ok"] is True
    assert response["data"]["status"] == "ACCEPTED"


def test_unauthorized_branch_rejected():
    auth_provider = InMemoryAuthProvider(
        {
            "valid": _principal(
                branches_by_business={BUSINESS_ID: (OTHER_BRANCH_ID,)},
            )
        }
    )
    dependencies = _build_dependencies(auth_provider=auth_provider)

    response = post_feature_flag_set(
        _request(actor=None, branch_id=BRANCH_ID),
        dependencies,
        headers=_headers("valid", BUSINESS_ID, branch_id=BRANCH_ID),
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "ACTOR_UNAUTHORIZED_BRANCH"


def test_resolver_determinism_same_headers_body_same_contexts():
    auth_provider = InMemoryAuthProvider({"valid": _principal()})
    headers = _headers("valid", BUSINESS_ID)
    body = _request(actor=None)

    resolved_1 = resolve_request_context(headers, body, auth_provider)
    resolved_2 = resolve_request_context(headers, body, auth_provider)

    assert not isinstance(resolved_1, RejectionReason)
    assert not isinstance(resolved_2, RejectionReason)
    assert resolved_1 == resolved_2


def test_user_actor_type_normalizes_to_human():
    auth_provider = InMemoryAuthProvider({"valid": _principal(actor_type="USER")})
    actor_context = resolve_actor_context(_headers("valid", BUSINESS_ID), auth_provider)

    assert isinstance(actor_context, ActorContext)
    assert actor_context.actor_type == "HUMAN"


def test_business_header_body_mismatch_rejected():
    rejection = resolve_business_context(
        _headers("valid", BUSINESS_ID),
        _request(business_id=OTHER_BUSINESS_ID),
    )

    assert isinstance(rejection, RejectionReason)
    assert rejection.code == "INVALID_CONTEXT"


def test_branch_header_body_mismatch_rejected():
    rejection = resolve_business_context(
        _headers("valid", BUSINESS_ID, branch_id=BRANCH_ID),
        _request(branch_id=OTHER_BRANCH_ID),
    )

    assert isinstance(rejection, RejectionReason)
    assert rejection.code == "INVALID_CONTEXT"


def test_auth_enabled_read_requires_valid_api_key_and_authorized_business():
    auth_provider = InMemoryAuthProvider({"valid": _principal()})
    dependencies = _build_dependencies(auth_provider=auth_provider)
    request = BusinessReadRequest(business_id=BUSINESS_ID)

    missing_key = list_feature_flags(
        request,
        dependencies,
        headers={"X-BUSINESS-ID": str(BUSINESS_ID)},
    )
    allowed = list_feature_flags(
        request,
        dependencies,
        headers=_headers("valid", BUSINESS_ID),
    )

    assert missing_key["ok"] is False
    assert missing_key["error"]["code"] == "ACTOR_REQUIRED_MISSING"
    assert allowed["ok"] is True


def test_auth_disabled_keeps_legacy_phase2_behavior():
    dependencies = _build_dependencies(auth_provider=None)
    response = post_feature_flag_set(
        _request(actor=LEGACY_ACTOR),
        dependencies,
    )

    assert response["ok"] is True


def test_replay_module_has_no_http_api_auth_reference():
    replay_file = Path("core/replay/event_replayer.py")
    source = replay_file.read_text(encoding="utf-8").lower()
    assert "http_api.auth" not in source
