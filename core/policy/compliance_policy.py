"""
BOS Policy - Compliance Authorization Guard
===========================================
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import ReasonCode, RejectionReason
from core.compliance.evaluator import ComplianceEvaluator
from core.feature_flags.evaluator import FeatureFlagEvaluator
from core.feature_flags.registry import FLAG_ENABLE_COMPLIANCE_ENGINE
from core.identity.requirements import SYSTEM_ALLOWED


def _resolve_compliance_provider(context, compliance_provider):
    if compliance_provider is not None:
        return compliance_provider

    getter = getattr(context, "get_compliance_provider", None)
    if getter is None:
        return None

    resolved = getter()
    if callable(resolved):
        return resolved()
    return resolved


def _resolve_feature_flag_provider(context, feature_flag_provider):
    if feature_flag_provider is not None:
        return feature_flag_provider

    getter = getattr(context, "get_feature_flag_provider", None)
    if getter is None:
        return None

    resolved = getter()
    if callable(resolved):
        return resolved()
    return resolved


def compliance_authorization_guard(
    command: Command,
    context,
    compliance_provider=None,
    feature_flag_provider=None,
) -> Optional[RejectionReason]:
    if command.actor_requirement == SYSTEM_ALLOWED:
        return None

    resolved_feature_provider = _resolve_feature_flag_provider(
        context=context,
        feature_flag_provider=feature_flag_provider,
    )
    try:
        compliance_flag_result = FeatureFlagEvaluator.evaluate_for_flag_key(
            flag_key=FLAG_ENABLE_COMPLIANCE_ENGINE,
            command=command,
            provider=resolved_feature_provider,
        )
    except Exception:
        # Governance skip when feature flag evaluation fails.
        return None

    if not compliance_flag_result.allowed:
        return None

    resolved_compliance_provider = _resolve_compliance_provider(
        context=context,
        compliance_provider=compliance_provider,
    )
    if resolved_compliance_provider is None:
        return None

    try:
        result = ComplianceEvaluator.evaluate(
            command=command,
            business_context=context,
            provider=resolved_compliance_provider,
        )
    except Exception:
        return RejectionReason(
            code=ReasonCode.COMPLIANCE_VIOLATION,
            message="Compliance evaluation failed.",
            policy_name="compliance_authorization_guard",
        )

    if result.allowed:
        return None

    violations = result.details.get("violations", [])
    message = "Compliance violation."
    if violations:
        first = violations[0]
        message = first.get("message") or message

    return RejectionReason(
        code=result.rejection_code or ReasonCode.COMPLIANCE_VIOLATION,
        message=message,
        policy_name="compliance_authorization_guard",
    )

