"""
BOS Policy - Feature Flag Authorization Guard
=============================================
Feature flags are governance controls evaluated on command dispatch.
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import ReasonCode, RejectionReason
from core.feature_flags.evaluator import FeatureFlagEvaluator


def _resolve_feature_flag_provider(context, provider):
    if provider is not None:
        return provider

    getter = getattr(context, "get_feature_flag_provider", None)
    if getter is None:
        return None

    resolved = getter()
    if callable(resolved):
        return resolved()
    return resolved


def feature_flag_authorization_guard(
    command: Command,
    context,
    provider=None,
) -> Optional[RejectionReason]:
    try:
        result = FeatureFlagEvaluator.evaluate(
            command=command,
            business_context=context,
            provider=_resolve_feature_flag_provider(
                context=context,
                provider=provider,
            ),
        )
    except Exception:
        # Governance layer fail-open per BOS tweak.
        return None

    if result.allowed:
        return None

    return RejectionReason(
        code=result.rejection_code or ReasonCode.FEATURE_DISABLED,
        message=result.message or "Feature is disabled.",
        policy_name="feature_flag_authorization_guard",
    )

