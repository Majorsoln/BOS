"""
BOS HTTP API - Framework-Agnostic Handlers
==========================================
Pure handler functions over contracts and injected dependencies.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from core.admin.commands import AdminCommandContext
from core.commands.rejection import ReasonCode, RejectionReason
from core.context.actor_context import ActorContext
from core.context.business_context import BusinessContext
from core.http_api.auth.middleware import resolve_request_context
from core.http_api.contracts import (
    ActorMetadata,
    BusinessReadRequest,
    ComplianceProfileDeactivateHttpRequest,
    ComplianceProfileUpsertHttpRequest,
    DocumentTemplateDeactivateHttpRequest,
    DocumentTemplateUpsertHttpRequest,
    FeatureFlagClearHttpRequest,
    FeatureFlagSetHttpRequest,
)
from core.http_api.errors import error_response, rejection_response, success_response


def _iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _actor_context(actor: ActorMetadata) -> ActorContext:
    return ActorContext(
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        actor_roles=tuple(actor.actor_roles),
        actor_scopes=tuple(actor.actor_scopes),
    )


def _build_admin_command_context(
    *,
    business_context: BusinessContext,
    actor_context: ActorContext,
    dependencies,
) -> AdminCommandContext:
    return AdminCommandContext(
        business_id=business_context.business_id,
        actor_type=actor_context.actor_type,
        actor_id=actor_context.actor_id,
        actor_context=actor_context,
        command_id=dependencies.id_provider.new_command_id(),
        correlation_id=dependencies.id_provider.new_correlation_id(),
        issued_at=dependencies.clock.now_issued_at(),
    )


def _resolve_handler_context(
    *,
    request,
    dependencies,
    headers: dict[str, Any] | None,
    require_actor: bool,
) -> tuple[ActorContext | None, BusinessContext] | RejectionReason:
    auth_provider = getattr(dependencies, "auth_provider", None)
    if auth_provider is not None:
        resolved = resolve_request_context(
            headers=headers,
            body=request,
            auth_provider=auth_provider,
        )
        if isinstance(resolved, RejectionReason):
            return resolved
        return resolved

    branch_id = getattr(request, "branch_id", None)
    business_context = BusinessContext(
        business_id=request.business_id,
        branch_id=branch_id,
    )
    if not require_actor:
        return (None, business_context)

    actor_metadata = getattr(request, "actor", None)
    if actor_metadata is None:
        return RejectionReason(
            code=ReasonCode.ACTOR_REQUIRED_MISSING,
            message="actor is required when auth_provider is not configured.",
            policy_name="http_api_handler_context",
        )

    actor_context = _actor_context(actor_metadata)
    return (actor_context, business_context)


def _serialize_feature_flag(flag) -> dict[str, Any]:
    return {
        "flag_key": flag.flag_key,
        "business_id": str(flag.business_id),
        "branch_id": None if flag.branch_id is None else str(flag.branch_id),
        "status": flag.status,
        "rollout_type": flag.rollout_type,
        "created_at": _iso_or_none(flag.created_at),
    }


def _serialize_rule(rule) -> dict[str, Any]:
    return {
        "rule_key": rule.rule_key,
        "applies_to": rule.applies_to,
        "severity": rule.severity,
        "predicate": dict(rule.predicate),
        "message": rule.message,
    }


def _serialize_compliance_profile(profile) -> dict[str, Any]:
    ordered_rules = tuple(sorted(profile.ruleset, key=lambda item: item.sort_key()))
    return {
        "profile_id": profile.profile_id,
        "business_id": str(profile.business_id),
        "branch_id": None if profile.branch_id is None else str(profile.branch_id),
        "status": profile.status,
        "version": profile.version,
        "ruleset": tuple(_serialize_rule(rule) for rule in ordered_rules),
        "updated_by_actor_id": profile.updated_by_actor_id,
        "updated_at": _iso_or_none(profile.updated_at),
    }


def _serialize_document_template(template) -> dict[str, Any]:
    return {
        "template_id": template.template_id,
        "business_id": str(template.business_id),
        "branch_id": None if template.branch_id is None else str(template.branch_id),
        "doc_type": template.doc_type,
        "version": template.version,
        "status": template.status,
        "schema_version": template.schema_version,
        "layout_spec": dict(template.layout_spec),
        "created_by_actor_id": template.created_by_actor_id,
        "created_at": _iso_or_none(template.created_at),
    }


def list_feature_flags(
    request: BusinessReadRequest,
    dependencies,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_context = _resolve_handler_context(
        request=request,
        dependencies=dependencies,
        headers=headers,
        require_actor=False,
    )
    if isinstance(resolved_context, RejectionReason):
        return rejection_response(resolved_context)
    _, business_context = resolved_context

    try:
        flags = dependencies.admin_repository.get_feature_flags(
            business_context.business_id
        )
    except Exception as exc:
        return error_response(
            code="READ_MODEL_ERROR",
            message="Failed to read feature flags.",
            details={"error_type": type(exc).__name__},
        )

    ordered = tuple(sorted(flags, key=lambda item: item.sort_key()))
    return success_response(
        {
            "items": tuple(_serialize_feature_flag(flag) for flag in ordered),
            "count": len(ordered),
        }
    )


def list_compliance_profiles(
    request: BusinessReadRequest,
    dependencies,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_context = _resolve_handler_context(
        request=request,
        dependencies=dependencies,
        headers=headers,
        require_actor=False,
    )
    if isinstance(resolved_context, RejectionReason):
        return rejection_response(resolved_context)
    _, business_context = resolved_context

    try:
        profiles = dependencies.admin_repository.get_compliance_profiles(
            business_context.business_id
        )
    except Exception as exc:
        return error_response(
            code="READ_MODEL_ERROR",
            message="Failed to read compliance profiles.",
            details={"error_type": type(exc).__name__},
        )

    ordered = tuple(sorted(profiles, key=lambda item: item.sort_key()))
    return success_response(
        {
            "items": tuple(
                _serialize_compliance_profile(profile) for profile in ordered
            ),
            "count": len(ordered),
        }
    )


def list_document_templates(
    request: BusinessReadRequest,
    dependencies,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_context = _resolve_handler_context(
        request=request,
        dependencies=dependencies,
        headers=headers,
        require_actor=False,
    )
    if isinstance(resolved_context, RejectionReason):
        return rejection_response(resolved_context)
    _, business_context = resolved_context

    try:
        templates = dependencies.admin_repository.get_document_templates(
            business_context.business_id
        )
    except Exception as exc:
        return error_response(
            code="READ_MODEL_ERROR",
            message="Failed to read document templates.",
            details={"error_type": type(exc).__name__},
        )

    ordered = tuple(sorted(templates, key=lambda item: item.sort_key()))
    return success_response(
        {
            "items": tuple(
                _serialize_document_template(template) for template in ordered
            ),
            "count": len(ordered),
        }
    )


def _write_result_response(command_result) -> dict[str, Any]:
    status = command_result.outcome.status.value
    command_id = str(command_result.outcome.command_id)
    rejection = command_result.outcome.reason

    if command_result.is_rejected:
        if rejection is None:
            return error_response(
                code="UNKNOWN_REJECTION",
                message="Command rejected without rejection details.",
                details={"status": status, "command_id": command_id},
            )
        return rejection_response(
            rejection,
            extra_details={"status": status, "command_id": command_id},
        )

    execution = command_result.execution_result
    event_type = None
    correlation_id = None
    created_identifiers = {}
    projection_applied = None
    if execution is not None:
        event_type = getattr(execution, "event_type", None)
        projection_applied = getattr(execution, "projection_applied", None)
        event_data = getattr(execution, "event_data", None)
        if isinstance(event_data, dict):
            raw_correlation_id = event_data.get("correlation_id")
            if raw_correlation_id is not None:
                correlation_id = str(raw_correlation_id)
            payload = event_data.get("payload", {})
            if isinstance(payload, dict):
                for identifier_key in ("profile_id", "template_id"):
                    identifier_value = payload.get(identifier_key)
                    if identifier_value is not None:
                        created_identifiers[identifier_key] = identifier_value

    return success_response(
        {
            "status": status,
            "command_id": command_id,
            "rejection": None,
            "event_type": event_type,
            "correlation_id": correlation_id,
            "created_identifiers": created_identifiers,
            "projection_applied": projection_applied,
        }
    )


def _run_write(write_call) -> dict[str, Any]:
    try:
        command_result = write_call()
    except ValueError as exc:
        return error_response(
            code="INVALID_REQUEST",
            message=str(exc),
            details={},
        )
    except Exception as exc:
        return error_response(
            code="HANDLER_EXECUTION_FAILED",
            message="Failed to execute admin command.",
            details={"error_type": type(exc).__name__},
        )
    return _write_result_response(command_result)


def post_feature_flag_set(
    request: FeatureFlagSetHttpRequest,
    dependencies,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_context = _resolve_handler_context(
        request=request,
        dependencies=dependencies,
        headers=headers,
        require_actor=True,
    )
    if isinstance(resolved_context, RejectionReason):
        return rejection_response(resolved_context)
    actor_context, business_context = resolved_context

    def _call():
        command_context = _build_admin_command_context(
            business_context=business_context,
            actor_context=actor_context,
            dependencies=dependencies,
        )
        return dependencies.admin_service.set_feature_flag(
            context=command_context,
            flag_key=request.flag_key,
            status=request.status,
            branch_id=request.branch_id,
        )

    return _run_write(_call)


def post_feature_flag_clear(
    request: FeatureFlagClearHttpRequest,
    dependencies,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_context = _resolve_handler_context(
        request=request,
        dependencies=dependencies,
        headers=headers,
        require_actor=True,
    )
    if isinstance(resolved_context, RejectionReason):
        return rejection_response(resolved_context)
    actor_context, business_context = resolved_context

    def _call():
        command_context = _build_admin_command_context(
            business_context=business_context,
            actor_context=actor_context,
            dependencies=dependencies,
        )
        return dependencies.admin_service.clear_feature_flag(
            context=command_context,
            flag_key=request.flag_key,
            branch_id=request.branch_id,
        )

    return _run_write(_call)


def post_compliance_profile_upsert(
    request: ComplianceProfileUpsertHttpRequest,
    dependencies,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_context = _resolve_handler_context(
        request=request,
        dependencies=dependencies,
        headers=headers,
        require_actor=True,
    )
    if isinstance(resolved_context, RejectionReason):
        return rejection_response(resolved_context)
    actor_context, business_context = resolved_context

    def _call():
        command_context = _build_admin_command_context(
            business_context=business_context,
            actor_context=actor_context,
            dependencies=dependencies,
        )
        return dependencies.admin_service.upsert_compliance_profile(
            context=command_context,
            branch_id=request.branch_id,
            ruleset=request.ruleset,
            status=request.status,
            version=request.version,
        )

    return _run_write(_call)


def post_compliance_profile_deactivate(
    request: ComplianceProfileDeactivateHttpRequest,
    dependencies,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_context = _resolve_handler_context(
        request=request,
        dependencies=dependencies,
        headers=headers,
        require_actor=True,
    )
    if isinstance(resolved_context, RejectionReason):
        return rejection_response(resolved_context)
    actor_context, business_context = resolved_context

    def _call():
        command_context = _build_admin_command_context(
            business_context=business_context,
            actor_context=actor_context,
            dependencies=dependencies,
        )
        return dependencies.admin_service.deactivate_compliance_profile(
            context=command_context,
            branch_id=request.branch_id,
        )

    return _run_write(_call)


def post_document_template_upsert(
    request: DocumentTemplateUpsertHttpRequest,
    dependencies,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_context = _resolve_handler_context(
        request=request,
        dependencies=dependencies,
        headers=headers,
        require_actor=True,
    )
    if isinstance(resolved_context, RejectionReason):
        return rejection_response(resolved_context)
    actor_context, business_context = resolved_context

    def _call():
        command_context = _build_admin_command_context(
            business_context=business_context,
            actor_context=actor_context,
            dependencies=dependencies,
        )
        return dependencies.admin_service.upsert_document_template(
            context=command_context,
            doc_type=request.doc_type,
            branch_id=request.branch_id,
            layout_spec=request.layout_spec,
            status=request.status,
            version=request.version,
        )

    return _run_write(_call)


def post_document_template_deactivate(
    request: DocumentTemplateDeactivateHttpRequest,
    dependencies,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_context = _resolve_handler_context(
        request=request,
        dependencies=dependencies,
        headers=headers,
        require_actor=True,
    )
    if isinstance(resolved_context, RejectionReason):
        return rejection_response(resolved_context)
    actor_context, business_context = resolved_context

    def _call():
        command_context = _build_admin_command_context(
            business_context=business_context,
            actor_context=actor_context,
            dependencies=dependencies,
        )
        return dependencies.admin_service.deactivate_document_template(
            context=command_context,
            doc_type=request.doc_type,
            branch_id=request.branch_id,
        )

    return _run_write(_call)
