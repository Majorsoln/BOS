"""
BOS HTTP API - Framework-Agnostic Handlers
==========================================
Pure handler functions over contracts and injected dependencies.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.auth.service import ApiKeyService, serialize_api_key_credential
from core.commands.base import Command
from core.admin.commands import AdminCommandContext
from core.permissions.evaluator import PermissionEvaluator
from core.commands.rejection import ReasonCode, RejectionReason
from core.context.actor_context import ActorContext
from core.context.business_context import BusinessContext
from core.identity_store.service import (
    assign_role as assign_identity_role,
    bootstrap_identity as bootstrap_identity_store,
    list_actors_for_business as list_identity_actors_for_business,
    list_role_assignments_for_business as list_identity_assignments_for_business,
    list_roles_for_business as list_identity_roles_for_business,
    revoke_role as revoke_identity_role,
)
from core.document_issuance.registry import (
    DOC_INVOICE_ISSUE_REQUEST,
    DOC_QUOTE_ISSUE_REQUEST,
    DOC_RECEIPT_ISSUE_REQUEST,
    resolve_doc_type_for_issue_command,
)
from core.document_issuance.repository import DocumentCursorError
from core.http_api.auth.middleware import resolve_request_context
from core.http_api.contracts import (
    ActorMetadata,
    ApiKeyCreateHttpRequest,
    ApiKeyRevokeHttpRequest,
    ApiKeyRotateHttpRequest,
    BusinessReadRequest,
    ComplianceProfileDeactivateHttpRequest,
    ComplianceProfileUpsertHttpRequest,
    DocumentTemplateDeactivateHttpRequest,
    DocumentTemplateUpsertHttpRequest,
    FeatureFlagClearHttpRequest,
    FeatureFlagSetHttpRequest,
    IdentityBootstrapHttpRequest,
    IssueInvoiceHttpRequest,
    IssueQuoteHttpRequest,
    IssueReceiptHttpRequest,
    IssuedDocumentsReadRequest,
    RoleAssignHttpRequest,
    RoleRevokeHttpRequest,
)
from core.http_api.errors import error_response, rejection_response, success_response

ADMIN_API_KEY_CREATE_REQUEST = "admin.api_key.create.request"
ADMIN_API_KEY_REVOKE_REQUEST = "admin.api_key.revoke.request"
ADMIN_API_KEY_ROTATE_REQUEST = "admin.api_key.rotate.request"
ADMIN_API_KEY_LIST_REQUEST = "admin.api_key.list.request"
ADMIN_IDENTITY_BOOTSTRAP_REQUEST = "admin.identity.bootstrap.request"
ADMIN_ROLES_ASSIGN_REQUEST = "admin.roles.assign.request"
ADMIN_ROLES_REVOKE_REQUEST = "admin.roles.revoke.request"
ADMIN_ROLES_LIST_REQUEST = "admin.roles.list.request"
ADMIN_ACTORS_LIST_REQUEST = "admin.actors.list.request"

_PERMISSION_PROBE_COMMAND_ID = uuid.UUID(int=0)
_PERMISSION_PROBE_CORRELATION_ID = uuid.UUID(int=1)
_PERMISSION_PROBE_ISSUED_AT = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _iso_datetime_value(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _new_document_id(dependencies) -> uuid.UUID:
    id_provider = dependencies.id_provider
    candidate_factory = getattr(id_provider, "new_document_id", None)
    value = (
        candidate_factory()
        if callable(candidate_factory)
        else id_provider.new_command_id()
    )
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _resolve_language(headers: dict[str, Any] | None) -> str:
    for key, value in (headers or {}).items():
        if str(key).strip().lower() != "accept-language":
            continue
        raw = str(value).strip().lower()
        if not raw:
            break
        first_segment = raw.split(",")[0]
        lang = first_segment.split(";")[0].strip()
        if lang:
            return lang
        break
    return "en"


def _success_with_language(
    data: Any,
    *,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return success_response(
        data,
        meta={"lang": _resolve_language(headers)},
    )


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


def _enforce_admin_permission(
    *,
    dependencies,
    actor_context: ActorContext | None,
    business_context: BusinessContext,
    branch_id: uuid.UUID | None,
    command_type: str,
) -> RejectionReason | None:
    if actor_context is None:
        return RejectionReason(
            code=ReasonCode.ACTOR_REQUIRED_MISSING,
            message="actor_context is required for admin API key operations.",
            policy_name="http_api_admin_permission_guard",
        )

    permission_provider = getattr(dependencies, "permission_provider", None)
    if permission_provider is None:
        return RejectionReason(
            code=ReasonCode.PERMISSION_DENIED,
            message="Permission provider is not configured.",
            policy_name="http_api_admin_permission_guard",
        )

    try:
        probe_command = Command(
            command_id=_PERMISSION_PROBE_COMMAND_ID,
            command_type=command_type,
            business_id=business_context.business_id,
            branch_id=branch_id,
            actor_type=actor_context.actor_type,
            actor_id=actor_context.actor_id,
            actor_context=actor_context,
            payload={},
            issued_at=_PERMISSION_PROBE_ISSUED_AT,
            correlation_id=_PERMISSION_PROBE_CORRELATION_ID,
            source_engine="admin",
        )
        result = PermissionEvaluator.evaluate(
            command=probe_command,
            actor_context=actor_context,
            business_context=business_context,
            provider=permission_provider,
        )
    except Exception:
        return RejectionReason(
            code=ReasonCode.PERMISSION_DENIED,
            message="Permission authorization check failed.",
            policy_name="http_api_admin_permission_guard",
        )

    if result.allowed:
        return None

    return RejectionReason(
        code=result.rejection_code or ReasonCode.PERMISSION_DENIED,
        message=result.message or "Permission denied.",
        policy_name="http_api_admin_permission_guard",
    )


def _new_raw_api_key(dependencies) -> str:
    return f"bos_{dependencies.id_provider.new_command_id().hex}"


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


def _serialize_issued_document(record) -> dict[str, Any]:
    doc_id = str(record.document_id)
    template_id = _canonical_uuid_text(record.template_id, namespace="template")
    correlation_id = _canonical_uuid_text(
        getattr(record, "correlation_id", None),
        namespace="correlation",
    )
    return {
        "doc_id": doc_id,
        "doc_type": record.doc_type,
        "status": str(record.status),
        "business_id": str(record.business_id),
        "branch_id": None if record.branch_id is None else str(record.branch_id),
        "issued_at": _iso_datetime_value(record.issued_at),
        "issued_by_actor_id": str(record.actor_id),
        "correlation_id": correlation_id,
        "template_id": template_id,
        "template_version": int(record.template_version),
        "schema_version": int(record.schema_version),
        "totals": _normalize_totals(getattr(record, "totals", {})),
        "links": {
            "self": f"/v1/docs/{doc_id}",
            "render_plan": f"/v1/docs/{doc_id}/render-plan",
        },
    }


def _canonical_uuid_text(value, *, namespace: str) -> str:
    if value is None:
        return str(uuid.UUID(int=0))
    if isinstance(value, uuid.UUID):
        return str(value)
    raw = str(value)
    try:
        return str(uuid.UUID(raw))
    except Exception:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{namespace}:{raw}"))


def _normalize_totals(value) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    ordered = sorted(
        ((str(key), value[key]) for key in value.keys()),
        key=lambda item: item[0],
    )
    return {key: item_value for key, item_value in ordered}


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
    return _success_with_language(
        {
            "items": tuple(_serialize_feature_flag(flag) for flag in ordered),
            "count": len(ordered),
        },
        headers=headers,
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
    return _success_with_language(
        {
            "items": tuple(
                _serialize_compliance_profile(profile) for profile in ordered
            ),
            "count": len(ordered),
        },
        headers=headers,
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
    return _success_with_language(
        {
            "items": tuple(
                _serialize_document_template(template) for template in ordered
            ),
            "count": len(ordered),
        },
        headers=headers,
    )


def list_issued_documents(
    request: IssuedDocumentsReadRequest,
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

    repository = getattr(dependencies, "document_issuance_repository", None)
    if repository is None:
        return error_response(
            code="READ_MODEL_ERROR",
            message="Failed to read issued documents.",
            details={"error_type": "RepositoryNotConfigured"},
        )

    branch_filter = (
        business_context.branch_id
        if business_context.branch_id is not None
        else request.branch_id
    )

    next_cursor = None
    try:
        get_documents_page = getattr(repository, "get_documents_page", None)
        if callable(get_documents_page):
            records, next_cursor = get_documents_page(
                business_id=business_context.business_id,
                branch_id=branch_filter,
                limit=request.limit,
                cursor=request.cursor,
            )
        else:
            if request.cursor is not None:
                return error_response(
                    code="INVALID_REQUEST",
                    message="cursor pagination is not supported by repository.",
                    details={},
                )
            all_records = repository.get_documents(
                business_context.business_id,
                branch_filter,
            )
            records = tuple(all_records[: request.limit])
            next_cursor = None
    except (DocumentCursorError, ValueError) as exc:
        return error_response(
            code="INVALID_REQUEST",
            message=str(exc),
            details={},
        )
    except Exception as exc:
        return error_response(
            code="READ_MODEL_ERROR",
            message="Failed to read issued documents.",
            details={"error_type": type(exc).__name__},
        )

    return _success_with_language(
        {
            "items": tuple(_serialize_issued_document(item) for item in records),
            "count": len(records),
            "next_cursor": next_cursor,
        },
        headers=headers,
    )


def list_api_keys(
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
    actor_context, business_context = resolved_context

    if getattr(dependencies, "auth_provider", None) is not None:
        permission_rejection = _enforce_admin_permission(
            dependencies=dependencies,
            actor_context=actor_context,
            business_context=business_context,
            branch_id=business_context.branch_id,
            command_type=ADMIN_API_KEY_LIST_REQUEST,
        )
        if permission_rejection is not None:
            return rejection_response(permission_rejection)

    try:
        rows = ApiKeyService.list_api_keys_for_business(
            business_id=business_context.business_id
        )
    except ValueError as exc:
        return error_response(
            code="INVALID_REQUEST",
            message=str(exc),
            details={},
        )
    except Exception as exc:
        return error_response(
            code="READ_MODEL_ERROR",
            message="Failed to read API keys.",
            details={"error_type": type(exc).__name__},
        )

    items = tuple(serialize_api_key_credential(row) for row in rows)
    return _success_with_language(
        {
            "items": items,
            "count": len(items),
        },
        headers=headers,
    )


def list_roles(
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
    actor_context, business_context = resolved_context

    if getattr(dependencies, "auth_provider", None) is not None:
        permission_rejection = _enforce_admin_permission(
            dependencies=dependencies,
            actor_context=actor_context,
            business_context=business_context,
            branch_id=business_context.branch_id,
            command_type=ADMIN_ROLES_LIST_REQUEST,
        )
        if permission_rejection is not None:
            return rejection_response(permission_rejection)

    try:
        roles = list_identity_roles_for_business(business_context.business_id)
        assignments = list_identity_assignments_for_business(
            business_context.business_id
        )
    except ValueError as exc:
        return error_response(
            code="INVALID_REQUEST",
            message=str(exc),
            details={},
        )
    except Exception as exc:
        return error_response(
            code="READ_MODEL_ERROR",
            message="Failed to read roles.",
            details={"error_type": type(exc).__name__},
        )

    return _success_with_language(
        {
            "roles": roles,
            "assignments": assignments,
            "role_count": len(roles),
            "assignment_count": len(assignments),
        },
        headers=headers,
    )


def list_actors(
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
    actor_context, business_context = resolved_context

    if getattr(dependencies, "auth_provider", None) is not None:
        permission_rejection = _enforce_admin_permission(
            dependencies=dependencies,
            actor_context=actor_context,
            business_context=business_context,
            branch_id=business_context.branch_id,
            command_type=ADMIN_ACTORS_LIST_REQUEST,
        )
        if permission_rejection is not None:
            return rejection_response(permission_rejection)

    try:
        items = list_identity_actors_for_business(business_context.business_id)
    except ValueError as exc:
        return error_response(
            code="INVALID_REQUEST",
            message=str(exc),
            details={},
        )
    except Exception as exc:
        return error_response(
            code="READ_MODEL_ERROR",
            message="Failed to read actors.",
            details={"error_type": type(exc).__name__},
        )

    return _success_with_language(
        {
            "items": items,
            "count": len(items),
        },
        headers=headers,
    )


def post_identity_bootstrap(
    request: IdentityBootstrapHttpRequest,
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

    permission_rejection = _enforce_admin_permission(
        dependencies=dependencies,
        actor_context=actor_context,
        business_context=business_context,
        branch_id=request.branch_id,
        command_type=ADMIN_IDENTITY_BOOTSTRAP_REQUEST,
    )
    if permission_rejection is not None:
        return rejection_response(permission_rejection)

    try:
        bootstrap_data = bootstrap_identity_store(
            business_id=request.business_id,
            business_name=request.business_name,
            default_currency=request.default_currency,
            default_language=request.default_language,
            branches=request.branches,
            admin_actor_id=request.admin_actor_id,
            cashier_actor_id=request.cashier_actor_id,
        )
    except ValueError as exc:
        return error_response(
            code="INVALID_REQUEST",
            message=str(exc),
            details={},
        )
    except Exception as exc:
        return error_response(
            code="HANDLER_EXECUTION_FAILED",
            message="Failed to bootstrap identity.",
            details={"error_type": type(exc).__name__},
        )

    return _success_with_language(bootstrap_data, headers=headers)


def post_role_assign(
    request: RoleAssignHttpRequest,
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

    permission_rejection = _enforce_admin_permission(
        dependencies=dependencies,
        actor_context=actor_context,
        business_context=business_context,
        branch_id=request.branch_id,
        command_type=ADMIN_ROLES_ASSIGN_REQUEST,
    )
    if permission_rejection is not None:
        return rejection_response(permission_rejection)

    try:
        assignment = assign_identity_role(
            business_id=request.business_id,
            actor_id=request.actor_id,
            actor_type=request.actor_type,
            role_name=request.role_name,
            branch_id=request.branch_id,
            display_name=request.display_name,
        )
    except ValueError as exc:
        return error_response(
            code="INVALID_REQUEST",
            message=str(exc),
            details={},
        )
    except Exception as exc:
        return error_response(
            code="HANDLER_EXECUTION_FAILED",
            message="Failed to assign role.",
            details={"error_type": type(exc).__name__},
        )

    return _success_with_language({"assignment": assignment}, headers=headers)


def post_role_revoke(
    request: RoleRevokeHttpRequest,
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

    permission_rejection = _enforce_admin_permission(
        dependencies=dependencies,
        actor_context=actor_context,
        business_context=business_context,
        branch_id=request.branch_id,
        command_type=ADMIN_ROLES_REVOKE_REQUEST,
    )
    if permission_rejection is not None:
        return rejection_response(permission_rejection)

    try:
        assignment = revoke_identity_role(
            business_id=request.business_id,
            actor_id=request.actor_id,
            role_name=request.role_name,
            branch_id=request.branch_id,
        )
    except ValueError as exc:
        return error_response(
            code="INVALID_REQUEST",
            message=str(exc),
            details={},
        )
    except Exception as exc:
        return error_response(
            code="HANDLER_EXECUTION_FAILED",
            message="Failed to revoke role.",
            details={"error_type": type(exc).__name__},
        )

    if assignment is None:
        return error_response(
            code="ROLE_ASSIGNMENT_NOT_FOUND",
            message="Role assignment was not found.",
            details={},
        )

    return _success_with_language(
        {
            "revoked": True,
            "assignment": assignment,
        },
        headers=headers,
    )


def _write_result_response(
    command_result,
    *,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
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

    return _success_with_language(
        {
            "status": status,
            "command_id": command_id,
            "rejection": None,
            "event_type": event_type,
            "correlation_id": correlation_id,
            "created_identifiers": created_identifiers,
            "projection_applied": projection_applied,
        },
        headers=headers,
    )


def _run_write(
    write_call,
    *,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    return _write_result_response(command_result, headers=headers)


def _issue_result_response(
    command_result,
    *,
    document_id: uuid.UUID,
    doc_type: str,
    issued_at: datetime,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if command_result.is_rejected:
        rejection = command_result.outcome.reason
        if rejection is None:
            return error_response(
                code="UNKNOWN_REJECTION",
                message="Command rejected without rejection details.",
                details={
                    "status": command_result.outcome.status.value,
                    "command_id": str(command_result.outcome.command_id),
                },
            )
        return rejection_response(
            rejection,
            extra_details={
                "status": command_result.outcome.status.value,
                "command_id": str(command_result.outcome.command_id),
            },
        )

    payload = {}
    execution = command_result.execution_result
    if execution is not None:
        event_data = getattr(execution, "event_data", None)
        if isinstance(event_data, dict):
            event_payload = event_data.get("payload")
            if isinstance(event_payload, dict):
                payload = event_payload

    resolved_document_id = payload.get("document_id", document_id)
    resolved_doc_type = payload.get("doc_type", doc_type)
    resolved_issued_at = payload.get("issued_at", issued_at)

    return _success_with_language(
        {
            "document_id": str(resolved_document_id),
            "doc_type": str(resolved_doc_type),
            "issued_at": _iso_datetime_value(resolved_issued_at),
        },
        headers=headers,
    )


def _run_issue_write(
    write_call,
    *,
    document_id: uuid.UUID,
    doc_type: str,
    issued_at: datetime,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
            message="Failed to execute document issuance command.",
            details={"error_type": type(exc).__name__},
        )
    return _issue_result_response(
        command_result,
        document_id=document_id,
        doc_type=doc_type,
        issued_at=issued_at,
        headers=headers,
    )


def post_api_key_create(
    request: ApiKeyCreateHttpRequest,
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

    permission_rejection = _enforce_admin_permission(
        dependencies=dependencies,
        actor_context=actor_context,
        business_context=business_context,
        branch_id=request.branch_id,
        command_type=ADMIN_API_KEY_CREATE_REQUEST,
    )
    if permission_rejection is not None:
        return rejection_response(permission_rejection)

    try:
        raw_api_key = _new_raw_api_key(dependencies)
        credential = ApiKeyService.create_api_key_credential(
            api_key=raw_api_key,
            actor_id=request.actor_id,
            actor_type=request.actor_type,
            allowed_business_ids=request.allowed_business_ids,
            allowed_branch_ids_by_business=request.allowed_branch_ids_by_business,
            created_by_actor_id=actor_context.actor_id,
            label=request.label,
        )
    except ValueError as exc:
        return error_response(
            code="INVALID_REQUEST",
            message=str(exc),
            details={},
        )
    except Exception as exc:
        return error_response(
            code="HANDLER_EXECUTION_FAILED",
            message="Failed to create API key.",
            details={"error_type": type(exc).__name__},
        )

    return _success_with_language(
        {
            "api_key": raw_api_key,
            "credential": serialize_api_key_credential(credential),
        },
        headers=headers,
    )


def post_api_key_revoke(
    request: ApiKeyRevokeHttpRequest,
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

    permission_rejection = _enforce_admin_permission(
        dependencies=dependencies,
        actor_context=actor_context,
        business_context=business_context,
        branch_id=request.branch_id,
        command_type=ADMIN_API_KEY_REVOKE_REQUEST,
    )
    if permission_rejection is not None:
        return rejection_response(permission_rejection)

    try:
        credential = ApiKeyService.revoke_api_key_credential(
            key_id=request.key_id,
            key_hash=request.key_hash,
            revoked_by_actor_id=actor_context.actor_id,
        )
    except ValueError as exc:
        return error_response(
            code="INVALID_REQUEST",
            message=str(exc),
            details={},
        )
    except Exception as exc:
        return error_response(
            code="HANDLER_EXECUTION_FAILED",
            message="Failed to revoke API key.",
            details={"error_type": type(exc).__name__},
        )

    if credential is None:
        return error_response(
            code="API_KEY_NOT_FOUND",
            message="API key credential was not found.",
            details={},
        )

    return _success_with_language(
        {
            "revoked": True,
            "credential": serialize_api_key_credential(credential),
        },
        headers=headers,
    )


def post_api_key_rotate(
    request: ApiKeyRotateHttpRequest,
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

    permission_rejection = _enforce_admin_permission(
        dependencies=dependencies,
        actor_context=actor_context,
        business_context=business_context,
        branch_id=request.branch_id,
        command_type=ADMIN_API_KEY_ROTATE_REQUEST,
    )
    if permission_rejection is not None:
        return rejection_response(permission_rejection)

    try:
        raw_api_key = _new_raw_api_key(dependencies)
        rotated = ApiKeyService.rotate_api_key_credential(
            new_api_key=raw_api_key,
            key_id=request.key_id,
            key_hash=request.key_hash,
            rotated_by_actor_id=actor_context.actor_id,
            label=request.label,
        )
    except ValueError as exc:
        return error_response(
            code="INVALID_REQUEST",
            message=str(exc),
            details={},
        )
    except Exception as exc:
        return error_response(
            code="HANDLER_EXECUTION_FAILED",
            message="Failed to rotate API key.",
            details={"error_type": type(exc).__name__},
        )

    if rotated is None:
        return error_response(
            code="API_KEY_NOT_FOUND",
            message="API key credential was not found.",
            details={},
        )

    revoked_credential, replacement_credential = rotated
    return _success_with_language(
        {
            "api_key": raw_api_key,
            "revoked_credential": serialize_api_key_credential(revoked_credential),
            "credential": serialize_api_key_credential(replacement_credential),
        },
        headers=headers,
    )


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

    return _run_write(_call, headers=headers)


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

    return _run_write(_call, headers=headers)


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

    return _run_write(_call, headers=headers)


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

    return _run_write(_call, headers=headers)


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

    return _run_write(_call, headers=headers)


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

    return _run_write(_call, headers=headers)


def _post_issue_document(
    *,
    request,
    dependencies,
    headers: dict[str, Any] | None,
    command_type: str,
    issue_method_name: str,
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

    issuance_service = getattr(dependencies, "document_issuance_service", None)
    if issuance_service is None:
        return error_response(
            code="HANDLER_EXECUTION_FAILED",
            message="Document issuance service is not configured.",
            details={},
        )

    document_id = _new_document_id(dependencies)
    command_id = dependencies.id_provider.new_command_id()
    correlation_id = dependencies.id_provider.new_correlation_id()
    issued_at = dependencies.clock.now_issued_at()
    doc_type = resolve_doc_type_for_issue_command(command_type)
    if doc_type is None:
        return error_response(
            code="INVALID_REQUEST",
            message=f"Unsupported issue command type: {command_type}",
            details={},
        )

    def _call():
        issue_method = getattr(issuance_service, issue_method_name)
        return issue_method(
            business_id=business_context.business_id,
            branch_id=business_context.branch_id,
            document_id=document_id,
            payload=request.payload,
            actor_context=actor_context,
            command_id=command_id,
            correlation_id=correlation_id,
            issued_at=issued_at,
        )

    return _run_issue_write(
        _call,
        document_id=document_id,
        doc_type=doc_type,
        issued_at=issued_at,
        headers=headers,
    )


def post_issue_receipt(
    request: IssueReceiptHttpRequest,
    dependencies,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _post_issue_document(
        request=request,
        dependencies=dependencies,
        headers=headers,
        command_type=DOC_RECEIPT_ISSUE_REQUEST,
        issue_method_name="issue_receipt",
    )


def post_issue_quote(
    request: IssueQuoteHttpRequest,
    dependencies,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _post_issue_document(
        request=request,
        dependencies=dependencies,
        headers=headers,
        command_type=DOC_QUOTE_ISSUE_REQUEST,
        issue_method_name="issue_quote",
    )


def post_issue_invoice(
    request: IssueInvoiceHttpRequest,
    dependencies,
    headers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _post_issue_document(
        request=request,
        dependencies=dependencies,
        headers=headers,
        command_type=DOC_INVOICE_ISSUE_REQUEST,
        issue_method_name="issue_invoice",
    )
