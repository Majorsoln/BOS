"""
BOS Admin - Deterministic Projections
=====================================
Derived state rebuilt from admin events.
"""

from __future__ import annotations

import uuid

from core.admin.events import (
    ADMIN_COMPLIANCE_PROFILE_DEACTIVATED_V1,
    ADMIN_COMPLIANCE_PROFILE_UPSERTED_V1,
    ADMIN_DOCUMENT_TEMPLATE_DEACTIVATED_V1,
    ADMIN_DOCUMENT_TEMPLATE_UPSERTED_V1,
    ADMIN_FEATURE_FLAG_CLEARED_V1,
    ADMIN_FEATURE_FLAG_SET_V1,
)
from core.compliance.models import ComplianceProfile
from core.documents.models import DocumentTemplate
from core.feature_flags.models import FeatureFlag


class FeatureFlagProjection:
    def __init__(self):
        self._records: dict[tuple[uuid.UUID, uuid.UUID | None, str], str] = {}

    def set_flag(
        self,
        *,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None,
        flag_key: str,
        status: str,
    ) -> None:
        self._records[(business_id, branch_id, flag_key)] = status

    def clear_flag(
        self,
        *,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None,
        flag_key: str,
    ) -> bool:
        key = (business_id, branch_id, flag_key)
        return self._records.pop(key, None) is not None

    def has_flag(
        self,
        *,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None,
        flag_key: str,
    ) -> bool:
        return (business_id, branch_id, flag_key) in self._records

    def apply_set(self, payload: dict) -> None:
        self.set_flag(
            business_id=payload["business_id"],
            branch_id=payload["branch_id"],
            flag_key=payload["flag_key"],
            status=payload["status"],
        )

    def apply_cleared(self, payload: dict) -> None:
        if payload.get("no_op"):
            return
        self.clear_flag(
            business_id=payload["business_id"],
            branch_id=payload["branch_id"],
            flag_key=payload["flag_key"],
        )

    def get_feature_flags(self, business_id: uuid.UUID) -> tuple[FeatureFlag, ...]:
        flags = []
        for (record_business_id, branch_id, flag_key), status in self._records.items():
            if record_business_id != business_id:
                continue
            flags.append(
                FeatureFlag(
                    flag_key=flag_key,
                    business_id=record_business_id,
                    branch_id=branch_id,
                    status=status,
                )
            )
        return tuple(sorted(flags, key=lambda item: item.sort_key()))

    def snapshot(self) -> tuple[tuple[str, str, str, str], ...]:
        rows = []
        for (business_id, branch_id, flag_key), status in self._records.items():
            rows.append(
                (
                    str(business_id),
                    "" if branch_id is None else str(branch_id),
                    flag_key,
                    status,
                )
            )
        rows.sort()
        return tuple(rows)


class ComplianceProfileProjection:
    def __init__(self):
        self._records: dict[
            tuple[uuid.UUID, uuid.UUID | None, int],
            dict,
        ] = {}

    def next_version(
        self,
        *,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None,
    ) -> int:
        versions = [
            version
            for (record_business_id, record_branch_id, version) in self._records
            if record_business_id == business_id and record_branch_id == branch_id
        ]
        return (max(versions) + 1) if versions else 1

    def latest_active_version(
        self,
        *,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None,
    ) -> int | None:
        active_versions = []
        for key, value in self._records.items():
            record_business_id, record_branch_id, version = key
            if record_business_id != business_id or record_branch_id != branch_id:
                continue
            if value["status"] == "ACTIVE":
                active_versions.append(version)
        if not active_versions:
            return None
        return max(active_versions)

    def apply_upserted(self, payload: dict) -> None:
        key = (payload["business_id"], payload["branch_id"], payload["version"])
        self._records[key] = {
            "profile_id": payload["profile_id"],
            "status": payload["status"],
            "ruleset": payload["ruleset"],
            "updated_by_actor_id": payload.get("updated_by_actor_id"),
            "updated_at": payload.get("updated_at"),
        }

    def apply_deactivated(self, payload: dict) -> None:
        if payload.get("no_op"):
            return
        target_version = payload.get("target_version")
        if target_version is None:
            return
        key = (payload["business_id"], payload["branch_id"], target_version)
        existing = self._records.get(key)
        if existing is None:
            return
        updated = dict(existing)
        updated["status"] = "INACTIVE"
        self._records[key] = updated

    def get_compliance_profiles(
        self,
        business_id: uuid.UUID,
    ) -> tuple[ComplianceProfile, ...]:
        profiles = []
        for (record_business_id, branch_id, version), record in self._records.items():
            if record_business_id != business_id:
                continue
            profiles.append(
                ComplianceProfile(
                    profile_id=record["profile_id"],
                    business_id=record_business_id,
                    branch_id=branch_id,
                    status=record["status"],
                    version=version,
                    ruleset=record["ruleset"],
                    updated_by_actor_id=record.get("updated_by_actor_id"),
                    updated_at=record.get("updated_at"),
                )
            )
        return tuple(sorted(profiles, key=lambda item: item.sort_key()))

    def snapshot(self) -> tuple[tuple[str, str, int, str, str], ...]:
        rows = []
        for (business_id, branch_id, version), record in self._records.items():
            rows.append(
                (
                    str(business_id),
                    "" if branch_id is None else str(branch_id),
                    version,
                    record["profile_id"],
                    record["status"],
                )
            )
        rows.sort()
        return tuple(rows)


class DocumentTemplateProjection:
    def __init__(self):
        self._records: dict[
            tuple[uuid.UUID, uuid.UUID | None, str, int],
            dict,
        ] = {}

    def next_version(
        self,
        *,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None,
        doc_type: str,
    ) -> int:
        versions = [
            version
            for (record_business_id, record_branch_id, record_doc_type, version) in self._records
            if (
                record_business_id == business_id
                and record_branch_id == branch_id
                and record_doc_type == doc_type
            )
        ]
        return (max(versions) + 1) if versions else 1

    def latest_active_version(
        self,
        *,
        business_id: uuid.UUID,
        branch_id: uuid.UUID | None,
        doc_type: str,
    ) -> int | None:
        active_versions = []
        for key, value in self._records.items():
            record_business_id, record_branch_id, record_doc_type, version = key
            if record_business_id != business_id:
                continue
            if record_branch_id != branch_id:
                continue
            if record_doc_type != doc_type:
                continue
            if value["status"] == "ACTIVE":
                active_versions.append(version)
        if not active_versions:
            return None
        return max(active_versions)

    def apply_upserted(self, payload: dict) -> None:
        key = (
            payload["business_id"],
            payload["branch_id"],
            payload["doc_type"],
            payload["version"],
        )
        self._records[key] = {
            "template_id": payload["template_id"],
            "status": payload["status"],
            "schema_version": payload["schema_version"],
            "layout_spec": payload["layout_spec"],
            "created_by_actor_id": payload.get("created_by_actor_id"),
            "created_at": payload.get("created_at"),
        }

    def apply_deactivated(self, payload: dict) -> None:
        if payload.get("no_op"):
            return
        target_version = payload.get("target_version")
        if target_version is None:
            return
        key = (
            payload["business_id"],
            payload["branch_id"],
            payload["doc_type"],
            target_version,
        )
        existing = self._records.get(key)
        if existing is None:
            return
        updated = dict(existing)
        updated["status"] = "INACTIVE"
        self._records[key] = updated

    def get_document_templates(
        self,
        business_id: uuid.UUID,
    ) -> tuple[DocumentTemplate, ...]:
        templates = []
        for (
            record_business_id,
            branch_id,
            doc_type,
            version,
        ), record in self._records.items():
            if record_business_id != business_id:
                continue
            templates.append(
                DocumentTemplate(
                    template_id=record["template_id"],
                    business_id=record_business_id,
                    branch_id=branch_id,
                    doc_type=doc_type,
                    version=version,
                    status=record["status"],
                    schema_version=record["schema_version"],
                    layout_spec=record["layout_spec"],
                    created_by_actor_id=record.get("created_by_actor_id"),
                    created_at=record.get("created_at"),
                )
            )
        return tuple(sorted(templates, key=lambda item: item.sort_key()))

    def snapshot(self) -> tuple[tuple[str, str, str, int, str, str], ...]:
        rows = []
        for (business_id, branch_id, doc_type, version), record in self._records.items():
            rows.append(
                (
                    str(business_id),
                    "" if branch_id is None else str(branch_id),
                    doc_type,
                    version,
                    record["template_id"],
                    record["status"],
                )
            )
        rows.sort()
        return tuple(rows)


class AdminProjectionStore:
    def __init__(self):
        self.feature_flags = FeatureFlagProjection()
        self.compliance_profiles = ComplianceProfileProjection()
        self.document_templates = DocumentTemplateProjection()

    def apply(self, event_data: dict) -> None:
        event_type = event_data["event_type"]
        payload = event_data["payload"]

        if event_type == ADMIN_FEATURE_FLAG_SET_V1:
            self.feature_flags.apply_set(payload)
            return
        if event_type == ADMIN_FEATURE_FLAG_CLEARED_V1:
            self.feature_flags.apply_cleared(payload)
            return
        if event_type == ADMIN_COMPLIANCE_PROFILE_UPSERTED_V1:
            self.compliance_profiles.apply_upserted(payload)
            return
        if event_type == ADMIN_COMPLIANCE_PROFILE_DEACTIVATED_V1:
            self.compliance_profiles.apply_deactivated(payload)
            return
        if event_type == ADMIN_DOCUMENT_TEMPLATE_UPSERTED_V1:
            self.document_templates.apply_upserted(payload)
            return
        if event_type == ADMIN_DOCUMENT_TEMPLATE_DEACTIVATED_V1:
            self.document_templates.apply_deactivated(payload)

    def snapshot(self) -> dict:
        return {
            "feature_flags": self.feature_flags.snapshot(),
            "compliance_profiles": self.compliance_profiles.snapshot(),
            "document_templates": self.document_templates.snapshot(),
        }

