"""
BOS Admin - Repository and Provider Adapters
============================================
Read helpers over derived admin projections.
"""

from __future__ import annotations

import uuid

from core.admin.projections import AdminProjectionStore
from core.compliance.models import ComplianceProfile
from core.documents.models import DocumentTemplate
from core.feature_flags.models import FeatureFlag


class AdminRepository:
    def __init__(self, projection_store: AdminProjectionStore):
        self._projection_store = projection_store

    def get_feature_flags(
        self,
        business_id: uuid.UUID,
    ) -> tuple[FeatureFlag, ...]:
        return self._projection_store.feature_flags.get_feature_flags(business_id)

    def get_compliance_profiles(
        self,
        business_id: uuid.UUID,
    ) -> tuple[ComplianceProfile, ...]:
        return self._projection_store.compliance_profiles.get_compliance_profiles(
            business_id
        )

    def get_document_templates(
        self,
        business_id: uuid.UUID,
    ) -> tuple[DocumentTemplate, ...]:
        return self._projection_store.document_templates.get_document_templates(
            business_id
        )


class RepositoryFeatureFlagProvider:
    def __init__(self, repository: AdminRepository):
        self._repository = repository

    def get_flags_for_business(
        self,
        business_id: uuid.UUID,
    ) -> tuple[FeatureFlag, ...]:
        return self._repository.get_feature_flags(business_id)


class RepositoryComplianceProvider:
    def __init__(self, repository: AdminRepository):
        self._repository = repository

    def get_profiles_for_business(
        self,
        business_id: uuid.UUID,
    ) -> tuple[ComplianceProfile, ...]:
        return self._repository.get_compliance_profiles(business_id)


class RepositoryDocumentProvider:
    def __init__(self, repository: AdminRepository):
        self._repository = repository

    def get_templates_for_business(
        self,
        business_id: uuid.UUID,
    ) -> tuple[DocumentTemplate, ...]:
        return self._repository.get_document_templates(business_id)

