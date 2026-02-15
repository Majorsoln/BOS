"""
BOS Compliance - Deterministic Evaluator
========================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.commands.rejection import ReasonCode
from core.compliance.models import ComplianceProfile, PROFILE_ACTIVE
from core.compliance.provider import ComplianceProvider
from core.compliance.registry import resolve_compliance_targets
from core.compliance.rules import (
    RULE_BLOCK,
    RULE_WARN,
    ComplianceRule,
    evaluate_rule_predicate,
    rule_applies,
)


@dataclass(frozen=True)
class ComplianceEvaluationResult:
    allowed: bool
    rejection_code: Optional[str] = None
    details: dict = field(default_factory=dict)


class ComplianceEvaluator:
    @staticmethod
    def _allow(details: dict | None = None) -> ComplianceEvaluationResult:
        return ComplianceEvaluationResult(allowed=True, details=details or {})

    @staticmethod
    def _deny(code: str, details: dict) -> ComplianceEvaluationResult:
        return ComplianceEvaluationResult(
            allowed=False,
            rejection_code=code,
            details=details,
        )

    @staticmethod
    def _canonicalize_profiles(
        profiles: tuple[ComplianceProfile, ...],
    ) -> tuple[ComplianceProfile, ...]:
        """
        Canonicalize non-compliant provider duplicates deterministically.
        For identical (business, branch, version), last sorted wins.
        """

        def precedence(
            profile: ComplianceProfile,
        ) -> tuple[str, str, int, str, int, str]:
            return (
                str(profile.business_id),
                "" if profile.branch_id is None else str(profile.branch_id),
                profile.version,
                profile.profile_id,
                1 if profile.status == PROFILE_ACTIVE else 2,
                (
                    ""
                    if profile.updated_at is None
                    else profile.updated_at.isoformat()
                ),
            )

        ordered = tuple(sorted(profiles, key=precedence))
        canonical: dict[
            tuple[object, object, int],
            ComplianceProfile,
        ] = {}
        for profile in ordered:
            canonical[
                (profile.business_id, profile.branch_id, profile.version)
            ] = profile
        return tuple(canonical.values())

    @staticmethod
    def _select_effective_profile(
        command,
        profiles: tuple[ComplianceProfile, ...],
    ) -> ComplianceProfile | None:
        branch_candidates: list[ComplianceProfile] = []
        business_candidates: list[ComplianceProfile] = []

        for profile in profiles:
            if profile.business_id != command.business_id:
                continue
            if profile.branch_id is None:
                business_candidates.append(profile)
            elif (
                command.branch_id is not None
                and profile.branch_id == command.branch_id
            ):
                branch_candidates.append(profile)

        scope_candidates = (
            branch_candidates
            if command.branch_id is not None and branch_candidates
            else business_candidates
        )
        if not scope_candidates:
            return None

        scope_candidates.sort(
            key=lambda profile: (profile.version, profile.profile_id)
        )
        return scope_candidates[-1]

    @staticmethod
    def _evaluate_rules(
        ruleset: tuple[ComplianceRule, ...],
        command,
    ) -> tuple[list[dict], list[dict]]:
        targets = resolve_compliance_targets(command.command_type)
        ordered_rules = tuple(sorted(ruleset, key=lambda rule: rule.sort_key()))

        warnings: list[dict] = []
        violations: list[dict] = []

        for rule in ordered_rules:
            if not rule_applies(rule=rule, command=command, targets=targets):
                continue

            matched = evaluate_rule_predicate(rule=rule, command=command)
            if not matched:
                continue

            entry = {
                "rule_key": rule.rule_key,
                "severity": rule.severity,
                "message": rule.message,
                "applies_to": rule.applies_to,
            }

            if rule.severity == RULE_WARN:
                warnings.append(entry)
                continue

            if rule.severity == RULE_BLOCK:
                violations.append(entry)

        return warnings, violations

    @staticmethod
    def evaluate(
        command,
        business_context,
        provider: ComplianceProvider | None,
    ) -> ComplianceEvaluationResult:
        if provider is None:
            return ComplianceEvaluator._allow(
                {
                    "profile_applied": False,
                    "warnings": [],
                    "violations": [],
                    "reason": "Compliance provider not configured.",
                }
            )

        profiles = provider.get_profiles_for_business(command.business_id)
        if not profiles:
            return ComplianceEvaluator._allow(
                {
                    "profile_applied": False,
                    "warnings": [],
                    "violations": [],
                }
            )

        canonical_profiles = ComplianceEvaluator._canonicalize_profiles(profiles)
        selected = ComplianceEvaluator._select_effective_profile(
            command=command,
            profiles=canonical_profiles,
        )
        if selected is None:
            return ComplianceEvaluator._allow(
                {
                    "profile_applied": False,
                    "warnings": [],
                    "violations": [],
                }
            )

        if selected.status != PROFILE_ACTIVE:
            return ComplianceEvaluator._allow(
                {
                    "profile_applied": False,
                    "warnings": [],
                    "violations": [],
                    "profile_id": selected.profile_id,
                    "profile_status": selected.status,
                }
            )

        warnings, violations = ComplianceEvaluator._evaluate_rules(
            ruleset=selected.ruleset,
            command=command,
        )

        details = {
            "profile_applied": True,
            "profile_id": selected.profile_id,
            "profile_version": selected.version,
            "profile_branch_id": selected.branch_id,
            "warnings": warnings,
            "violations": violations,
        }

        if violations:
            return ComplianceEvaluator._deny(
                code=ReasonCode.COMPLIANCE_VIOLATION,
                details=details,
            )

        return ComplianceEvaluator._allow(details)

