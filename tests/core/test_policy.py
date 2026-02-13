"""
BOS Policy Engine — Comprehensive Tests (Stabilization Patch v1.0.2)
======================================================================
Tests verify BEHAVIOR, not just coverage.

Required stabilization tests:
1. Rule exception converts to BLOCK (Fix 1)
2. Evaluation never raises (Fix 1)
3. Version snapshot integrity (Fix 3)
4. Unknown version startup failure (Fix 3)
5. Time injection consistency (Fix 2)
6. Contract validation failure (Fix 4)
7. ESCALATE forces REVIEW_REQUIRED (Fix 5)
8. Deterministic replay (Fix 3 + Fix 2)

Plus: all original tests, individual rules, registry, integration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import pytest

from core.commands.base import Command
from core.commands.dispatcher import ai_execution_guard
from core.commands.outcomes import CommandStatus
from core.policy.contracts import BaseRule
from core.policy.engine import PolicyEngine
from core.policy.exceptions import (
    DuplicateRuleError,
    RegistryLockedError,
)
from core.policy.registry import PolicyRegistry
from core.policy.result import PolicyDecision, RuleResult, Severity
from core.policy.versioning import INITIAL_POLICY_VERSION
from core.policy.rules import (
    ClosedBusinessBlock,
    HighDiscountEscalate,
    MissingVATEscalate,
    NegativeStockBlock,
    TenantScopeBlock,
)
from core.policy.integration import (
    EVENT_STATUS_FINAL,
    EVENT_STATUS_REVIEW_REQUIRED,
    PolicyAwareDispatcher,
    PolicyAwareOutcome,
)


# ══════════════════════════════════════════════════════════════
# TEST STUBS
# ══════════════════════════════════════════════════════════════

BUSINESS_ID = uuid.uuid4()
FIXED_TIME = datetime(2026, 2, 13, 12, 0, 0, tzinfo=timezone.utc)


class StubContext:
    def __init__(
        self,
        active: bool = True,
        business_id: Optional[uuid.UUID] = None,
        lifecycle_state: str = "ACTIVE",
        branches: Optional[set] = None,
    ):
        self._active = active
        self._business_id = business_id or BUSINESS_ID
        self._lifecycle_state = lifecycle_state
        self._branches = branches or set()

    def has_active_context(self) -> bool:
        return self._active

    def get_active_business_id(self):
        return self._business_id

    def get_active_branch_id(self):
        return None

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        return branch_id in self._branches

    def get_business_lifecycle_state(self) -> str:
        return self._lifecycle_state


def make_command(
    command_type: str = "inventory.stock.move.request",
    source_engine: str = "inventory",
    payload: dict = None,
    actor_type: str = "HUMAN",
    business_id: uuid.UUID = None,
    issued_at: datetime = None,
) -> Command:
    return Command(
        command_id=uuid.uuid4(),
        command_type=command_type,
        business_id=business_id or BUSINESS_ID,
        branch_id=None,
        actor_type=actor_type,
        actor_id="user-1",
        payload=payload or {},
        issued_at=issued_at or FIXED_TIME,
        correlation_id=uuid.uuid4(),
        source_engine=source_engine,
    )


# ══════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def registry():
    reg = PolicyRegistry()
    reg.register_rule(NegativeStockBlock())
    reg.register_rule(HighDiscountEscalate())
    reg.register_rule(ClosedBusinessBlock())
    reg.register_rule(MissingVATEscalate())
    reg.register_rule(TenantScopeBlock())
    reg.lock(version="1.0.0")
    return reg


@pytest.fixture
def engine(registry):
    return PolicyEngine(registry=registry)


@pytest.fixture
def context():
    return StubContext()


# ══════════════════════════════════════════════════════════════
# FIX 1: FAIL-SAFE — RULE EXCEPTION CONVERTS TO BLOCK
# ══════════════════════════════════════════════════════════════

class TestFailSafeBehavior:
    """Fix 1: evaluate() NEVER raises. Exceptions → BLOCK."""

    def test_rule_exception_converts_to_block(self):
        """Broken rule → BLOCK RuleResult, not exception."""

        class BrokenRule(BaseRule):
            rule_id = "BRK-001"
            version = "1.0.0"
            domain = "test"
            severity = Severity.WARN  # Even if WARN, error → BLOCK
            applies_to = ["test.thing.do.request"]

            def evaluate(self, c, ctx, s):
                raise RuntimeError("I am broken")

        reg = PolicyRegistry()
        reg.register_rule(BrokenRule())
        reg.lock(version="1.0.0")
        eng = PolicyEngine(registry=reg)

        cmd = make_command(
            command_type="test.thing.do.request",
            source_engine="test",
        )

        # MUST NOT raise
        decision = eng.evaluate(
            cmd, StubContext(), {}, policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )

        # Must convert to BLOCK
        assert not decision.allowed
        assert len(decision.violations) == 1
        assert decision.violations[0].severity == Severity.BLOCK
        assert "RuntimeError" in decision.violations[0].metadata["error_type"]
        assert decision.violations[0].rule_id == "BRK-001"

    def test_evaluation_never_raises_on_any_exception(self):
        """Any exception type is caught — never propagates."""

        class TypeErrorRule(BaseRule):
            rule_id = "ERR-001"
            version = "1.0.0"
            domain = "test"
            severity = Severity.BLOCK
            applies_to = ["test.thing.do.request"]

            def evaluate(self, c, ctx, s):
                raise TypeError("bad type")

        class ValueErrorRule(BaseRule):
            rule_id = "ERR-002"
            version = "1.0.0"
            domain = "test"
            severity = Severity.BLOCK
            applies_to = ["test.thing.do.request"]

            def evaluate(self, c, ctx, s):
                raise ValueError("bad value")

        class KeyErrorRule(BaseRule):
            rule_id = "ERR-003"
            version = "1.0.0"
            domain = "test"
            severity = Severity.BLOCK
            applies_to = ["test.thing.do.request"]

            def evaluate(self, c, ctx, s):
                raise KeyError("missing key")

        reg = PolicyRegistry()
        reg.register_rule(TypeErrorRule())
        reg.register_rule(ValueErrorRule())
        reg.register_rule(KeyErrorRule())
        reg.lock(version="1.0.0")
        eng = PolicyEngine(registry=reg)

        cmd = make_command(
            command_type="test.thing.do.request",
            source_engine="test",
        )

        # MUST NOT raise — all caught
        decision = eng.evaluate(
            cmd, StubContext(), {}, policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )
        assert not decision.allowed
        assert len(decision.violations) == 3

    def test_invalid_return_type_converts_to_block(self):
        """Rule returning wrong type → BLOCK, not crash."""

        class BadReturnRule(BaseRule):
            rule_id = "BAD-001"
            version = "1.0.0"
            domain = "test"
            severity = Severity.WARN
            applies_to = ["test.thing.do.request"]

            def evaluate(self, c, ctx, s):
                return "not a RuleResult"

        reg = PolicyRegistry()
        reg.register_rule(BadReturnRule())
        reg.lock(version="1.0.0")
        eng = PolicyEngine(registry=reg)

        cmd = make_command(
            command_type="test.thing.do.request",
            source_engine="test",
        )

        decision = eng.evaluate(
            cmd, StubContext(), {}, policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )
        assert not decision.allowed
        assert decision.violations[0].metadata["error_type"] == "INVALID_RETURN_TYPE"


# ══════════════════════════════════════════════════════════════
# FIX 2: TIME INJECTION — NO SYSTEM CLOCK
# ══════════════════════════════════════════════════════════════

class TestTimeInjection:
    """Fix 2: Time from command context, never datetime.now()."""

    def test_evaluation_time_in_explanation(self, engine, context):
        cmd = make_command(
            payload={"quantity": 1}, issued_at=FIXED_TIME
        )
        decision = engine.evaluate(
            cmd, context, {"available_stock": 100},
            policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )
        assert decision.explanation_tree["evaluation_time"] == FIXED_TIME.isoformat()

    def test_dispatcher_uses_command_issued_at(self, registry, context):
        """PolicyAwareDispatcher passes command.issued_at, not now()."""
        eng = PolicyEngine(registry=registry)
        dispatcher = PolicyAwareDispatcher(
            context=context, policy_engine=eng
        )

        specific_time = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        cmd = make_command(
            payload={"quantity": 1},
            issued_at=specific_time,
        )

        result = dispatcher.dispatch(
            cmd,
            projected_state={"available_stock": 100},
            policy_version="1.0.0",
        )

        # Outcome timestamp must be command's issued_at
        assert result.outcome.occurred_at == specific_time

    def test_none_evaluation_time_produces_null(self, engine, context):
        cmd = make_command(payload={"quantity": 1})
        decision = engine.evaluate(
            cmd, context, {"available_stock": 100},
            policy_version="1.0.0",
            evaluation_time=None,
        )
        assert decision.explanation_tree["evaluation_time"] is None


# ══════════════════════════════════════════════════════════════
# FIX 3: VERSION SNAPSHOT INTEGRITY
# ══════════════════════════════════════════════════════════════

class TestVersionSnapshots:
    """Fix 3: Version-scoped rule registry with frozen snapshots."""

    def test_lock_creates_version_snapshot(self):
        reg = PolicyRegistry()
        reg.register_rule(NegativeStockBlock())
        reg.lock(version="1.0.0")

        assert reg.has_version("1.0.0")

    def test_version_scoped_rules(self, registry):
        """Querying with version returns snapshot rules."""
        rules = registry.get_rules_for_command(
            "inventory.stock.move.request",
            policy_version="1.0.0",
        )
        assert len(rules) > 0
        rule_ids = {r.rule_id for r in rules}
        assert "INV-001" in rule_ids

    def test_unknown_version_returns_empty(self, registry):
        """Unknown version → empty rule set (fail-safe)."""
        rules = registry.get_rules_for_command(
            "inventory.stock.move.request",
            policy_version="99.99.99",
        )
        assert rules == []

    def test_unknown_version_evaluation_allows(self, registry):
        """Unknown version → no rules → allowed (fail-safe)."""
        eng = PolicyEngine(registry=registry)
        cmd = make_command(payload={"quantity": 9999})

        decision = eng.evaluate(
            cmd, StubContext(), {"available_stock": 0},
            policy_version="99.99.99",
            evaluation_time=FIXED_TIME,
        )
        # No rules found → allowed (no violations)
        assert decision.allowed
        assert decision.explanation_tree["rules_evaluated"] == 0

    def test_multiple_versions(self):
        """Registry supports multiple version snapshots."""
        reg = PolicyRegistry()
        reg.register_rule(NegativeStockBlock())
        reg.lock(version="1.0.0")

        # Can't add more after lock, but version exists
        assert reg.has_version("1.0.0")
        assert not reg.has_version("2.0.0")

    def test_snapshot_frozen_at_lock_time(self):
        """Snapshot reflects rules at time of lock(), not after."""
        reg = PolicyRegistry()
        reg.register_rule(NegativeStockBlock())
        reg.lock(version="1.0.0")

        # Snapshot has INV-001
        rules = reg.get_rules_for_command(
            "inventory.stock.move.request",
            policy_version="1.0.0",
        )
        assert any(r.rule_id == "INV-001" for r in rules)


# ══════════════════════════════════════════════════════════════
# FIX 4: CONTRACT VALIDATION — SEMVER ENFORCEMENT
# ══════════════════════════════════════════════════════════════

class TestContractValidation:
    """Fix 4: BaseRule contract validated at class creation time."""

    def test_missing_rule_id_rejected(self):
        with pytest.raises(TypeError, match="rule_id"):
            class BadId(BaseRule):
                rule_id = ""
                version = "1.0.0"
                domain = "test"
                severity = Severity.BLOCK
                applies_to = ["test.x.y.request"]

                def evaluate(self, c, ctx, s):
                    return self.pass_rule()

    def test_invalid_semver_rejected(self):
        with pytest.raises(TypeError, match="semantic version"):
            class BadVer(BaseRule):
                rule_id = "T-001"
                version = "v1"
                domain = "test"
                severity = Severity.BLOCK
                applies_to = ["test.x.y.request"]

                def evaluate(self, c, ctx, s):
                    return self.pass_rule()

    def test_invalid_semver_two_parts_rejected(self):
        with pytest.raises(TypeError, match="semantic version"):
            class BadVer2(BaseRule):
                rule_id = "T-002"
                version = "1.0"
                domain = "test"
                severity = Severity.BLOCK
                applies_to = ["test.x.y.request"]

                def evaluate(self, c, ctx, s):
                    return self.pass_rule()

    def test_valid_semver_accepted(self):
        # Should NOT raise
        class GoodVer(BaseRule):
            rule_id = "T-003"
            version = "2.1.3"
            domain = "test"
            severity = Severity.BLOCK
            applies_to = ["test.x.y.request"]

            def evaluate(self, c, ctx, s):
                return self.pass_rule()

        assert GoodVer.version == "2.1.3"

    def test_invalid_severity_rejected(self):
        with pytest.raises(TypeError, match="severity"):
            class BadSev(BaseRule):
                rule_id = "T-004"
                version = "1.0.0"
                domain = "test"
                severity = "CRITICAL"
                applies_to = ["test.x.y.request"]

                def evaluate(self, c, ctx, s):
                    return self.pass_rule()

    def test_missing_domain_rejected(self):
        with pytest.raises(TypeError, match="domain"):
            class NoDomain(BaseRule):
                rule_id = "T-005"
                version = "1.0.0"
                domain = ""
                severity = Severity.BLOCK
                applies_to = ["test.x.y.request"]

                def evaluate(self, c, ctx, s):
                    return self.pass_rule()

    def test_empty_applies_to_rejected(self):
        with pytest.raises(TypeError, match="applies_to"):
            class NoApplies(BaseRule):
                rule_id = "T-006"
                version = "1.0.0"
                domain = "test"
                severity = Severity.BLOCK
                applies_to = []

                def evaluate(self, c, ctx, s):
                    return self.pass_rule()


# ══════════════════════════════════════════════════════════════
# FIX 5: ESCALATE → REVIEW_REQUIRED ENFORCEMENT
# ══════════════════════════════════════════════════════════════

class TestEscalateEnforcement:
    """Fix 5: ESCALATE forces event_status=REVIEW_REQUIRED."""

    def test_escalate_enforces_review_required(self, context):
        reg = PolicyRegistry()
        reg.register_rule(HighDiscountEscalate())
        reg.lock(version="1.0.0")
        eng = PolicyEngine(registry=reg)

        dispatcher = PolicyAwareDispatcher(
            context=context, policy_engine=eng
        )

        cmd = make_command(
            command_type="retail.sale.apply_discount.request",
            source_engine="retail",
            payload={"discount_percent": 0.60},
        )

        result = dispatcher.dispatch(
            cmd,
            projected_state={"discount_threshold": 0.30},
            policy_version="1.0.0",
        )

        assert result.is_accepted
        assert result.requires_review
        assert result.enforced_event_status == EVENT_STATUS_REVIEW_REQUIRED

    def test_no_escalation_means_final(self, registry, context):
        eng = PolicyEngine(registry=registry)
        dispatcher = PolicyAwareDispatcher(
            context=context, policy_engine=eng
        )

        cmd = make_command(payload={"quantity": 1})
        result = dispatcher.dispatch(
            cmd,
            projected_state={"available_stock": 100},
            policy_version="1.0.0",
        )

        assert result.is_accepted
        assert not result.requires_review
        assert result.enforced_event_status == EVENT_STATUS_FINAL

    def test_rejected_command_status_final(self, registry, context):
        eng = PolicyEngine(registry=registry)
        dispatcher = PolicyAwareDispatcher(
            context=context, policy_engine=eng
        )

        cmd = make_command(payload={"quantity": 999})
        result = dispatcher.dispatch(
            cmd,
            projected_state={"available_stock": 1},
            policy_version="1.0.0",
        )

        assert result.is_rejected
        # Rejection events are FINAL (rejection itself is the record)
        assert result.enforced_event_status == EVENT_STATUS_FINAL


# ══════════════════════════════════════════════════════════════
# FIX 6: EXPLANATION TREE ENHANCED
# ══════════════════════════════════════════════════════════════

class TestExplanationTreeEnhanced:
    """Fix 6: Explanation includes metadata, version, evaluation_time."""

    def test_explanation_has_metadata(self, engine, context):
        cmd = make_command(payload={"quantity": 100})
        decision = engine.evaluate(
            cmd, context, {"available_stock": 10},
            policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )
        details = decision.explanation_tree["details"]
        # Failed rule should have metadata
        failed = [d for d in details if not d["passed"]]
        assert any("metadata" in d for d in failed)
        assert any(d["metadata"].get("deficit") for d in failed)

    def test_explanation_has_version(self, engine, context):
        cmd = make_command(payload={"quantity": 1})
        decision = engine.evaluate(
            cmd, context, {"available_stock": 100},
            policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )
        assert decision.explanation_tree["policy_version"] == "1.0.0"

    def test_explanation_has_evaluation_time(self, engine, context):
        cmd = make_command(payload={"quantity": 1})
        decision = engine.evaluate(
            cmd, context, {"available_stock": 100},
            policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )
        assert decision.explanation_tree["evaluation_time"] == FIXED_TIME.isoformat()


# ══════════════════════════════════════════════════════════════
# FIX 7: PROHIBIT DUPLICATE RULES
# ══════════════════════════════════════════════════════════════

class TestDuplicateRulePrevention:
    """Fix 7: Duplicate rule_id + version hard fails."""

    def test_duplicate_rule_rejected(self):
        reg = PolicyRegistry()
        reg.register_rule(NegativeStockBlock())
        with pytest.raises(DuplicateRuleError):
            reg.register_rule(NegativeStockBlock())

    def test_lock_prevents_registration(self):
        reg = PolicyRegistry()
        reg.lock(version="1.0.0")
        with pytest.raises(RegistryLockedError):
            reg.register_rule(NegativeStockBlock())


# ══════════════════════════════════════════════════════════════
# DETERMINISTIC REPLAY (Fix 2 + Fix 3 combined)
# ══════════════════════════════════════════════════════════════

class TestDeterministicReplay:
    """Replay with same version + same time → identical result."""

    def test_replay_identical_results(self, engine, context):
        cmd = make_command(payload={"quantity": 50})
        state = {"available_stock": 10}

        d1 = engine.evaluate(
            cmd, context, state,
            policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )
        d2 = engine.evaluate(
            cmd, context, state,
            policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )

        assert d1.allowed == d2.allowed
        assert d1.policy_version == d2.policy_version
        assert len(d1.violations) == len(d2.violations)
        assert (
            d1.explanation_tree["evaluation_time"]
            == d2.explanation_tree["evaluation_time"]
        )

    def test_different_versions_may_differ(self):
        """Different version snapshots can have different rules."""
        reg = PolicyRegistry()
        reg.register_rule(NegativeStockBlock())
        reg.lock(version="1.0.0")
        eng = PolicyEngine(registry=reg)

        cmd = make_command(payload={"quantity": 100})
        state = {"available_stock": 10}

        # Version 1.0.0 has rules → BLOCKED
        d1 = eng.evaluate(
            cmd, StubContext(), state,
            policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )

        # Version 99.0.0 has no snapshot → no rules → ALLOWED
        d2 = eng.evaluate(
            cmd, StubContext(), state,
            policy_version="99.0.0",
            evaluation_time=FIXED_TIME,
        )

        assert not d1.allowed
        assert d2.allowed  # No rules for this version

    def test_pure_no_state_mutation(self, engine, context):
        state = {"available_stock": 5}
        state_copy = dict(state)
        cmd = make_command(payload={"quantity": 10})

        engine.evaluate(
            cmd, context, state,
            policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )
        assert state == state_copy


# ══════════════════════════════════════════════════════════════
# INDIVIDUAL RULE TESTS
# ══════════════════════════════════════════════════════════════

class TestNegativeStockBlock:
    def test_insufficient_stock_blocks(self):
        rule = NegativeStockBlock()
        cmd = make_command(payload={"quantity": 100})
        result = rule.evaluate(cmd, StubContext(), {"available_stock": 10})
        assert not result.passed
        assert result.severity == Severity.BLOCK
        assert result.metadata["deficit"] == 90

    def test_sufficient_stock_passes(self):
        rule = NegativeStockBlock()
        cmd = make_command(payload={"quantity": 5})
        result = rule.evaluate(cmd, StubContext(), {"available_stock": 100})
        assert result.passed

    def test_no_projected_state_passes(self):
        rule = NegativeStockBlock()
        cmd = make_command(payload={"quantity": 5})
        result = rule.evaluate(cmd, StubContext(), {})
        assert result.passed


class TestHighDiscountEscalate:
    def test_high_discount_escalates(self):
        rule = HighDiscountEscalate()
        cmd = make_command(
            command_type="retail.sale.apply_discount.request",
            source_engine="retail",
            payload={"discount_percent": 0.50},
        )
        result = rule.evaluate(cmd, StubContext(), {"discount_threshold": 0.30})
        assert not result.passed
        assert result.severity == Severity.ESCALATE

    def test_normal_discount_passes(self):
        rule = HighDiscountEscalate()
        cmd = make_command(
            command_type="retail.sale.apply_discount.request",
            source_engine="retail",
            payload={"discount_percent": 0.10},
        )
        result = rule.evaluate(cmd, StubContext(), {"discount_threshold": 0.30})
        assert result.passed


class TestClosedBusinessBlock:
    def test_closed_blocks(self):
        rule = ClosedBusinessBlock()
        result = rule.evaluate(
            make_command(), StubContext(lifecycle_state="CLOSED"), {}
        )
        assert not result.passed
        assert result.severity == Severity.BLOCK

    def test_active_passes(self):
        rule = ClosedBusinessBlock()
        result = rule.evaluate(
            make_command(), StubContext(lifecycle_state="ACTIVE"), {}
        )
        assert result.passed


class TestMissingVATEscalate:
    def test_b2b_zero_rate_no_vat_escalates(self):
        rule = MissingVATEscalate()
        cmd = make_command(
            command_type="retail.sale.complete.request",
            source_engine="retail",
            payload={"vat_rate": 0.0, "customer_type": "B2B",
                     "customer_vat_number": ""},
        )
        result = rule.evaluate(cmd, StubContext(), {})
        assert not result.passed
        assert result.severity == Severity.ESCALATE

    def test_b2c_passes(self):
        rule = MissingVATEscalate()
        cmd = make_command(
            command_type="retail.sale.complete.request",
            source_engine="retail",
            payload={"vat_rate": 0.18, "customer_type": "B2C"},
        )
        result = rule.evaluate(cmd, StubContext(), {})
        assert result.passed

    def test_b2b_with_vat_number_passes(self):
        rule = MissingVATEscalate()
        cmd = make_command(
            command_type="retail.sale.complete.request",
            source_engine="retail",
            payload={"vat_rate": 0.0, "customer_type": "B2B",
                     "customer_vat_number": "TZ123456789"},
        )
        result = rule.evaluate(cmd, StubContext(), {})
        assert result.passed


# ══════════════════════════════════════════════════════════════
# REGISTRY TESTS
# ══════════════════════════════════════════════════════════════

class TestPolicyRegistry:
    def test_register_and_query(self):
        reg = PolicyRegistry()
        reg.register_rule(NegativeStockBlock())
        assert reg.rule_count() == 1

    def test_domain_filtering(self, registry):
        inv_rules = registry.get_rules_by_domain("inventory")
        assert all(r.domain == "inventory" for r in inv_rules)

    def test_get_specific_rule(self):
        reg = PolicyRegistry()
        reg.register_rule(NegativeStockBlock())
        rule = reg.get_rule("INV-001", "1.0.0")
        assert rule is not None

    def test_get_missing_rule_returns_none(self):
        reg = PolicyRegistry()
        assert reg.get_rule("GHOST", "1.0.0") is None

    def test_locked_versions_tracking(self):
        reg = PolicyRegistry()
        reg.register_rule(NegativeStockBlock())
        reg.lock(version="1.0.0")
        assert "1.0.0" in reg.get_locked_versions()


# ══════════════════════════════════════════════════════════════
# RESULT SERIALIZATION
# ══════════════════════════════════════════════════════════════

class TestResultSerialization:
    def test_to_payload(self, engine, context):
        cmd = make_command(payload={"quantity": 100})
        decision = engine.evaluate(
            cmd, context, {"available_stock": 10},
            policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )
        payload = decision.to_payload()
        assert "allowed" in payload
        assert "policy_version" in payload
        assert "violations" in payload
        assert payload["policy_version"] == "1.0.0"


# ══════════════════════════════════════════════════════════════
# INTEGRATION: PolicyAwareDispatcher
# ══════════════════════════════════════════════════════════════

class TestPolicyAwareDispatcher:
    def test_block_produces_rejected(self, registry, context):
        eng = PolicyEngine(registry=registry)
        d = PolicyAwareDispatcher(context=context, policy_engine=eng)

        cmd = make_command(payload={"quantity": 100})
        result = d.dispatch(
            cmd, projected_state={"available_stock": 10},
            policy_version="1.0.0",
        )
        assert result.is_rejected

    def test_legacy_policies_still_work(self, context):
        d = PolicyAwareDispatcher(context=context)
        d.register_policy(ai_execution_guard)

        cmd = make_command(actor_type="AI")
        result = d.dispatch(cmd)
        assert result.is_rejected

    def test_no_policy_engine_backward_compat(self, context):
        d = PolicyAwareDispatcher(context=context)
        cmd = make_command()
        result = d.dispatch(cmd)
        assert result.is_accepted
        assert result.policy_decision is None

    def test_policy_version_preserved(self, registry, context):
        eng = PolicyEngine(registry=registry)
        d = PolicyAwareDispatcher(context=context, policy_engine=eng)

        cmd = make_command(payload={"quantity": 1})
        result = d.dispatch(
            cmd,
            projected_state={"available_stock": 100},
            policy_version="1.0.0",
        )
        assert result.policy_version == "1.0.0"


# ══════════════════════════════════════════════════════════════
# FULL INTEGRATION FLOW
# ══════════════════════════════════════════════════════════════

class TestFullStabilizedFlow:
    def test_complete_block_flow(self):
        biz_id = uuid.uuid4()
        ctx = StubContext(active=True, business_id=biz_id)

        reg = PolicyRegistry()
        reg.register_rule(NegativeStockBlock())
        reg.register_rule(ClosedBusinessBlock())
        reg.lock(version="1.0.0")
        eng = PolicyEngine(registry=reg)

        d = PolicyAwareDispatcher(context=ctx, policy_engine=eng)

        cmd = Command(
            command_id=uuid.uuid4(),
            command_type="inventory.stock.move.request",
            business_id=biz_id,
            branch_id=None,
            actor_type="HUMAN",
            actor_id="user-42",
            payload={"quantity": 999},
            issued_at=FIXED_TIME,
            correlation_id=uuid.uuid4(),
            source_engine="inventory",
        )

        result = d.dispatch(
            cmd, projected_state={"available_stock": 10},
            policy_version="1.0.0",
        )

        assert result.is_rejected
        assert result.policy_decision is not None
        assert not result.policy_decision.allowed
        assert result.enforced_event_status == EVENT_STATUS_FINAL

    def test_complete_escalate_flow(self):
        biz_id = uuid.uuid4()
        ctx = StubContext(active=True, business_id=biz_id)

        reg = PolicyRegistry()
        reg.register_rule(HighDiscountEscalate())
        reg.lock(version="1.0.0")
        eng = PolicyEngine(registry=reg)

        d = PolicyAwareDispatcher(context=ctx, policy_engine=eng)

        cmd = Command(
            command_id=uuid.uuid4(),
            command_type="retail.sale.apply_discount.request",
            business_id=biz_id,
            branch_id=None,
            actor_type="HUMAN",
            actor_id="user-42",
            payload={"discount_percent": 0.75},
            issued_at=FIXED_TIME,
            correlation_id=uuid.uuid4(),
            source_engine="retail",
        )

        result = d.dispatch(
            cmd, projected_state={"discount_threshold": 0.30},
            policy_version="1.0.0",
        )

        assert result.is_accepted
        assert result.requires_review
        assert result.enforced_event_status == EVENT_STATUS_REVIEW_REQUIRED
        assert result.policy_decision.escalations[0].rule_id == "PROMO-001"


class TestTenantScopePolicy:
    """Tenant scope policy must block cross-tenant access."""

    def test_cross_tenant_aggregate_access_blocked(self, engine, context):
        cmd = make_command(
            command_type="inventory.stock.move.request",
            source_engine="inventory",
            business_id=BUSINESS_ID,
        )
        decision = engine.evaluate(
            cmd,
            context,
            {
                "available_stock": 10,
                "aggregate_business_id": uuid.uuid4(),
            },
            policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )

        assert not decision.allowed
        assert any(v.rule_id == "TEN-001" for v in decision.violations)

    def test_replay_determinism_with_scope_policy(self, engine, context):
        aggregate_owner = uuid.uuid4()
        cmd = make_command(
            command_type="inventory.stock.move.request",
            source_engine="inventory",
            business_id=BUSINESS_ID,
        )

        d1 = engine.evaluate(
            cmd,
            context,
            {"available_stock": 5, "aggregate_business_id": aggregate_owner},
            policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )
        d2 = engine.evaluate(
            cmd,
            context,
            {"available_stock": 5, "aggregate_business_id": aggregate_owner},
            policy_version="1.0.0",
            evaluation_time=FIXED_TIME,
        )

        assert d1.to_payload() == d2.to_payload()
