"""
BOS Documents - Public API
==========================
"""

from core.documents.builder import (
    DocumentBuilder,
    DocumentBuilderError,
    normalize_layout_spec,
)
from core.documents.defaults import (
    DEFAULT_LAYOUT_SPECS,
    build_default_template,
    get_default_layout_spec,
)
from core.documents.models import (
    DOCUMENT_INVOICE,
    DOCUMENT_QUOTE,
    DOCUMENT_RECEIPT,
    TEMPLATE_ACTIVE,
    TEMPLATE_INACTIVE,
    DocumentTemplate,
)
from core.documents.provider import (
    DocumentProvider,
    InMemoryDocumentProvider,
)
from core.documents.registry import resolve_document_type

__all__ = [
    "DOCUMENT_RECEIPT",
    "DOCUMENT_QUOTE",
    "DOCUMENT_INVOICE",
    "TEMPLATE_ACTIVE",
    "TEMPLATE_INACTIVE",
    "DocumentTemplate",
    "DEFAULT_LAYOUT_SPECS",
    "get_default_layout_spec",
    "build_default_template",
    "DocumentProvider",
    "InMemoryDocumentProvider",
    "resolve_document_type",
    "DocumentBuilder",
    "DocumentBuilderError",
    "normalize_layout_spec",
]
