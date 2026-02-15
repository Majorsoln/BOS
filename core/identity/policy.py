"""
BOS Identity - Actor Scope Authorization Policy
===============================================
Deterministic actor authorization guard for command execution.
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import ReasonCode, RejectionReason
from core.context.actor_context import ActorContext
from core.identity.requirements import SYSTEM_ALLOWED


def _is_actor_authorized_for_business(
    context,
    actor_context: ActorContext,
    business_id,
) -> bool:
    checker = getattr(context, "is_actor_authorized_for_business", None)
    if checker is None:
        # v1 non-security hook: allow when checker is not implemented.
        return True
    return bool(checker(actor_context, business_id))


def _is_actor_authorized_for_branch(
    context,
    actor_context: ActorContext,
    business_id,
    branch_id,
) -> bool:
    checker = getattr(context, "is_actor_authorized_for_branch", None)
    if checker is None:
        # v1 non-security hook: allow when checker is not implemented.
        return True
    return bool(checker(actor_context, business_id, branch_id))


def evaluate_actor_scope_authorization(
    *,
    actor_context,
    context,
    business_id,
    branch_id,
    policy_name: str,
) -> Optional[RejectionReason]:
    if actor_context is None:
        return RejectionReason(
            code=ReasonCode.ACTOR_REQUIRED_MISSING,
            message="actor_context is required for command execution.",
            policy_name=policy_name,
        )

    if not isinstance(actor_context, ActorContext):
        return RejectionReason(
            code=ReasonCode.ACTOR_INVALID,
            message="actor_context must be ActorContext.",
            policy_name=policy_name,
        )

    try:
        if not _is_actor_authorized_for_business(
            context=context,
            actor_context=actor_context,
            business_id=business_id,
        ):
            return RejectionReason(
                code=ReasonCode.ACTOR_UNAUTHORIZED_BUSINESS,
                message=(
                    f"Actor '{actor_context.actor_id}' is not authorized "
                    f"for business_id '{business_id}'."
                ),
                policy_name=policy_name,
            )

        if branch_id is not None and not _is_actor_authorized_for_branch(
            context=context,
            actor_context=actor_context,
            business_id=business_id,
            branch_id=branch_id,
        ):
            return RejectionReason(
                code=ReasonCode.ACTOR_UNAUTHORIZED_BRANCH,
                message=(
                    f"Actor '{actor_context.actor_id}' is not authorized "
                    f"for branch_id '{branch_id}'."
                ),
                policy_name=policy_name,
            )
    except Exception:
        # Deterministic fail-closed for invalid/unstable authorization hooks.
        return RejectionReason(
            code=ReasonCode.ACTOR_INVALID,
            message="Actor authorization check failed.",
            policy_name=policy_name,
        )

    return None


def actor_scope_authorization_guard(
    command: Command,
    context,
) -> Optional[RejectionReason]:
    """
    Policy guard:
    - For ACTOR_REQUIRED commands, actor must be authorized for business.
    - If branch scope is used (branch_id set), actor must be authorized for branch.
    """
    if command.actor_requirement == SYSTEM_ALLOWED:
        return None

    return evaluate_actor_scope_authorization(
        actor_context=command.actor_context,
        context=context,
        business_id=command.business_id,
        branch_id=command.branch_id,
        policy_name="actor_scope_authorization_guard",
    )
