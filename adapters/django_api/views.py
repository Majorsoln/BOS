"""
BOS Django Adapter Views
========================
Pass-through HTTP views over core/http_api handlers.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from adapters.django_api.wiring import build_dependencies
from core.http_api.contracts import (
    ActorMetadata,
    ApiKeyCreateHttpRequest,
    ApiKeyRevokeHttpRequest,
    ApiKeyRotateHttpRequest,
    BusinessReadRequest,
    ComplianceProfileDeactivateHttpRequest,
    ComplianceProfileUpsertHttpRequest,
    DocumentRenderRequest,
    DocumentTemplateDeactivateHttpRequest,
    DocumentTemplateUpsertHttpRequest,
    DocumentVerifyRequest,
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
from core.http_api.errors import error_response
from core.http_api.handlers import (
    get_document_render_html,
    get_document_render_pdf,
    get_document_render_plan,
    get_document_verify,
    list_api_keys,
    list_actors,
    list_compliance_profiles,
    list_document_templates,
    list_feature_flags,
    list_issued_documents,
    list_roles,
    post_api_key_create,
    post_api_key_revoke,
    post_api_key_rotate,
    post_compliance_profile_deactivate,
    post_compliance_profile_upsert,
    post_document_template_deactivate,
    post_document_template_upsert,
    post_feature_flag_clear,
    post_feature_flag_set,
    post_identity_bootstrap,
    post_issue_invoice,
    post_issue_quote,
    post_issue_receipt,
    post_role_assign,
    post_role_revoke,
)


def _headers_from_request(request: HttpRequest) -> dict[str, str]:
    return {str(key): str(value) for key, value in request.headers.items()}


def _json_error(code: str, message: str, status: int = 400) -> JsonResponse:
    return JsonResponse(
        error_response(code=code, message=message, details={}),
        status=status,
    )


def _parse_uuid(value: Any, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except Exception as exc:
        raise ValueError(f"{field_name} must be a valid UUID.") from exc


def _parse_optional_uuid(value: Any, field_name: str) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    return _parse_uuid(value, field_name)


def _parse_json_body(request: HttpRequest) -> dict[str, Any]:
    if not request.body:
        return {}
    try:
        parsed = json.loads(request.body.decode("utf-8"))
    except Exception as exc:
        raise ValueError("Request body must be valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Request body must be a JSON object.")
    return parsed


def _parse_actor_metadata(body: dict[str, Any]) -> ActorMetadata | None:
    actor_payload = body.get("actor")
    if actor_payload is None:
        return None
    if not isinstance(actor_payload, dict):
        raise ValueError("actor must be an object.")
    return ActorMetadata(
        actor_type=actor_payload["actor_type"],
        actor_id=actor_payload["actor_id"],
        actor_roles=tuple(actor_payload.get("actor_roles", tuple())),
        actor_scopes=tuple(actor_payload.get("actor_scopes", tuple())),
    )


def _coerce_ruleset(value: Any) -> tuple[Any, ...]:
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    raise ValueError("ruleset must be a list or tuple.")


def _parse_payload_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("payload must be a JSON object.")
    return value


def _parse_uuid_string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a list or tuple.")
    return tuple(str(_parse_uuid(item, field_name)) for item in value)


def _parse_uuid_map(value: Any, field_name: str) -> dict[str, tuple[str, ...]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object.")

    parsed: dict[str, tuple[str, ...]] = {}
    for business_id, branch_ids in value.items():
        canonical_business_id = str(
            _parse_uuid(business_id, f"{field_name} business_id")
        )
        parsed[canonical_business_id] = _parse_uuid_string_tuple(
            branch_ids,
            f"{field_name} branch_ids",
        )
    return parsed


def _parse_limit(value: Any) -> int:
    if value is None or value == "":
        return 50
    try:
        return int(value)
    except Exception as exc:
        raise ValueError("limit must be an integer.") from exc


def _parse_branch_specs(value: Any) -> tuple[dict[str, Any], ...]:
    if value is None:
        return tuple()
    if not isinstance(value, (list, tuple)):
        raise ValueError("branches must be a list or tuple.")

    parsed: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError("branches items must be objects.")
        branch = dict(item)
        branch_id = branch.get("branch_id")
        if branch_id not in (None, ""):
            branch["branch_id"] = str(
                _parse_uuid(branch_id, f"branches[{index}].branch_id")
            )
        if "name" in branch and branch["name"] is not None:
            branch["name"] = str(branch["name"])
        if "timezone" in branch and branch["timezone"] is not None:
            branch["timezone"] = str(branch["timezone"])
        parsed.append(branch)
    return tuple(parsed)


def _dispatch_read(read_handler, request: HttpRequest) -> JsonResponse:
    headers = _headers_from_request(request)
    try:
        business_id_raw = request.GET.get("business_id")
        if business_id_raw is None:
            raise ValueError("business_id is required.")
        contract = BusinessReadRequest(
            business_id=_parse_uuid(business_id_raw, "business_id")
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    payload = read_handler(
        contract,
        build_dependencies(),
        headers=headers,
    )
    return JsonResponse(payload)


def _dispatch_issued_documents_read(
    read_handler,
    request: HttpRequest,
) -> JsonResponse:
    headers = _headers_from_request(request)
    try:
        business_id_raw = request.GET.get("business_id")
        if business_id_raw is None:
            raise ValueError("business_id is required.")
        contract = IssuedDocumentsReadRequest(
            business_id=_parse_uuid(business_id_raw, "business_id"),
            branch_id=_parse_optional_uuid(
                request.GET.get("branch_id"),
                "branch_id",
            ),
            limit=_parse_limit(request.GET.get("limit")),
            cursor=request.GET.get("cursor") or None,
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    payload = read_handler(
        contract,
        build_dependencies(),
        headers=headers,
    )
    return JsonResponse(payload)


def _dispatch_write(write_handler, request_contract_factory, request: HttpRequest):
    headers = _headers_from_request(request)
    try:
        body = _parse_json_body(request)
        business_id = _parse_uuid(body["business_id"], "business_id")
        branch_id = _parse_optional_uuid(body.get("branch_id"), "branch_id")
        actor = _parse_actor_metadata(body)
        contract = request_contract_factory(
            body=body,
            actor=actor,
            business_id=business_id,
            branch_id=branch_id,
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    payload = write_handler(
        contract,
        build_dependencies(),
        headers=headers,
    )
    return JsonResponse(payload)


def _method_not_allowed() -> JsonResponse:
    return _json_error(
        "METHOD_NOT_ALLOWED",
        "Method not allowed for this endpoint.",
        status=405,
    )


def _feature_flag_set_contract_factory(*, body, actor, business_id, branch_id):
    return FeatureFlagSetHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        flag_key=body["flag_key"],
        status=body["status"],
    )


def _feature_flag_clear_contract_factory(*, body, actor, business_id, branch_id):
    return FeatureFlagClearHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        flag_key=body["flag_key"],
    )


def _compliance_upsert_contract_factory(*, body, actor, business_id, branch_id):
    return ComplianceProfileUpsertHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        ruleset=_coerce_ruleset(body["ruleset"]),
        status=body.get("status", "ACTIVE"),
        version=body.get("version"),
    )


def _compliance_deactivate_contract_factory(*, body, actor, business_id, branch_id):
    return ComplianceProfileDeactivateHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
    )


def _document_upsert_contract_factory(*, body, actor, business_id, branch_id):
    return DocumentTemplateUpsertHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        doc_type=body["doc_type"],
        layout_spec=body["layout_spec"],
        status=body.get("status", "ACTIVE"),
        version=body.get("version"),
    )


def _document_deactivate_contract_factory(*, body, actor, business_id, branch_id):
    return DocumentTemplateDeactivateHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        doc_type=body["doc_type"],
    )


def _issue_receipt_contract_factory(*, body, actor, business_id, branch_id):
    return IssueReceiptHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        payload=_parse_payload_object(body["payload"]),
    )


def _issue_quote_contract_factory(*, body, actor, business_id, branch_id):
    return IssueQuoteHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        payload=_parse_payload_object(body["payload"]),
    )


def _issue_invoice_contract_factory(*, body, actor, business_id, branch_id):
    return IssueInvoiceHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        payload=_parse_payload_object(body["payload"]),
    )


def _api_key_create_contract_factory(*, body, actor, business_id, branch_id):
    return ApiKeyCreateHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        label=body.get("label"),
        actor_id=body["actor_id"],
        actor_type=body["actor_type"],
        allowed_business_ids=_parse_uuid_string_tuple(
            body["allowed_business_ids"],
            "allowed_business_ids",
        ),
        allowed_branch_ids_by_business=_parse_uuid_map(
            body.get("allowed_branch_ids_by_business", {}),
            "allowed_branch_ids_by_business",
        ),
    )


def _api_key_revoke_contract_factory(*, body, actor, business_id, branch_id):
    return ApiKeyRevokeHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        key_id=_parse_optional_uuid(body.get("key_id"), "key_id"),
        key_hash=body.get("key_hash"),
    )


def _api_key_rotate_contract_factory(*, body, actor, business_id, branch_id):
    return ApiKeyRotateHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        key_id=_parse_optional_uuid(body.get("key_id"), "key_id"),
        key_hash=body.get("key_hash"),
        label=body.get("label"),
    )


def _identity_bootstrap_contract_factory(*, body, actor, business_id, branch_id):
    return IdentityBootstrapHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        business_name=body["business_name"],
        default_currency=body.get("default_currency", "USD"),
        default_language=body.get("default_language", "en"),
        branches=_parse_branch_specs(body.get("branches")),
        admin_actor_id=body.get("admin_actor_id"),
        cashier_actor_id=body.get("cashier_actor_id"),
    )


def _role_assign_contract_factory(*, body, actor, business_id, branch_id):
    return RoleAssignHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        actor_id=body["actor_id"],
        actor_type=body["actor_type"],
        role_name=body["role_name"],
        display_name=body.get("display_name"),
    )


def _role_revoke_contract_factory(*, body, actor, business_id, branch_id):
    return RoleRevokeHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        actor_id=body["actor_id"],
        role_name=body["role_name"],
    )


@csrf_exempt
def feature_flags_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_read(list_feature_flags, request)


@csrf_exempt
def compliance_profiles_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_read(list_compliance_profiles, request)


@csrf_exempt
def document_templates_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_read(list_document_templates, request)


@csrf_exempt
def issued_documents_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_issued_documents_read(list_issued_documents, request)


@csrf_exempt
def api_keys_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_read(list_api_keys, request)


@csrf_exempt
def roles_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_read(list_roles, request)


@csrf_exempt
def actors_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_read(list_actors, request)


@csrf_exempt
def feature_flags_set_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_feature_flag_set,
        _feature_flag_set_contract_factory,
        request,
    )


@csrf_exempt
def feature_flags_clear_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_feature_flag_clear,
        _feature_flag_clear_contract_factory,
        request,
    )


@csrf_exempt
def compliance_profiles_upsert_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_compliance_profile_upsert,
        _compliance_upsert_contract_factory,
        request,
    )


@csrf_exempt
def compliance_profiles_deactivate_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_compliance_profile_deactivate,
        _compliance_deactivate_contract_factory,
        request,
    )


@csrf_exempt
def document_templates_upsert_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_document_template_upsert,
        _document_upsert_contract_factory,
        request,
    )


@csrf_exempt
def document_templates_deactivate_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_document_template_deactivate,
        _document_deactivate_contract_factory,
        request,
    )


@csrf_exempt
def issue_receipt_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_issue_receipt,
        _issue_receipt_contract_factory,
        request,
    )


@csrf_exempt
def issue_quote_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_issue_quote,
        _issue_quote_contract_factory,
        request,
    )


@csrf_exempt
def issue_invoice_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_issue_invoice,
        _issue_invoice_contract_factory,
        request,
    )


@csrf_exempt
def api_keys_create_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_api_key_create,
        _api_key_create_contract_factory,
        request,
    )


@csrf_exempt
def api_keys_revoke_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_api_key_revoke,
        _api_key_revoke_contract_factory,
        request,
    )


@csrf_exempt
def api_keys_rotate_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_api_key_rotate,
        _api_key_rotate_contract_factory,
        request,
    )


@csrf_exempt
def identity_bootstrap_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_identity_bootstrap,
        _identity_bootstrap_contract_factory,
        request,
    )


@csrf_exempt
def roles_assign_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_role_assign,
        _role_assign_contract_factory,
        request,
    )


@csrf_exempt
def roles_revoke_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_role_revoke,
        _role_revoke_contract_factory,
        request,
    )


# ---------------------------------------------------------------------------
# Phase 3: Document render & verification views
# ---------------------------------------------------------------------------

def _dispatch_document_read(
    read_handler,
    request: HttpRequest,
    document_id: uuid.UUID,
) -> JsonResponse:
    """Dispatch a document-specific read request (render-plan, render-html, etc.)."""
    headers = _headers_from_request(request)
    try:
        business_id_raw = request.GET.get("business_id")
        if business_id_raw is None:
            raise ValueError("business_id is required.")
        contract = DocumentRenderRequest(
            business_id=_parse_uuid(business_id_raw, "business_id"),
            document_id=document_id,
            branch_id=_parse_optional_uuid(
                request.GET.get("branch_id"), "branch_id"
            ),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    payload = read_handler(contract, build_dependencies(), headers=headers)
    return JsonResponse(payload)


@csrf_exempt
def document_render_plan_view(request: HttpRequest, document_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_document_read(get_document_render_plan, request, document_id)


@csrf_exempt
def document_render_html_view(request: HttpRequest, document_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_document_read(get_document_render_html, request, document_id)


@csrf_exempt
def document_render_pdf_view(request: HttpRequest, document_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_document_read(get_document_render_pdf, request, document_id)


@csrf_exempt
def document_verify_view(request: HttpRequest, document_id: uuid.UUID) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    headers = _headers_from_request(request)
    try:
        business_id_raw = request.GET.get("business_id")
        if business_id_raw is None:
            raise ValueError("business_id is required.")
        contract = DocumentVerifyRequest(
            business_id=_parse_uuid(business_id_raw, "business_id"),
            document_id=document_id,
            branch_id=_parse_optional_uuid(
                request.GET.get("branch_id"), "branch_id"
            ),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    payload = get_document_verify(contract, build_dependencies(), headers=headers)
    return JsonResponse(payload)
