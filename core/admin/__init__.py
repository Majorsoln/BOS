"""
BOS Admin - Public API
======================
"""

from core.admin.commands import (
    AdminCommandContext,
    ComplianceProfileDeactivateRequest,
    ComplianceProfileUpsertRequest,
    DocumentTemplateDeactivateRequest,
    DocumentTemplateUpsertRequest,
    FeatureFlagClearRequest,
    FeatureFlagSetRequest,
)
from core.admin.events import (
    ADMIN_COMPLIANCE_PROFILE_DEACTIVATED_V1,
    ADMIN_COMPLIANCE_PROFILE_UPSERTED_V1,
    ADMIN_DOCUMENT_TEMPLATE_DEACTIVATED_V1,
    ADMIN_DOCUMENT_TEMPLATE_UPSERTED_V1,
    ADMIN_FEATURE_FLAG_CLEARED_V1,
    ADMIN_FEATURE_FLAG_SET_V1,
    resolve_admin_event_type,
)
from core.admin.projections import AdminProjectionStore
from core.admin.registry import (
    ADMIN_COMPLIANCE_PROFILE_DEACTIVATE_REQUEST,
    ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST,
    ADMIN_DOCUMENT_TEMPLATE_DEACTIVATE_REQUEST,
    ADMIN_DOCUMENT_TEMPLATE_UPSERT_REQUEST,
    ADMIN_FEATURE_FLAG_CLEAR_REQUEST,
    ADMIN_FEATURE_FLAG_SET_REQUEST,
    is_admin_command_type,
)
from core.admin.repository import (
    AdminRepository,
    RepositoryComplianceProvider,
    RepositoryDocumentProvider,
    RepositoryFeatureFlagProvider,
)
from core.admin.service import AdminDataService, AdminExecutionResult

__all__ = [
    "AdminCommandContext",
    "FeatureFlagSetRequest",
    "FeatureFlagClearRequest",
    "ComplianceProfileUpsertRequest",
    "ComplianceProfileDeactivateRequest",
    "DocumentTemplateUpsertRequest",
    "DocumentTemplateDeactivateRequest",
    "ADMIN_FEATURE_FLAG_SET_REQUEST",
    "ADMIN_FEATURE_FLAG_CLEAR_REQUEST",
    "ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST",
    "ADMIN_COMPLIANCE_PROFILE_DEACTIVATE_REQUEST",
    "ADMIN_DOCUMENT_TEMPLATE_UPSERT_REQUEST",
    "ADMIN_DOCUMENT_TEMPLATE_DEACTIVATE_REQUEST",
    "is_admin_command_type",
    "ADMIN_FEATURE_FLAG_SET_V1",
    "ADMIN_FEATURE_FLAG_CLEARED_V1",
    "ADMIN_COMPLIANCE_PROFILE_UPSERTED_V1",
    "ADMIN_COMPLIANCE_PROFILE_DEACTIVATED_V1",
    "ADMIN_DOCUMENT_TEMPLATE_UPSERTED_V1",
    "ADMIN_DOCUMENT_TEMPLATE_DEACTIVATED_V1",
    "resolve_admin_event_type",
    "AdminProjectionStore",
    "AdminRepository",
    "RepositoryFeatureFlagProvider",
    "RepositoryComplianceProvider",
    "RepositoryDocumentProvider",
    "AdminDataService",
    "AdminExecutionResult",
]
