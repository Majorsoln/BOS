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
    BusinessReadRequest,
    ComplianceProfileDeactivateHttpRequest,
    ComplianceProfileUpsertHttpRequest,
    DocumentTemplateDeactivateHttpRequest,
    DocumentTemplateUpsertHttpRequest,
    FeatureFlagClearHttpRequest,
    FeatureFlagSetHttpRequest,
)
from core.http_api.errors import error_response
from core.http_api.handlers import (
    list_compliance_profiles,
    list_document_templates,
    list_feature_flags,
    post_compliance_profile_deactivate,
    post_compliance_profile_upsert,
    post_document_template_deactivate,
    post_document_template_upsert,
    post_feature_flag_clear,
    post_feature_flag_set,
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
