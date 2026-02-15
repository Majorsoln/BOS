"""
BOS HTTP API - Public API
=========================
"""

from core.http_api.contracts import (
    ActorMetadata,
    BusinessReadRequest,
    ComplianceProfileDeactivateHttpRequest,
    ComplianceProfileUpsertHttpRequest,
    DocumentTemplateDeactivateHttpRequest,
    DocumentTemplateUpsertHttpRequest,
    FeatureFlagClearHttpRequest,
    FeatureFlagSetHttpRequest,
    HttpApiErrorBody,
    HttpApiResponse,
)
from core.http_api.dependencies import (
    Clock,
    HttpApiDependencies,
    IdProvider,
    UtcClock,
    UuidIdProvider,
)
from core.http_api.errors import (
    error_response,
    map_rejection_reason,
    rejection_response,
    success_response,
)
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

__all__ = [
    "ActorMetadata",
    "BusinessReadRequest",
    "FeatureFlagSetHttpRequest",
    "FeatureFlagClearHttpRequest",
    "ComplianceProfileUpsertHttpRequest",
    "ComplianceProfileDeactivateHttpRequest",
    "DocumentTemplateUpsertHttpRequest",
    "DocumentTemplateDeactivateHttpRequest",
    "HttpApiErrorBody",
    "HttpApiResponse",
    "IdProvider",
    "Clock",
    "UuidIdProvider",
    "UtcClock",
    "HttpApiDependencies",
    "error_response",
    "success_response",
    "map_rejection_reason",
    "rejection_response",
    "list_feature_flags",
    "list_compliance_profiles",
    "list_document_templates",
    "post_feature_flag_set",
    "post_feature_flag_clear",
    "post_compliance_profile_upsert",
    "post_compliance_profile_deactivate",
    "post_document_template_upsert",
    "post_document_template_deactivate",
]

