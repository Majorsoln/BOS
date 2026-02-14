"""
BOS Permissions - Deterministic Permission Evaluator
====================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.commands.base import Command
from core.commands.rejection import ReasonCode
from core.context.scope import SCOPE_BRANCH_REQUIRED
from core.identity.requirements import SYSTEM_ALLOWED
from core.permissions.constants import (
    GRANT_STATUS_ACTIVE,
    SCOPE_GRANT_BRANCH,
    SCOPE_GRANT_BUSINESS,
)
from core.permissions.provider import PermissionProvider
from core.permissions.registry import resolve_required_permission


@dataclass(frozen=True)
class PermissionEvaluationResult:
    allowed: bool
    rejection_code: Optional[str] = None
    message: str = ""


class PermissionEvaluator:
    @staticmethod
    def _allow() -> PermissionEvaluationResult:
        return PermissionEvaluationResult(allowed=True)

    @staticmethod
    def _deny(code: str, message: str) -> PermissionEvaluationResult:
        return PermissionEvaluationResult(
            allowed=False,
            rejection_code=code,
            message=message,
        )

    @staticmethod
    def evaluate(
        command: Command,
        actor_context,
        business_context,
        provider: PermissionProvider | None,
    ) -> PermissionEvaluationResult:
        """
        Evaluate command authorization against role/permission/scope grants.
        """
        if command.actor_requirement == SYSTEM_ALLOWED:
            return PermissionEvaluator._allow()

        if actor_context is None:
            return PermissionEvaluator._deny(
                ReasonCode.PERMISSION_DENIED,
                "Permission evaluation requires actor_context.",
            )

        required_permission = resolve_required_permission(command.command_type)
        if required_permission is None:
            return PermissionEvaluator._deny(
                ReasonCode.PERMISSION_MAPPING_MISSING,
                (
                    "No permission mapping for command_type "
                    f"'{command.command_type}'."
                ),
            )

        if provider is None:
            return PermissionEvaluator._deny(
                ReasonCode.PERMISSION_DENIED,
                "Permission provider is not configured.",
            )

        grants = provider.get_grants_for_actor(
            actor_id=actor_context.actor_id,
            business_id=command.business_id,
        )
        if not grants:
            return PermissionEvaluator._deny(
                ReasonCode.PERMISSION_DENIED,
                (
                    f"Actor '{actor_context.actor_id}' has no active "
                    f"grants for business_id '{command.business_id}'."
                ),
            )

        ordered_grants = tuple(sorted(grants, key=lambda grant: grant.sort_key()))

        has_business_permission = False
        has_matching_branch_permission = False
        has_branch_permission_other_branch = False

        for grant in ordered_grants:
            if grant.status != GRANT_STATUS_ACTIVE:
                continue

            if grant.business_id != command.business_id:
                continue

            role = provider.get_role(grant.role_id)
            if role is None:
                continue

            if required_permission not in role.permissions:
                continue

            if grant.scope_type == SCOPE_GRANT_BUSINESS:
                has_business_permission = True
                continue

            if grant.scope_type == SCOPE_GRANT_BRANCH:
                if command.branch_id is not None and grant.branch_id == command.branch_id:
                    has_matching_branch_permission = True
                else:
                    has_branch_permission_other_branch = True

        if command.scope_requirement == SCOPE_BRANCH_REQUIRED:
            if command.branch_id is None:
                return PermissionEvaluator._deny(
                    ReasonCode.PERMISSION_SCOPE_REQUIRED_BRANCH,
                    "Branch scope permission is required for this command.",
                )

            if has_matching_branch_permission:
                return PermissionEvaluator._allow()

            if has_business_permission or has_branch_permission_other_branch:
                return PermissionEvaluator._deny(
                    ReasonCode.PERMISSION_SCOPE_REQUIRED_BRANCH,
                    (
                        f"Actor '{actor_context.actor_id}' requires a "
                        f"branch-scoped grant for branch_id '{command.branch_id}'."
                    ),
                )

            return PermissionEvaluator._deny(
                ReasonCode.PERMISSION_DENIED,
                (
                    f"Actor '{actor_context.actor_id}' is missing permission "
                    f"'{required_permission}' for branch scope."
                ),
            )

        if command.branch_id is None:
            if has_business_permission:
                return PermissionEvaluator._allow()

            return PermissionEvaluator._deny(
                ReasonCode.PERMISSION_DENIED,
                (
                    f"Actor '{actor_context.actor_id}' is missing business "
                    f"permission '{required_permission}'."
                ),
            )

        if has_business_permission or has_matching_branch_permission:
            return PermissionEvaluator._allow()

        return PermissionEvaluator._deny(
            ReasonCode.PERMISSION_DENIED,
            (
                f"Actor '{actor_context.actor_id}' is missing permission "
                f"'{required_permission}' for branch_id '{command.branch_id}'."
            ),
        )
