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
    """Lazy-load SaaS service singletons."""
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
    return JsonResponse({"status": "ok"})
