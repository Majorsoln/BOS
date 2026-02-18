"""
BOS Document Issuance - Deterministic Projections
=================================================
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.document_issuance.registry import DOCUMENT_ISSUANCE_EVENT_TYPES


def _coerce_uuid(value) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def _coerce_optional_uuid(value) -> uuid.UUID | None:
    if value is None:
        return None
    return _coerce_uuid(value)


def _coerce_issued_at(value) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    return datetime.fromisoformat(text)


def _coerce_correlation_id(value) -> uuid.UUID:
    if value is None:
        return uuid.UUID(int=0)
    if isinstance(value, uuid.UUID):
        return value
    text = str(value)
    try:
        return uuid.UUID(text)
    except Exception:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"correlation:{text}")


def _extract_minimal_totals(payload: dict) -> dict[str, Any]:
    render_plan = payload.get("render_plan")
    if not isinstance(render_plan, dict):
        return {}

    totals = render_plan.get("totals")
    if not isinstance(totals, dict):
        return {}

    minimal: dict[str, Any] = {}
    for key in ("grand_total", "currency"):
        if key in totals:
            minimal[key] = totals[key]
    if minimal:
        return minimal

    ordered_items = sorted(
        ((str(key), totals[key]) for key in totals.keys()),
        key=lambda item: item[0],
    )
    return {key: value for key, value in ordered_items}


@dataclass(frozen=True)
class IssuedDocumentRecord:
    business_id: uuid.UUID
    branch_id: uuid.UUID | None
    document_id: uuid.UUID
    doc_type: str
    template_id: str
    template_version: int
    schema_version: int
    issued_at: datetime
    actor_id: str
    correlation_id: uuid.UUID
    status: str
    totals: dict[str, Any]
    doc_number: str | None = None
    render_plan: dict | None = None
    render_plan_hash: str | None = None


class DocumentIssuanceProjectionStore:
    def __init__(self):
        self._records: dict[
            tuple[uuid.UUID, uuid.UUID | None, uuid.UUID],
            IssuedDocumentRecord,
        ] = {}

    def apply(self, event_type: str, payload: dict) -> None:
        if event_type not in DOCUMENT_ISSUANCE_EVENT_TYPES:
            return
        if not isinstance(payload, dict):
            return

        raw_render_plan = payload.get("render_plan")
        stored_render_plan = dict(raw_render_plan) if isinstance(raw_render_plan, dict) else None
        raw_hash = payload.get("render_plan_hash")
        stored_hash = str(raw_hash) if raw_hash else None
        raw_doc_number = payload.get("doc_number")
        stored_doc_number = str(raw_doc_number) if raw_doc_number is not None else None

        record = IssuedDocumentRecord(
            business_id=_coerce_uuid(payload["business_id"]),
            branch_id=_coerce_optional_uuid(payload.get("branch_id")),
            document_id=_coerce_uuid(payload["document_id"]),
            doc_type=str(payload["doc_type"]),
            template_id=str(payload["template_id"]),
            template_version=int(payload["template_version"]),
            schema_version=int(payload["schema_version"]),
            issued_at=_coerce_issued_at(payload["issued_at"]),
            actor_id=str(payload["actor_id"]),
            correlation_id=_coerce_correlation_id(payload.get("correlation_id")),
            status=str(payload.get("status", "ISSUED")),
            totals=_extract_minimal_totals(payload),
            doc_number=stored_doc_number,
            render_plan=stored_render_plan,
            render_plan_hash=stored_hash,
        )
        self._records[
            (record.business_id, record.branch_id, record.document_id)
        ] = record

    def list_documents(
        self,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None = None,
    ) -> tuple[IssuedDocumentRecord, ...]:
        items = []
        for record in self._records.values():
            if record.business_id != business_id:
                continue
            if branch_id is not None and record.branch_id != branch_id:
                continue
            items.append(record)
        items.sort(key=lambda item: (item.issued_at, str(item.document_id)))
        return tuple(items)
