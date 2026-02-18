"""
BOS HTTP API - Error Mapping
============================
Stable transport error mapping for command rejections and handler failures.
"""

from __future__ import annotations

from typing import Any, Optional

from core.commands.rejection import RejectionReason
from core.http_api.contracts import HttpApiErrorBody, HttpApiResponse


def error_response(
    *,
    code: str,
    message: str,
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return HttpApiResponse(
        ok=False,
        error=HttpApiErrorBody(
            code=code,
            message=message,
            details=details or {},
        ),
    ).to_dict()


def success_response(
    data: Any,
    *,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return HttpApiResponse(ok=True, data=data, meta=meta).to_dict()


def map_rejection_reason(reason: RejectionReason) -> HttpApiErrorBody:
    message_key = (
        reason.message_key
        if reason.message_key is not None
        else f"rejection.{reason.code.lower()}"
    )
    message_params = (
        {}
        if reason.message_params is None
        else dict(reason.message_params)
    )
    return HttpApiErrorBody(
        code=reason.code,
        message=reason.message,
        details={
            "policy_name": reason.policy_name,
            "message_key": message_key,
            "message_params": message_params,
        },
    )


def rejection_response(
    reason: RejectionReason,
    *,
    extra_details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    mapped = map_rejection_reason(reason)
    details = dict(mapped.details)
    if extra_details:
        details.update(extra_details)
    return error_response(
        code=mapped.code,
        message=mapped.message,
        details=details,
    )
