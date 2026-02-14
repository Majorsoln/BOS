from __future__ import annotations

import uuid
from datetime import datetime, timezone

from core.commands.base import Command
from core.commands.dispatcher import CommandDispatcher
from core.context.actor_context import ActorContext
from core.identity.requirements import SYSTEM_ALLOWED


BUSINESS_ID = uuid.uuid4()
BRANCH_ID = uuid.uuid4()


class StubContext:
    def __init__(
        self,
        active: bool = True,
        allow_business: bool = True,
        allow_branch: bool = True,
    ):
        self._active = active
        self._allow_business = allow_business
        self._allow_branch = allow_branch

    def has_active_context(self) -> bool:
        return self._active

    def get_active_business_id(self):
        return BUSINESS_ID

    def get_business_lifecycle_state(self) -> str:
        return "ACTIVE"

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        return True

    def is_actor_authorized_for_business(
        self,
        actor_context: ActorContext,
        business_id,
    ) -> bool:
        return self._allow_business

    def is_actor_authorized_for_branch(
        self,
        actor_context: ActorContext,
        business_id,
        branch_id,
    ) -> bool:
        return self._allow_branch


def _command(
    *,
    actor_type: str = "HUMAN",
    actor_id: str = "user-1",
    actor_context: ActorContext | None = None,
    actor_requirement: str | None = None,
    branch_id=None,
) -> Command:
    kwargs = {}
    if actor_requirement is not None:
        kwargs["actor_requirement"] = actor_requirement

    return Command(
        command_id=uuid.uuid4(),
        command_type="inventory.stock.move.request",
        business_id=BUSINESS_ID,
        branch_id=branch_id,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_context=actor_context,
        payload={"sku": "A", "qty": 1},
        issued_at=datetime.now(timezone.utc),
        correlation_id=uuid.uuid4(),
        source_engine="inventory",
        **kwargs,
    )


def test_actor_required_missing_rejected():
    dispatcher = CommandDispatcher(context=StubContext())
    outcome = dispatcher.dispatch(
        _command(actor_context=None)
    )

    assert outcome.is_rejected
    assert outcome.reason.code == "ACTOR_REQUIRED_MISSING"


def test_system_allowed_does_not_require_actor_context():
    dispatcher = CommandDispatcher(context=StubContext())
    outcome = dispatcher.dispatch(
        _command(
            actor_type="SYSTEM",
            actor_id="kernel",
            actor_context=None,
            actor_requirement=SYSTEM_ALLOWED,
        )
    )

    assert outcome.is_accepted


def test_actor_unauthorized_business_rejected():
    dispatcher = CommandDispatcher(
        context=StubContext(allow_business=False)
    )
    outcome = dispatcher.dispatch(
        _command(
            actor_context=ActorContext(
                actor_type="HUMAN",
                actor_id="user-1",
            )
        )
    )

    assert outcome.is_rejected
    assert outcome.reason.code == "ACTOR_UNAUTHORIZED_BUSINESS"


def test_actor_unauthorized_branch_rejected():
    dispatcher = CommandDispatcher(
        context=StubContext(
            allow_business=True,
            allow_branch=False,
        )
    )
    outcome = dispatcher.dispatch(
        _command(
            branch_id=BRANCH_ID,
            actor_context=ActorContext(
                actor_type="HUMAN",
                actor_id="user-1",
            ),
        )
    )

    assert outcome.is_rejected
    assert outcome.reason.code == "ACTOR_UNAUTHORIZED_BRANCH"

