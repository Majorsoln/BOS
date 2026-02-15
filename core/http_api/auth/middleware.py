"""
BOS HTTP API Auth - Request Context Middleware Utility
======================================================
Framework-agnostic context resolution and authorization.
"""

from __future__ import annotations

import uuid
from typing import Any

from core.commands.rejection import RejectionReason
from core.context.business_context import BusinessContext
from core.http_api.auth.resolver import (
    resolve_actor_context_from_principal,
    resolve_auth_principal,
    resolve_business_context,
)
from core.identity.policy import evaluate_actor_scope_authorization


def resolve_request_context(
    headers: dict[str, Any] | None,
    body: Any,
    auth_provider,
) -> tuple | RejectionReason:
    principal = resolve_auth_principal(headers, auth_provider)
    if isinstance(principal, RejectionReason):
        return principal

    actor_context = resolve_actor_context_from_principal(principal)
    if isinstance(actor_context, RejectionReason):
        return actor_context

    resolved_business_context = resolve_business_context(headers, body)
    if isinstance(resolved_business_context, RejectionReason):
        return resolved_business_context

    allowed_business_ids = set(principal.allowed_business_ids)
    branch_map = dict(principal.allowed_branch_ids_by_business)

    def _business_checker(_, business_id: uuid.UUID) -> bool:
        return str(business_id) in allowed_business_ids

    def _branch_checker(_, business_id: uuid.UUID, branch_id: uuid.UUID) -> bool:
        allowed_branches = branch_map.get(str(business_id), tuple())
        return str(branch_id) in set(allowed_branches)

    business_context = BusinessContext(
        business_id=resolved_business_context.business_id,
        branch_id=resolved_business_context.branch_id,
        _actor_business_authorization_checker=_business_checker,
        _actor_branch_authorization_checker=_branch_checker,
    )

    rejection = evaluate_actor_scope_authorization(
        actor_context=actor_context,
        context=business_context,
        business_id=business_context.business_id,
        branch_id=business_context.branch_id,
        policy_name="http_api_auth_middleware",
    )
    if rejection is not None:
        return rejection

    return (actor_context, business_context)

