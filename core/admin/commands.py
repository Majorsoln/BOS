"""
BOS Admin - Request Commands
============================
Typed admin requests that convert into canonical Command objects.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.admin.registry import (
    ADMIN_COMPLIANCE_PROFILE_DEACTIVATE_REQUEST,
    ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST,
    ADMIN_DOCUMENT_TEMPLATE_DEACTIVATE_REQUEST,
    ADMIN_DOCUMENT_TEMPLATE_UPSERT_REQUEST,
    ADMIN_FEATURE_FLAG_CLEAR_REQUEST,
    ADMIN_FEATURE_FLAG_SET_REQUEST,
)
from core.commands.base import Command
from core.compliance.models import VALID_PROFILE_STATUSES
from core.context.actor_context import ActorContext
from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.documents.models import (
    VALID_DOCUMENT_TYPES,
    VALID_TEMPLATE_STATUSES,
)
from core.feature_flags.models import VALID_FEATURE_STATUSES
from core.identity.requirements import ACTOR_REQUIRED


def _validate_branch_id(branch_id: Optional[uuid.UUID]) -> None:
    if branch_id is not None and not isinstance(branch_id, uuid.UUID):
        raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class AdminCommandContext:
    business_id: uuid.UUID
    actor_type: str
    actor_id: str
    actor_context: ActorContext
    command_id: uuid.UUID
    correlation_id: uuid.UUID
    issued_at: datetime

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.actor_context, ActorContext):
            raise ValueError("actor_context must be ActorContext.")
        if self.actor_context.actor_type != self.actor_type:
            raise ValueError(
                "actor_context.actor_type must match actor_type."
            )
        if self.actor_context.actor_id != self.actor_id:
            raise ValueError("actor_context.actor_id must match actor_id.")
        if not isinstance(self.command_id, uuid.UUID):
            raise ValueError("command_id must be UUID.")
        if not isinstance(self.correlation_id, uuid.UUID):
            raise ValueError("correlation_id must be UUID.")
        if not isinstance(self.issued_at, datetime):
            raise ValueError("issued_at must be datetime.")


@dataclass(frozen=True)
class FeatureFlagSetRequest:
    flag_key: str
    status: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.flag_key or not isinstance(self.flag_key, str):
            raise ValueError("flag_key must be a non-empty string.")
        if self.status not in VALID_FEATURE_STATUSES:
            raise ValueError(
                f"status '{self.status}' not valid. "
                f"Must be one of: {sorted(VALID_FEATURE_STATUSES)}"
            )
        _validate_branch_id(self.branch_id)

    def to_command(self, context: AdminCommandContext) -> Command:
        return Command(
            command_id=context.command_id,
            command_type=ADMIN_FEATURE_FLAG_SET_REQUEST,
            business_id=context.business_id,
            branch_id=self.branch_id,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
            actor_context=context.actor_context,
            payload={
                "flag_key": self.flag_key,
                "status": self.status,
                "branch_id": self.branch_id,
            },
            issued_at=context.issued_at,
            correlation_id=context.correlation_id,
            source_engine="admin",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class FeatureFlagClearRequest:
    flag_key: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.flag_key or not isinstance(self.flag_key, str):
            raise ValueError("flag_key must be a non-empty string.")
        _validate_branch_id(self.branch_id)

    def to_command(self, context: AdminCommandContext) -> Command:
        return Command(
            command_id=context.command_id,
            command_type=ADMIN_FEATURE_FLAG_CLEAR_REQUEST,
            business_id=context.business_id,
            branch_id=self.branch_id,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
            actor_context=context.actor_context,
            payload={
                "flag_key": self.flag_key,
                "branch_id": self.branch_id,
            },
            issued_at=context.issued_at,
            correlation_id=context.correlation_id,
            source_engine="admin",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class ComplianceProfileUpsertRequest:
    ruleset: tuple
    branch_id: Optional[uuid.UUID] = None
    status: str = "ACTIVE"
    version: Optional[int] = None

    def __post_init__(self):
        if not isinstance(self.ruleset, tuple):
            raise ValueError("ruleset must be tuple.")
        _validate_branch_id(self.branch_id)
        if self.status not in VALID_PROFILE_STATUSES:
            raise ValueError(
                f"status '{self.status}' not valid. "
                f"Must be one of: {sorted(VALID_PROFILE_STATUSES)}"
            )
        if self.version is not None:
            if not isinstance(self.version, int) or self.version < 1:
                raise ValueError("version must be int >= 1 or None.")

    def with_resolved_version(self, version: int) -> "ComplianceProfileUpsertRequest":
        return ComplianceProfileUpsertRequest(
            ruleset=self.ruleset,
            branch_id=self.branch_id,
            status=self.status,
            version=version,
        )

    def to_command(self, context: AdminCommandContext) -> Command:
        return Command(
            command_id=context.command_id,
            command_type=ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST,
            business_id=context.business_id,
            branch_id=self.branch_id,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
            actor_context=context.actor_context,
            payload={
                "ruleset": self.ruleset,
                "status": self.status,
                "version": self.version,
                "branch_id": self.branch_id,
            },
            issued_at=context.issued_at,
            correlation_id=context.correlation_id,
            source_engine="admin",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class ComplianceProfileDeactivateRequest:
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        _validate_branch_id(self.branch_id)

    def to_command(self, context: AdminCommandContext) -> Command:
        return Command(
            command_id=context.command_id,
            command_type=ADMIN_COMPLIANCE_PROFILE_DEACTIVATE_REQUEST,
            business_id=context.business_id,
            branch_id=self.branch_id,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
            actor_context=context.actor_context,
            payload={"branch_id": self.branch_id},
            issued_at=context.issued_at,
            correlation_id=context.correlation_id,
            source_engine="admin",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class DocumentTemplateUpsertRequest:
    doc_type: str
    layout_spec: dict
    branch_id: Optional[uuid.UUID] = None
    status: str = "ACTIVE"
    version: Optional[int] = None
    schema_version: int = 1

    def __post_init__(self):
        if self.doc_type not in VALID_DOCUMENT_TYPES:
            raise ValueError(
                f"doc_type '{self.doc_type}' not valid. "
                f"Must be one of: {sorted(VALID_DOCUMENT_TYPES)}"
            )
        if not isinstance(self.layout_spec, dict):
            raise ValueError("layout_spec must be dict.")
        _validate_branch_id(self.branch_id)
        if self.status not in VALID_TEMPLATE_STATUSES:
            raise ValueError(
                f"status '{self.status}' not valid. "
                f"Must be one of: {sorted(VALID_TEMPLATE_STATUSES)}"
            )
        if self.version is not None:
            if not isinstance(self.version, int) or self.version < 1:
                raise ValueError("version must be int >= 1 or None.")
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ValueError("schema_version must be int >= 1.")

    def with_resolved_version(self, version: int) -> "DocumentTemplateUpsertRequest":
        return DocumentTemplateUpsertRequest(
            doc_type=self.doc_type,
            layout_spec=self.layout_spec,
            branch_id=self.branch_id,
            status=self.status,
            version=version,
            schema_version=self.schema_version,
        )

    def to_command(self, context: AdminCommandContext) -> Command:
        return Command(
            command_id=context.command_id,
            command_type=ADMIN_DOCUMENT_TEMPLATE_UPSERT_REQUEST,
            business_id=context.business_id,
            branch_id=self.branch_id,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
            actor_context=context.actor_context,
            payload={
                "doc_type": self.doc_type,
                "layout_spec": self.layout_spec,
                "status": self.status,
                "version": self.version,
                "schema_version": self.schema_version,
                "branch_id": self.branch_id,
            },
            issued_at=context.issued_at,
            correlation_id=context.correlation_id,
            source_engine="admin",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )


@dataclass(frozen=True)
class DocumentTemplateDeactivateRequest:
    doc_type: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if self.doc_type not in VALID_DOCUMENT_TYPES:
            raise ValueError(
                f"doc_type '{self.doc_type}' not valid. "
                f"Must be one of: {sorted(VALID_DOCUMENT_TYPES)}"
            )
        _validate_branch_id(self.branch_id)

    def to_command(self, context: AdminCommandContext) -> Command:
        return Command(
            command_id=context.command_id,
            command_type=ADMIN_DOCUMENT_TEMPLATE_DEACTIVATE_REQUEST,
            business_id=context.business_id,
            branch_id=self.branch_id,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
            actor_context=context.actor_context,
            payload={
                "doc_type": self.doc_type,
                "branch_id": self.branch_id,
            },
            issued_at=context.issued_at,
            correlation_id=context.correlation_id,
            source_engine="admin",
            scope_requirement=SCOPE_BUSINESS_ALLOWED,
            actor_requirement=ACTOR_REQUIRED,
        )

