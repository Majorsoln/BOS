"""
BOS Policy Engine — Rule Contract (Stabilization Patch v1.0.2)
=================================================================
Abstract base class for all policy rules.

Every rule must:
- Be pure (no side effects)
- Be deterministic (same input → same output)
- Not access database
- Not emit events
- Not persist anything
- Not mutate global state
- Declare its severity (BLOCK / WARN / ESCALATE)
- Declare which command types it applies to

Contract validation enforced at class creation time:
- rule_id: non-empty string
- version: semantic version (X.Y.Z)
- domain: non-empty string
- severity: BLOCK | WARN | ESCALATE
- applies_to: non-empty list of command_type patterns

Patch v1.0.2: Added semver enforcement.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, List

from core.policy.result import RuleResult, Severity


# ══════════════════════════════════════════════════════════════
# SEMVER PATTERN
# ══════════════════════════════════════════════════════════════

SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class BaseRule(ABC):
    """
    Abstract base for BOS policy rules.

    Subclasses must:
    - Set rule_id (unique identifier, e.g. 'INV-001')
    - Set version (semver string, e.g. '1.0.0')
    - Set domain (e.g. 'inventory', 'compliance', 'lifecycle')
    - Set severity (BLOCK | WARN | ESCALATE)
    - Set applies_to (list of command_type patterns)
    - Implement evaluate()

    Contract is validated at class creation time (__init_subclass__).
    Invalid rules cannot exist. This is governance law.
    """

    rule_id: str = ""
    version: str = ""
    domain: str = ""
    severity: str = ""
    applies_to: List[str] = []

    def __init_subclass__(cls, **kwargs):
        """
        Validate subclass declarations at class creation time.
        Invalid rules are rejected immediately — they never reach runtime.
        """
        super().__init_subclass__(**kwargs)

        # Skip validation for intermediate abstract classes
        if getattr(cls, "__abstractmethods__", None):
            return

        # ── rule_id: non-empty string ─────────────────────────
        if not cls.rule_id or not isinstance(cls.rule_id, str):
            raise TypeError(
                f"Rule class {cls.__name__} must declare "
                f"rule_id as non-empty string."
            )

        # ── version: semantic version X.Y.Z ───────────────────
        if not cls.version or not isinstance(cls.version, str):
            raise TypeError(
                f"Rule class {cls.__name__} must declare "
                f"version as non-empty string."
            )

        if not SEMVER_PATTERN.match(cls.version):
            raise TypeError(
                f"Rule class {cls.__name__} version '{cls.version}' "
                f"must be semantic version format X.Y.Z "
                f"(e.g. '1.0.0', '2.1.3')."
            )

        # ── domain: non-empty string ──────────────────────────
        if not cls.domain or not isinstance(cls.domain, str):
            raise TypeError(
                f"Rule class {cls.__name__} must declare "
                f"domain as non-empty string."
            )

        # ── severity: valid enum ──────────────────────────────
        if cls.severity not in Severity.ALL:
            raise TypeError(
                f"Rule class {cls.__name__} severity "
                f"'{cls.severity}' must be one of: {sorted(Severity.ALL)}"
            )

        # ── applies_to: non-empty list ────────────────────────
        if not cls.applies_to or not isinstance(cls.applies_to, list):
            raise TypeError(
                f"Rule class {cls.__name__} must declare applies_to "
                f"as non-empty list of command_type patterns."
            )

    @abstractmethod
    def evaluate(
        self,
        command: Any,
        context: Any,
        projected_state: dict,
    ) -> RuleResult:
        """
        Evaluate this rule against command + context + projected state.

        MUST be pure. No DB. No persistence. No events. No mutation.

        Args:
            command:          The Command being evaluated.
            context:          Business context (CommandContextProtocol).
            projected_state:  Current projected state relevant to this rule.

        Returns:
            RuleResult — passed=True (ok) or passed=False (violation).
        """
        ...

    # ══════════════════════════════════════════════════════════
    # CONVENIENCE BUILDERS (for subclasses)
    # ══════════════════════════════════════════════════════════

    def pass_rule(self, message: str = "Rule passed.") -> RuleResult:
        """Build a passing RuleResult."""
        return RuleResult(
            rule_id=self.rule_id,
            passed=True,
            severity=self.severity,
            message=message,
        )

    def fail(
        self,
        message: str,
        metadata: dict = None,
    ) -> RuleResult:
        """Build a failing RuleResult with this rule's severity."""
        return RuleResult(
            rule_id=self.rule_id,
            passed=False,
            severity=self.severity,
            message=message,
            metadata=metadata or {},
        )

    def applies_to_command(self, command_type: str) -> bool:
        """Check if this rule applies to the given command_type."""
        return command_type in self.applies_to
