"""
BOS Policy Engine — Result Models
====================================
RuleResult: single rule evaluation outcome.
PolicyDecision: aggregate of all rule results with graduated enforcement.

Graduated Enforcement:
    BLOCK     → command rejected, full stop
    WARN      → command proceeds, warning attached
    ESCALATE  → command proceeds, event marked REVIEW_REQUIRED

These are pure data structures. No side effects. No persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List


# ══════════════════════════════════════════════════════════════
# SEVERITY LEVELS
# ══════════════════════════════════════════════════════════════

class Severity:
    """Graduated enforcement levels."""
    BLOCK = "BLOCK"
    WARN = "WARN"
    ESCALATE = "ESCALATE"

    ALL = frozenset({"BLOCK", "WARN", "ESCALATE"})


# ══════════════════════════════════════════════════════════════
# RULE RESULT (single rule evaluation outcome)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RuleResult:
    """
    Outcome of a single rule evaluation.

    Fields:
        rule_id:    Unique rule identifier.
        passed:     True if rule passed (no violation).
        severity:   BLOCK | WARN | ESCALATE (meaningful only if not passed).
        message:    Human-readable explanation.
        metadata:   Structured data for audit/explainability.

    If passed=True, severity is informational (the rule's declared level).
    If passed=False, severity determines enforcement action.
    """

    rule_id: str
    passed: bool
    severity: str
    message: str
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.rule_id or not isinstance(self.rule_id, str):
            raise ValueError("rule_id must be a non-empty string.")

        if not isinstance(self.passed, bool):
            raise ValueError("passed must be a bool.")

        if self.severity not in Severity.ALL:
            raise ValueError(
                f"severity '{self.severity}' not valid. "
                f"Must be one of: {sorted(Severity.ALL)}"
            )

        if not self.message or not isinstance(self.message, str):
            raise ValueError("message must be a non-empty string.")


# ══════════════════════════════════════════════════════════════
# POLICY DECISION (aggregate of all rule results)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PolicyDecision:
    """
    Aggregate decision from policy evaluation.

    Fields:
        allowed:           True if command may proceed (no BLOCKs).
        warnings:          List of WARN RuleResults (passed=False).
        violations:        List of BLOCK RuleResults (passed=False).
        escalations:       List of ESCALATE RuleResults (passed=False).
        explanation_tree:  Structured explanation for audit.
        policy_version:    Version identifier for replay determinism.

    Enforcement rules:
        - Any BLOCK → allowed=False
        - Only WARNs → allowed=True, warnings attached
        - Any ESCALATE → allowed=True, but event status=REVIEW_REQUIRED
        - All pass → allowed=True, clean
    """

    allowed: bool
    warnings: List[RuleResult] = field(default_factory=list)
    violations: List[RuleResult] = field(default_factory=list)
    escalations: List[RuleResult] = field(default_factory=list)
    explanation_tree: dict = field(default_factory=dict)
    policy_version: str = ""

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0

    @property
    def has_escalations(self) -> bool:
        return len(self.escalations) > 0

    @property
    def requires_review(self) -> bool:
        """True if any ESCALATE rule failed → event needs REVIEW_REQUIRED."""
        return self.has_escalations

    def to_payload(self) -> dict:
        """
        Serialize for event payload embedding.
        This goes into the event so replay can use the same version.
        """
        return {
            "allowed": self.allowed,
            "policy_version": self.policy_version,
            "warnings": [
                {"rule_id": w.rule_id, "message": w.message,
                 "metadata": w.metadata}
                for w in self.warnings
            ],
            "violations": [
                {"rule_id": v.rule_id, "message": v.message,
                 "metadata": v.metadata}
                for v in self.violations
            ],
            "escalations": [
                {"rule_id": e.rule_id, "message": e.message,
                 "metadata": e.metadata}
                for e in self.escalations
            ],
            "explanation_tree": self.explanation_tree,
        }
