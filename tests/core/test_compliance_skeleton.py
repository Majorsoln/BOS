from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.commands.base import Command
from core.commands.dispatcher import CommandDispatcher
from core.compliance import (
    OP_GT,
    OP_GTE,
    PROFILE_ACTIVE,
    RULE_BLOCK,
    RULE_WARN,
    ComplianceEvaluator,
    ComplianceProfile,
    ComplianceRule,
    InMemoryComplianceProvider,
)
from core.context.actor_context import ActorContext
from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.feature_flags import (
    FEATURE_DISABLED as FLAG_STATUS_DISABLED,
    FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
    FLAG_ENABLE_COMPLIANCE_ENGINE,
    FeatureFlag,
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


class StubContext:
    def has_active_context(self) -> bool:
        return True

    def get_active_business_id(self):
        return BUSINESS_ID

    def get_business_lifecycle_state(self) -> str:
        return "ACTIVE"

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        return True


def _permission_provider_with_grant(actor_id: str = "user-1"):
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


def _command(
    *,
    branch_id=None,
    payload: dict | None = None,
    actor_requirement: str | None = None,
    actor_type: str = "HUMAN",
    actor_id: str = "user-1",
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
        command_type="test.x.y.request",
        business_id=BUSINESS_ID,
        branch_id=branch_id,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_context=actor_context,
        payload=payload or {"amount": 10},
        issued_at=datetime.now(timezone.utc),
        correlation_id=uuid.uuid4(),
        source_engine="test",
        scope_requirement=SCOPE_BUSINESS_ALLOWED,
        **kwargs,
    )


def _feature_provider(*flags: FeatureFlag):
    return InMemoryFeatureFlagProvider(flags=flags)


def _block_rule(
    threshold: int,
    message: str = "Amount exceeds compliance threshold.",
) -> ComplianceRule:
    return ComplianceRule(
        rule_key="CMP-BLOCK-001",
        applies_to="DOCUMENT:INVOICE",
        severity=RULE_BLOCK,
        predicate={"field": "amount", "op": OP_GT, "value": threshold},
        message=message,
    )


def _warn_rule(threshold: int) -> ComplianceRule:
    return ComplianceRule(
        rule_key="CMP-WARN-001",
        applies_to="DOCUMENT:INVOICE",
        severity=RULE_WARN,
        predicate={"field": "amount", "op": OP_GTE, "value": threshold},
        message="Amount should be reviewed.",
    )


def _profile(
    *,
    profile_id: str,
    version: int,
    ruleset: tuple[ComplianceRule, ...],
    branch_id=None,
    status: str = PROFILE_ACTIVE,
) -> ComplianceProfile:
    return ComplianceProfile(
        profile_id=profile_id,
        business_id=BUSINESS_ID,
        branch_id=branch_id,
        status=status,
        version=version,
        ruleset=ruleset,
    )


def test_compliance_disabled_via_feature_flag_skips_checks():
    permission_provider = _permission_provider_with_grant()
    feature_provider = _feature_provider(
        FeatureFlag(
            flag_key=FLAG_ENABLE_COMPLIANCE_ENGINE,
            business_id=BUSINESS_ID,
            status=FLAG_STATUS_DISABLED,
        )
    )
    compliance_provider = InMemoryComplianceProvider(
        profiles=(
            _profile(
                profile_id="biz-1",
                version=1,
                ruleset=(_block_rule(threshold=5),),
            ),
        )
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=permission_provider,
        feature_flag_provider=feature_provider,
        compliance_provider=compliance_provider,
    )

    outcome = dispatcher.dispatch(_command(payload={"amount": 50}))

    assert outcome.is_accepted


def test_no_profile_exists_allowed():
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider_with_grant(),
        feature_flag_provider=_feature_provider(),
        compliance_provider=InMemoryComplianceProvider(),
    )

    outcome = dispatcher.dispatch(_command(payload={"amount": 50}))

    assert outcome.is_accepted


def test_business_profile_block_rule_rejects():
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider_with_grant(),
        feature_flag_provider=_feature_provider(),
        compliance_provider=InMemoryComplianceProvider(
            profiles=(
                _profile(
                    profile_id="biz-1",
                    version=1,
                    ruleset=(_block_rule(threshold=5),),
                ),
            )
        ),
    )

    outcome = dispatcher.dispatch(_command(payload={"amount": 99}))

    assert outcome.is_rejected
    assert outcome.reason.code == "COMPLIANCE_VIOLATION"


def test_branch_override_profile_wins_over_business_profile():
    business_profile = _profile(
        profile_id="biz-1",
        version=1,
        ruleset=(_block_rule(threshold=100),),
    )
    branch_profile = _profile(
        profile_id="branch-1",
        version=1,
        branch_id=BRANCH_ID,
        ruleset=(_block_rule(threshold=5, message="Branch rule violated."),),
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider_with_grant(),
        feature_flag_provider=_feature_provider(),
        compliance_provider=InMemoryComplianceProvider(
            profiles=(business_profile, branch_profile)
        ),
    )

    outcome = dispatcher.dispatch(
        _command(branch_id=BRANCH_ID, payload={"amount": 50})
    )

    assert outcome.is_rejected
    assert outcome.reason.code == "COMPLIANCE_VIOLATION"
    assert "Branch rule violated." in outcome.reason.message


def test_warn_rule_does_not_reject():
    provider = InMemoryComplianceProvider(
        profiles=(
            _profile(
                profile_id="biz-1",
                version=1,
                ruleset=(_warn_rule(threshold=10),),
            ),
        )
    )
    command = _command(payload={"amount": 10})
    result = ComplianceEvaluator.evaluate(
        command=command,
        business_context=StubContext(),
        provider=provider,
    )

    assert result.allowed
    assert len(result.details.get("warnings", [])) == 1


def test_system_allowed_bypasses_compliance():
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider_with_grant(),
        feature_flag_provider=_feature_provider(),
        compliance_provider=InMemoryComplianceProvider(
            profiles=(
                _profile(
                    profile_id="biz-1",
                    version=1,
                    ruleset=(_block_rule(threshold=5),),
                ),
            )
        ),
    )

    outcome = dispatcher.dispatch(
        _command(
            actor_requirement=SYSTEM_ALLOWED,
            payload={"amount": 999},
        )
    )

    assert outcome.is_accepted


def test_feature_flag_evaluation_error_skips_compliance():
    class BrokenFeatureProvider:
        def get_flags_for_business(self, business_id):
            raise RuntimeError("flag provider down")

    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider_with_grant(),
        feature_flag_provider=BrokenFeatureProvider(),
        compliance_provider=InMemoryComplianceProvider(
            profiles=(
                _profile(
                    profile_id="biz-1",
                    version=1,
                    ruleset=(_block_rule(threshold=5),),
                ),
            )
        ),
    )

    outcome = dispatcher.dispatch(_command(payload={"amount": 999}))

    assert outcome.is_accepted


def test_compliance_evaluation_error_rejects_deterministically():
    class BrokenComplianceProvider:
        def get_profiles_for_business(self, business_id):
            raise RuntimeError("compliance provider down")

    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider_with_grant(),
        feature_flag_provider=_feature_provider(),
        compliance_provider=BrokenComplianceProvider(),
    )

    outcome = dispatcher.dispatch(_command(payload={"amount": 999}))

    assert outcome.is_rejected
    assert outcome.reason.code == "COMPLIANCE_VIOLATION"


def test_inmemory_provider_duplicate_scope_version_rejected():
    profile_a = _profile(
        profile_id="same-scope-a",
        version=1,
        ruleset=(_block_rule(threshold=5),),
    )
    profile_b = _profile(
        profile_id="same-scope-b",
        version=1,
        ruleset=(_block_rule(threshold=50),),
    )

    with pytest.raises(ValueError):
        InMemoryComplianceProvider(profiles=(profile_a, profile_b))


def test_evaluator_canonicalizes_noncompliant_provider_duplicates():
    class NonCompliantProvider:
        def __init__(self, profiles):
            self._profiles = tuple(profiles)

        def get_profiles_for_business(self, business_id):
            return self._profiles

    profile_a = _profile(
        profile_id="dup-a",
        version=1,
        ruleset=(_block_rule(threshold=5),),
    )
    profile_b = _profile(
        profile_id="dup-b",
        version=1,
        ruleset=(_block_rule(threshold=500),),
    )

    command = _command(payload={"amount": 100})
    result_1 = ComplianceEvaluator.evaluate(
        command=command,
        business_context=StubContext(),
        provider=NonCompliantProvider((profile_a, profile_b)),
    )
    result_2 = ComplianceEvaluator.evaluate(
        command=command,
        business_context=StubContext(),
        provider=NonCompliantProvider((profile_b, profile_a)),
    )

    assert result_1.allowed == result_2.allowed
    assert result_1.details.get("profile_id") == result_2.details.get("profile_id")


def test_no_branch_inference_other_branch_only_profile_allows():
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider_with_grant(),
        feature_flag_provider=_feature_provider(),
        compliance_provider=InMemoryComplianceProvider(
            profiles=(
                _profile(
                    profile_id="other-branch",
                    version=1,
                    branch_id=OTHER_BRANCH_ID,
                    ruleset=(_block_rule(threshold=5),),
                ),
            )
        ),
    )

    outcome = dispatcher.dispatch(
        _command(branch_id=BRANCH_ID, payload={"amount": 999})
    )

    assert outcome.is_accepted


def test_branch_without_exact_profile_falls_back_to_business_profile():
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider_with_grant(),
        feature_flag_provider=_feature_provider(),
        compliance_provider=InMemoryComplianceProvider(
            profiles=(
                _profile(
                    profile_id="business-default",
                    version=1,
                    ruleset=(_block_rule(threshold=5),),
                ),
                _profile(
                    profile_id="other-branch",
                    version=1,
                    branch_id=OTHER_BRANCH_ID,
                    ruleset=(_block_rule(threshold=500),),
                ),
            )
        ),
    )

    outcome = dispatcher.dispatch(
        _command(branch_id=BRANCH_ID, payload={"amount": 50})
    )

    assert outcome.is_rejected
    assert outcome.reason.code == "COMPLIANCE_VIOLATION"


def test_permission_denial_happens_before_compliance():
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=InMemoryPermissionProvider(),
        feature_flag_provider=_feature_provider(),
        compliance_provider=InMemoryComplianceProvider(
            profiles=(
                _profile(
                    profile_id="business-default",
                    version=1,
                    ruleset=(_block_rule(threshold=5),),
                ),
            )
        ),
    )

    outcome = dispatcher.dispatch(_command(payload={"amount": 999}))

    assert outcome.is_rejected
    assert outcome.reason.code == "PERMISSION_DENIED"


def test_feature_flag_boundary_denial_happens_before_compliance():
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider_with_grant(),
        feature_flag_provider=_feature_provider(
            FeatureFlag(
                flag_key=FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
                business_id=BUSINESS_ID,
                status=FLAG_STATUS_DISABLED,
            )
        ),
        compliance_provider=InMemoryComplianceProvider(
            profiles=(
                _profile(
                    profile_id="business-default",
                    version=1,
                    ruleset=(_block_rule(threshold=5),),
                ),
            )
        ),
    )

    outcome = dispatcher.dispatch(_command(payload={"amount": 999}))

    assert outcome.is_rejected
    assert outcome.reason.code == "FEATURE_DISABLED"


def test_replay_path_does_not_reference_compliance_guard():
    replay_file = Path("core/replay/event_replayer.py")
    source = replay_file.read_text(encoding="utf-8").lower()
    assert "compliance_" not in source

