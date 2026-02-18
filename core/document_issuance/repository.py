"""
BOS Document Issuance - Read Repository
=======================================
"""

from __future__ import annotations

import base64
from datetime import datetime
import uuid

from core.document_issuance.projections import (
    DocumentIssuanceProjectionStore,
    IssuedDocumentRecord,
)


DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 200


class DocumentCursorError(ValueError):
    pass


def _cursor_sort_key(record: IssuedDocumentRecord) -> tuple[datetime, str]:
    return (record.issued_at, str(record.document_id))


def _encode_cursor_token(issued_at: datetime, document_id: uuid.UUID) -> str:
    raw = f"{issued_at.isoformat()}|{document_id}"
    encoded = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def _decode_cursor_token(cursor: str) -> tuple[datetime, str]:
    if not isinstance(cursor, str) or not cursor.strip():
        raise DocumentCursorError("cursor must be a non-empty string.")

    token = cursor.strip()
    padding = "=" * ((4 - len(token) % 4) % 4)
    try:
        decoded = base64.urlsafe_b64decode((token + padding).encode("ascii")).decode(
            "utf-8"
        )
    except Exception as exc:
        raise DocumentCursorError("cursor is not valid base64.") from exc

    parts = decoded.split("|", 1)
    if len(parts) != 2:
        raise DocumentCursorError("cursor payload format is invalid.")
    issued_at_raw, document_id_raw = parts

    try:
        issued_at = datetime.fromisoformat(issued_at_raw)
    except Exception as exc:
        raise DocumentCursorError("cursor issued_at value is invalid.") from exc
    if issued_at.tzinfo is None:
        raise DocumentCursorError("cursor issued_at value must include timezone.")
    try:
        document_id = str(uuid.UUID(document_id_raw))
    except Exception as exc:
        raise DocumentCursorError("cursor document_id value is invalid.") from exc
    return issued_at, document_id


class DocumentIssuanceRepository:
    def __init__(self, projection_store: DocumentIssuanceProjectionStore):
        self._projection_store = projection_store

    def get_documents(
        self,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None = None,
    ) -> tuple[IssuedDocumentRecord, ...]:
        return self._projection_store.list_documents(
            business_id=business_id,
            branch_id=branch_id,
        )

    def get_documents_page(
        self,
        *,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None = None,
        limit: int = DEFAULT_PAGE_LIMIT,
        cursor: str | None = None,
    ) -> tuple[tuple[IssuedDocumentRecord, ...], str | None]:
        if not isinstance(limit, int):
            raise ValueError("limit must be int.")
        if limit < 1:
            raise ValueError("limit must be >= 1.")
        if limit > MAX_PAGE_LIMIT:
            raise ValueError(f"limit must be <= {MAX_PAGE_LIMIT}.")

        records = self.get_documents(
            business_id=business_id,
            branch_id=branch_id,
        )

        start_key: tuple[datetime, str] | None = None
        if cursor is not None:
            start_key = _decode_cursor_token(cursor)

        filtered: list[IssuedDocumentRecord] = []
        for record in records:
            sort_key = _cursor_sort_key(record)
            if start_key is not None and sort_key <= start_key:
                continue
            filtered.append(record)

        page_items = tuple(filtered[:limit])
        if not page_items:
            return page_items, None

        if len(filtered) <= limit:
            return page_items, None

        tail = page_items[-1]
        next_cursor = _encode_cursor_token(tail.issued_at, tail.document_id)
        return page_items, next_cursor
