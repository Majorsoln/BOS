from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.commands.base import Command
from core.commands.dispatcher import CommandDispatcher
from core.context.actor_context import ActorContext
from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.feature_flags import (
    FEATURE_DISABLED as FLAG_STATUS_DISABLED,
    FEATURE_ENABLED as FLAG_STATUS_ENABLED,
    FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
    FeatureFlag,
    FeatureFlagEvaluator,
    InMemoryFeatureFlagProvider,
)
from core.identity.requirements import SYSTEM_ALLOWED
from core.permissions import (
    InMemoryPermissionProvider,
    PERMISSION_CMD_EXECUTE_GENERIC,
    Role,
    ScopeGrant,
)


BUSINESS_ID = uuid.uuid4()
BRANCH_ID = uuid.uuid4()
OTHER_BRANCH_ID = uuid.uuid4()
MAPPED_COMMAND_TYPE = "test.x.y.request"
UNMAPPED_COMMAND_TYPE = "test.thing.do.request"


def _permission_provider_with_grant(actor_id: str) -> InMemoryPermissionProvider:
    role = Role(
        role_id="generic-role",
        permissions=(PERMISSION_CMD_EXECUTE_GENERIC,),
    )
    grant = ScopeGrant(
        actor_id=actor_id,
        role_id="generic-role",
        business_id=BUSINESS_ID,
    )
    return InMemoryPermissionProvider(roles=(role,), grants=(grant,))


class StubContext:
    def has_active_context(self) -> bool:
        return True

    def get_active_business_id(self):
        return BUSINESS_ID

    def get_business_lifecycle_state(self) -> str:
        return "ACTIVE"

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        return True


def _command(
    *,
    command_type: str = MAPPED_COMMAND_TYPE,
    source_engine: str = "test",
    actor_id: str = "user-1",
    actor_type: str = "HUMAN",
    actor_requirement: str | None = None,
    branch_id=None,
) -> Command:
    kwargs = {}
    actor_context = ActorContext(actor_type=actor_type, actor_id=actor_id)

    if actor_requirement is not None:
        kwargs["actor_requirement"] = actor_requirement
        if actor_requirement == SYSTEM_ALLOWED:
            actor_type = "SYSTEM"
            actor_id = "kernel"
            actor_context = None

    return Command(
        command_id=uuid.uuid4(),
        command_type=command_type,
        business_id=BUSINESS_ID,
        branch_id=branch_id,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_context=actor_context,
        payload={"x": 1},
        issued_at=datetime.now(timezone.utc),
        correlation_id=uuid.uuid4(),
        source_engine=source_engine,
        scope_requirement=SCOPE_BUSINESS_ALLOWED,
        **kwargs,
    )


def _flag_provider(*flags: FeatureFlag) -> InMemoryFeatureFlagProvider:
    return InMemoryFeatureFlagProvider(flags=flags)


def test_mapped_command_disabled_flag_rejected():
    permission_provider = _permission_provider_with_grant("user-1")
    feature_provider = _flag_provider(
        FeatureFlag(
            flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
            business_id=BUSINESS_ID,
            status=FLAG_STATUS_DISABLED,
        )
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=permission_provider,
        feature_flag_provider=feature_provider,
    )

    outcome = dispatcher.dispatch(_command())

    assert outcome.is_rejected
    assert outcome.reason.code == "FEATURE_DISABLED"


def test_mapped_command_enabled_flag_allowed():
    permission_provider = _permission_provider_with_grant("user-1")
    feature_provider = _flag_provider(
        FeatureFlag(
            flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
            business_id=BUSINESS_ID,
            status=FLAG_STATUS_ENABLED,
        )
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=permission_provider,
        feature_flag_provider=feature_provider,
    )

    outcome = dispatcher.dispatch(_command())

    assert outcome.is_accepted


def test_unmapped_command_allowed():
    permission_provider = _permission_provider_with_grant("user-1")
    feature_provider = _flag_provider(
        FeatureFlag(
            flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
            business_id=BUSINESS_ID,
            status=FLAG_STATUS_DISABLED,
        )
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=permission_provider,
        feature_flag_provider=feature_provider,
    )

    outcome = dispatcher.dispatch(
        _command(
            command_type=UNMAPPED_COMMAND_TYPE,
            source_engine="test",
        )
    )

    assert outcome.is_accepted


def test_branch_exact_override_disabled_rejected():
    permission_provider = _permission_provider_with_grant("user-1")
    feature_provider = _flag_provider(
        FeatureFlag(
            flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
            business_id=BUSINESS_ID,
            status=FLAG_STATUS_ENABLED,
        ),
        FeatureFlag(
            flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
            business_id=BUSINESS_ID,
            branch_id=BRANCH_ID,
            status=FLAG_STATUS_DISABLED,
        ),
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=permission_provider,
        feature_flag_provider=feature_provider,
    )

    outcome = dispatcher.dispatch(_command(branch_id=BRANCH_ID))

    assert outcome.is_rejected
    assert outcome.reason.code == "FEATURE_DISABLED"


def test_no_exact_branch_record_falls_back_to_business_enabled():
    permission_provider = _permission_provider_with_grant("user-1")
    feature_provider = _flag_provider(
        FeatureFlag(
            flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
            business_id=BUSINESS_ID,
            status=FLAG_STATUS_ENABLED,
        ),
        FeatureFlag(
            flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
            business_id=BUSINESS_ID,
            branch_id=OTHER_BRANCH_ID,
            status=FLAG_STATUS_DISABLED,
        ),
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=permission_provider,
        feature_flag_provider=feature_provider,
    )

    outcome = dispatcher.dispatch(_command(branch_id=BRANCH_ID))

    assert outcome.is_accepted


def test_other_branch_override_does_not_block_without_exact_match():
    permission_provider = _permission_provider_with_grant("user-1")
    feature_provider = _flag_provider(
        FeatureFlag(
            flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
            business_id=BUSINESS_ID,
            status=FLAG_STATUS_ENABLED,
        ),
        FeatureFlag(
            flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
            business_id=BUSINESS_ID,
            branch_id=OTHER_BRANCH_ID,
            status=FLAG_STATUS_ENABLED,
        ),
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=permission_provider,
        feature_flag_provider=feature_provider,
    )

    outcome = dispatcher.dispatch(_command(branch_id=BRANCH_ID))

    assert outcome.is_accepted


def test_no_effective_record_allows_enabled_if_missing():
    permission_provider = _permission_provider_with_grant("user-1")
    feature_provider = _flag_provider(
        FeatureFlag(
            flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
            business_id=BUSINESS_ID,
            branch_id=OTHER_BRANCH_ID,
            status=FLAG_STATUS_DISABLED,
        )
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=permission_provider,
        feature_flag_provider=feature_provider,
    )

    outcome = dispatcher.dispatch(_command(branch_id=BRANCH_ID))

    assert outcome.is_accepted


def test_system_allowed_bypasses_feature_flags():
    permission_provider = _permission_provider_with_grant("user-1")
    feature_provider = _flag_provider(
        FeatureFlag(
            flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
            business_id=BUSINESS_ID,
            status=FLAG_STATUS_DISABLED,
        )
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=permission_provider,
        feature_flag_provider=feature_provider,
    )

    outcome = dispatcher.dispatch(
        _command(
            actor_requirement=SYSTEM_ALLOWED,
        )
    )

    assert outcome.is_accepted


def test_feature_flag_guard_fail_open_on_provider_exception():
    class BrokenFeatureProvider:
        def get_flags_for_business(self, business_id):
            raise RuntimeError("provider unavailable")

    permission_provider = _permission_provider_with_grant("user-1")
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=permission_provider,
        feature_flag_provider=BrokenFeatureProvider(),
    )

    outcome = dispatcher.dispatch(_command())

    assert outcome.is_accepted


def test_duplicate_scope_in_memory_provider_rejected():
    flag_a = FeatureFlag(
        flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
        business_id=BUSINESS_ID,
        status=FLAG_STATUS_ENABLED,
    )
    flag_b = FeatureFlag(
        flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
        business_id=BUSINESS_ID,
        status=FLAG_STATUS_DISABLED,
    )

    with pytest.raises(ValueError):
        InMemoryFeatureFlagProvider(flags=(flag_a, flag_b))


def test_evaluator_canonicalization_is_deterministic_for_noncompliant_provider():
    class NonCompliantProvider:
        def __init__(self, flags):
            self._flags = tuple(flags)

        def get_flags_for_business(self, business_id):
            return self._flags

    command = _command()

    enabled = FeatureFlag(
        flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
        business_id=BUSINESS_ID,
        status=FLAG_STATUS_ENABLED,
    )
    disabled = FeatureFlag(
        flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
        business_id=BUSINESS_ID,
        status=FLAG_STATUS_DISABLED,
    )

    result_a = FeatureFlagEvaluator.evaluate(
        command=command,
        business_context=StubContext(),
        provider=NonCompliantProvider((enabled, disabled)),
    )
    result_b = FeatureFlagEvaluator.evaluate(
        command=command,
        business_context=StubContext(),
        provider=NonCompliantProvider((disabled, enabled)),
    )

    assert result_a.allowed is False
    assert result_b.allowed is False
    assert result_a.rejection_code == "FEATURE_DISABLED"
    assert result_b.rejection_code == "FEATURE_DISABLED"


def test_permission_boundary_runs_before_feature_flags():
    feature_provider = _flag_provider(
        FeatureFlag(
            flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
            business_id=BUSINESS_ID,
            status=FLAG_STATUS_ENABLED,
        )
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=InMemoryPermissionProvider(),
        feature_flag_provider=feature_provider,
    )

    outcome = dispatcher.dispatch(_command())

    assert outcome.is_rejected
    assert outcome.reason.code == "PERMISSION_DENIED"


def test_replay_path_does_not_include_feature_flag_evaluation():
    replay_file = Path("core/replay/event_replayer.py")
    source = replay_file.read_text(encoding="utf-8").lower()
    assert "feature_flag" not in source
