"""
BOS HTTP API - Contracts
========================
Framework-agnostic request/response DTOs for admin endpoints.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ActorMetadata:
    actor_type: str
    actor_id: str
    actor_roles: tuple[str, ...] = field(default_factory=tuple)
    actor_scopes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not self.actor_type or not isinstance(self.actor_type, str):
            raise ValueError("actor_type must be a non-empty string.")
        if not self.actor_id or not isinstance(self.actor_id, str):
            raise ValueError("actor_id must be a non-empty string.")
        if not isinstance(self.actor_roles, tuple):
            raise ValueError("actor_roles must be a tuple.")
        if not isinstance(self.actor_scopes, tuple):
            raise ValueError("actor_scopes must be a tuple.")


@dataclass(frozen=True)
class BusinessReadRequest:
    business_id: uuid.UUID

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")


@dataclass(frozen=True)
class FeatureFlagSetHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata
    flag_key: str
    status: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not self.flag_key or not isinstance(self.flag_key, str):
            raise ValueError("flag_key must be a non-empty string.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class FeatureFlagClearHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata
    flag_key: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not self.flag_key or not isinstance(self.flag_key, str):
            raise ValueError("flag_key must be a non-empty string.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class ComplianceProfileUpsertHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata
    ruleset: tuple
    branch_id: Optional[uuid.UUID] = None
    status: str = "ACTIVE"
    version: Optional[int] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not isinstance(self.ruleset, tuple):
            raise ValueError("ruleset must be tuple.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")
        if self.version is not None and (
            not isinstance(self.version, int) or self.version < 1
        ):
            raise ValueError("version must be int >= 1 or None.")


@dataclass(frozen=True)
class ComplianceProfileDeactivateHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class DocumentTemplateUpsertHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata
    doc_type: str
    layout_spec: dict
    branch_id: Optional[uuid.UUID] = None
    status: str = "ACTIVE"
    version: Optional[int] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not self.doc_type or not isinstance(self.doc_type, str):
            raise ValueError("doc_type must be a non-empty string.")
        if not isinstance(self.layout_spec, dict):
            raise ValueError("layout_spec must be dict.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")
        if self.version is not None and (
            not isinstance(self.version, int) or self.version < 1
        ):
            raise ValueError("version must be int >= 1 or None.")


@dataclass(frozen=True)
class DocumentTemplateDeactivateHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata
    doc_type: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not self.doc_type or not isinstance(self.doc_type, str):
            raise ValueError("doc_type must be a non-empty string.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class HttpApiErrorBody:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class HttpApiResponse:
    ok: bool
    data: Any = None
    error: Optional[HttpApiErrorBody] = None

    def to_dict(self) -> dict[str, Any]:
        if self.ok:
            return {"ok": True, "data": self.data}
        if self.error is None:
            raise ValueError("error must be set when ok is False.")
        return {"ok": False, "error": self.error.to_dict()}

