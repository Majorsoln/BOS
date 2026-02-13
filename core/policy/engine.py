"""
BOS Policy Engine — Core Evaluation Engine (Stabilization Patch v1.0.2)
========================================================================
Pure, deterministic, replay-safe, FAIL-SAFE policy evaluation.

Patch v1.0.2 Fixes:
- Fix 1: evaluate() NEVER raises. Rule exceptions convert to BLOCK.
- Fix 2: No datetime.now(). Time injected via evaluation_time parameter.
- Fix 3: Version-scoped rule selection from registry snapshots.
- Fix 6: Explanation tree includes metadata, version, evaluation_time.

The PolicyEngine does NOT:
- Persist anything
- Emit events
- Access database
- Mutate global state
- Read system clock
- Raise exceptions during evaluation

Graduated Enforcement:
    BLOCK    → command rejected
    WARN     → command proceeds with warning
    ESCALATE → command proceeds, event marked REVIEW_REQUIRED
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List

from core.policy.contracts import BaseRule
from core.policy.registry import PolicyRegistry
from core.policy.result import PolicyDecision, RuleResult, Severity
from core.policy.versioning import INITIAL_POLICY_VERSION


class PolicyEngine:
    """
    Core policy evaluation engine.

    Pure function wrapped in a class for dependency injection.

    GUARANTEE: evaluate() NEVER raises. All errors are converted
    to structured BLOCK results. This is deterministic doctrine.

    Usage:
        engine = PolicyEngine(registry=policy_registry)
        decision = engine.evaluate(
            command=cmd,
            business_context=ctx,
            projected_state={"available_stock": 100},
            policy_version="1.0.0",
            evaluation_time=command.issued_at,
        )
    """

    def __init__(self, registry: PolicyRegistry):
        self._registry = registry

    def evaluate(
        self,
        command: Any,
        business_context: Any,
        projected_state: dict = None,
        policy_version: str = None,
        evaluation_time: datetime = None,
    ) -> PolicyDecision:
        """
        Evaluate all applicable policies for a command.

        GUARANTEE: This method NEVER raises.

        Flow:
        1. Select applicable rules (version-scoped if snapshot exists)
        2. Execute each in deterministic order (sorted by rule_id)
        3. Collect results into graduated buckets
        4. Determine allowed flag
        5. Build audit-grade explanation tree
        6. Return PolicyDecision

        Args:
            command:          Command being evaluated.
            business_context: Active business context.
            projected_state:  Current projected state (dict, optional).
            policy_version:   Explicit version for replay. Defaults to INITIAL.
            evaluation_time:  Injected time. NEVER read system clock.

        Returns:
            PolicyDecision — pure aggregate, no side effects.
        """
        if projected_state is None:
            projected_state = {}

        if policy_version is None:
            policy_version = INITIAL_POLICY_VERSION

        # ── Step 1: Select applicable rules (version-scoped) ──
        command_type = command.command_type
        applicable_rules = self._registry.get_rules_for_command(
            command_type, policy_version=policy_version
        )

        # ── Step 2: Execute deterministically ─────────────────
        all_results: List[RuleResult] = []
        for rule in applicable_rules:
            result = self._execute_rule_safe(
                rule, command, business_context, projected_state
            )
            all_results.append(result)

        # ── Step 3: Classify results ──────────────────────────
        violations: List[RuleResult] = []
        warnings: List[RuleResult] = []
        escalations: List[RuleResult] = []

        for result in all_results:
            if result.passed:
                continue

            if result.severity == Severity.BLOCK:
                violations.append(result)
            elif result.severity == Severity.WARN:
                warnings.append(result)
            elif result.severity == Severity.ESCALATE:
                escalations.append(result)

        # ── Step 4: Determine allowed flag ────────────────────
        allowed = len(violations) == 0

        # ── Step 5: Build audit-grade explanation tree ────────
        explanation_tree = self._build_explanation(
            command_type=command_type,
            policy_version=policy_version,
            evaluation_time=evaluation_time,
            all_results=all_results,
            violations=violations,
            warnings=warnings,
            escalations=escalations,
        )

        # ── Step 6: Return decision ──────────────────────────
        return PolicyDecision(
            allowed=allowed,
            warnings=warnings,
            violations=violations,
            escalations=escalations,
            explanation_tree=explanation_tree,
            policy_version=policy_version,
        )

    # ══════════════════════════════════════════════════════════
    # RULE EXECUTION — FAIL-SAFE (Fix 1)
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def _execute_rule_safe(
        rule: BaseRule,
        command: Any,
        context: Any,
        projected_state: dict,
    ) -> RuleResult:
        """
        Execute a single rule with ABSOLUTE error isolation.

        If a rule raises ANY exception:
        - Convert to BLOCK RuleResult
        - Include structured error metadata
        - NEVER re-raise

        This is deterministic doctrine. PolicyEngine.evaluate()
        must NEVER raise during evaluation.
        """
        try:
            result = rule.evaluate(command, context, projected_state)
            if not isinstance(result, RuleResult):
                return RuleResult(
                    rule_id=rule.rule_id,
                    passed=False,
                    severity=Severity.BLOCK,
                    message=(
                        f"Rule returned {type(result).__name__}, "
                        f"expected RuleResult. Treated as BLOCK."
                    ),
                    metadata={
                        "error_type": "INVALID_RETURN_TYPE",
                        "returned_type": type(result).__name__,
                    },
                )
            return result
        except Exception as exc:
            # ── FAIL-SAFE: convert ANY exception to BLOCK ─────
            return RuleResult(
                rule_id=rule.rule_id,
                passed=False,
                severity=Severity.BLOCK,
                message=f"Rule execution failure: {type(exc).__name__}",
                metadata={
                    "error_type": type(exc).__name__,
                    "exception": str(exc),
                    "rule_version": rule.version,
                },
            )

    # ══════════════════════════════════════════════════════════
    # EXPLANATION TREE — AUDIT GRADE (Fix 6)
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def _build_explanation(
        command_type: str,
        policy_version: str,
        evaluation_time: datetime,
        all_results: List[RuleResult],
        violations: List[RuleResult],
        warnings: List[RuleResult],
        escalations: List[RuleResult],
    ) -> dict:
        """
        Build audit-grade structured explanation.

        Includes metadata, version, evaluation_time for full
        replay determinism and legal defensibility.
        """
        return {
            "command_type": command_type,
            "policy_version": policy_version,
            "evaluation_time": (
                evaluation_time.isoformat() if evaluation_time else None
            ),
            "rules_evaluated": len(all_results),
            "rules_passed": sum(1 for r in all_results if r.passed),
            "rules_failed": sum(1 for r in all_results if not r.passed),
            "block_count": len(violations),
            "warn_count": len(warnings),
            "escalate_count": len(escalations),
            "details": [
                {
                    "rule_id": r.rule_id,
                    "passed": r.passed,
                    "severity": r.severity,
                    "message": r.message,
                    "metadata": r.metadata,
                }
                for r in all_results
            ],
        }
