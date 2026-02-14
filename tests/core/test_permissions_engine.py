from __future__ import annotations

import uuid
from datetime import datetime, timezone

from core.commands.base import Command
from core.commands.dispatcher import CommandDispatcher
from core.context.actor_context import ActorContext
from core.context.scope import SCOPE_BRANCH_REQUIRED, SCOPE_BUSINESS_ALLOWED
from core.identity.requirements import SYSTEM_ALLOWED
from core.permissions import (
    InMemoryPermissionProvider,
    PERMISSION_INVENTORY_MOVE,
    Role,
    SCOPE_GRANT_BRANCH,
    ScopeGrant,
)


BUSINESS_ID = uuid.uuid4()
BRANCH_ID = uuid.uuid4()
OTHER_BRANCH_ID = uuid.uuid4()


class StubContext:
    def __init__(self, provider):
        self._provider = provider

    def has_active_context(self) -> bool:
        return True

    def get_active_business_id(self):
        return BUSINESS_ID

    def get_business_lifecycle_state(self) -> str:
        return "ACTIVE"

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        return True

    def get_permission_provider(self):
        return self._provider


def _command(
    *,
    actor_id: str = "user-1",
    branch_id=None,
    actor_requirement: str | None = None,
    command_type: str = "inventory.stock.move.request",
) -> Command:
    kwargs = {}
    if actor_requirement is not None:
        kwargs["actor_requirement"] = actor_requirement

    actor_type = "SYSTEM" if actor_requirement == SYSTEM_ALLOWED else "HUMAN"
    actor_context = None
    if actor_requirement != SYSTEM_ALLOWED:
        actor_context = ActorContext(
            actor_type=actor_type,
            actor_id=actor_id,
        )

    return Command(
        command_id=uuid.uuid4(),
        command_type=command_type,
        business_id=BUSINESS_ID,
        branch_id=branch_id,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_context=actor_context,
        payload={"sku": "A", "qty": 1},
        issued_at=datetime.now(timezone.utc),
        correlation_id=uuid.uuid4(),
        source_engine="inventory",
        scope_requirement=(
            SCOPE_BRANCH_REQUIRED
            if branch_id is not None
            else SCOPE_BUSINESS_ALLOWED
        ),
        **kwargs,
    )


def _provider_with_business_grant(actor_id: str) -> InMemoryPermissionProvider:
    role = Role(
        role_id="inventory-role",
        permissions=(PERMISSION_INVENTORY_MOVE,),
    )
    grant = ScopeGrant(
        actor_id=actor_id,
        role_id="inventory-role",
        business_id=BUSINESS_ID,
    )
    return InMemoryPermissionProvider(roles=(role,), grants=(grant,))


def _provider_with_branch_grant(actor_id: str, branch_id) -> InMemoryPermissionProvider:
    role = Role(
        role_id="inventory-role",
        permissions=(PERMISSION_INVENTORY_MOVE,),
    )
    grant = ScopeGrant(
        actor_id=actor_id,
        role_id="inventory-role",
        business_id=BUSINESS_ID,
        scope_type=SCOPE_GRANT_BRANCH,
        branch_id=branch_id,
    )
    return InMemoryPermissionProvider(roles=(role,), grants=(grant,))


def test_actor_with_no_grants_rejected_permission_denied():
    provider = InMemoryPermissionProvider()
    context = StubContext(provider=provider)
    dispatcher = CommandDispatcher(
        context=context,
        permission_provider=provider,
    )

    outcome = dispatcher.dispatch(_command(actor_id="user-1"))

    assert outcome.is_rejected
    assert outcome.reason.code == "PERMISSION_DENIED"


def test_business_grant_allows_business_scope_command():
    provider = _provider_with_business_grant(actor_id="user-1")
    context = StubContext(provider=provider)
    dispatcher = CommandDispatcher(
        context=context,
        permission_provider=provider,
    )

    outcome = dispatcher.dispatch(_command(actor_id="user-1", branch_id=None))

    assert outcome.is_accepted


def test_business_grant_rejected_for_branch_required_scope():
    # Enterprise implication: business admin grants cannot silently authorize
    # branch operations; branch delegation must be explicit.
    provider = _provider_with_business_grant(actor_id="user-1")
    context = StubContext(provider=provider)
    dispatcher = CommandDispatcher(
        context=context,
        permission_provider=provider,
    )

    outcome = dispatcher.dispatch(_command(actor_id="user-1", branch_id=BRANCH_ID))

    assert outcome.is_rejected
    assert outcome.reason.code == "PERMISSION_SCOPE_REQUIRED_BRANCH"


def test_branch_grant_allows_matching_branch_scope_command():
    provider = _provider_with_branch_grant(
        actor_id="user-1",
        branch_id=BRANCH_ID,
    )
    context = StubContext(provider=provider)
    dispatcher = CommandDispatcher(
        context=context,
        permission_provider=provider,
    )

    outcome = dispatcher.dispatch(_command(actor_id="user-1", branch_id=BRANCH_ID))

    assert outcome.is_accepted


def test_system_allowed_bypasses_permission_check():
    provider = InMemoryPermissionProvider()
    context = StubContext(provider=provider)
    dispatcher = CommandDispatcher(
        context=context,
        permission_provider=provider,
    )

    outcome = dispatcher.dispatch(
        _command(
            actor_id="kernel",
            actor_requirement=SYSTEM_ALLOWED,
        )
    )

    assert outcome.is_accepted


def test_mapping_missing_rejected_deterministically():
    provider = _provider_with_business_grant(actor_id="user-1")
    context = StubContext(provider=provider)
    dispatcher = CommandDispatcher(
        context=context,
        permission_provider=provider,
    )

    outcome = dispatcher.dispatch(
        _command(
            actor_id="user-1",
            command_type="inventory.unknown.action.request",
        )
    )

    assert outcome.is_rejected
    assert outcome.reason.code == "PERMISSION_MAPPING_MISSING"


def test_branch_grant_wrong_branch_rejected_scope_required_branch():
    provider = _provider_with_branch_grant(
        actor_id="user-1",
        branch_id=OTHER_BRANCH_ID,
    )
    context = StubContext(provider=provider)
    dispatcher = CommandDispatcher(
        context=context,
        permission_provider=provider,
    )

    outcome = dispatcher.dispatch(_command(actor_id="user-1", branch_id=BRANCH_ID))

    assert outcome.is_rejected
    assert outcome.reason.code == "PERMISSION_SCOPE_REQUIRED_BRANCH"

