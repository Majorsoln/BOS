"""
BOS Policy - Permission Authorization Guard
===========================================
Deterministic deny-by-default role/permission/scope authorization.
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import ReasonCode, RejectionReason
from core.identity.requirements import SYSTEM_ALLOWED
from core.permissions.evaluator import PermissionEvaluator


def _resolve_permission_provider(
    context,
    provider,
):
    if provider is not None:
        return provider

    getter = getattr(context, "get_permission_provider", None)
    if getter is None:
        return None

    resolved = getter()
    if callable(resolved):
        return resolved()
    return resolved


def permission_authorization_guard(
    command: Command,
    context,
    provider=None,
) -> Optional[RejectionReason]:
    """
    Policy guard:
    - Applies to ACTOR_REQUIRED commands.
    - SYSTEM_ALLOWED bypasses permission evaluation.
    - Deny by default when mapping/grants/provider do not authorize.
    """
    if command.actor_requirement == SYSTEM_ALLOWED:
        return None

    try:
        result = PermissionEvaluator.evaluate(
            command=command,
            actor_context=command.actor_context,
            business_context=context,
            provider=_resolve_permission_provider(
                context=context,
                provider=provider,
            ),
        )
    except Exception:
        return RejectionReason(
            code=ReasonCode.PERMISSION_DENIED,
            message="Permission authorization check failed.",
            policy_name="permission_authorization_guard",
        )

    if result.allowed:
        return None

    return RejectionReason(
        code=result.rejection_code or ReasonCode.PERMISSION_DENIED,
        message=result.message or "Permission denied.",
        policy_name="permission_authorization_guard",
    )
