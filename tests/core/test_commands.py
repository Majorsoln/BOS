"""
BOS Command Layer â€” Comprehensive Tests
==========================================
Tests for the entire Command â†’ Outcome â†’ Event chain.

Required test scenarios:
1. Valid command â†’ ACCEPTED
2. Invalid structure â†’ validation error
3. Policy failure â†’ REJECTED outcome
4. REJECTED produces event
5. ACCEPTED produces event (via engine handler)
6. No silent path
7. Wrong namespace â†’ rejected
8. AI actor cannot produce execution command
9. Additional: rejection event naming, frozen immutability,
   bus orchestration, multi-tenant enforcement
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import pytest

from core.commands.base import (
    Command,
    derive_rejection_event_type,
    derive_source_engine,
)
from core.commands.outcomes import CommandOutcome, CommandStatus
from core.commands.rejection import RejectionReason, ReasonCode
from core.commands.validator import (
    CommandValidationError,
    validate_command,
)
from core.commands.dispatcher import (
    CommandDispatcher,
    ai_execution_guard,
)
from core.commands.bus import (
    CommandBus,
    CommandResult,
    NoHandlerRegistered,
)
from core.context.actor_context import ActorContext
from core.context.scope import SCOPE_BRANCH_REQUIRED


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# TEST INFRASTRUCTURE â€” STUBS (no Django)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class StubContext:
    """
    Stub matching CommandContextProtocol.
    Configurable for different test scenarios.
    """

    def __init__(
        self,
        active: bool = True,
        business_id: Optional[uuid.UUID] = None,
        branches: Optional[set] = None,
        lifecycle_state: str = "ACTIVE",
    ):
        self._active = active
        self._business_id = business_id or uuid.uuid4()
        self._branches = branches or set()
        self._lifecycle_state = lifecycle_state

    def has_active_context(self) -> bool:
        return self._active

    def get_active_business_id(self):
        return self._business_id

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        return branch_id in self._branches

    def get_business_lifecycle_state(self) -> str:
        return self._lifecycle_state


class StubEngineService:
    """Stub engine service that records execute calls."""

    def __init__(self, return_value: Any = "executed"):
        self.executed_commands = []
        self.return_value = return_value

    def execute(self, command: Command) -> Any:
        self.executed_commands.append(command)
        return self.return_value


class StubPersistEvent:
    """Stub for persist_event that records calls."""

    def __init__(self):
        self.persisted_events = []

    def __call__(
        self, event_data: dict, context: Any, registry: Any, **kwargs
    ) -> Any:
        self.persisted_events.append(event_data)
        return {"accepted": True}


class StubEventTypeRegistry:
    """Stub EventTypeRegistry."""

    def __init__(self):
        self._registered = set()

    def register(self, event_type: str) -> None:
        self._registered.add(event_type)

    def is_registered(self, event_type: str) -> bool:
        return event_type in self._registered


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# FIXTURES
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

BUSINESS_ID = uuid.uuid4()
BRANCH_ID = uuid.uuid4()


@pytest.fixture
def context():
    return StubContext(
        active=True,
        business_id=BUSINESS_ID,
        branches={BRANCH_ID},
        lifecycle_state="ACTIVE",
    )


@pytest.fixture
def valid_command():
    return Command(
        command_id=uuid.uuid4(),
        command_type="inventory.stock.move.request",
        business_id=BUSINESS_ID,
        branch_id=None,
        actor_type="HUMAN",
        actor_id="user-123",
        actor_context=ActorContext(actor_type="HUMAN", actor_id="user-123"),
        payload={"sku": "ABC", "quantity": 10},
        issued_at=datetime.now(timezone.utc),
        correlation_id=uuid.uuid4(),
        source_engine="inventory",
    )


@pytest.fixture
def ai_command():
    return Command(
        command_id=uuid.uuid4(),
        command_type="inventory.stock.move.request",
        business_id=BUSINESS_ID,
        branch_id=None,
        actor_type="AI",
        actor_id="ai-advisor-1",
        actor_context=ActorContext(actor_type="AI", actor_id="ai-advisor-1"),
        payload={"sku": "ABC", "quantity": 5},
        issued_at=datetime.now(timezone.utc),
        correlation_id=uuid.uuid4(),
        source_engine="inventory",
    )


@pytest.fixture
def dispatcher(context):
    d = CommandDispatcher(context=context)
    d.register_policy(ai_execution_guard)
    return d


@pytest.fixture
def persist_event_stub():
    return StubPersistEvent()


@pytest.fixture
def event_type_registry():
    return StubEventTypeRegistry()


@pytest.fixture
def engine_service():
    return StubEngineService()


@pytest.fixture
def command_bus(dispatcher, persist_event_stub, context, event_type_registry):
    return CommandBus(
        dispatcher=dispatcher,
        persist_event=persist_event_stub,
        context=context,
        event_type_registry=event_type_registry,
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 1. VALID COMMAND â†’ ACCEPTED
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestValidCommandAccepted:
    """Scenario 1: Valid command produces ACCEPTED outcome."""

    def test_valid_command_accepted(self, dispatcher, valid_command):
        outcome = dispatcher.dispatch(valid_command)
        assert outcome.is_accepted
        assert outcome.status == CommandStatus.ACCEPTED
        assert outcome.reason is None
        assert outcome.command_id == valid_command.command_id

    def test_accepted_outcome_has_timestamp(self, dispatcher, valid_command):
        outcome = dispatcher.dispatch(valid_command)
        assert isinstance(outcome.occurred_at, datetime)

    def test_bus_accepted_calls_handler(
        self, command_bus, engine_service, valid_command
    ):
        command_bus.register_handler(
            "inventory.stock.move.request", engine_service
        )
        result = command_bus.handle(valid_command)
        assert result.is_accepted
        assert len(engine_service.executed_commands) == 1
        assert engine_service.executed_commands[0] is valid_command


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 2. INVALID STRUCTURE â†’ VALIDATION ERROR
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestInvalidStructure:
    """Scenario 2: Invalid command structure fails validation."""

    def test_command_type_without_request_suffix(self):
        with pytest.raises(ValueError, match=".request"):
            Command(
                command_id=uuid.uuid4(),
                command_type="inventory.stock.moved",
                business_id=BUSINESS_ID,
                branch_id=None,
                actor_type="HUMAN",
                actor_id="user-1",
                actor_context=ActorContext(actor_type="HUMAN", actor_id="user-1"),
                payload={"a": 1},
                issued_at=datetime.now(timezone.utc),
                correlation_id=uuid.uuid4(),
                source_engine="inventory",
            )

    def test_command_type_too_few_segments(self):
        with pytest.raises(ValueError, match="engine.domain.action.request"):
            Command(
                command_id=uuid.uuid4(),
                command_type="inventory.move.request",
                business_id=BUSINESS_ID,
                branch_id=None,
                actor_type="HUMAN",
                actor_id="user-1",
                actor_context=ActorContext(actor_type="HUMAN", actor_id="user-1"),
                payload={"a": 1},
                issued_at=datetime.now(timezone.utc),
                correlation_id=uuid.uuid4(),
                source_engine="inventory",
            )

    def test_invalid_actor_type(self):
        with pytest.raises(ValueError, match="actor_type"):
            Command(
                command_id=uuid.uuid4(),
                command_type="inventory.stock.move.request",
                business_id=BUSINESS_ID,
                branch_id=None,
                actor_type="ROBOT",
                actor_id="user-1",
                actor_context=ActorContext(actor_type="ROBOT", actor_id="user-1"),
                payload={"a": 1},
                issued_at=datetime.now(timezone.utc),
                correlation_id=uuid.uuid4(),
                source_engine="inventory",
            )

    def test_empty_actor_id(self):
        with pytest.raises(ValueError, match="actor_id"):
            Command(
                command_id=uuid.uuid4(),
                command_type="inventory.stock.move.request",
                business_id=BUSINESS_ID,
                branch_id=None,
                actor_type="HUMAN",
                actor_id="",
                actor_context=ActorContext(actor_type="HUMAN", actor_id=""),
                payload={"a": 1},
                issued_at=datetime.now(timezone.utc),
                correlation_id=uuid.uuid4(),
                source_engine="inventory",
            )

    def test_payload_not_dict(self):
        with pytest.raises(TypeError, match="payload"):
            Command(
                command_id=uuid.uuid4(),
                command_type="inventory.stock.move.request",
                business_id=BUSINESS_ID,
                branch_id=None,
                actor_type="HUMAN",
                actor_id="user-1",
                actor_context=ActorContext(actor_type="HUMAN", actor_id="user-1"),
                payload="not a dict",
                issued_at=datetime.now(timezone.utc),
                correlation_id=uuid.uuid4(),
                source_engine="inventory",
            )

    def test_command_is_frozen(self, valid_command):
        with pytest.raises(AttributeError):
            valid_command.command_type = "hacked"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 3. POLICY FAILURE â†’ REJECTED OUTCOME
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestPolicyRejection:
    """Scenario 3: Policy evaluation produces REJECTED outcome."""

    def test_custom_policy_rejects(self, context, valid_command):
        def deny_all(cmd, ctx):
            return RejectionReason(
                code="ALWAYS_DENY",
                message="Testing â€” always deny.",
                policy_name="deny_all_policy",
            )

        dispatcher = CommandDispatcher(context=context)
        dispatcher.register_policy(deny_all)

        outcome = dispatcher.dispatch(valid_command)
        assert outcome.is_rejected
        assert outcome.reason.code == "ALWAYS_DENY"
        assert outcome.reason.policy_name == "deny_all_policy"

    def test_first_rejection_wins(self, context, valid_command):
        def policy_a(cmd, ctx):
            return RejectionReason(
                code="POLICY_A", message="A", policy_name="a"
            )

        def policy_b(cmd, ctx):
            return RejectionReason(
                code="POLICY_B", message="B", policy_name="b"
            )

        dispatcher = CommandDispatcher(context=context)
        dispatcher.register_policy(policy_a)
        dispatcher.register_policy(policy_b)

        outcome = dispatcher.dispatch(valid_command)
        assert outcome.reason.code == "POLICY_A"

    def test_passing_policy_does_not_reject(self, context, valid_command):
        def allow_all(cmd, ctx):
            return None  # Pass

        dispatcher = CommandDispatcher(context=context)
        dispatcher.register_policy(allow_all)

        outcome = dispatcher.dispatch(valid_command)
        assert outcome.is_accepted


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 4. REJECTED PRODUCES EVENT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestRejectedProducesEvent:
    """Scenario 4: REJECTED commands produce rejection events."""

    def test_rejection_event_persisted(
        self, command_bus, persist_event_stub, ai_command
    ):
        # AI command â†’ rejected by ai_execution_guard
        # No handler needed â€” rejection path doesn't call handler
        result = command_bus.handle(ai_command)

        assert result.is_rejected
        assert result.rejection_event_persisted
        assert len(persist_event_stub.persisted_events) == 1

    def test_rejection_event_type_correct(
        self, command_bus, persist_event_stub, ai_command
    ):
        command_bus.handle(ai_command)

        event_data = persist_event_stub.persisted_events[0]
        assert event_data["event_type"] == "inventory.stock.move.rejected"

    def test_rejection_event_contains_reason(
        self, command_bus, persist_event_stub, ai_command
    ):
        command_bus.handle(ai_command)

        event_data = persist_event_stub.persisted_events[0]
        payload = event_data["payload"]
        assert "rejection" in payload
        assert payload["rejection"]["code"] == ReasonCode.AI_EXECUTION_FORBIDDEN
        assert "command_id" in payload
        assert "original_payload" in payload

    def test_rejection_event_preserves_tenant(
        self, command_bus, persist_event_stub, ai_command
    ):
        command_bus.handle(ai_command)

        event_data = persist_event_stub.persisted_events[0]
        assert event_data["business_id"] == ai_command.business_id
        assert event_data["source_engine"] == ai_command.source_engine
        assert event_data["actor_type"] == ai_command.actor_type
        assert event_data["actor_id"] == ai_command.actor_id
        assert event_data["correlation_id"] == ai_command.correlation_id


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 5. ACCEPTED PRODUCES EVENT (via engine handler)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestAcceptedProducesEvent:
    """Scenario 5: ACCEPTED commands trigger engine handler."""

    def test_handler_receives_command(
        self, command_bus, engine_service, valid_command
    ):
        command_bus.register_handler(
            "inventory.stock.move.request", engine_service
        )
        result = command_bus.handle(valid_command)

        assert result.is_accepted
        assert len(engine_service.executed_commands) == 1

    def test_handler_return_value_in_result(
        self, command_bus, valid_command
    ):
        service = StubEngineService(return_value={"persisted": True})
        command_bus.register_handler(
            "inventory.stock.move.request", service
        )
        result = command_bus.handle(valid_command)

        assert result.execution_result == {"persisted": True}

    def test_no_handler_raises_error(
        self, command_bus, valid_command
    ):
        # No handler registered for this command type
        with pytest.raises(NoHandlerRegistered):
            command_bus.handle(valid_command)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 6. NO SILENT PATH
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestNoSilentPath:
    """Scenario 6: Every command produces a traceable result."""

    def test_accepted_has_outcome(
        self, command_bus, engine_service, valid_command
    ):
        command_bus.register_handler(
            "inventory.stock.move.request", engine_service
        )
        result = command_bus.handle(valid_command)
        assert result.outcome is not None
        assert result.outcome.command_id == valid_command.command_id

    def test_rejected_has_outcome(self, command_bus, ai_command):
        result = command_bus.handle(ai_command)
        assert result.outcome is not None
        assert result.outcome.is_rejected

    def test_outcome_always_has_command_id(
        self, dispatcher, valid_command, ai_command
    ):
        accepted = dispatcher.dispatch(valid_command)
        rejected = dispatcher.dispatch(ai_command)

        assert accepted.command_id == valid_command.command_id
        assert rejected.command_id == ai_command.command_id

    def test_rejected_outcome_always_has_reason(
        self, dispatcher, ai_command
    ):
        outcome = dispatcher.dispatch(ai_command)
        assert outcome.reason is not None
        assert outcome.reason.code is not None
        assert outcome.reason.message is not None


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 7. WRONG NAMESPACE â†’ REJECTED
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestNamespaceEnforcement:
    """Scenario 7: Namespace mismatch is rejected."""

    def test_namespace_mismatch_at_command_creation(self):
        with pytest.raises(ValueError, match="namespace.*does not match"):
            Command(
                command_id=uuid.uuid4(),
                command_type="inventory.stock.move.request",
                business_id=BUSINESS_ID,
                branch_id=None,
                actor_type="HUMAN",
                actor_id="user-1",
                actor_context=ActorContext(actor_type="HUMAN", actor_id="user-1"),
                payload={"a": 1},
                issued_at=datetime.now(timezone.utc),
                correlation_id=uuid.uuid4(),
                source_engine="cash",  # Mismatch!
            )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 8. AI ACTOR CANNOT EXECUTE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestAIExecutionGuard:
    """Scenario 8: AI actor cannot produce execution commands."""

    def test_ai_command_rejected(self, dispatcher, ai_command):
        outcome = dispatcher.dispatch(ai_command)
        assert outcome.is_rejected
        assert outcome.reason.code == ReasonCode.AI_EXECUTION_FORBIDDEN

    def test_ai_rejection_has_policy_name(self, dispatcher, ai_command):
        outcome = dispatcher.dispatch(ai_command)
        assert outcome.reason.policy_name == "ai_execution_guard"

    def test_human_command_passes_ai_guard(
        self, dispatcher, valid_command
    ):
        outcome = dispatcher.dispatch(valid_command)
        assert outcome.is_accepted


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 9. MULTI-TENANT ENFORCEMENT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestMultiTenantEnforcement:
    """Multi-tenant context enforcement."""

    def test_missing_business_context_object_rejected(self, valid_command):
        dispatcher = CommandDispatcher(context=None)
        outcome = dispatcher.dispatch(valid_command)

        assert outcome.is_rejected
        assert outcome.reason.code == "INVALID_CONTEXT"

    def test_no_active_context_rejected(self, valid_command):
        ctx = StubContext(active=False)
        dispatcher = CommandDispatcher(context=ctx)
        outcome = dispatcher.dispatch(valid_command)

        assert outcome.is_rejected
        assert outcome.reason.code == "NO_ACTIVE_CONTEXT"

    def test_branch_required_missing_rejected(self):
        ctx = StubContext(
            active=True,
            business_id=BUSINESS_ID,
            branches={BRANCH_ID},
        )
        cmd = Command(
            command_id=uuid.uuid4(),
            command_type="inventory.stock.move.request",
            business_id=BUSINESS_ID,
            branch_id=None,
            actor_type="HUMAN",
            actor_id="user-1",
            actor_context=ActorContext(actor_type="HUMAN", actor_id="user-1"),
            payload={"a": 1},
            issued_at=datetime.now(timezone.utc),
            correlation_id=uuid.uuid4(),
            source_engine="inventory",
            scope_requirement=SCOPE_BRANCH_REQUIRED,
        )
        dispatcher = CommandDispatcher(context=ctx)
        outcome = dispatcher.dispatch(cmd)

        assert outcome.is_rejected
        assert outcome.reason.code == "BRANCH_REQUIRED_MISSING"

    def test_suspended_business_rejected(self, valid_command):
        ctx = StubContext(
            active=True,
            business_id=BUSINESS_ID,
            lifecycle_state="SUSPENDED",
        )
        dispatcher = CommandDispatcher(context=ctx)
        outcome = dispatcher.dispatch(valid_command)

        assert outcome.is_rejected
        assert outcome.reason.code == "BUSINESS_SUSPENDED"

    def test_closed_business_rejected(self, valid_command):
        ctx = StubContext(
            active=True,
            business_id=BUSINESS_ID,
            lifecycle_state="CLOSED",
        )
        dispatcher = CommandDispatcher(context=ctx)
        outcome = dispatcher.dispatch(valid_command)

        assert outcome.is_rejected
        assert outcome.reason.code == "BUSINESS_CLOSED"

    def test_legal_hold_rejected(self, valid_command):
        ctx = StubContext(
            active=True,
            business_id=BUSINESS_ID,
            lifecycle_state="LEGAL_HOLD",
        )
        dispatcher = CommandDispatcher(context=ctx)
        outcome = dispatcher.dispatch(valid_command)

        assert outcome.is_rejected
        assert outcome.reason.code == "BUSINESS_LEGAL_HOLD"

    def test_business_id_mismatch_rejected(self):
        wrong_biz = uuid.uuid4()
        ctx = StubContext(
            active=True,
            business_id=wrong_biz,
        )
        cmd = Command(
            command_id=uuid.uuid4(),
            command_type="inventory.stock.move.request",
            business_id=BUSINESS_ID,  # Different from context
            branch_id=None,
            actor_type="HUMAN",
            actor_id="user-1",
            actor_context=ActorContext(actor_type="HUMAN", actor_id="user-1"),
            payload={"a": 1},
            issued_at=datetime.now(timezone.utc),
            correlation_id=uuid.uuid4(),
            source_engine="inventory",
        )
        dispatcher = CommandDispatcher(context=ctx)
        outcome = dispatcher.dispatch(cmd)

        assert outcome.is_rejected
        assert outcome.reason.code == "BUSINESS_ID_MISMATCH"

    def test_branch_not_in_business_rejected(self):
        ctx = StubContext(
            active=True,
            business_id=BUSINESS_ID,
            branches=set(),  # No branches
        )
        cmd = Command(
            command_id=uuid.uuid4(),
            command_type="inventory.stock.move.request",
            business_id=BUSINESS_ID,
            branch_id=uuid.uuid4(),  # Branch not in context
            actor_type="HUMAN",
            actor_id="user-1",
            actor_context=ActorContext(actor_type="HUMAN", actor_id="user-1"),
            payload={"a": 1},
            issued_at=datetime.now(timezone.utc),
            correlation_id=uuid.uuid4(),
            source_engine="inventory",
        )
        dispatcher = CommandDispatcher(context=ctx)
        outcome = dispatcher.dispatch(cmd)

        assert outcome.is_rejected
        assert outcome.reason.code == "BRANCH_NOT_IN_BUSINESS"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EVENT NAMING LAW
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestEventNamingLaw:
    """Event type derivation from command type."""

    def test_rejection_event_derivation(self):
        assert (
            derive_rejection_event_type("inventory.stock.move.request")
            == "inventory.stock.move.rejected"
        )

    def test_rejection_derivation_cash(self):
        assert (
            derive_rejection_event_type("cash.session.open.request")
            == "cash.session.open.rejected"
        )

    def test_rejection_derivation_invalid_suffix(self):
        with pytest.raises(ValueError, match=".request"):
            derive_rejection_event_type("inventory.stock.moved")

    def test_source_engine_derivation(self):
        assert derive_source_engine("inventory.stock.move.request") == "inventory"
        assert derive_source_engine("cash.session.open.request") == "cash"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# OUTCOME INVARIANTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestOutcomeInvariants:
    """CommandOutcome frozen contract enforcement."""

    def test_rejected_without_reason_fails(self):
        with pytest.raises(ValueError, match="RejectionReason"):
            CommandOutcome(
                command_id=uuid.uuid4(),
                status=CommandStatus.REJECTED,
                reason=None,  # Missing!
                occurred_at=datetime.now(timezone.utc),
            )

    def test_accepted_with_reason_fails(self):
        with pytest.raises(ValueError, match="must NOT"):
            CommandOutcome(
                command_id=uuid.uuid4(),
                status=CommandStatus.ACCEPTED,
                reason=RejectionReason(
                    code="X", message="Y", policy_name="Z"
                ),
                occurred_at=datetime.now(timezone.utc),
            )

    def test_outcome_is_frozen(self, dispatcher, valid_command):
        outcome = dispatcher.dispatch(valid_command)
        with pytest.raises(AttributeError):
            outcome.status = CommandStatus.REJECTED


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# REJECTION REASON STRUCTURE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestRejectionReason:
    """RejectionReason structure validation."""

    def test_valid_reason(self):
        r = RejectionReason(
            code="TEST_CODE",
            message="Test message.",
            policy_name="test_policy",
        )
        assert r.code == "TEST_CODE"

    def test_reason_to_dict(self):
        r = RejectionReason(
            code="X", message="Y", policy_name="Z"
        )
        d = r.to_dict()
        assert d == {"code": "X", "message": "Y", "policy_name": "Z"}

    def test_empty_code_fails(self):
        with pytest.raises(ValueError):
            RejectionReason(code="", message="M", policy_name="P")

    def test_empty_message_fails(self):
        with pytest.raises(ValueError):
            RejectionReason(code="C", message="", policy_name="P")

    def test_empty_policy_fails(self):
        with pytest.raises(ValueError):
            RejectionReason(code="C", message="M", policy_name="")

    def test_reason_is_frozen(self):
        r = RejectionReason(code="C", message="M", policy_name="P")
        with pytest.raises(AttributeError):
            r.code = "HACKED"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# FULL INTEGRATION FLOW
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TestFullIntegrationFlow:
    """End-to-end command lifecycle."""

    def test_complete_accepted_flow(self):
        """Command â†’ validate â†’ policies â†’ ACCEPTED â†’ handler â†’ event."""
        biz_id = uuid.uuid4()
        ctx = StubContext(active=True, business_id=biz_id)
        persist_fn = StubPersistEvent()
        etr = StubEventTypeRegistry()
        service = StubEngineService(return_value="inventory.stock.moved persisted")

        dispatcher = CommandDispatcher(context=ctx)
        dispatcher.register_policy(ai_execution_guard)

        bus = CommandBus(
            dispatcher=dispatcher,
            persist_event=persist_fn,
            context=ctx,
            event_type_registry=etr,
        )
        bus.register_handler("inventory.stock.move.request", service)

        cmd = Command(
            command_id=uuid.uuid4(),
            command_type="inventory.stock.move.request",
            business_id=biz_id,
            branch_id=None,
            actor_type="HUMAN",
            actor_id="user-42",
            actor_context=ActorContext(actor_type="HUMAN", actor_id="user-42"),
            payload={"sku": "XYZ", "qty": 5},
            issued_at=datetime.now(timezone.utc),
            correlation_id=uuid.uuid4(),
            source_engine="inventory",
        )

        result = bus.handle(cmd)

        # Assertions
        assert result.is_accepted
        assert len(service.executed_commands) == 1
        assert service.executed_commands[0].command_id == cmd.command_id
        assert result.execution_result == "inventory.stock.moved persisted"
        # No rejection event persisted
        assert len(persist_fn.persisted_events) == 0

    def test_complete_rejected_flow(self):
        """Command â†’ validate â†’ policies â†’ REJECTED â†’ rejection event."""
        biz_id = uuid.uuid4()
        ctx = StubContext(active=True, business_id=biz_id)
        persist_fn = StubPersistEvent()
        etr = StubEventTypeRegistry()

        dispatcher = CommandDispatcher(context=ctx)
        dispatcher.register_policy(ai_execution_guard)

        bus = CommandBus(
            dispatcher=dispatcher,
            persist_event=persist_fn,
            context=ctx,
            event_type_registry=etr,
        )

        cmd = Command(
            command_id=uuid.uuid4(),
            command_type="inventory.stock.move.request",
            business_id=biz_id,
            branch_id=None,
            actor_type="AI",
            actor_id="ai-1",
            actor_context=ActorContext(actor_type="AI", actor_id="ai-1"),
            payload={"sku": "ABC"},
            issued_at=datetime.now(timezone.utc),
            correlation_id=uuid.uuid4(),
            source_engine="inventory",
        )

        result = bus.handle(cmd)

        # Assertions
        assert result.is_rejected
        assert result.rejection_event_persisted
        assert len(persist_fn.persisted_events) == 1

        event = persist_fn.persisted_events[0]
        assert event["event_type"] == "inventory.stock.move.rejected"
        assert event["business_id"] == biz_id
        assert event["source_engine"] == "inventory"
        assert event["payload"]["rejection"]["code"] == "AI_EXECUTION_FORBIDDEN"
        assert event["payload"]["command_id"] == str(cmd.command_id)

    def test_context_failure_produces_rejection_event(self):
        """Suspended business â†’ REJECTED â†’ rejection event persisted."""
        biz_id = uuid.uuid4()
        ctx = StubContext(
            active=True,
            business_id=biz_id,
            lifecycle_state="SUSPENDED",
        )
        persist_fn = StubPersistEvent()
        etr = StubEventTypeRegistry()

        dispatcher = CommandDispatcher(context=ctx)
        bus = CommandBus(
            dispatcher=dispatcher,
            persist_event=persist_fn,
            context=ctx,
            event_type_registry=etr,
        )

        cmd = Command(
            command_id=uuid.uuid4(),
            command_type="cash.session.open.request",
            business_id=biz_id,
            branch_id=None,
            actor_type="HUMAN",
            actor_id="user-1",
            actor_context=ActorContext(actor_type="HUMAN", actor_id="user-1"),
            payload={"register": "R1"},
            issued_at=datetime.now(timezone.utc),
            correlation_id=uuid.uuid4(),
            source_engine="cash",
        )

        result = bus.handle(cmd)

        assert result.is_rejected
        assert result.rejection_event_persisted
        event = persist_fn.persisted_events[0]
        assert event["event_type"] == "cash.session.open.rejected"
        assert event["payload"]["rejection"]["code"] == "BUSINESS_SUSPENDED"


