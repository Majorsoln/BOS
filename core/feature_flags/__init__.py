"""
BOS Feature Flags - Public API
==============================
"""

from core.feature_flags.evaluator import (
    FeatureFlagEvaluationResult,
    FeatureFlagEvaluator,
)
from core.feature_flags.models import (
    FEATURE_DISABLED,
    FEATURE_ENABLED,
    ROLLOUT_STATIC,
    FeatureFlag,
)
from core.feature_flags.provider import (
    FeatureFlagProvider,
    InMemoryFeatureFlagProvider,
)
from core.feature_flags.registry import (
    FLAG_ENABLE_ADVANCED_POLICY_ESCALATION,
    FLAG_ENABLE_COMPLIANCE_ENGINE,
    FLAG_ENABLE_DOCUMENT_DESIGNER,
    FLAG_ENABLE_DOCUMENT_RENDER_PLAN,
    FLAG_ENABLE_WORKSHOP_ENGINE,
    resolve_flag_for_command,
)

__all__ = [
    "FEATURE_ENABLED",
    "FEATURE_DISABLED",
    "ROLLOUT_STATIC",
    "FeatureFlag",
    "FeatureFlagProvider",
    "InMemoryFeatureFlagProvider",
    "FeatureFlagEvaluator",
    "FeatureFlagEvaluationResult",
    "FLAG_ENABLE_COMPLIANCE_ENGINE",
    "FLAG_ENABLE_ADVANCED_POLICY_ESCALATION",
    "FLAG_ENABLE_DOCUMENT_DESIGNER",
    "FLAG_ENABLE_DOCUMENT_RENDER_PLAN",
    "FLAG_ENABLE_WORKSHOP_ENGINE",
    "resolve_flag_for_command",
]
