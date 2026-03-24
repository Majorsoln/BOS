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
    ActorDeactivateHttpRequest,
    ActorMetadata,
    ApiKeyCreateHttpRequest,
    ApiKeyRevokeHttpRequest,
    ApiKeyRotateHttpRequest,
    BusinessReadRequest,
    BusinessUpdateHttpRequest,
    ComplianceProfileDeactivateHttpRequest,
    ComplianceProfileUpsertHttpRequest,
    CustomerProfileCreateHttpRequest,
    CustomerProfileUpdateHttpRequest,
    DocumentRenderRequest,
    DocumentTemplateDeactivateHttpRequest,
    DocumentTemplateUpsertHttpRequest,
    DocumentVerifyRequest,
    FeatureFlagClearHttpRequest,
    FeatureFlagSetHttpRequest,
    IdentityBootstrapHttpRequest,
    IssueDocumentHttpRequest,
    IssueInvoiceHttpRequest,
    IssueQuoteHttpRequest,
    IssueReceiptHttpRequest,
    IssuedDocumentsReadRequest,
    RoleAssignHttpRequest,
    RoleCreateHttpRequest,
    RoleRevokeHttpRequest,
    TaxRuleSetHttpRequest,
)
from core.http_api.errors import error_response
from core.http_api.handlers import (
    get_business_profile,
    get_document_render_html,
    get_document_render_pdf,
    get_document_render_plan,
    get_document_verify,
    list_actors,
    list_api_keys,
    list_branches,
    list_compliance_profiles,
    list_customers,
    list_document_templates,
    list_feature_flags,
    list_issued_documents,
    list_roles,
    list_tax_rules,
    post_actor_deactivate,
    post_api_key_create,
    post_api_key_revoke,
    post_api_key_rotate,
    post_business_update,
    post_compliance_profile_deactivate,
    post_compliance_profile_upsert,
    post_customer_create,
    post_customer_update,
    post_document_template_deactivate,
    post_document_template_upsert,
    post_feature_flag_clear,
    post_feature_flag_set,
    post_identity_bootstrap,
    post_issue_document_by_type,
    post_issue_invoice,
    post_issue_quote,
    post_issue_receipt,
    post_role_assign,
    post_role_create,
    post_role_revoke,
    post_tax_rule_set,
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


def _make_issue_document_contract_factory(doc_type: str):
    """Return a contract factory bound to a specific doc_type from the URL."""
    def _factory(*, body, actor, business_id, branch_id):
        return IssueDocumentHttpRequest(
            business_id=business_id,
            branch_id=branch_id,
            actor=actor,
            payload=_parse_payload_object(body.get("payload", {})),
            doc_type=doc_type,
        )
    return _factory


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
        address=body.get("address", ""),
        city=body.get("city", ""),
        country_code=body.get("country_code", ""),
        phone=body.get("phone", ""),
        email=body.get("email", ""),
        tax_id=body.get("tax_id", ""),
        logo_url=body.get("logo_url", ""),
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
def issue_document_type_view(request: HttpRequest, doc_type: str) -> JsonResponse:
    """
    Generic document issue endpoint for all 25 document types.
    URL: POST /docs/<doc_type>/issue
    e.g. /docs/proforma_invoice/issue, /docs/work_order/issue, /docs/folio/issue
    """
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_issue_document_by_type,
        _make_issue_document_contract_factory(doc_type),
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


@csrf_exempt
def business_profile_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_read(get_business_profile, request)


@csrf_exempt
def branches_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_read(list_branches, request)


def _actor_deactivate_contract_factory(*, body, actor, business_id, branch_id):
    return ActorDeactivateHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        actor_id=body["actor_id"],
    )


@csrf_exempt
def actors_deactivate_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_actor_deactivate,
        _actor_deactivate_contract_factory,
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
            locale=request.GET.get("locale"),
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


# ---------------------------------------------------------------------------
# Tax Rule endpoints
# ---------------------------------------------------------------------------

def _tax_rule_set_contract_factory(*, body, actor, business_id, branch_id):
    return TaxRuleSetHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        tax_code=body["tax_code"],
        rate=str(body["rate"]),
        description=body.get("description", ""),
    )


@csrf_exempt
def tax_rules_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_read(list_tax_rules, request)


@csrf_exempt
def tax_rules_set_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_tax_rule_set,
        _tax_rule_set_contract_factory,
        request,
    )


# ---------------------------------------------------------------------------
# Business Profile Update endpoint
# ---------------------------------------------------------------------------

def _business_update_contract_factory(*, body, actor, business_id, branch_id):
    return BusinessUpdateHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        business_name=body.get("business_name"),
        default_currency=body.get("default_currency"),
        default_language=body.get("default_language"),
        address=body.get("address"),
        city=body.get("city"),
        country_code=body.get("country_code"),
        phone=body.get("phone"),
        email=body.get("email"),
        tax_id=body.get("tax_id"),
        logo_url=body.get("logo_url"),
    )


@csrf_exempt
def business_update_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_business_update,
        _business_update_contract_factory,
        request,
    )


# ---------------------------------------------------------------------------
# Custom Role Creation endpoint
# ---------------------------------------------------------------------------

def _role_create_contract_factory(*, body, actor, business_id, branch_id):
    permissions = body.get("permissions", [])
    if isinstance(permissions, list):
        permissions = tuple(permissions)
    return RoleCreateHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        role_name=body["role_name"],
        permissions=permissions,
    )


@csrf_exempt
def roles_create_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_role_create,
        _role_create_contract_factory,
        request,
    )


# ---------------------------------------------------------------------------
# Customer Profile CRUD endpoints
# ---------------------------------------------------------------------------

def _customer_create_contract_factory(*, body, actor, business_id, branch_id):
    return CustomerProfileCreateHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        display_name=body["display_name"],
        phone=body.get("phone", ""),
        email=body.get("email", ""),
        address=body.get("address", ""),
    )


def _customer_update_contract_factory(*, body, actor, business_id, branch_id):
    return CustomerProfileUpdateHttpRequest(
        business_id=business_id,
        branch_id=branch_id,
        actor=actor,
        customer_id=body["customer_id"],
        display_name=body.get("display_name"),
        phone=body.get("phone"),
        email=body.get("email"),
        address=body.get("address"),
    )


@csrf_exempt
def customers_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    return _dispatch_read(list_customers, request)


@csrf_exempt
def customers_create_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_customer_create,
        _customer_create_contract_factory,
        request,
    )


@csrf_exempt
def customers_update_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    return _dispatch_write(
        post_customer_update,
        _customer_update_contract_factory,
        request,
    )


# ---------------------------------------------------------------------------
# Data Migration ("Hamisha Data") endpoints
# ---------------------------------------------------------------------------

def _get_migration_service():
    """Lazy-load MigrationService singleton."""
    from core.migration.service import MigrationService
    if not hasattr(_get_migration_service, "_instance"):
        _get_migration_service._instance = MigrationService()
    return _get_migration_service._instance


@csrf_exempt
def migration_create_job_view(request: HttpRequest) -> JsonResponse:
    """POST /admin/migration/create-job — Create a new migration job."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        business_id = _parse_uuid(body["business_id"], "business_id")
        source_system = body["source_system"]
        entity_type = body["entity_type"]
        actor_id = body.get("actor_id", "")
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svc = _get_migration_service()
    try:
        job = svc.create_job(
            business_id=business_id,
            source_system=source_system,
            entity_type=entity_type,
            actor_id=actor_id,
        )
    except ValueError as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    return JsonResponse({
        "status": "ok",
        "job_id": str(job.job_id),
        "entity_type": job.entity_type,
        "source_system": job.source_system,
        "job_status": job.status,
    })


@csrf_exempt
def migration_upload_view(request: HttpRequest) -> JsonResponse:
    """POST /admin/migration/upload — Upload a batch of rows for import."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        job_id = _parse_uuid(body["job_id"], "job_id")
        business_id = _parse_uuid(body["business_id"], "business_id")
        entity_type = body["entity_type"]
        rows = body.get("rows", [])
        if not isinstance(rows, list) or not rows:
            raise ValueError("rows must be a non-empty list of objects.")
        actor_id = body.get("actor_id", "")
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    from core.migration.models import MigrationBatchRequest

    svc = _get_migration_service()
    try:
        batch_req = MigrationBatchRequest(
            job_id=job_id,
            business_id=business_id,
            entity_type=entity_type,
            rows=tuple(rows),
            actor_id=actor_id,
        )
        result = svc.import_batch(batch_req)
    except ValueError as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    return JsonResponse({
        "status": "ok",
        "job_id": str(result.job_id),
        "total": result.total,
        "imported": result.imported,
        "skipped": result.skipped,
        "errors": result.errors,
        "row_results": [
            {
                "row_index": r.row_index,
                "external_id": r.external_id,
                "status": r.status,
                "bos_id": r.bos_id,
                "error_message": r.error_message,
            }
            for r in result.row_results
        ],
    })


@csrf_exempt
def migration_complete_view(request: HttpRequest) -> JsonResponse:
    """POST /admin/migration/complete — Mark a migration job as completed."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        job_id = _parse_uuid(body["job_id"], "job_id")
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svc = _get_migration_service()
    ok = svc.complete_job(job_id)
    if not ok:
        return _json_error("INVALID_STATE", "Job not found or not in progress.", status=400)
    job = svc.get_job(job_id)
    return JsonResponse({
        "status": "ok",
        "job_id": str(job_id),
        "job_status": job.status if job else "COMPLETED",
        "total_rows": job.total_rows if job else 0,
        "imported_rows": job.imported_rows if job else 0,
        "skipped_rows": job.skipped_rows if job else 0,
        "error_rows": job.error_rows if job else 0,
    })


@csrf_exempt
def migration_cancel_view(request: HttpRequest) -> JsonResponse:
    """POST /admin/migration/cancel — Cancel a migration job."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        job_id = _parse_uuid(body["job_id"], "job_id")
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svc = _get_migration_service()
    ok = svc.cancel_job(job_id)
    if not ok:
        return _json_error("INVALID_STATE", "Job not found or already completed/cancelled.", status=400)
    return JsonResponse({"status": "ok", "job_id": str(job_id), "job_status": "CANCELLED"})


@csrf_exempt
def migration_jobs_list_view(request: HttpRequest) -> JsonResponse:
    """GET /admin/migration/jobs?business_id=... — List migration jobs."""
    if request.method != "GET":
        return _method_not_allowed()
    try:
        business_id_raw = request.GET.get("business_id")
        if not business_id_raw:
            raise ValueError("business_id is required.")
        business_id = _parse_uuid(business_id_raw, "business_id")
    except ValueError as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svc = _get_migration_service()
    jobs = svc.list_jobs(business_id)
    return JsonResponse({
        "status": "ok",
        "jobs": [
            {
                "job_id": str(j.job_id),
                "source_system": j.source_system,
                "entity_type": j.entity_type,
                "job_status": j.status,
                "total_rows": j.total_rows,
                "imported_rows": j.imported_rows,
                "skipped_rows": j.skipped_rows,
                "error_rows": j.error_rows,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            }
            for j in jobs
        ],
    })


@csrf_exempt
def migration_mappings_view(request: HttpRequest) -> JsonResponse:
    """GET /admin/migration/mappings?business_id=...&source_system=...&entity_type=..."""
    if request.method != "GET":
        return _method_not_allowed()
    try:
        business_id = _parse_uuid(request.GET.get("business_id", ""), "business_id")
        source_system = request.GET.get("source_system", "")
        entity_type = request.GET.get("entity_type", "")
        if not source_system:
            raise ValueError("source_system is required.")
        if not entity_type:
            raise ValueError("entity_type is required.")
    except ValueError as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svc = _get_migration_service()
    mappings = svc.list_mappings(business_id, source_system, entity_type)
    return JsonResponse({
        "status": "ok",
        "mappings": [
            {
                "external_id": m.external_id,
                "bos_id": str(m.bos_id),
                "entity_type": m.entity_type,
                "imported_at": m.imported_at.isoformat() if m.imported_at else None,
            }
            for m in mappings
        ],
    })


# ---------------------------------------------------------------------------
# SaaS — Engine Combos, Pricing, Trials, Promotions, Referrals, Resellers
# ---------------------------------------------------------------------------

def _get_saas_services():
    """Lazy-load SaaS service singletons with DB-backed persistence."""
    if not hasattr(_get_saas_services, "_loaded"):
        from core.saas.plans import PlanProjection, PlanManager
        from core.saas.rate_governance import RateGovernanceProjection, RateGovernanceService
        from core.saas.promotions import PromotionProjection, PromotionService
        from core.saas.referrals import ReferralProjection, ReferralService
        from core.saas.resellers import ResellerProjection, ResellerService
        from core.saas.subscriptions import SubscriptionProjection, SubscriptionManager

        plan_proj = PlanProjection()
        rate_proj = RateGovernanceProjection()
        promo_proj = PromotionProjection()
        referral_proj = ReferralProjection()
        reseller_proj = ResellerProjection()
        subscription_proj = SubscriptionProjection()

        # Load from DB into in-memory projections
        try:
            from core.saas.persistence import SaaSPersistenceStore
            SaaSPersistenceStore.load_plan_projection(plan_proj)
            SaaSPersistenceStore.load_rate_governance_projection(rate_proj)
            SaaSPersistenceStore.load_subscription_projection(subscription_proj)
            SaaSPersistenceStore.load_promotion_projection(promo_proj)
            SaaSPersistenceStore.load_referral_projection(referral_proj)
            SaaSPersistenceStore.load_reseller_projection(reseller_proj)
        except Exception:
            pass  # DB not ready yet (migrations pending); start with empty projections

        _get_saas_services._plan_manager = PlanManager(plan_proj)
        _get_saas_services._rate_service = RateGovernanceService(rate_proj)
        _get_saas_services._promo_service = PromotionService(promo_proj)
        _get_saas_services._referral_service = ReferralService(referral_proj)
        _get_saas_services._reseller_service = ResellerService(reseller_proj)
        _get_saas_services._sub_manager = SubscriptionManager(subscription_proj)
        _get_saas_services._plan_proj = plan_proj
        _get_saas_services._rate_proj = rate_proj
        _get_saas_services._promo_proj = promo_proj
        _get_saas_services._referral_proj = referral_proj
        _get_saas_services._reseller_proj = reseller_proj
        _get_saas_services._sub_proj = subscription_proj
        _get_saas_services._loaded = True
    return _get_saas_services


def _persist_saas(fn_name, **kwargs):
    """Persist SaaS state change to DB. Silently ignores if DB not ready."""
    try:
        from core.saas.persistence import SaaSPersistenceStore
        getattr(SaaSPersistenceStore, fn_name)(**kwargs)
    except Exception:
        pass


def _saas_rejection_response(result: dict) -> JsonResponse:
    """If result has 'rejected' key, return error response."""
    rej = result.get("rejected")
    if rej is None:
        return None
    return _json_error(rej.code, rej.message, status=400)


def _dt_from_body(body: dict, key: str = "issued_at"):
    """Parse datetime from body, defaulting to now."""
    from datetime import datetime, timezone
    raw = body.get(key)
    if raw is None:
        return datetime.now(tz=timezone.utc)
    if isinstance(raw, datetime):
        return raw
    return datetime.fromisoformat(str(raw))


# ── Engine Catalog ──────────────────────────────────────────

@csrf_exempt
def saas_register_engine_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/engines/register — Register an engine in the catalog."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.plans import RegisterEngineRequest
        req = RegisterEngineRequest(
            engine_key=body["engine_key"],
            display_name=body["display_name"],
            category=body.get("category", "PAID"),
            description=body.get("description", ""),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._plan_manager.register_engine(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_engine", engine_key=req.engine_key,
                  display_name=req.display_name, category=req.category,
                  description=req.description)
    return JsonResponse({"status": "ok", "engine_key": result["engine_key"]})


@csrf_exempt
def saas_engines_list_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/engines — List all registered engines."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    engines = svcs._plan_proj.list_engines()
    return JsonResponse({
        "status": "ok",
        "engines": [
            {
                "engine_key": e.engine_key,
                "display_name": e.display_name,
                "category": e.category.value,
                "description": e.description,
            }
            for e in engines
        ],
    })


# ── Combos ──────────────────────────────────────────────────

@csrf_exempt
def saas_define_combo_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/combos/define — Define a new engine combo."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.plans import DefineComboRequest
        req = DefineComboRequest(
            name=body["name"],
            slug=body["slug"],
            description=body.get("description", ""),
            business_model=body.get("business_model", "BOTH"),
            paid_engines=tuple(body.get("paid_engines", [])),
            max_branches=body.get("max_branches", 1),
            max_users=body.get("max_users", 3),
            max_api_calls_per_month=body.get("max_api_calls_per_month", 5000),
            max_documents_per_month=body.get("max_documents_per_month", 500),
            sort_order=body.get("sort_order", 0),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._plan_manager.define_combo(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_combo", combo_id=result["combo_id"],
                  name=req.name, slug=req.slug, description=req.description,
                  business_model=req.business_model,
                  paid_engines=list(req.paid_engines),
                  max_branches=req.max_branches, max_users=req.max_users,
                  max_api_calls_per_month=req.max_api_calls_per_month,
                  max_documents_per_month=req.max_documents_per_month,
                  sort_order=req.sort_order)
    return JsonResponse({
        "status": "ok",
        "combo_id": str(result["combo_id"]),
    })


@csrf_exempt
def saas_update_combo_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/combos/update — Update an existing combo."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.plans import UpdateComboRequest
        combo_id = _parse_uuid(body["combo_id"], "combo_id")
        req = UpdateComboRequest(
            combo_id=combo_id,
            name=body.get("name"),
            description=body.get("description"),
            paid_engines=tuple(body["paid_engines"]) if "paid_engines" in body else None,
            max_branches=body.get("max_branches"),
            max_users=body.get("max_users"),
            max_api_calls_per_month=body.get("max_api_calls_per_month"),
            max_documents_per_month=body.get("max_documents_per_month"),
            sort_order=body.get("sort_order"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    rejection = svcs._plan_manager.update_combo(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    # Persist updated combo state
    combo = svcs._plan_proj.get_combo(req.combo_id)
    if combo:
        _persist_saas("save_combo", combo_id=combo.combo_id,
                      name=combo.name, slug=combo.slug,
                      description=combo.description,
                      business_model=combo.business_model.value,
                      paid_engines=sorted(combo.paid_engines),
                      max_branches=combo.quota.max_branches,
                      max_users=combo.quota.max_users,
                      max_api_calls_per_month=combo.quota.max_api_calls_per_month,
                      max_documents_per_month=combo.quota.max_documents_per_month,
                      sort_order=combo.sort_order, status=combo.status.value)
    return JsonResponse({"status": "ok", "combo_id": str(body["combo_id"])})


@csrf_exempt
def saas_deactivate_combo_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/combos/deactivate — Deactivate a combo."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.plans import DeactivateComboRequest
        req = DeactivateComboRequest(
            combo_id=_parse_uuid(body["combo_id"], "combo_id"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
            reason=body.get("reason", ""),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    rejection = svcs._plan_manager.deactivate_combo(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    _persist_saas("deactivate_combo", combo_id=req.combo_id)
    return JsonResponse({"status": "ok"})


@csrf_exempt
def saas_combos_list_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/combos — List all active combos."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    combos = svcs._plan_proj.list_combos(active_only=True)
    return JsonResponse({
        "status": "ok",
        "combos": [
            {
                "combo_id": str(c.combo_id),
                "name": c.name,
                "slug": c.slug,
                "description": c.description,
                "business_model": c.business_model.value,
                "paid_engines": sorted(c.paid_engines),
                "all_engines": sorted(c.all_engines),
                "sort_order": c.sort_order,
                "quota": {
                    "max_branches": c.quota.max_branches,
                    "max_users": c.quota.max_users,
                    "max_api_calls_per_month": c.quota.max_api_calls_per_month,
                    "max_documents_per_month": c.quota.max_documents_per_month,
                },
            }
            for c in combos
        ],
    })


# ── Combo Rates / Pricing ──────────────────────────────────

@csrf_exempt
def saas_set_combo_rate_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/combos/set-rate — Set monthly price for a combo in a region."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from decimal import Decimal
        from core.saas.plans import SetComboRateRequest
        req = SetComboRateRequest(
            combo_id=_parse_uuid(body["combo_id"], "combo_id"),
            region_code=body["region_code"],
            currency=body["currency"],
            monthly_amount=Decimal(str(body["monthly_amount"])),
            effective_from=_dt_from_body(body, "effective_from") if "effective_from" in body else None,
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._plan_manager.set_combo_rate(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    rate = svcs._plan_proj.get_rate(req.combo_id, req.region_code)
    _persist_saas("save_combo_rate", combo_id=req.combo_id,
                  region_code=req.region_code, currency=req.currency,
                  monthly_amount=req.monthly_amount,
                  rate_version=rate.rate_version if rate else 1)
    return JsonResponse({"status": "ok"})


@csrf_exempt
def saas_pricing_catalog_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/pricing?region_code=KE&business_model=B2C — User-facing catalog."""
    if request.method != "GET":
        return _method_not_allowed()
    region_code = request.GET.get("region_code", "")
    if not region_code:
        return _json_error("INVALID_REQUEST", "region_code is required.", status=400)
    business_model = request.GET.get("business_model")

    svcs = _get_saas_services()
    catalog = svcs._plan_manager.get_pricing_catalog(
        region_code=region_code,
        business_model=business_model,
    )
    return JsonResponse({"status": "ok", "plans": catalog})


# ── Trial Policy & Agreements ──────────────────────────────

@csrf_exempt
def saas_set_trial_policy_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/trial-policy/set — Set platform-wide trial policy."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.rate_governance import SetTrialPolicyRequest
        req = SetTrialPolicyRequest(
            default_trial_days=body["default_trial_days"],
            max_trial_days=body["max_trial_days"],
            grace_period_days=body.get("grace_period_days", 7),
            rate_notice_days=body.get("rate_notice_days", 90),
            version=body.get("version", "v1"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    svcs._rate_service.set_trial_policy(req)
    _persist_saas("save_trial_policy",
                  default_trial_days=req.default_trial_days,
                  max_trial_days=req.max_trial_days,
                  grace_period_days=req.grace_period_days,
                  rate_notice_days=req.rate_notice_days,
                  version=req.version)
    return JsonResponse({"status": "ok"})


@csrf_exempt
def saas_trial_policy_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/trial-policy — Get current trial policy."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    policy = svcs._rate_proj.get_trial_policy()
    if policy is None:
        return JsonResponse({
            "status": "ok",
            "policy": {"default_trial_days": 180, "max_trial_days": 365,
                       "grace_period_days": 7, "rate_notice_days": 90, "version": "default"},
        })
    return JsonResponse({
        "status": "ok",
        "policy": {
            "default_trial_days": policy.default_trial_days,
            "max_trial_days": policy.max_trial_days,
            "grace_period_days": policy.grace_period_days,
            "rate_notice_days": policy.rate_notice_days,
            "version": policy.version,
        },
    })


@csrf_exempt
def saas_create_trial_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/trials/create — Create immutable trial agreement for a tenant."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from decimal import Decimal
        from core.saas.rate_governance import CreateTrialAgreementRequest
        req = CreateTrialAgreementRequest(
            business_id=_parse_uuid(body["business_id"], "business_id"),
            combo_id=_parse_uuid(body["combo_id"], "combo_id"),
            region_code=body["region_code"],
            currency=body["currency"],
            monthly_amount=Decimal(str(body["monthly_amount"])),
            rate_version=body.get("rate_version", 1),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
            referral_bonus_days=body.get("referral_bonus_days", 0),
            promo_code=body.get("promo_code", ""),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._rate_service.create_trial_agreement(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_trial_agreement",
                  agreement_id=result["agreement_id"],
                  business_id=req.business_id,
                  combo_id=req.combo_id,
                  region_code=req.region_code,
                  currency=result["currency"],
                  monthly_amount=result["monthly_amount"],
                  rate_version=req.rate_version,
                  trial_days=result["trial_days"],
                  bonus_days=req.referral_bonus_days,
                  total_trial_days=result["trial_days"],
                  trial_ends_at=result.get("trial_ends_at"),
                  billing_starts_at=result.get("billing_starts_at"))
    return JsonResponse({
        "status": "ok",
        "agreement_id": str(result["agreement_id"]),
        "trial_days": result["trial_days"],
        "trial_ends_at": result["trial_ends_at"].isoformat() if result.get("trial_ends_at") else None,
        "billing_starts_at": result["billing_starts_at"].isoformat() if result.get("billing_starts_at") else None,
        "monthly_amount": result["monthly_amount"],
        "currency": result["currency"],
    })


@csrf_exempt
def saas_extend_trial_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/trials/extend — Extend an active trial."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.rate_governance import ExtendTrialRequest
        req = ExtendTrialRequest(
            business_id=_parse_uuid(body["business_id"], "business_id"),
            extra_days=body["extra_days"],
            reason=body.get("reason", ""),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    rejection = svcs._rate_service.extend_trial(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    return JsonResponse({"status": "ok"})


@csrf_exempt
def saas_convert_trial_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/trials/convert — Mark trial as converted (user started paying)."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.rate_governance import ConvertTrialRequest
        req = ConvertTrialRequest(
            business_id=_parse_uuid(body["business_id"], "business_id"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    rejection = svcs._rate_service.convert_trial(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    return JsonResponse({"status": "ok"})


@csrf_exempt
def saas_trial_agreement_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/trials/agreement?business_id=... — Get trial agreement for a business."""
    if request.method != "GET":
        return _method_not_allowed()
    try:
        business_id = _parse_uuid(request.GET.get("business_id", ""), "business_id")
    except ValueError as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    agreement = svcs._rate_proj.get_agreement(business_id)
    if agreement is None:
        return _json_error("NOT_FOUND", "No trial agreement found.", status=404)
    return JsonResponse({
        "status": "ok",
        "agreement": {
            "agreement_id": str(agreement.agreement_id),
            "business_id": str(agreement.business_id),
            "combo_id": str(agreement.combo_id),
            "region_code": agreement.region_code,
            "trial_days": agreement.trial_days,
            "bonus_days": agreement.bonus_days,
            "trial_starts_at": agreement.trial_starts_at.isoformat(),
            "trial_ends_at": agreement.trial_ends_at.isoformat(),
            "billing_starts_at": agreement.billing_starts_at.isoformat(),
            "status": agreement.status.value,
            "rate_snapshot": {
                "currency": agreement.rate_snapshot.currency,
                "monthly_amount": str(agreement.rate_snapshot.monthly_amount),
                "rate_version": agreement.rate_snapshot.rate_version,
            },
            "terms_version": agreement.terms_version,
            "promo_code": agreement.promo_code,
        },
    })


# ── Rate Changes ───────────────────────────────────────────

@csrf_exempt
def saas_publish_rate_change_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/rates/publish-change — Publish a rate change (90-day notice)."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from decimal import Decimal
        from core.saas.rate_governance import PublishRateChangeRequest
        req = PublishRateChangeRequest(
            combo_id=_parse_uuid(body["combo_id"], "combo_id"),
            region_code=body["region_code"],
            old_amount=Decimal(str(body["old_amount"])),
            new_amount=Decimal(str(body["new_amount"])),
            old_version=body.get("old_version", 0),
            new_version=body.get("new_version", 0),
            currency=body["currency"],
            effective_from=_dt_from_body(body, "effective_from"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._rate_service.publish_rate_change(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    return JsonResponse({
        "status": "ok",
        "change_id": str(result["change_id"]),
        "tenants_to_notify": [str(t) for t in result.get("tenants_to_notify", [])],
    })


@csrf_exempt
def saas_effective_rate_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/rates/effective?business_id=... — Get current effective rate."""
    if request.method != "GET":
        return _method_not_allowed()
    try:
        business_id = _parse_uuid(request.GET.get("business_id", ""), "business_id")
    except ValueError as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    from datetime import datetime, timezone
    svcs = _get_saas_services()
    result = svcs._rate_service.get_effective_rate(business_id, datetime.now(tz=timezone.utc))
    if result is None:
        return _json_error("NOT_FOUND", "No agreement found.", status=404)
    return JsonResponse({"status": "ok", "rate": result})


# ── Promotions ─────────────────────────────────────────────

@csrf_exempt
def saas_create_promo_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/promos/create — Create a promotion."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from decimal import Decimal
        from core.saas.promotions import CreatePromoRequest
        req = CreatePromoRequest(
            promo_code=body["promo_code"],
            promo_type=body["promo_type"],
            description=body.get("description", ""),
            valid_from=_dt_from_body(body, "valid_from"),
            valid_until=_dt_from_body(body, "valid_until"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
            max_redemptions=body.get("max_redemptions", 0),
            region_codes=tuple(body.get("region_codes", [])),
            combo_ids=tuple(body.get("combo_ids", [])),
            discount_pct=Decimal(str(body.get("discount_pct", "0"))),
            discount_months=body.get("discount_months", 0),
            credit_amount=Decimal(str(body.get("credit_amount", "0"))),
            credit_currency=body.get("credit_currency", ""),
            credit_expires_months=body.get("credit_expires_months", 6),
            extra_trial_days=body.get("extra_trial_days", 0),
            bonus_engine=body.get("bonus_engine", ""),
            bonus_months=body.get("bonus_months", 0),
            bonus_after=body.get("bonus_after", "auto_remove"),
            bundle_engines=tuple(body.get("bundle_engines", [])),
            bundle_discount_pct=Decimal(str(body.get("bundle_discount_pct", "0"))),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._promo_service.create_promo(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_promotion", promo_id=result["promo_id"],
                  promo_code=req.promo_code, promo_type=req.promo_type,
                  description=req.description,
                  discount_pct=req.discount_pct if req.discount_pct else None,
                  credit_amount=req.credit_amount if req.credit_amount else None,
                  extra_trial_days=req.extra_trial_days or None,
                  bonus_engine=req.bonus_engine,
                  max_redemptions=req.max_redemptions,
                  valid_from=req.valid_from, valid_until=req.valid_until)
    return JsonResponse({
        "status": "ok",
        "promo_id": str(result["promo_id"]),
        "promo_code": result["promo_code"],
    })


@csrf_exempt
def saas_redeem_promo_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/promos/redeem — Redeem a promo code."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.promotions import RedeemPromoRequest
        req = RedeemPromoRequest(
            promo_code=body["promo_code"],
            business_id=_parse_uuid(body["business_id"], "business_id"),
            region_code=body["region_code"],
            combo_id=_parse_uuid(body["combo_id"], "combo_id"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._promo_service.redeem_promo(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_promo_redemption",
                  promo_id=result.get("promo_id"),
                  business_id=req.business_id,
                  redeemed_at=req.issued_at,
                  details=result.get("details", {}))
    return JsonResponse({
        "status": "ok",
        "redemption_id": str(result["redemption_id"]),
        "promo_type": result["promo_type"],
        "details": result["details"],
    })


@csrf_exempt
def saas_promos_list_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/promos — List active promotions."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    promos = svcs._promo_proj.list_active_promos()
    return JsonResponse({
        "status": "ok",
        "promotions": [
            {
                "promo_id": str(p.promo_id),
                "promo_code": p.promo_code,
                "promo_type": p.promo_type.value,
                "description": p.description,
                "valid_from": p.valid_from.isoformat() if p.valid_from else None,
                "valid_until": p.valid_until.isoformat() if p.valid_until else None,
                "max_redemptions": p.max_redemptions,
                "current_redemptions": p.current_redemptions,
                "status": p.status.value,
            }
            for p in promos
        ],
    })


# ── Referrals ("Alika Rafiki") ─────────────────────────────

@csrf_exempt
def saas_set_referral_policy_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/referrals/set-policy — Set referral program policy."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.referrals import SetReferralPolicyRequest
        req = SetReferralPolicyRequest(
            referrer_reward_days=body.get("referrer_reward_days", 30),
            referee_bonus_days=body.get("referee_bonus_days", 30),
            qualification_days=body.get("qualification_days", 30),
            qualification_min_transactions=body.get("qualification_min_transactions", 10),
            max_referrals_per_year=body.get("max_referrals_per_year", 12),
            champion_threshold=body.get("champion_threshold", 10),
            version=body.get("version", "v1"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    svcs._referral_service.set_policy(req)
    _persist_saas("save_referral_policy",
                  referrer_reward_days=req.referrer_reward_days,
                  referee_bonus_days=req.referee_bonus_days,
                  max_referrals_per_year=req.max_referrals_per_year,
                  qualification_days=req.qualification_days,
                  qualification_transactions=req.qualification_min_transactions)
    return JsonResponse({"status": "ok"})


@csrf_exempt
def saas_generate_referral_code_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/referrals/generate-code — Generate referral code for a tenant."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.referrals import GenerateReferralCodeRequest
        req = GenerateReferralCodeRequest(
            business_id=_parse_uuid(body["business_id"], "business_id"),
            business_name=body.get("business_name", "BOS"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._referral_service.generate_code(req)
    _persist_saas("save_referral_code",
                  business_id=req.business_id, code=result["code"])
    return JsonResponse({"status": "ok", "referral_code": result["code"]})


@csrf_exempt
def saas_submit_referral_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/referrals/submit — Submit a referral during signup."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.referrals import SubmitReferralRequest
        req = SubmitReferralRequest(
            referral_code=body["referral_code"],
            referee_business_id=_parse_uuid(body["referee_business_id"], "referee_business_id"),
            referee_phone=body.get("referee_phone", ""),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._referral_service.submit_referral(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_referral",
                  referral_id=result["referral_id"],
                  referrer_business_id=result.get("referrer_business_id"),
                  referee_business_id=req.referee_business_id,
                  status="PENDING",
                  submitted_at=req.issued_at)
    return JsonResponse({
        "status": "ok",
        "referral_id": str(result["referral_id"]),
        "referee_bonus_days": result["referee_bonus_days"],
    })


@csrf_exempt
def saas_qualify_referral_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/referrals/qualify — Mark referral as qualified (system call)."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.referrals import QualifyReferralRequest
        req = QualifyReferralRequest(
            referee_business_id=_parse_uuid(body["referee_business_id"], "referee_business_id"),
            actor_id=body.get("actor_id", "SYSTEM"),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._referral_service.qualify_referral(req)
    return JsonResponse({
        "status": "ok",
        "qualified": result["qualified"],
        "referrer_business_id": str(result.get("referrer_business_id", "")),
        "reward_days": result.get("reward_days", 0),
        "is_champion": result.get("is_champion", False),
    })


# ── Resellers ("Wakala wa BOS") ────────────────────────────

@csrf_exempt
def saas_register_reseller_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/register — Register a new reseller."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.resellers import RegisterResellerRequest
        req = RegisterResellerRequest(
            company_name=body["company_name"],
            contact_person=body.get("contact_person", ""),
            phone=body.get("phone", ""),
            email=body.get("email", ""),
            region_codes=tuple(body.get("region_codes", [])),
            payout_method=body.get("payout_method", "MPESA"),
            payout_phone=body.get("payout_phone", ""),
            payout_bank_name=body.get("payout_bank_name", ""),
            payout_account_number=body.get("payout_account_number", ""),
            payout_account_name=body.get("payout_account_name", ""),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._reseller_service.register_reseller(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_reseller",
                  reseller_id=result["reseller_id"],
                  company_name=req.company_name,
                  contact_name=req.contact_person,
                  contact_phone=req.phone,
                  contact_email=req.email,
                  tier=result["tier"],
                  commission_rate=result["commission_rate"],
                  payout_method=req.payout_method)
    return JsonResponse({
        "status": "ok",
        "reseller_id": str(result["reseller_id"]),
        "tier": result["tier"],
        "commission_rate": result["commission_rate"],
    })


@csrf_exempt
def saas_link_tenant_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/link-tenant — Link a tenant to a reseller."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.resellers import LinkTenantRequest
        req = LinkTenantRequest(
            reseller_id=_parse_uuid(body["reseller_id"], "reseller_id"),
            business_id=_parse_uuid(body["business_id"], "business_id"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._reseller_service.link_tenant(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_reseller_tenant_link",
                  reseller_id=req.reseller_id,
                  business_id=req.business_id,
                  linked_at=req.issued_at)
    return JsonResponse({
        "status": "ok",
        "new_tier": result["new_tier"],
        "active_tenant_count": result["active_tenant_count"],
    })


@csrf_exempt
def saas_accrue_commission_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/accrue-commission — Record commission for a paying tenant."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from decimal import Decimal
        from core.saas.resellers import AccrueCommissionRequest
        req = AccrueCommissionRequest(
            reseller_id=_parse_uuid(body["reseller_id"], "reseller_id"),
            business_id=_parse_uuid(body["business_id"], "business_id"),
            tenant_monthly_amount=Decimal(str(body["tenant_monthly_amount"])),
            currency=body["currency"],
            period=body["period"],
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._reseller_service.accrue_commission(req)
    if result.get("accrued"):
        _persist_saas("save_commission",
                      reseller_id=req.reseller_id,
                      business_id=req.business_id,
                      amount=result.get("commission", "0"),
                      currency=req.currency,
                      period=req.period,
                      entry_type="ACCRUAL")
    return JsonResponse({
        "status": "ok",
        "accrued": result["accrued"],
        "commission": result.get("commission", "0"),
        "rate": result.get("rate", "0"),
    })


@csrf_exempt
def saas_request_payout_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/request-payout — Request a commission payout."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from decimal import Decimal
        from core.saas.resellers import RequestPayoutRequest
        req = RequestPayoutRequest(
            reseller_id=_parse_uuid(body["reseller_id"], "reseller_id"),
            amount=Decimal(str(body["amount"])),
            currency=body["currency"],
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._reseller_service.request_payout(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_payout",
                  payout_id=result["payout_id"],
                  reseller_id=req.reseller_id,
                  amount=req.amount,
                  currency=req.currency,
                  status="PENDING",
                  requested_at=req.issued_at)
    return JsonResponse({
        "status": "ok",
        "payout_id": str(result["payout_id"]),
    })


@csrf_exempt
def saas_resellers_list_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/resellers — List active resellers."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    resellers = svcs._reseller_proj.list_resellers(active_only=True)
    return JsonResponse({
        "status": "ok",
        "resellers": [
            {
                "reseller_id": str(r.reseller_id),
                "company_name": r.company_name,
                "contact_person": r.contact_person,
                "tier": r.tier.value,
                "status": r.status.value,
                "commission_rate": str(r.commission_rate),
                "active_tenant_count": r.active_tenant_count,
                "total_commission_earned": str(r.total_commission_earned),
                "pending_commission": str(r.pending_commission),
                "region_codes": list(r.region_codes),
            }
            for r in resellers
        ],
    })


# ── Reseller Management (Platform Admin) ──────────────────

@csrf_exempt
def saas_reseller_detail_view(request: HttpRequest, reseller_id: str) -> JsonResponse:
    """GET /saas/resellers/<id> — Get single reseller detail."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    rid = _parse_uuid(reseller_id, "reseller_id")
    r = svcs._reseller_proj.get_reseller(rid)
    if r is None:
        return _json_error("RESELLER_NOT_FOUND", "Reseller not found.", status=404)
    territories = svcs._reseller_proj.get_territories_for_reseller(rid)
    commissions = svcs._reseller_proj.get_commissions(rid)
    payouts = svcs._reseller_proj.get_payouts(rid)
    links = svcs._reseller_proj.get_tenant_links(rid)
    # Check if regional manager
    mgr_regions = [
        m.region_code for m in svcs._reseller_proj.list_regional_managers()
        if m.reseller_id == rid
    ]
    return JsonResponse({
        "status": "ok",
        "reseller": {
            "reseller_id": str(r.reseller_id),
            "company_name": r.company_name,
            "contact_person": r.contact_person,
            "phone": r.phone,
            "email": r.email,
            "region_codes": list(r.region_codes),
            "tier": r.tier.value,
            "status": r.status.value,
            "commission_rate": str(r.commission_rate),
            "effective_commission_rate": str(svcs._reseller_proj.get_effective_commission_rate(rid)),
            "payout_method": r.payout_method,
            "active_tenant_count": r.active_tenant_count,
            "total_commission_earned": str(r.total_commission_earned),
            "total_commission_paid": str(r.total_commission_paid),
            "pending_commission": str(r.pending_commission),
            "is_regional_manager": len(mgr_regions) > 0,
            "managed_regions": mgr_regions,
            "territories": [
                {"territory_id": str(t.territory_id), "territory_name": t.territory_name,
                 "region_code": t.region_code}
                for t in territories
            ],
            "tenant_count": len([lnk for lnk in links if lnk.is_active]),
            "tenants": [
                {"business_id": str(lnk.business_id), "is_active": lnk.is_active,
                 "linked_at": str(lnk.linked_at) if lnk.linked_at else None}
                for lnk in links
            ],
            "commission_history": [
                {"amount": str(c.amount), "currency": c.currency, "period": c.period,
                 "is_clawback": c.is_clawback}
                for c in commissions[-20:]  # last 20
            ],
            "payouts": [
                {"payout_id": str(p.payout_id), "amount": str(p.amount),
                 "currency": p.currency, "status": p.status.value}
                for p in payouts
            ],
        },
    })


@csrf_exempt
def saas_update_reseller_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/update — Update reseller profile."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.resellers import UpdateResellerRequest
        req = UpdateResellerRequest(
            reseller_id=_parse_uuid(body["reseller_id"], "reseller_id"),
            company_name=body.get("company_name"),
            contact_person=body.get("contact_person"),
            phone=body.get("phone"),
            email=body.get("email"),
            region_codes=tuple(body["region_codes"]) if "region_codes" in body else None,
            payout_method=body.get("payout_method"),
            payout_phone=body.get("payout_phone"),
            payout_bank_name=body.get("payout_bank_name"),
            payout_account_number=body.get("payout_account_number"),
            payout_account_name=body.get("payout_account_name"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.update_reseller(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    # Re-persist updated reseller
    r = svcs._reseller_proj.get_reseller(req.reseller_id)
    if r:
        _persist_saas("save_reseller",
                      reseller_id=r.reseller_id, company_name=r.company_name,
                      contact_name=r.contact_person, contact_phone=r.phone,
                      contact_email=r.email, tier=r.tier.value,
                      commission_rate=str(r.commission_rate),
                      payout_method=r.payout_method)
    return JsonResponse({"status": "ok"})


@csrf_exempt
def saas_suspend_reseller_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/suspend — Suspend a reseller."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        rid = _parse_uuid(body["reseller_id"], "reseller_id")
        reason = body.get("reason", "")
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.suspend_reseller(
        rid, reason, body.get("actor_id", ""), _dt_from_body(body))
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_reseller", reseller_id=rid, company_name="",
                  status="DEACTIVATED")
    return JsonResponse({"status": "ok", "reseller_status": result["status"]})


@csrf_exempt
def saas_reinstate_reseller_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/reinstate — Reinstate a suspended reseller."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        rid = _parse_uuid(body["reseller_id"], "reseller_id")
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.reinstate_reseller(
        rid, body.get("actor_id", ""), _dt_from_body(body))
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_reseller", reseller_id=rid, company_name="",
                  status="ACTIVE")
    return JsonResponse({"status": "ok", "reseller_status": result["status"]})


@csrf_exempt
def saas_terminate_reseller_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/terminate — Permanently terminate a reseller."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        rid = _parse_uuid(body["reseller_id"], "reseller_id")
        reason = body.get("reason", "")
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.terminate_reseller(
        rid, reason, body.get("actor_id", ""), _dt_from_body(body))
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    return JsonResponse({"status": "ok", "reseller_status": result["status"]})


@csrf_exempt
def saas_approve_payout_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/approve-payout — Approve a pending payout."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.resellers import ApprovePayoutRequest
        req = ApprovePayoutRequest(
            payout_id=_parse_uuid(body["payout_id"], "payout_id"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.approve_payout(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    payout = svcs._reseller_proj.get_payout(req.payout_id)
    if payout:
        _persist_saas("save_payout", payout_id=req.payout_id,
                      reseller_id=payout.reseller_id, amount=payout.amount,
                      currency=payout.currency, status="COMPLETED",
                      requested_at=payout.requested_at,
                      completed_at=req.issued_at)
    return JsonResponse({"status": "ok", "payout_status": result["status"]})


@csrf_exempt
def saas_reject_payout_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/reject-payout — Reject a pending payout."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.resellers import RejectPayoutRequest
        req = RejectPayoutRequest(
            payout_id=_parse_uuid(body["payout_id"], "payout_id"),
            reason=body.get("reason", ""),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.reject_payout(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    payout = svcs._reseller_proj.get_payout(req.payout_id)
    if payout:
        _persist_saas("save_payout", payout_id=req.payout_id,
                      reseller_id=payout.reseller_id, amount=payout.amount,
                      currency=payout.currency, status="FAILED",
                      requested_at=payout.requested_at)
    return JsonResponse({"status": "ok", "payout_status": result["status"],
                         "reason": result.get("reason", "")})


@csrf_exempt
def saas_payouts_list_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/resellers/payouts — List all payouts (admin view)."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    status_filter = request.GET.get("status")
    payouts = svcs._reseller_proj.list_all_payouts(status=status_filter)
    return JsonResponse({
        "status": "ok",
        "payouts": [
            {
                "payout_id": str(p.payout_id),
                "reseller_id": str(p.reseller_id),
                "amount": str(p.amount),
                "currency": p.currency,
                "status": p.status.value,
                "method": p.method,
                "requested_at": str(p.requested_at) if p.requested_at else None,
                "completed_at": str(p.completed_at) if p.completed_at else None,
                "rejection_reason": p.rejection_reason,
            }
            for p in payouts
        ],
    })


# ── Regional Management ───────────────────────────────────

@csrf_exempt
def saas_appoint_regional_manager_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/appoint-manager — Appoint a reseller as regional manager."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from decimal import Decimal
        from core.saas.resellers import AppointRegionalManagerRequest, REGIONAL_MANAGER_BONUS_RATE
        req = AppointRegionalManagerRequest(
            reseller_id=_parse_uuid(body["reseller_id"], "reseller_id"),
            region_code=body["region_code"],
            bonus_rate=Decimal(str(body.get("bonus_rate", REGIONAL_MANAGER_BONUS_RATE))),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.appoint_regional_manager(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_regional_manager",
                  region_code=req.region_code,
                  reseller_id=req.reseller_id,
                  bonus_rate=req.bonus_rate,
                  appointed_at=req.issued_at)
    return JsonResponse({
        "status": "ok",
        "region_code": result["region_code"],
        "reseller_id": result["reseller_id"],
        "bonus_rate": result["bonus_rate"],
    })


@csrf_exempt
def saas_remove_regional_manager_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/remove-manager — Remove regional manager."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.resellers import RemoveRegionalManagerRequest
        req = RemoveRegionalManagerRequest(
            region_code=body["region_code"],
            reason=body.get("reason", ""),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.remove_regional_manager(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("remove_regional_manager", region_code=req.region_code)
    return JsonResponse({
        "status": "ok",
        "region_code": result["region_code"],
        "removed_reseller_id": result["removed_reseller_id"],
    })


@csrf_exempt
def saas_region_resellers_view(request: HttpRequest, region_code: str) -> JsonResponse:
    """GET /saas/regions/<code>/resellers — List resellers in a region."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    resellers = svcs._reseller_proj.list_resellers_by_region(region_code)
    return JsonResponse({
        "status": "ok",
        "region_code": region_code,
        "resellers": [
            {
                "reseller_id": str(r.reseller_id),
                "company_name": r.company_name,
                "tier": r.tier.value,
                "status": r.status.value,
                "commission_rate": str(r.commission_rate),
                "effective_rate": str(svcs._reseller_proj.get_effective_commission_rate(r.reseller_id)),
                "active_tenant_count": r.active_tenant_count,
                "pending_commission": str(r.pending_commission),
            }
            for r in resellers
        ],
    })


@csrf_exempt
def saas_region_performance_view(request: HttpRequest, region_code: str) -> JsonResponse:
    """GET /saas/regions/<code>/performance — Regional performance metrics."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    period = request.GET.get("period", "")
    if not period:
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        period = now.strftime("%Y-%m")
    result = svcs._reseller_service.get_regional_performance(region_code, period)
    return JsonResponse({"status": "ok", **result})


@csrf_exempt
def saas_region_summary_view(request: HttpRequest, region_code: str) -> JsonResponse:
    """GET /saas/regions/<code>/summary — Full region summary."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    result = svcs._reseller_service.get_region_summary(region_code)
    return JsonResponse({"status": "ok", **result})


@csrf_exempt
def saas_assign_territory_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/assign-territory — Assign territory to reseller."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.resellers import AssignTerritoryRequest
        req = AssignTerritoryRequest(
            reseller_id=_parse_uuid(body["reseller_id"], "reseller_id"),
            region_code=body["region_code"],
            territory_name=body["territory_name"],
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.assign_territory(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_territory",
                  territory_id=result["territory_id"],
                  region_code=req.region_code,
                  territory_name=req.territory_name,
                  reseller_id=req.reseller_id,
                  assigned_at=req.issued_at)
    return JsonResponse({
        "status": "ok",
        "territory_id": result["territory_id"],
    })


@csrf_exempt
def saas_revoke_territory_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/revoke-territory — Revoke territory from reseller."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.resellers import RevokeTerritoryRequest
        req = RevokeTerritoryRequest(
            territory_id=_parse_uuid(body["territory_id"], "territory_id"),
            reason=body.get("reason", ""),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.revoke_territory(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("revoke_territory", territory_id=req.territory_id)
    return JsonResponse({
        "status": "ok",
        "territory_id": result["territory_id"],
    })


@csrf_exempt
def saas_transfer_reseller_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/resellers/transfer — Transfer reseller between regions."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.resellers import TransferResellerRequest
        req = TransferResellerRequest(
            reseller_id=_parse_uuid(body["reseller_id"], "reseller_id"),
            from_region_code=body["from_region_code"],
            to_region_code=body["to_region_code"],
            reason=body.get("reason", ""),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.transfer_reseller(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    # Update persisted reseller region_codes
    r = svcs._reseller_proj.get_reseller(req.reseller_id)
    if r:
        _persist_saas("save_reseller", reseller_id=r.reseller_id,
                      company_name=r.company_name, contact_name=r.contact_person,
                      contact_phone=r.phone, contact_email=r.email)
    return JsonResponse({
        "status": "ok",
        "reseller_id": result["reseller_id"],
        "from_region_code": result["from_region_code"],
        "to_region_code": result["to_region_code"],
    })


@csrf_exempt
def saas_set_commission_override_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/set-commission-override — Set regional commission override."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from decimal import Decimal
        from core.saas.resellers import SetRegionalCommissionOverrideRequest
        req = SetRegionalCommissionOverrideRequest(
            region_code=body["region_code"],
            override_rate=Decimal(str(body["override_rate"])),
            reason=body.get("reason", ""),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.set_regional_commission_override(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_commission_override",
                  region_code=req.region_code,
                  override_rate=req.override_rate,
                  reason=req.reason,
                  set_at=req.issued_at)
    return JsonResponse({
        "status": "ok",
        "region_code": result["region_code"],
        "override_rate": result["override_rate"],
    })


@csrf_exempt
def saas_set_regional_target_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/set-target — Set monthly target for a region."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from decimal import Decimal
        from core.saas.resellers import SetRegionalTargetRequest
        req = SetRegionalTargetRequest(
            region_code=body["region_code"],
            period=body["period"],
            target_tenant_count=int(body.get("target_tenant_count", 0)),
            target_revenue=Decimal(str(body.get("target_revenue", "0"))),
            currency=body.get("currency", ""),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)
    svcs = _get_saas_services()
    result = svcs._reseller_service.set_regional_target(req)
    _persist_saas("save_regional_target",
                  region_code=req.region_code, period=req.period,
                  target_tenant_count=req.target_tenant_count,
                  target_revenue=req.target_revenue,
                  currency=req.currency, set_at=req.issued_at)
    return JsonResponse({
        "status": "ok",
        "region_code": result["region_code"],
        "period": result["period"],
    })


@csrf_exempt
def saas_regional_managers_list_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/regions/managers — List all regional managers."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    managers = svcs._reseller_proj.list_regional_managers()
    result = []
    for m in managers:
        r = svcs._reseller_proj.get_reseller(m.reseller_id)
        result.append({
            "region_code": m.region_code,
            "reseller_id": str(m.reseller_id),
            "company_name": r.company_name if r else "",
            "bonus_rate": str(m.bonus_rate),
            "appointed_at": str(m.appointed_at) if m.appointed_at else None,
        })
    return JsonResponse({"status": "ok", "managers": result})


@csrf_exempt
def saas_region_territories_view(request: HttpRequest, region_code: str) -> JsonResponse:
    """GET /saas/regions/<code>/territories — List territories in a region."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    territories = svcs._reseller_proj.get_territories_for_region(
        region_code, active_only=False)
    return JsonResponse({
        "status": "ok",
        "region_code": region_code,
        "territories": [
            {
                "territory_id": str(t.territory_id),
                "territory_name": t.territory_name,
                "reseller_id": str(t.reseller_id),
                "is_active": t.is_active,
                "assigned_at": str(t.assigned_at) if t.assigned_at else None,
            }
            for t in territories
        ],
    })


@csrf_exempt
def saas_commission_overrides_list_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/regions/commission-overrides — List all commission overrides."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    overrides = svcs._reseller_proj.list_commission_overrides()
    return JsonResponse({
        "status": "ok",
        "overrides": [
            {
                "region_code": o.region_code,
                "override_rate": str(o.override_rate),
                "reason": o.reason,
                "set_at": str(o.set_at) if o.set_at else None,
            }
            for o in overrides
        ],
    })


@csrf_exempt
def saas_regional_targets_list_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/regions/targets — List regional targets."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_saas_services()
    region_code = request.GET.get("region_code")
    targets = svcs._reseller_proj.list_regional_targets(region_code)
    return JsonResponse({
        "status": "ok",
        "targets": [
            {
                "region_code": t.region_code,
                "period": t.period,
                "target_tenant_count": t.target_tenant_count,
                "target_revenue": str(t.target_revenue),
                "currency": t.currency,
                "set_at": str(t.set_at) if t.set_at else None,
            }
            for t in targets
        ],
    })


# ── Subscriptions ──────────────────────────────────────────

@csrf_exempt
def saas_start_trial_sub_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/subscriptions/start-trial — Start trial subscription."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.subscriptions import StartTrialRequest
        req = StartTrialRequest(
            business_id=_parse_uuid(body["business_id"], "business_id"),
            combo_id=_parse_uuid(body["combo_id"], "combo_id"),
            trial_agreement_id=_parse_uuid(body["trial_agreement_id"], "trial_agreement_id"),
            billing_starts_at=_dt_from_body(body, "billing_starts_at"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._sub_manager.start_trial(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    _persist_saas("save_subscription",
                  subscription_id=result["subscription_id"],
                  business_id=req.business_id,
                  combo_id=req.combo_id,
                  trial_agreement_id=req.trial_agreement_id,
                  status="TRIAL",
                  billing_starts_at=req.billing_starts_at,
                  activated_at=req.issued_at)
    return JsonResponse({
        "status": "ok",
        "subscription_id": str(result["subscription_id"]),
        "subscription_status": result["status"],
    })


@csrf_exempt
def saas_activate_sub_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/subscriptions/activate — Activate subscription (trial→paying)."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.subscriptions import ActivateSubscriptionRequest
        combo_id_raw = body.get("combo_id")
        req = ActivateSubscriptionRequest(
            business_id=_parse_uuid(body["business_id"], "business_id"),
            plan_id=_parse_uuid(body.get("plan_id", body.get("combo_id", "")), "plan_id"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
            combo_id=_parse_uuid(combo_id_raw, "combo_id") if combo_id_raw else None,
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    result = svcs._sub_manager.activate(req)
    rej = _saas_rejection_response(result)
    if rej:
        return rej
    sub = svcs._sub_proj.get_subscription(req.business_id)
    if sub:
        _persist_saas("save_subscription",
                      subscription_id=sub.subscription_id,
                      business_id=sub.business_id,
                      combo_id=sub.combo_id,
                      trial_agreement_id=sub.trial_agreement_id,
                      status=sub.status.value,
                      billing_starts_at=sub.billing_starts_at,
                      activated_at=sub.activated_at)
    return JsonResponse({
        "status": "ok",
        "subscription_id": str(result["subscription_id"]),
    })


@csrf_exempt
def saas_cancel_sub_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/subscriptions/cancel — Cancel a subscription."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.subscriptions import CancelSubscriptionRequest
        req = CancelSubscriptionRequest(
            business_id=_parse_uuid(body["business_id"], "business_id"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
            reason=body.get("reason", ""),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    rejection = svcs._sub_manager.cancel(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    sub = svcs._sub_proj.get_subscription(req.business_id)
    if sub:
        _persist_saas("save_subscription",
                      subscription_id=sub.subscription_id,
                      business_id=sub.business_id,
                      combo_id=sub.combo_id,
                      trial_agreement_id=sub.trial_agreement_id,
                      status=sub.status.value,
                      billing_starts_at=sub.billing_starts_at,
                      activated_at=sub.activated_at,
                      cancelled_at=sub.cancelled_at)
    return JsonResponse({"status": "ok"})


@csrf_exempt
def saas_subscription_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/subscriptions?business_id=... — Get subscription for a business."""
    if request.method != "GET":
        return _method_not_allowed()
    try:
        business_id = _parse_uuid(request.GET.get("business_id", ""), "business_id")
    except ValueError as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    sub = svcs._sub_proj.get_subscription(business_id)
    if sub is None:
        return _json_error("NOT_FOUND", "No subscription found.", status=404)
    return JsonResponse({
        "status": "ok",
        "subscription": {
            "subscription_id": str(sub.subscription_id),
            "business_id": str(sub.business_id),
            "combo_id": str(sub.combo_id) if sub.combo_id else None,
            "status": sub.status.value,
            "activated_at": sub.activated_at.isoformat() if sub.activated_at else None,
            "billing_starts_at": sub.billing_starts_at.isoformat() if sub.billing_starts_at else None,
            "renewal_count": sub.renewal_count,
        },
    })


@csrf_exempt
def saas_change_combo_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/subscriptions/change-combo — Switch to a different combo."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.subscriptions import ChangeComboRequest
        req = ChangeComboRequest(
            business_id=_parse_uuid(body["business_id"], "business_id"),
            new_combo_id=_parse_uuid(body["new_combo_id"], "new_combo_id"),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    rejection = svcs._sub_manager.change_combo(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    sub = svcs._sub_proj.get_subscription(req.business_id)
    if sub:
        _persist_saas("save_subscription",
                      subscription_id=sub.subscription_id,
                      business_id=sub.business_id,
                      combo_id=sub.combo_id,
                      trial_agreement_id=sub.trial_agreement_id,
                      status=sub.status.value,
                      billing_starts_at=sub.billing_starts_at,
                      activated_at=sub.activated_at)
    return JsonResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Tenant Plan Builder — self-service plan selection for tenants
# ---------------------------------------------------------------------------

@csrf_exempt
def saas_tenant_available_plans_view(request: HttpRequest) -> JsonResponse:
    """
    GET /saas/tenant/available-plans?region_code=KE&business_model=B2C
    Tenant-facing: browse available combos with pricing for their region.
    """
    if request.method != "GET":
        return _method_not_allowed()
    region_code = request.GET.get("region_code", "")
    if not region_code:
        return _json_error("INVALID_REQUEST", "region_code is required.", status=400)
    business_model = request.GET.get("business_model")

    svcs = _get_saas_services()
    catalog = svcs._plan_manager.get_pricing_catalog(
        region_code=region_code,
        business_model=business_model,
    )

    # Get trial policy for display
    trial_policy = svcs._rate_proj.get_trial_policy()
    trial_days = trial_policy.default_trial_days if trial_policy else 180

    return JsonResponse({
        "status": "ok",
        "region_code": region_code,
        "trial_days": trial_days,
        "plans": catalog,
    })


@csrf_exempt
def saas_tenant_my_plan_view(request: HttpRequest) -> JsonResponse:
    """
    GET /saas/tenant/my-plan?business_id=...
    Tenant-facing: view current subscription, combo details, and trial status.
    """
    if request.method != "GET":
        return _method_not_allowed()
    try:
        business_id = _parse_uuid(request.GET.get("business_id", ""), "business_id")
    except ValueError as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()
    sub = svcs._sub_proj.get_subscription(business_id)
    if sub is None:
        return JsonResponse({
            "status": "ok",
            "has_subscription": False,
            "subscription": None,
            "combo": None,
            "trial": None,
        })

    # Resolve combo details
    combo_data = None
    if sub.combo_id:
        combo = svcs._plan_proj.get_combo(sub.combo_id)
        if combo:
            combo_data = {
                "combo_id": str(combo.combo_id),
                "name": combo.name,
                "slug": combo.slug,
                "description": combo.description,
                "business_model": combo.business_model.value,
                "paid_engines": sorted(combo.paid_engines),
                "all_engines": sorted(combo.all_engines),
                "quota": {
                    "max_branches": combo.quota.max_branches,
                    "max_users": combo.quota.max_users,
                    "max_api_calls_per_month": combo.quota.max_api_calls_per_month,
                    "max_documents_per_month": combo.quota.max_documents_per_month,
                },
            }

    # Resolve trial agreement
    trial_data = None
    agreement = svcs._rate_proj.get_agreement(business_id)
    if agreement:
        trial_data = {
            "agreement_id": str(agreement.agreement_id),
            "trial_days": agreement.trial_days,
            "bonus_days": agreement.bonus_days,
            "trial_starts_at": agreement.trial_starts_at.isoformat(),
            "trial_ends_at": agreement.trial_ends_at.isoformat(),
            "billing_starts_at": agreement.billing_starts_at.isoformat(),
            "status": agreement.status.value,
            "rate_snapshot": {
                "currency": agreement.rate_snapshot.currency,
                "monthly_amount": str(agreement.rate_snapshot.monthly_amount),
            },
        }

    return JsonResponse({
        "status": "ok",
        "has_subscription": True,
        "subscription": {
            "subscription_id": str(sub.subscription_id),
            "status": sub.status.value,
            "activated_at": sub.activated_at.isoformat() if sub.activated_at else None,
            "billing_starts_at": sub.billing_starts_at.isoformat() if sub.billing_starts_at else None,
            "renewal_count": sub.renewal_count,
        },
        "combo": combo_data,
        "trial": trial_data,
    })


@csrf_exempt
def saas_tenant_select_plan_view(request: HttpRequest) -> JsonResponse:
    """
    POST /saas/tenant/select-plan
    Tenant self-service: select a combo → create trial agreement → start subscription.

    Body: {
        "business_id": "...",
        "combo_slug": "bos-duka",  (or "combo_id")
        "region_code": "KE",
        "referral_code": ""  (optional)
    }
    """
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        business_id = _parse_uuid(body["business_id"], "business_id")
        region_code = body["region_code"]
        referral_code = body.get("referral_code", "")
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_saas_services()

    # Resolve combo by slug or ID
    combo = None
    if "combo_slug" in body:
        combo = svcs._plan_proj.get_combo_by_slug(body["combo_slug"])
    elif "combo_id" in body:
        combo = svcs._plan_proj.get_combo(_parse_uuid(body["combo_id"], "combo_id"))
    if combo is None:
        return _json_error("COMBO_NOT_FOUND", "No active combo found.", status=400)

    # Get rate for region
    rate = svcs._plan_proj.get_rate(combo.combo_id, region_code)
    if rate is None:
        return _json_error("NO_RATE_FOR_REGION",
                           f"Combo '{combo.name}' has no pricing for region {region_code}.",
                           status=400)

    # Check if already subscribed
    existing = svcs._sub_proj.get_subscription(business_id)
    if existing and existing.status.value in ("TRIAL", "ACTIVE"):
        return _json_error("SUBSCRIPTION_EXISTS",
                           "Business already has an active or trial subscription.",
                           status=400)

    from datetime import datetime, timezone
    from decimal import Decimal
    now = datetime.now(tz=timezone.utc)

    # Handle referral bonus days
    referral_bonus_days = 0
    if referral_code:
        try:
            from core.saas.referrals import SubmitReferralRequest
            ref_result = svcs._referral_service.submit_referral(SubmitReferralRequest(
                referral_code=referral_code,
                referee_business_id=business_id,
                referee_phone="",
                actor_id=str(business_id),
                issued_at=now,
            ))
            if "rejected" not in ref_result:
                referral_bonus_days = ref_result.get("referee_bonus_days", 0)
                _persist_saas("save_referral",
                              referral_id=ref_result["referral_id"],
                              referrer_business_id=ref_result.get("referrer_business_id"),
                              referee_business_id=business_id,
                              status="PENDING",
                              submitted_at=now)
        except Exception:
            pass  # referral failure should not block signup

    # Create trial agreement
    from core.saas.rate_governance import CreateTrialAgreementRequest
    trial_result = svcs._rate_service.create_trial_agreement(CreateTrialAgreementRequest(
        business_id=business_id,
        combo_id=combo.combo_id,
        region_code=region_code,
        currency=rate.currency,
        monthly_amount=rate.monthly_amount,
        rate_version=rate.rate_version,
        actor_id=str(business_id),
        issued_at=now,
        referral_bonus_days=referral_bonus_days,
    ))
    if "rejected" in trial_result:
        rej = trial_result["rejected"]
        return _json_error(rej.code, rej.message, status=400)

    agreement_id = trial_result["agreement_id"]
    _persist_saas("save_trial_agreement",
                  agreement_id=agreement_id,
                  business_id=business_id,
                  combo_id=combo.combo_id,
                  region_code=region_code,
                  currency=trial_result["currency"],
                  monthly_amount=trial_result["monthly_amount"],
                  rate_version=rate.rate_version,
                  trial_days=trial_result["trial_days"],
                  bonus_days=referral_bonus_days,
                  total_trial_days=trial_result["trial_days"],
                  trial_ends_at=trial_result.get("trial_ends_at"),
                  billing_starts_at=trial_result.get("billing_starts_at"))

    # Start trial subscription
    from core.saas.subscriptions import StartTrialRequest
    sub_result = svcs._sub_manager.start_trial(StartTrialRequest(
        business_id=business_id,
        combo_id=combo.combo_id,
        trial_agreement_id=agreement_id,
        billing_starts_at=trial_result.get("billing_starts_at", now),
        actor_id=str(business_id),
        issued_at=now,
    ))
    if "rejected" in sub_result:
        rej = sub_result["rejected"]
        return _json_error(rej.code, rej.message, status=400)

    _persist_saas("save_subscription",
                  subscription_id=sub_result["subscription_id"],
                  business_id=business_id,
                  combo_id=combo.combo_id,
                  trial_agreement_id=agreement_id,
                  status="TRIAL",
                  billing_starts_at=trial_result.get("billing_starts_at"),
                  activated_at=now)

    return JsonResponse({
        "status": "ok",
        "subscription_id": str(sub_result["subscription_id"]),
        "subscription_status": "TRIAL",
        "combo": {
            "combo_id": str(combo.combo_id),
            "name": combo.name,
            "slug": combo.slug,
            "all_engines": sorted(combo.all_engines),
        },
        "trial": {
            "agreement_id": str(agreement_id),
            "trial_days": trial_result["trial_days"],
            "trial_ends_at": trial_result["trial_ends_at"].isoformat() if trial_result.get("trial_ends_at") else None,
            "billing_starts_at": trial_result["billing_starts_at"].isoformat() if trial_result.get("billing_starts_at") else None,
        },
        "pricing": {
            "currency": rate.currency,
            "monthly_amount": str(rate.monthly_amount),
        },
        "referral_bonus_days": referral_bonus_days,
    })


# ---------------------------------------------------------------------------
# SaaS — Service-Based Pricing (Regions, Services, Capacity, Reductions)
# ---------------------------------------------------------------------------

def _get_pricing_projection():
    """Lazy-load the ServicePricingProjection singleton."""
    if not hasattr(_get_pricing_projection, "_proj"):
        from core.saas.pricing import ServicePricingProjection
        proj = ServicePricingProjection()
        # Load from DB
        try:
            from core.saas.persistence import SaaSPersistenceStore
            SaaSPersistenceStore.load_pricing_projection(proj)
        except Exception:
            pass
        _get_pricing_projection._proj = proj
    return _get_pricing_projection._proj


def _persist_pricing(fn_name, **kwargs):
    """Persist pricing state change to DB."""
    try:
        from core.saas.persistence import SaaSPersistenceStore
        getattr(SaaSPersistenceStore, fn_name)(**kwargs)
    except Exception:
        pass


# ── Regions (Nchi / Mikoa) — Full Platform Admin ──────────────


def _region_to_dict(r) -> dict:
    """Serialize a RegionEntry to dict (full representation)."""
    return {
        "code": r.code,
        "name": r.name,
        "currency": r.currency,
        "status": getattr(r, "status", "ACTIVE"),
        # Tax & compliance
        "tax_name": r.tax_name,
        "vat_rate": r.vat_rate,
        "digital_tax_rate": r.digital_tax_rate,
        "b2b_reverse_charge": r.b2b_reverse_charge,
        "registration_required": r.registration_required,
        "regulatory_body": getattr(r, "regulatory_body", ""),
        "business_license_required": getattr(r, "business_license_required", True),
        "data_residency_required": getattr(r, "data_residency_required", False),
        # Financial
        "min_payout_amount": str(getattr(r, "min_payout_amount", 0)),
        "payout_currency": getattr(r, "payout_currency", "") or r.currency,
        "payment_channels": [
            {
                "channel_key": ch.channel_key,
                "display_name": ch.display_name,
                "provider": ch.provider,
                "channel_type": ch.channel_type,
                "is_active": ch.is_active,
                "min_amount": str(ch.min_amount),
                "max_amount": str(ch.max_amount),
                "settlement_delay_days": ch.settlement_delay_days,
            }
            for ch in getattr(r, "payment_channels", {}).values()
        ],
        "settlement_accounts": [
            {
                "bank_name": sa.bank_name,
                "account_name": sa.account_name,
                "account_number": sa.account_number,
                "branch_code": sa.branch_code,
                "swift_code": sa.swift_code,
                "currency": sa.currency,
                "is_primary": sa.is_primary,
            }
            for sa in getattr(r, "settlement_accounts", [])
        ],
        # Operations
        "default_language": getattr(r, "default_language", "en"),
        "timezone": getattr(r, "timezone", "Africa/Nairobi"),
        "support_phone": getattr(r, "support_phone", ""),
        "support_email": getattr(r, "support_email", ""),
        "support_hours": getattr(r, "support_hours", ""),
        "country_calling_code": getattr(r, "country_calling_code", ""),
        "phone_format": getattr(r, "phone_format", ""),
        # Launch
        "launched_at": str(r.launched_at) if getattr(r, "launched_at", None) else None,
        "suspended_at": str(r.suspended_at) if getattr(r, "suspended_at", None) else None,
        "sunset_at": str(r.sunset_at) if getattr(r, "sunset_at", None) else None,
        "pilot_tenant_limit": getattr(r, "pilot_tenant_limit", 0),
        "launch_notes": getattr(r, "launch_notes", ""),
        "is_active": r.is_active,
    }


def _persist_region_full(region):
    """Persist a full region state to DB."""
    _persist_pricing("save_region",
                     code=region.code, name=region.name, currency=region.currency,
                     status=getattr(region, "status", "ACTIVE"),
                     tax_name=region.tax_name, vat_rate=region.vat_rate,
                     digital_tax_rate=region.digital_tax_rate,
                     b2b_reverse_charge=region.b2b_reverse_charge,
                     registration_required=region.registration_required,
                     regulatory_body=getattr(region, "regulatory_body", ""),
                     business_license_required=getattr(region, "business_license_required", True),
                     data_residency_required=getattr(region, "data_residency_required", False),
                     min_payout_amount=getattr(region, "min_payout_amount", 0),
                     payout_currency=getattr(region, "payout_currency", ""),
                     default_language=getattr(region, "default_language", "en"),
                     timezone=getattr(region, "timezone", "Africa/Nairobi"),
                     support_phone=getattr(region, "support_phone", ""),
                     support_email=getattr(region, "support_email", ""),
                     support_hours=getattr(region, "support_hours", ""),
                     country_calling_code=getattr(region, "country_calling_code", ""),
                     phone_format=getattr(region, "phone_format", ""),
                     launched_at=getattr(region, "launched_at", None),
                     suspended_at=getattr(region, "suspended_at", None),
                     sunset_at=getattr(region, "sunset_at", None),
                     pilot_tenant_limit=getattr(region, "pilot_tenant_limit", 0),
                     launch_notes=getattr(region, "launch_notes", ""),
                     is_active=region.is_active)


@csrf_exempt
def saas_regions_list_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/regions — List all regions with full operational detail."""
    if request.method != "GET":
        return _method_not_allowed()
    proj = _get_pricing_projection()
    status_filter = request.GET.get("status")
    if status_filter:
        regions = proj.list_regions_by_status(status_filter.upper())
    else:
        regions = proj.list_regions()
    return JsonResponse({
        "status": "ok",
        "data": {"regions": [_region_to_dict(r) for r in regions]},
    })


@csrf_exempt
def saas_region_detail_view(request: HttpRequest, region_code: str) -> JsonResponse:
    """GET /saas/regions/<code>/detail — Full region detail with channels, settlement, resellers."""
    if request.method != "GET":
        return _method_not_allowed()
    proj = _get_pricing_projection()
    region = proj.get_region(region_code.upper())
    if not region:
        return _json_error("NOT_FOUND", f"Region {region_code} not found", status=404)
    return JsonResponse({"status": "ok", "region": _region_to_dict(region)})


@csrf_exempt
def saas_regions_add_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/add — Create new region (starts as DRAFT)."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        code = body["code"].strip().upper()
        name = body["name"].strip()
        currency = body["currency"].strip().upper()
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    if len(code) != 2:
        return _json_error("INVALID_REQUEST",
                           "Country code must be 2 characters (ISO 3166-1 alpha-2)")

    proj = _get_pricing_projection()
    if proj.get_region(code):
        return _json_error("DUPLICATE", f"Region {code} already exists")

    payload = {
        "code": code,
        "name": name,
        "currency": currency,
        "status": body.get("status", "DRAFT"),
        # Tax
        "tax_name": body.get("tax_name", "VAT"),
        "vat_rate": float(body.get("vat_rate", 0)),
        "digital_tax_rate": float(body.get("digital_tax_rate", 0)),
        "b2b_reverse_charge": bool(body.get("b2b_reverse_charge", False)),
        "registration_required": bool(body.get("registration_required", True)),
        "regulatory_body": body.get("regulatory_body", ""),
        "business_license_required": bool(body.get("business_license_required", True)),
        "data_residency_required": bool(body.get("data_residency_required", False)),
        # Financial
        "min_payout_amount": body.get("min_payout_amount", "0"),
        "payout_currency": body.get("payout_currency", ""),
        # Operations
        "default_language": body.get("default_language", "en"),
        "timezone": body.get("timezone", "Africa/Nairobi"),
        "support_phone": body.get("support_phone", ""),
        "support_email": body.get("support_email", ""),
        "support_hours": body.get("support_hours", ""),
        "country_calling_code": body.get("country_calling_code", ""),
        "phone_format": body.get("phone_format", ""),
        # Launch
        "pilot_tenant_limit": int(body.get("pilot_tenant_limit", 0)),
        "launch_notes": body.get("launch_notes", ""),
        "is_active": body.get("status", "DRAFT") in ("ACTIVE", "PILOT"),
    }
    proj.apply("saas.region.added.v1", payload)
    region = proj.get_region(code)
    _persist_region_full(region)

    return JsonResponse({"status": "ok", "code": code})


@csrf_exempt
def saas_regions_update_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/update — Update region fields (partial update)."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        code = body["code"].strip().upper()
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    proj = _get_pricing_projection()
    if not proj.get_region(code):
        return _json_error("NOT_FOUND", f"Region {code} not found", status=404)

    payload = {"code": code}
    updatable_fields = (
        "name", "currency", "tax_name", "vat_rate", "digital_tax_rate",
        "b2b_reverse_charge", "registration_required", "is_active",
        "regulatory_body", "business_license_required", "data_residency_required",
        "min_payout_amount", "payout_currency",
        "default_language", "timezone", "support_phone", "support_email",
        "support_hours", "country_calling_code", "phone_format",
        "pilot_tenant_limit", "launch_notes",
    )
    for key in updatable_fields:
        if key in body:
            payload[key] = body[key]

    proj.apply("saas.region.updated.v1", payload)
    region = proj.get_region(code)
    _persist_region_full(region)

    return JsonResponse({"status": "ok", "code": code})


@csrf_exempt
def saas_region_launch_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/launch — Launch a region (DRAFT→PILOT or DRAFT→ACTIVE)."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        code = body["code"].strip().upper()
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    proj = _get_pricing_projection()
    region = proj.get_region(code)
    if not region:
        return _json_error("NOT_FOUND", f"Region {code} not found", status=404)
    if region.status not in ("DRAFT",):
        return _json_error("INVALID_STATE",
                           f"Region is {region.status}, can only launch from DRAFT")

    # Validate readiness: must have at least one payment channel
    channels = proj.get_region_payment_channels(code)
    if not channels:
        return _json_error("NOT_READY",
                           "Region must have at least one payment channel before launch")

    target = body.get("target_status", "PILOT")
    if target not in ("PILOT", "ACTIVE"):
        return _json_error("INVALID_REQUEST", "target_status must be PILOT or ACTIVE")

    payload = {
        "code": code,
        "target_status": target,
        "pilot_tenant_limit": int(body.get("pilot_tenant_limit", 50)),
        "issued_at": _dt_from_body(body),
    }
    proj.apply("saas.region.launched.v1", payload)
    region = proj.get_region(code)
    _persist_region_full(region)

    return JsonResponse({
        "status": "ok", "code": code, "region_status": region.status,
    })


@csrf_exempt
def saas_region_suspend_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/suspend — Suspend a region (no new signups)."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        code = body["code"].strip().upper()
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    proj = _get_pricing_projection()
    region = proj.get_region(code)
    if not region:
        return _json_error("NOT_FOUND", f"Region {code} not found", status=404)
    if region.status not in ("ACTIVE", "PILOT"):
        return _json_error("INVALID_STATE",
                           f"Region is {region.status}, can only suspend ACTIVE/PILOT")

    proj.apply("saas.region.suspended.v1", {
        "code": code, "reason": body.get("reason", ""),
        "issued_at": _dt_from_body(body),
    })
    region = proj.get_region(code)
    _persist_region_full(region)

    return JsonResponse({
        "status": "ok", "code": code, "region_status": region.status,
    })


@csrf_exempt
def saas_region_reactivate_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/reactivate — Reactivate a suspended region."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        code = body["code"].strip().upper()
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    proj = _get_pricing_projection()
    region = proj.get_region(code)
    if not region:
        return _json_error("NOT_FOUND", f"Region {code} not found", status=404)
    if region.status != "SUSPENDED":
        return _json_error("INVALID_STATE",
                           f"Region is {region.status}, can only reactivate SUSPENDED")

    proj.apply("saas.region.reactivated.v1", {
        "code": code, "issued_at": _dt_from_body(body),
    })
    region = proj.get_region(code)
    _persist_region_full(region)

    return JsonResponse({
        "status": "ok", "code": code, "region_status": region.status,
    })


@csrf_exempt
def saas_region_sunset_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/sunset — Begin winding down a region."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        code = body["code"].strip().upper()
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    proj = _get_pricing_projection()
    region = proj.get_region(code)
    if not region:
        return _json_error("NOT_FOUND", f"Region {code} not found", status=404)

    proj.apply("saas.region.sunset.v1", {
        "code": code, "reason": body.get("reason", ""),
        "issued_at": _dt_from_body(body),
    })
    region = proj.get_region(code)
    _persist_region_full(region)

    return JsonResponse({
        "status": "ok", "code": code, "region_status": region.status,
    })


@csrf_exempt
def saas_region_set_payment_channel_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/set-payment-channel — Add or update a payment channel for a region."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        region_code = body["region_code"].strip().upper()
        channel_key = body["channel_key"].strip()
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    proj = _get_pricing_projection()
    if not proj.get_region(region_code):
        return _json_error("NOT_FOUND", f"Region {region_code} not found", status=404)

    payload = {
        "region_code": region_code,
        "channel_key": channel_key,
        "display_name": body.get("display_name", channel_key),
        "provider": body.get("provider", ""),
        "channel_type": body.get("channel_type", "MOBILE_MONEY"),
        "is_active": bool(body.get("is_active", True)),
        "config": body.get("config", {}),
        "min_amount": str(body.get("min_amount", "0")),
        "max_amount": str(body.get("max_amount", "999999999")),
        "settlement_delay_days": int(body.get("settlement_delay_days", 1)),
    }
    proj.apply("saas.region.payment_channel_set.v1", payload)
    _persist_pricing("save_payment_channel", **payload)

    return JsonResponse({
        "status": "ok", "region_code": region_code, "channel_key": channel_key,
    })


@csrf_exempt
def saas_region_remove_payment_channel_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/remove-payment-channel — Remove a payment channel."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        region_code = body["region_code"].strip().upper()
        channel_key = body["channel_key"].strip()
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    proj = _get_pricing_projection()
    if not proj.get_region(region_code):
        return _json_error("NOT_FOUND", f"Region {region_code} not found", status=404)

    proj.apply("saas.region.payment_channel_removed.v1", {
        "region_code": region_code, "channel_key": channel_key,
    })
    _persist_pricing("remove_payment_channel",
                     region_code=region_code, channel_key=channel_key)

    return JsonResponse({
        "status": "ok", "region_code": region_code, "channel_key": channel_key,
    })


@csrf_exempt
def saas_region_payment_channels_view(request: HttpRequest, region_code: str) -> JsonResponse:
    """GET /saas/regions/<code>/payment-channels — List payment channels for a region."""
    if request.method != "GET":
        return _method_not_allowed()
    proj = _get_pricing_projection()
    code = region_code.upper()
    region = proj.get_region(code)
    if not region:
        return _json_error("NOT_FOUND", f"Region {code} not found", status=404)
    channels = proj.get_region_payment_channels(code)
    return JsonResponse({
        "status": "ok",
        "region_code": code,
        "channels": [
            {
                "channel_key": ch.channel_key,
                "display_name": ch.display_name,
                "provider": ch.provider,
                "channel_type": ch.channel_type,
                "is_active": ch.is_active,
                "min_amount": str(ch.min_amount),
                "max_amount": str(ch.max_amount),
                "settlement_delay_days": ch.settlement_delay_days,
            }
            for ch in channels
        ],
    })


@csrf_exempt
def saas_region_set_settlement_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/regions/set-settlement — Set settlement bank account for a region."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        region_code = body["region_code"].strip().upper()
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    proj = _get_pricing_projection()
    region = proj.get_region(region_code)
    if not region:
        return _json_error("NOT_FOUND", f"Region {region_code} not found", status=404)

    payload = {
        "region_code": region_code,
        "bank_name": body.get("bank_name", ""),
        "account_name": body.get("account_name", ""),
        "account_number": body.get("account_number", ""),
        "branch_code": body.get("branch_code", ""),
        "swift_code": body.get("swift_code", ""),
        "currency": body.get("currency", region.currency),
        "is_primary": bool(body.get("is_primary", True)),
    }
    proj.apply("saas.region.settlement_set.v1", payload)
    _persist_pricing("save_settlement_account", **payload)

    return JsonResponse({
        "status": "ok", "region_code": region_code,
        "bank_name": payload["bank_name"],
    })


@csrf_exempt
def saas_region_settlement_accounts_view(request: HttpRequest, region_code: str) -> JsonResponse:
    """GET /saas/regions/<code>/settlement-accounts — List settlement accounts."""
    if request.method != "GET":
        return _method_not_allowed()
    proj = _get_pricing_projection()
    code = region_code.upper()
    region = proj.get_region(code)
    if not region:
        return _json_error("NOT_FOUND", f"Region {code} not found", status=404)
    accounts = proj.get_region_settlement_accounts(code)
    return JsonResponse({
        "status": "ok",
        "region_code": code,
        "settlement_accounts": [
            {
                "bank_name": sa.bank_name,
                "account_name": sa.account_name,
                "account_number": sa.account_number,
                "branch_code": sa.branch_code,
                "swift_code": sa.swift_code,
                "currency": sa.currency,
                "is_primary": sa.is_primary,
            }
            for sa in accounts
        ],
    })


@csrf_exempt
def saas_region_dashboard_view(request: HttpRequest, region_code: str) -> JsonResponse:
    """GET /saas/regions/<code>/dashboard — Full operational dashboard for a region."""
    if request.method != "GET":
        return _method_not_allowed()
    proj = _get_pricing_projection()
    code = region_code.upper()
    region = proj.get_region(code)
    if not region:
        return _json_error("NOT_FOUND", f"Region {code} not found", status=404)

    channels = proj.get_region_payment_channels(code)
    accounts = proj.get_region_settlement_accounts(code)

    # Get reseller stats from reseller projection
    svcs = _get_saas_services()
    resellers = svcs._reseller_proj.list_resellers_by_region(code)
    mgr = svcs._reseller_proj.get_regional_manager(code)
    territories = svcs._reseller_proj.get_territories_for_region(code)
    override = svcs._reseller_proj.get_commission_override(code)

    active_channels = [ch for ch in channels if ch.is_active]

    return JsonResponse({
        "status": "ok",
        "region_code": code,
        "region_name": region.name,
        "region_status": region.status,
        "currency": region.currency,
        # Financial readiness
        "financial": {
            "payment_channels_total": len(channels),
            "payment_channels_active": len(active_channels),
            "channel_types": list({ch.channel_type for ch in active_channels}),
            "settlement_accounts": len(accounts),
            "has_primary_settlement": any(sa.is_primary for sa in accounts),
            "min_payout_amount": str(region.min_payout_amount),
        },
        # Tax configuration
        "tax": {
            "tax_name": region.tax_name,
            "vat_rate": region.vat_rate,
            "digital_tax_rate": region.digital_tax_rate,
            "regulatory_body": region.regulatory_body,
        },
        # Reseller network
        "reseller_network": {
            "total_resellers": len(resellers),
            "active_resellers": len([r for r in resellers if r.status.value == "ACTIVE"]),
            "total_tenants": sum(r.active_tenant_count for r in resellers),
            "regional_manager": {
                "reseller_id": str(mgr.reseller_id),
                "bonus_rate": str(mgr.bonus_rate),
            } if mgr else None,
            "territories": len(territories),
            "commission_override": str(override.override_rate) if override else None,
        },
        # Operations
        "operations": {
            "timezone": region.timezone,
            "default_language": region.default_language,
            "support_phone": region.support_phone,
            "support_email": region.support_email,
            "support_hours": region.support_hours,
        },
        # Launch info
        "launch": {
            "launched_at": str(region.launched_at) if region.launched_at else None,
            "pilot_tenant_limit": region.pilot_tenant_limit,
            "launch_notes": region.launch_notes,
        },
    })


# ── Services (Huduma) ──────────────────────────────────────


@csrf_exempt
def saas_services_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    proj = _get_pricing_projection()
    return JsonResponse({
        "status": "ok",
        "data": {
            "rates": proj.get_service_rates(),
            "active": proj.get_service_active_map(),
        },
    })


@csrf_exempt
def saas_services_set_rate_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        service_key = body["service_key"]
        region_code = body["region_code"]
        currency = body.get("currency", "USD")
        monthly_amount = body["monthly_amount"]
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    proj = _get_pricing_projection()
    payload = {
        "service_key": service_key,
        "region_code": region_code,
        "currency": currency,
        "monthly_amount": monthly_amount,
    }
    proj.apply("saas.service.rate_set.v1", payload)
    _persist_pricing("save_service_rate", **payload)

    return JsonResponse({"status": "ok", "service_key": service_key, "region_code": region_code})


@csrf_exempt
def saas_services_toggle_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        service_key = body["service_key"]
        active = bool(body["active"])
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    proj = _get_pricing_projection()
    payload = {"service_key": service_key, "active": active}
    proj.apply("saas.service.toggled.v1", payload)
    _persist_pricing("save_service_toggle", service_key=service_key, active=active)

    return JsonResponse({"status": "ok", "service_key": service_key, "active": active})


# ── Capacity Tiers ──────────────────────────────────────────


@csrf_exempt
def saas_capacity_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    proj = _get_pricing_projection()
    return JsonResponse({"status": "ok", "data": proj.get_capacity_rates()})


@csrf_exempt
def saas_capacity_set_rate_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        dimension = body["dimension"]
        tier_key = body["tier_key"]
        region_code = body["region_code"]
        currency = body.get("currency", "USD")
        monthly_amount = body["monthly_amount"]
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    proj = _get_pricing_projection()
    payload = {
        "dimension": dimension,
        "tier_key": tier_key,
        "region_code": region_code,
        "currency": currency,
        "monthly_amount": monthly_amount,
    }
    proj.apply("saas.capacity.rate_set.v1", payload)
    _persist_pricing("save_capacity_rate", **payload)

    return JsonResponse({"status": "ok", "dimension": dimension, "tier_key": tier_key, "region_code": region_code})


# ── Multi-Service Reduction ─────────────────────────────────


@csrf_exempt
def saas_reductions_list_view(request: HttpRequest) -> JsonResponse:
    if request.method != "GET":
        return _method_not_allowed()
    proj = _get_pricing_projection()
    return JsonResponse({"status": "ok", "data": proj.get_reduction_rates()})


@csrf_exempt
def saas_reductions_set_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        region_code = body["region_code"]
        service_count = int(body["service_count"])
        reduction_pct = float(body["reduction_pct"])
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    if not (2 <= service_count <= 5):
        return _json_error("INVALID_REQUEST", "service_count must be 2-5")
    if not (0 <= reduction_pct <= 50):
        return _json_error("INVALID_REQUEST", "reduction_pct must be 0-50")

    proj = _get_pricing_projection()
    payload = {
        "region_code": region_code,
        "service_count": service_count,
        "reduction_pct": reduction_pct,
    }
    proj.apply("saas.reduction.rate_set.v1", payload)
    _persist_pricing("save_reduction_rate", **payload)

    return JsonResponse({"status": "ok", "region_code": region_code, "service_count": service_count})


# ── Price Calculator ────────────────────────────────────────


@csrf_exempt
def saas_calculate_price_view(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        region_code = body["region_code"]
        services = body["services"]
        capacity = body.get("capacity", {})
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc))

    proj = _get_pricing_projection()
    result = proj.calculate_price(region_code, services, capacity)
    if result is None:
        return _json_error("NOT_FOUND", f"Region {region_code} not found", status=404)

    return JsonResponse({
        "status": "ok",
        "data": {
            "region_code": result.region_code,
            "currency": result.currency,
            "service_lines": result.service_lines,
            "service_total": float(result.service_total),
            "reduction_pct": float(result.reduction_pct),
            "reduction_amount": float(result.reduction_amount),
            "service_after_reduction": float(result.service_after_reduction),
            "capacity_lines": result.capacity_lines,
            "capacity_total": float(result.capacity_total),
            "monthly_total": float(result.monthly_total),
        },
    })


# ═══════════════════════════════════════════════════════════════
# COMPLIANCE PACKS & TENANT COMPLIANCE
# ═══════════════════════════════════════════════════════════════

def _get_compliance_services():
    """Lazy-load compliance service singletons."""
    if not hasattr(_get_compliance_services, "_loaded"):
        from core.saas.compliance_packs import CompliancePackProjection, CompliancePackService
        from core.saas.tenant_compliance import TenantComplianceProjection, TenantComplianceService

        pack_proj = CompliancePackProjection()
        tenant_proj = TenantComplianceProjection()

        _get_compliance_services._pack_service = CompliancePackService(pack_proj)
        _get_compliance_services._tenant_service = TenantComplianceService(tenant_proj)
        _get_compliance_services._pack_proj = pack_proj
        _get_compliance_services._tenant_proj = tenant_proj
        _get_compliance_services._loaded = True
    return _get_compliance_services


def _serialize_compliance_pack(pack) -> dict:
    """Serialize a CompliancePackVersion to JSON-safe dict."""
    return {
        "region_code": pack.region_code,
        "version": pack.version,
        "pack_ref": pack.pack_ref,
        "display_name": pack.display_name,
        "effective_date": pack.effective_date.isoformat() if pack.effective_date else None,
        "published_at": pack.published_at.isoformat() if pack.published_at else None,
        "published_by": pack.published_by,
        "tax_rules": [
            {
                "tax_code": t.tax_code,
                "rate": float(t.rate),
                "description": t.description,
                "applies_to": list(t.applies_to),
                "is_compound": t.is_compound,
            }
            for t in pack.tax_rules
        ],
        "receipt_requirements": {
            "require_sequential_number": pack.receipt_requirements.require_sequential_number,
            "require_tax_number": pack.receipt_requirements.require_tax_number,
            "require_customer_tax_id": pack.receipt_requirements.require_customer_tax_id,
            "require_digital_signature": pack.receipt_requirements.require_digital_signature,
            "require_qr_code": pack.receipt_requirements.require_qr_code,
            "number_prefix_format": pack.receipt_requirements.number_prefix_format,
        },
        "data_retention": {
            "financial_records_years": pack.data_retention.financial_records_years,
            "audit_log_years": pack.data_retention.audit_log_years,
            "personal_data_years": pack.data_retention.personal_data_years,
            "region_law_reference": pack.data_retention.region_law_reference,
        },
        "required_invoice_fields": list(pack.required_invoice_fields),
        "optional_invoice_fields": list(pack.optional_invoice_fields),
        "change_summary": pack.change_summary,
        "deprecated": pack.deprecated,
        "deprecated_at": pack.deprecated_at.isoformat() if pack.deprecated_at else None,
        "superseded_by": pack.superseded_by,
    }


def _serialize_tenant_profile(profile) -> dict:
    """Serialize a TenantComplianceProfile to JSON-safe dict."""
    return {
        "profile_id": profile.profile_id,
        "business_id": profile.business_id,
        "country_code": profile.country_code,
        "customer_type": profile.customer_type,
        "legal_name": profile.legal_name,
        "trade_name": profile.trade_name,
        "tax_id": profile.tax_id,
        "company_registration_number": profile.company_registration_number,
        "physical_address": profile.physical_address,
        "city": profile.city,
        "contact_email": profile.contact_email,
        "contact_phone": profile.contact_phone,
        "state": profile.state,
        "tax_id_verified": profile.tax_id_verified,
        "company_reg_verified": profile.company_reg_verified,
        "address_verified": profile.address_verified,
        "eligible_for_billing": profile.eligible_for_billing,
        "rejection_reason": profile.rejection_reason,
        "reviewer_id": profile.reviewer_id,
        "review_notes": profile.review_notes,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "verified_at": profile.verified_at.isoformat() if profile.verified_at else None,
        "pack_ref": profile.pack_ref,
    }


# ── Compliance Packs ──────────────────────────────────────────

def saas_compliance_packs_list_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/compliance-packs?region_code= — List pack versions for a region."""
    if request.method != "GET":
        return _method_not_allowed()
    region_code = request.GET.get("region_code", "")
    if not region_code:
        return _json_error("INVALID_REQUEST", "region_code is required.", status=400)

    svcs = _get_compliance_services()
    packs = svcs._pack_proj.list_versions(
        region_code, include_deprecated=request.GET.get("include_deprecated") == "true"
    )
    return JsonResponse({
        "status": "ok",
        "packs": [_serialize_compliance_pack(p) for p in packs],
    })


def saas_compliance_pack_latest_view(request: HttpRequest, region_code: str) -> JsonResponse:
    """GET /saas/compliance-packs/<region_code>/latest — Get latest active pack."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_compliance_services()
    pack = svcs._pack_proj.get_latest_version(region_code)
    if pack is None:
        return _json_error("NOT_FOUND", f"No compliance pack found for region {region_code}.", status=404)
    return JsonResponse({"status": "ok", "pack": _serialize_compliance_pack(pack)})


def saas_compliance_pack_detail_view(request: HttpRequest, region_code: str, version: int) -> JsonResponse:
    """GET /saas/compliance-packs/<region_code>/<version> — Get specific pack version."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_compliance_services()
    pack = svcs._pack_proj.get_pack(region_code, version)
    if pack is None:
        return _json_error("NOT_FOUND", f"Pack {region_code}:v{version} not found.", status=404)
    return JsonResponse({"status": "ok", "pack": _serialize_compliance_pack(pack)})


@csrf_exempt
def saas_publish_compliance_pack_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/compliance-packs/publish — Publish a new compliance pack version."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.compliance_packs import PublishCompliancePackRequest
        req = PublishCompliancePackRequest(
            region_code=body["region_code"],
            display_name=body["display_name"],
            effective_date=_dt_from_body(body, "effective_date"),
            tax_rules=tuple(body.get("tax_rules", [])),
            receipt_requirements=body.get("receipt_requirements", {}),
            data_retention=body.get("data_retention", {}),
            required_invoice_fields=tuple(body.get("required_invoice_fields", [])),
            optional_invoice_fields=tuple(body.get("optional_invoice_fields", [])),
            change_summary=body.get("change_summary", ""),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_compliance_services()
    result = svcs._pack_service.publish_pack(req)
    return JsonResponse({
        "status": "ok",
        "pack_ref": result["pack_ref"],
        "version": result["version"],
    })


@csrf_exempt
def saas_deprecate_compliance_pack_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/compliance-packs/deprecate — Deprecate a compliance pack version."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.compliance_packs import DeprecateCompliancePackRequest
        req = DeprecateCompliancePackRequest(
            region_code=body["region_code"],
            version=int(body["version"]),
            superseded_by_version=int(body["superseded_by_version"]),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_compliance_services()
    rejection = svcs._pack_service.deprecate_pack(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    return JsonResponse({"status": "ok"})


@csrf_exempt
def saas_pin_tenant_pack_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/compliance-packs/pin-tenant — Pin a tenant to a specific pack version."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.compliance_packs import PinTenantPackRequest
        req = PinTenantPackRequest(
            tenant_id=body["tenant_id"],
            region_code=body["region_code"],
            version=int(body["version"]),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_compliance_services()
    rejection = svcs._pack_service.pin_tenant_to_pack(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    return JsonResponse({"status": "ok"})


@csrf_exempt
def saas_upgrade_tenant_pack_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/compliance-packs/upgrade-tenant — Upgrade a tenant to a newer pack."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.compliance_packs import UpgradeTenantPackRequest
        req = UpgradeTenantPackRequest(
            tenant_id=body["tenant_id"],
            region_code=body["region_code"],
            to_version=int(body["to_version"]),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_compliance_services()
    rejection = svcs._pack_service.upgrade_tenant_pack(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    return JsonResponse({"status": "ok"})


# ── Tenant Compliance ─────────────────────────────────────────

@csrf_exempt
def saas_set_country_policy_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/compliance/set-country-policy — Set a country compliance policy."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.tenant_compliance import SetCountryPolicyRequest
        req = SetCountryPolicyRequest(
            country_code=body["country_code"],
            country_name=body.get("country_name", ""),
            b2b_allowed=body.get("b2b_allowed", True),
            b2c_allowed=body.get("b2c_allowed", True),
            vat_registration_required=body.get("vat_registration_required", False),
            company_registration_required=body.get("company_registration_required", False),
            requires_tax_id=body.get("requires_tax_id", False),
            requires_physical_address=body.get("requires_physical_address", False),
            default_trial_days=body.get("default_trial_days", 180),
            grace_period_days=body.get("grace_period_days", 30),
            manual_review_required=body.get("manual_review_required", False),
            active=body.get("active", True),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_compliance_services()
    result = svcs._tenant_service.set_country_policy(req)
    return JsonResponse({"status": "ok", "country_code": result["country_code"]})


def saas_country_policies_list_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/compliance/country-policies — List all country compliance policies."""
    if request.method != "GET":
        return _method_not_allowed()
    svcs = _get_compliance_services()
    policies = svcs._tenant_proj.list_policies()
    return JsonResponse({
        "status": "ok",
        "policies": [
            {
                "country_code": p.country_code,
                "country_name": p.country_name,
                "b2b_allowed": p.b2b_allowed,
                "b2c_allowed": p.b2c_allowed,
                "vat_registration_required": p.vat_registration_required,
                "company_registration_required": p.company_registration_required,
                "requires_tax_id": p.requires_tax_id,
                "requires_physical_address": p.requires_physical_address,
                "default_trial_days": p.default_trial_days,
                "grace_period_days": p.grace_period_days,
                "manual_review_required": p.manual_review_required,
                "active": p.active,
                "version": p.version,
            }
            for p in policies
        ],
    })


@csrf_exempt
def saas_submit_compliance_profile_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/compliance/submit-profile — Submit a tenant compliance profile."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.tenant_compliance import SubmitComplianceProfileRequest
        req = SubmitComplianceProfileRequest(
            business_id=body["business_id"],
            country_code=body["country_code"],
            customer_type=body.get("customer_type", "B2C"),
            legal_name=body.get("legal_name", ""),
            trade_name=body.get("trade_name", ""),
            tax_id=body.get("tax_id", ""),
            company_registration_number=body.get("company_registration_number", ""),
            physical_address=body.get("physical_address", ""),
            city=body.get("city", ""),
            contact_email=body.get("contact_email", ""),
            contact_phone=body.get("contact_phone", ""),
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_compliance_services()
    from core.commands.rejection import RejectionReason as _RR
    result = svcs._tenant_service.submit_compliance_profile(req)
    if isinstance(result, _RR):
        return _json_error(result.code, result.message, status=400)
    return JsonResponse({
        "status": "ok",
        "profile_id": result["profile_id"],
        "profile_state": result["state"],
    })


@csrf_exempt
def saas_review_compliance_profile_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/compliance/review-profile — Review (approve/reject) a compliance profile."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.tenant_compliance import ReviewComplianceProfileRequest
        req = ReviewComplianceProfileRequest(
            profile_id=body["profile_id"],
            decision=body["decision"],
            reviewer_id=body["reviewer_id"],
            reason=body.get("reason", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_compliance_services()
    rejection = svcs._tenant_service.review_compliance_profile(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    return JsonResponse({"status": "ok", "profile_id": req.profile_id})


@csrf_exempt
def saas_activate_compliance_profile_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/compliance/activate-profile — Activate an approved compliance profile."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.tenant_compliance import ActivateComplianceProfileRequest
        req = ActivateComplianceProfileRequest(
            profile_id=body["profile_id"],
            actor_id=body.get("actor_id", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_compliance_services()
    rejection = svcs._tenant_service.activate_compliance_profile(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    return JsonResponse({"status": "ok", "profile_id": req.profile_id})


@csrf_exempt
def saas_suspend_compliance_profile_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/compliance/suspend-profile — Suspend an active compliance profile."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.tenant_compliance import SuspendComplianceProfileRequest
        req = SuspendComplianceProfileRequest(
            profile_id=body["profile_id"],
            actor_id=body.get("actor_id", ""),
            reason=body.get("reason", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_compliance_services()
    rejection = svcs._tenant_service.suspend_compliance_profile(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    return JsonResponse({"status": "ok", "profile_id": req.profile_id})


@csrf_exempt
def saas_reactivate_compliance_profile_view(request: HttpRequest) -> JsonResponse:
    """POST /saas/compliance/reactivate-profile — Reactivate a suspended compliance profile."""
    if request.method != "POST":
        return _method_not_allowed()
    try:
        body = _parse_json_body(request)
        from core.saas.tenant_compliance import ReactivateComplianceProfileRequest
        req = ReactivateComplianceProfileRequest(
            profile_id=body["profile_id"],
            actor_id=body.get("actor_id", ""),
            reason=body.get("reason", ""),
            issued_at=_dt_from_body(body),
        )
    except (ValueError, KeyError) as exc:
        return _json_error("INVALID_REQUEST", str(exc), status=400)

    svcs = _get_compliance_services()
    rejection = svcs._tenant_service.reactivate_compliance_profile(req)
    if rejection is not None:
        return _json_error(rejection.code, rejection.message, status=400)
    return JsonResponse({"status": "ok", "profile_id": req.profile_id})


def saas_compliance_profile_view(request: HttpRequest) -> JsonResponse:
    """GET /saas/compliance/profile?business_id= — Get tenant compliance profile + decisions."""
    if request.method != "GET":
        return _method_not_allowed()
    business_id = request.GET.get("business_id", "")
    if not business_id:
        return _json_error("INVALID_REQUEST", "business_id is required.", status=400)

    svcs = _get_compliance_services()
    profile = svcs._tenant_proj.get_profile_by_business(business_id)
    if profile is None:
        return _json_error("NOT_FOUND", f"No compliance profile found for business {business_id}.", status=404)
    return JsonResponse({"status": "ok", "profile": _serialize_tenant_profile(profile)})
