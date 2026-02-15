"""
BOS HTTP API Auth - Context Resolvers
=====================================
Resolve actor and business contexts from request headers/body.
"""

from __future__ import annotations

import uuid
from typing import Any

from core.commands.base import VALID_ACTOR_TYPES
from core.commands.rejection import ReasonCode, RejectionReason
from core.context.actor_context import ActorContext
from core.context.business_context import BusinessContext
from core.http_api.auth.provider import AuthPrincipal

HEADER_API_KEY = "x-api-key"
HEADER_BUSINESS_ID = "x-business-id"
HEADER_BRANCH_ID = "x-branch-id"

_ACTOR_TYPE_NORMALIZATION = {
    "USER": "HUMAN",
}


def _normalize_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in (headers or {}).items():
        normalized_key = str(key).strip().lower()
        normalized_value = str(value).strip()
        normalized[normalized_key] = normalized_value
    return normalized


def _reject(code: str, message: str) -> RejectionReason:
    return RejectionReason(
        code=code,
        message=message,
        policy_name="http_api_auth_resolver",
    )


def _extract_body_value(body: Any, field_name: str) -> Any:
    if body is None:
        return None
    if isinstance(body, dict):
        return body.get(field_name)
    return getattr(body, field_name, None)


def _parse_uuid(
    value: Any,
    *,
    field_name: str,
    missing_code: str | None = None,
    missing_message: str | None = None,
) -> uuid.UUID | RejectionReason | None:
    if value is None:
        if missing_code is not None and missing_message is not None:
            return _reject(missing_code, missing_message)
        return None
    try:
        return uuid.UUID(str(value).strip())
    except Exception:
        return _reject(
            ReasonCode.INVALID_CONTEXT,
            f"{field_name} must be a valid UUID.",
        )


def _principal_to_actor_context(
    principal: AuthPrincipal,
) -> ActorContext | RejectionReason:
    actor_type = str(principal.actor_type).strip().upper()
    actor_type = _ACTOR_TYPE_NORMALIZATION.get(actor_type, actor_type)
    if actor_type not in VALID_ACTOR_TYPES:
        return _reject(
            ReasonCode.ACTOR_INVALID,
            f"Unsupported actor_type '{principal.actor_type}'.",
        )
    return ActorContext(
        actor_type=actor_type,
        actor_id=principal.actor_id,
    )


def resolve_auth_principal(
    headers: dict[str, Any] | None,
    provider,
) -> AuthPrincipal | RejectionReason:
    normalized_headers = _normalize_headers(headers)
    api_key = normalized_headers.get(HEADER_API_KEY)
    if api_key is None or not api_key:
        return _reject(
            ReasonCode.ACTOR_REQUIRED_MISSING,
            "Missing required header X-API-KEY.",
        )

    principal = provider.resolve_api_key(api_key)
    if principal is None:
        return _reject(
            ReasonCode.ACTOR_INVALID,
            "Invalid API key.",
        )
    return principal


def resolve_actor_context(
    headers: dict[str, Any] | None,
    provider,
) -> ActorContext | RejectionReason:
    principal = resolve_auth_principal(headers, provider)
    if isinstance(principal, RejectionReason):
        return principal
    return _principal_to_actor_context(principal)


def resolve_business_context(
    headers: dict[str, Any] | None,
    body: Any,
) -> BusinessContext | RejectionReason:
    normalized_headers = _normalize_headers(headers)
    header_business_id = _parse_uuid(
        normalized_headers.get(HEADER_BUSINESS_ID),
        field_name="X-BUSINESS-ID",
        missing_code=ReasonCode.INVALID_CONTEXT,
        missing_message="Missing required header X-BUSINESS-ID.",
    )
    if isinstance(header_business_id, RejectionReason):
        return header_business_id

    body_business_raw = _extract_body_value(body, "business_id")
    if body_business_raw is not None:
        body_business_id = _parse_uuid(
            body_business_raw,
            field_name="body.business_id",
        )
        if isinstance(body_business_id, RejectionReason):
            return body_business_id
        if body_business_id != header_business_id:
            return _reject(
                ReasonCode.INVALID_CONTEXT,
                "Header X-BUSINESS-ID does not match body business_id.",
            )

    header_branch_raw = normalized_headers.get(HEADER_BRANCH_ID)
    header_branch_id = _parse_uuid(
        header_branch_raw,
        field_name="X-BRANCH-ID",
    )
    if isinstance(header_branch_id, RejectionReason):
        return header_branch_id

    body_branch_raw = _extract_body_value(body, "branch_id")
    body_branch_id = _parse_uuid(
        body_branch_raw,
        field_name="body.branch_id",
    )
    if isinstance(body_branch_id, RejectionReason):
        return body_branch_id

    if header_branch_id is not None and body_branch_id is not None:
        if header_branch_id != body_branch_id:
            return _reject(
                ReasonCode.INVALID_CONTEXT,
                "Header X-BRANCH-ID does not match body branch_id.",
            )

    branch_id = header_branch_id if header_branch_id is not None else body_branch_id
    return BusinessContext(
        business_id=header_business_id,
        branch_id=branch_id,
    )


def resolve_actor_context_from_principal(
    principal: AuthPrincipal,
) -> ActorContext | RejectionReason:
    return _principal_to_actor_context(principal)

