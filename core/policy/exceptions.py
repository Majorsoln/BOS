"""
BOS Policy Engine — Exceptions
=================================
Structured errors for policy engine operations.

These are engine-internal errors, NOT business rejections.
Business rejections flow through RuleResult → PolicyDecision.
"""

from __future__ import annotations


class PolicyEngineError(Exception):
    """Base error for policy engine operations."""
    pass


class DuplicateRuleError(PolicyEngineError):
    """Rule with same rule_id + version already registered."""

    def __init__(self, rule_id: str, version: str):
        self.rule_id = rule_id
        self.version = version
        super().__init__(
            f"Rule '{rule_id}' version '{version}' is already registered."
        )


class RuleEvaluationError(PolicyEngineError):
    """A rule raised an unexpected error during evaluation."""

    def __init__(self, rule_id: str, version: str, cause: Exception):
        self.rule_id = rule_id
        self.version = version
        self.cause = cause
        super().__init__(
            f"Rule '{rule_id}' v{version} raised unexpected error: "
            f"{type(cause).__name__}: {cause}"
        )


class PolicyVersionNotFound(PolicyEngineError):
    """Requested policy version does not exist."""

    def __init__(self, version: str):
        self.version = version
        super().__init__(
            f"Policy version '{version}' is not registered."
        )


class RegistryLockedError(PolicyEngineError):
    """Policy registry is locked — no modifications allowed."""

    def __init__(self):
        super().__init__(
            "Policy Registry is locked after bootstrap. "
            "No dynamic rule registration allowed."
        )
