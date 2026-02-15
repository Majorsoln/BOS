"""
BOS Documents - Immutable Template Models
=========================================
Deterministic document template primitives.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


DOCUMENT_RECEIPT = "RECEIPT"
DOCUMENT_QUOTE = "QUOTE"
DOCUMENT_INVOICE = "INVOICE"

TEMPLATE_ACTIVE = "ACTIVE"
TEMPLATE_INACTIVE = "INACTIVE"

VALID_DOCUMENT_TYPES = frozenset(
    {DOCUMENT_RECEIPT, DOCUMENT_QUOTE, DOCUMENT_INVOICE}
)
VALID_TEMPLATE_STATUSES = frozenset({TEMPLATE_ACTIVE, TEMPLATE_INACTIVE})
REQUIRED_LAYOUT_KEYS = (
    "header_fields",
    "line_items_path",
    "total_fields",
    "footer_fields",
)


def _is_json_like(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_is_json_like(item) for item in value)
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                return False
            if not _is_json_like(item):
                return False
        return True
    return False


@dataclass(frozen=True)
class DocumentTemplate:
    template_id: str
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID]
    doc_type: str
    version: int
    status: str
    schema_version: int
    layout_spec: dict
    created_by_actor_id: Optional[str] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.template_id or not isinstance(self.template_id, str):
            raise ValueError("template_id must be a non-empty string.")

        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")

        if self.branch_id is not None and not isinstance(
            self.branch_id, uuid.UUID
        ):
            raise ValueError("branch_id must be UUID or None.")

        if self.doc_type not in VALID_DOCUMENT_TYPES:
            raise ValueError(
                f"doc_type '{self.doc_type}' not valid. "
                f"Must be one of: {sorted(VALID_DOCUMENT_TYPES)}"
            )

        if self.status not in VALID_TEMPLATE_STATUSES:
            raise ValueError(
                f"status '{self.status}' not valid. "
                f"Must be one of: {sorted(VALID_TEMPLATE_STATUSES)}"
            )

        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be int >= 1.")

        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ValueError("schema_version must be int >= 1.")

        if not isinstance(self.layout_spec, dict):
            raise ValueError("layout_spec must be a dict.")

        missing = tuple(
            key for key in REQUIRED_LAYOUT_KEYS if key not in self.layout_spec
        )
        if missing:
            raise ValueError(
                "layout_spec missing required key(s): "
                f"{', '.join(sorted(missing))}."
            )

        if not _is_json_like(self.layout_spec):
            raise ValueError("layout_spec must contain JSON-like values only.")

        if self.created_by_actor_id is not None and (
            not isinstance(self.created_by_actor_id, str)
            or not self.created_by_actor_id
        ):
            raise ValueError(
                "created_by_actor_id must be non-empty string or None."
            )

        if self.created_at is not None and not isinstance(
            self.created_at, datetime
        ):
            raise ValueError("created_at must be datetime or None.")

    def scope_key(
        self,
    ) -> tuple[uuid.UUID, Optional[uuid.UUID], str, int]:
        return (
            self.business_id,
            self.branch_id,
            self.doc_type,
            self.version,
        )

    def sort_key(self) -> tuple[str, str, str, int, str]:
        return (
            str(self.business_id),
            "" if self.branch_id is None else str(self.branch_id),
            self.doc_type,
            self.version,
            self.template_id,
        )
