"""
BOS Policy Engine — System Governance Layer
==============================================
Deterministic, replay-safe, engine-agnostic policy evaluation.

Policy is evaluation, not execution.
Enforcement is structured.
Explanation is mandatory.
Determinism is sacred.
"""

from core.policy.contracts import BaseRule
from core.policy.engine import PolicyEngine
from core.policy.exceptions import (
    DuplicateRuleError,
    PolicyEngineError,
    PolicyVersionNotFound,
    RegistryLockedError,
    RuleEvaluationError,
)
from core.policy.registry import PolicyRegistry
from core.policy.result import PolicyDecision, RuleResult, Severity
from core.policy.versioning import (
    INITIAL_POLICY_VERSION,
    PolicyVersion,
)

__all__ = [
    # ── Contract ──────────────────────────────────────────────
    "BaseRule",
    # ── Engine ────────────────────────────────────────────────
    "PolicyEngine",
    # ── Registry ──────────────────────────────────────────────
    "PolicyRegistry",
    # ── Results ───────────────────────────────────────────────
    "PolicyDecision",
    "RuleResult",
    "Severity",
    # ── Versioning ────────────────────────────────────────────
    "PolicyVersion",
    "INITIAL_POLICY_VERSION",
    # ── Exceptions ────────────────────────────────────────────
    "PolicyEngineError",
    "DuplicateRuleError",
    "RuleEvaluationError",
    "PolicyVersionNotFound",
    "RegistryLockedError",
]
