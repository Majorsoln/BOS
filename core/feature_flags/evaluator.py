"""
BOS Feature Flags - Deterministic Evaluator
===========================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.commands.base import Command
from core.commands.rejection import ReasonCode
from core.feature_flags.models import (
    FEATURE_DISABLED,
    FEATURE_ENABLED,
    FeatureFlag,
)
from core.feature_flags.provider import FeatureFlagProvider
from core.feature_flags.registry import resolve_flag_for_command
from core.identity.requirements import SYSTEM_ALLOWED


@dataclass(frozen=True)
class FeatureFlagEvaluationResult:
    allowed: bool
    rejection_code: Optional[str] = None
    message: str = ""


class FeatureFlagEvaluator:
    @staticmethod
    def _allow() -> FeatureFlagEvaluationResult:
        return FeatureFlagEvaluationResult(allowed=True)

    @staticmethod
    def _deny(code: str, message: str) -> FeatureFlagEvaluationResult:
        return FeatureFlagEvaluationResult(
            allowed=False,
            rejection_code=code,
            message=message,
        )

    @staticmethod
    def _canonicalize(
        flags: tuple[FeatureFlag, ...],
    ) -> dict[tuple[str, object], FeatureFlag]:
        """
        Canonicalize external provider results deterministically.
        Last item in stable sorted order wins for a duplicate scope key.
        Status precedence is deterministic: DISABLED overrides ENABLED.
        """
        def precedence(flag: FeatureFlag) -> tuple[str, str, str, int, str]:
            return (
                flag.flag_key,
                str(flag.business_id),
                "" if flag.branch_id is None else str(flag.branch_id),
                1 if flag.status == FEATURE_ENABLED else 2,
                (
                    ""
                    if flag.created_at is None
                    else flag.created_at.isoformat()
                ),
            )

        ordered = tuple(sorted(flags, key=precedence))
        canonical: dict[tuple[str, object], FeatureFlag] = {}
        for flag in ordered:
            canonical[(flag.flag_key, flag.branch_id)] = flag
        return canonical

    @staticmethod
    def evaluate(
        command: Command,
        business_context,
        provider: FeatureFlagProvider | None,
    ) -> FeatureFlagEvaluationResult:
        if command.actor_requirement == SYSTEM_ALLOWED:
            return FeatureFlagEvaluator._allow()

        flag_key = resolve_flag_for_command(command.command_type)
        if flag_key is None:
            return FeatureFlagEvaluator._allow()

        return FeatureFlagEvaluator.evaluate_for_flag_key(
            flag_key=flag_key,
            command=command,
            provider=provider,
        )

    @staticmethod
    def evaluate_for_flag_key(
        flag_key: str,
        command: Command,
        provider: FeatureFlagProvider | None,
    ) -> FeatureFlagEvaluationResult:
        if provider is None:
            return FeatureFlagEvaluator._allow()

        flags = provider.get_flags_for_business(command.business_id)
        if not flags:
            return FeatureFlagEvaluator._allow()

        canonical = FeatureFlagEvaluator._canonicalize(flags)

        effective_flag = None
        if command.branch_id is not None:
            effective_flag = canonical.get((flag_key, command.branch_id))
            if effective_flag is None:
                effective_flag = canonical.get((flag_key, None))
        else:
            effective_flag = canonical.get((flag_key, None))

        if effective_flag is None:
            return FeatureFlagEvaluator._allow()

        if effective_flag.status == FEATURE_DISABLED:
            return FeatureFlagEvaluator._deny(
                code=ReasonCode.FEATURE_DISABLED,
                message=(
                    f"Feature flag '{flag_key}' is disabled for "
                    f"business_id '{command.business_id}' and "
                    f"branch_id '{command.branch_id}'."
                ),
            )

        return FeatureFlagEvaluator._allow()
