"""
BOS Documents - Deterministic Template Resolver and Render Plan Builder
========================================================================
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Optional

from core.commands.rejection import ReasonCode
from core.documents.defaults import build_default_template
from core.documents.models import (
    REQUIRED_LAYOUT_KEYS,
    TEMPLATE_ACTIVE,
    DocumentTemplate,
)
from core.documents.provider import DocumentProvider


@dataclass(frozen=True)
class DocumentBuilderError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def _normalize_json_value(value: Any):
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        normalized = {}
        for key in sorted(value.keys()):
            if not isinstance(key, str):
                raise DocumentBuilderError(
                    code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
                    message="layout_spec dictionary keys must be strings.",
                )
            normalized[key] = _normalize_json_value(value[key])
        return normalized
    if isinstance(value, (list, tuple)):
        return tuple(_normalize_json_value(item) for item in value)
    raise DocumentBuilderError(
        code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
        message="layout_spec contains non JSON-like values.",
    )


def _normalize_string_sequence(
    value: Any,
    *,
    field_name: str,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise DocumentBuilderError(
            code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
            message=f"layout_spec.{field_name} must be a list or tuple.",
        )
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise DocumentBuilderError(
                code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
                message=f"layout_spec.{field_name} must contain non-empty strings.",
            )
        normalized.append(item)
    return tuple(normalized)


def normalize_layout_spec(layout_spec: dict) -> dict:
    if not isinstance(layout_spec, dict):
        raise DocumentBuilderError(
            code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
            message="layout_spec must be a dict.",
        )

    missing = tuple(
        key for key in REQUIRED_LAYOUT_KEYS if key not in layout_spec
    )
    if missing:
        raise DocumentBuilderError(
            code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
            message=(
                "layout_spec missing required key(s): "
                f"{', '.join(sorted(missing))}."
            ),
        )

    normalized = _normalize_json_value(layout_spec)
    line_items_path = normalized.get("line_items_path")
    if not isinstance(line_items_path, str) or not line_items_path:
        raise DocumentBuilderError(
            code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
            message="layout_spec.line_items_path must be a non-empty string.",
        )

    normalized["header_fields"] = _normalize_string_sequence(
        normalized.get("header_fields"),
        field_name="header_fields",
    )
    normalized["total_fields"] = _normalize_string_sequence(
        normalized.get("total_fields"),
        field_name="total_fields",
    )
    normalized["footer_fields"] = _normalize_string_sequence(
        normalized.get("footer_fields"),
        field_name="footer_fields",
    )

    if "line_item_fields" in normalized:
        normalized["line_item_fields"] = _normalize_string_sequence(
            normalized.get("line_item_fields"),
            field_name="line_item_fields",
        )

    return normalized


def _resolve_path_value(payload: dict, field_path: str) -> tuple[bool, Any]:
    if not isinstance(payload, dict):
        return False, None

    current: Any = payload
    for part in field_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _require_payload_value(payload: dict, field_path: str) -> Any:
    exists, value = _resolve_path_value(payload, field_path)
    if not exists:
        raise DocumentBuilderError(
            code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
            message=f"Required payload field '{field_path}' is missing.",
        )
    return _normalize_json_value(value)


class DocumentBuilder:
    @staticmethod
    def _canonicalize_templates(
        templates: tuple[DocumentTemplate, ...],
    ) -> tuple[DocumentTemplate, ...]:
        """
        Canonicalize non-compliant provider duplicates deterministically.
        Duplicate key: (business_id, branch_id, doc_type, version).
        Last entry in deterministic order wins.
        """

        def precedence(
            template: DocumentTemplate,
        ) -> tuple[str, str, str, int, str, int, str]:
            return (
                str(template.business_id),
                "" if template.branch_id is None else str(template.branch_id),
                template.doc_type,
                template.version,
                template.template_id,
                2 if template.status == TEMPLATE_ACTIVE else 1,
                (
                    ""
                    if template.created_at is None
                    else template.created_at.isoformat()
                ),
            )

        ordered = tuple(sorted(templates, key=precedence))
        canonical: dict[
            tuple[uuid.UUID, uuid.UUID | None, str, int],
            DocumentTemplate,
        ] = {}
        for template in ordered:
            canonical[template.scope_key()] = template
        return tuple(canonical.values())

    @staticmethod
    def _select_scope_template(
        *,
        business_id: uuid.UUID,
        branch_id: Optional[uuid.UUID],
        doc_type: str,
        templates: tuple[DocumentTemplate, ...],
    ) -> Optional[DocumentTemplate]:
        active = tuple(
            template
            for template in templates
            if template.business_id == business_id
            and template.doc_type == doc_type
            and template.status == TEMPLATE_ACTIVE
        )

        branch_candidates: list[DocumentTemplate] = []
        business_candidates: list[DocumentTemplate] = []
        for template in active:
            if template.branch_id is None:
                business_candidates.append(template)
                continue
            if branch_id is not None and template.branch_id == branch_id:
                branch_candidates.append(template)

        scope_candidates = (
            branch_candidates if branch_id is not None and branch_candidates else business_candidates
        )
        if not scope_candidates:
            return None

        scope_candidates.sort(key=lambda template: (template.version, template.template_id))
        return scope_candidates[-1]

    @staticmethod
    def resolve_template(
        *,
        business_id: uuid.UUID,
        branch_id: Optional[uuid.UUID],
        doc_type: str,
        provider: DocumentProvider | None,
    ) -> DocumentTemplate:
        templates = (
            provider.get_templates_for_business(business_id)
            if provider is not None
            else tuple()
        )
        canonical_templates = DocumentBuilder._canonicalize_templates(templates)
        selected = DocumentBuilder._select_scope_template(
            business_id=business_id,
            branch_id=branch_id,
            doc_type=doc_type,
            templates=canonical_templates,
        )
        if selected is not None:
            return selected

        default_template = build_default_template(
            business_id=business_id,
            doc_type=doc_type,
        )
        if default_template is None:
            raise DocumentBuilderError(
                code=ReasonCode.DOCUMENT_TEMPLATE_NOT_FOUND,
                message=(
                    f"No active template found for doc_type '{doc_type}' "
                    f"in business_id '{business_id}' and branch_id '{branch_id}'."
                ),
            )
        return default_template

    @staticmethod
    def build_render_plan(
        *,
        doc_type: str,
        template: DocumentTemplate,
        payload: dict,
    ) -> dict:
        if not isinstance(payload, dict):
            raise DocumentBuilderError(
                code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
                message="Command payload must be a dict for document planning.",
            )

        if template.doc_type != doc_type:
            raise DocumentBuilderError(
                code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
                message=(
                    f"Template doc_type '{template.doc_type}' does not match "
                    f"requested doc_type '{doc_type}'."
                ),
            )

        layout = normalize_layout_spec(template.layout_spec)
        header_fields = layout["header_fields"]
        total_fields = layout["total_fields"]
        footer_fields = layout["footer_fields"]
        line_items_path = layout["line_items_path"]
        line_item_fields = layout.get("line_item_fields")

        header = {
            field: _require_payload_value(payload, field)
            for field in header_fields
        }
        totals = {
            field: _require_payload_value(payload, field)
            for field in total_fields
        }
        footer = {
            field: _require_payload_value(payload, field)
            for field in footer_fields
        }

        exists, line_items_value = _resolve_path_value(payload, line_items_path)
        if not exists:
            raise DocumentBuilderError(
                code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
                message=f"Required payload field '{line_items_path}' is missing.",
            )
        if not isinstance(line_items_value, (list, tuple)):
            raise DocumentBuilderError(
                code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
                message=(
                    f"Payload field '{line_items_path}' must be a list or tuple."
                ),
            )

        line_items: list[dict] = []
        for index, raw_item in enumerate(line_items_value):
            if not isinstance(raw_item, dict):
                raise DocumentBuilderError(
                    code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
                    message=f"line_items[{index}] must be a dict.",
                )

            if line_item_fields is None:
                line_items.append(_normalize_json_value(raw_item))
                continue

            normalized_item = {}
            for field in line_item_fields:
                if field not in raw_item:
                    raise DocumentBuilderError(
                        code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
                        message=(
                            f"line_items[{index}] missing required field '{field}'."
                        ),
                    )
                normalized_item[field] = _normalize_json_value(raw_item[field])
            line_items.append(normalized_item)

        return {
            "doc_type": doc_type,
            "template_id": template.template_id,
            "template_version": template.version,
            "schema_version": template.schema_version,
            "header": header,
            "line_items": line_items,
            "totals": totals,
            "footer": footer,
        }

    @staticmethod
    def build_for_command(
        *,
        command,
        doc_type: str,
        provider: DocumentProvider | None,
    ) -> dict:
        template = DocumentBuilder.resolve_template(
            business_id=command.business_id,
            branch_id=command.branch_id,
            doc_type=doc_type,
            provider=provider,
        )
        return DocumentBuilder.build_render_plan(
            doc_type=doc_type,
            template=template,
            payload=command.payload,
        )
