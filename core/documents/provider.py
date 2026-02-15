"""
BOS Documents - Provider Protocol and In-Memory Provider
========================================================
"""

from __future__ import annotations

import uuid
from typing import Iterable, Protocol

from core.documents.models import DocumentTemplate


class DocumentProvider(Protocol):
    def get_templates_for_business(
        self,
        business_id: uuid.UUID,
    ) -> tuple[DocumentTemplate, ...]:
        ...


class InMemoryDocumentProvider:
    """
    Deterministic in-memory provider used by tests/bootstrap.
    Strictly rejects duplicate (business_id, branch_id, doc_type, version).
    """

    def __init__(
        self,
        templates: Iterable[DocumentTemplate] | None = None,
    ):
        self._templates_by_business: dict[
            uuid.UUID, tuple[DocumentTemplate, ...]
        ] = {}

        dedupe: set[tuple[uuid.UUID, uuid.UUID | None, str, int]] = set()
        temp: dict[uuid.UUID, list[DocumentTemplate]] = {}

        for template in templates or ():
            key = template.scope_key()
            if key in dedupe:
                raise ValueError(
                    "Duplicate document template scope/version "
                    f"(business_id='{template.business_id}', "
                    f"branch_id='{template.branch_id}', "
                    f"doc_type='{template.doc_type}', "
                    f"version='{template.version}')."
                )
            dedupe.add(key)
            temp.setdefault(template.business_id, []).append(template)

        for business_id, business_templates in temp.items():
            ordered = tuple(
                sorted(
                    business_templates,
                    key=lambda template: template.sort_key(),
                )
            )
            self._templates_by_business[business_id] = ordered

    def get_templates_for_business(
        self,
        business_id: uuid.UUID,
    ) -> tuple[DocumentTemplate, ...]:
        return self._templates_by_business.get(business_id, tuple())
