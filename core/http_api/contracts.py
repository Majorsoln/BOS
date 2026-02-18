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
class IssuedDocumentsReadRequest:
    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID] = None
    limit: int = 50
    cursor: str | None = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")
        if not isinstance(self.limit, int):
            raise ValueError("limit must be int.")
        if self.limit < 1 or self.limit > 200:
            raise ValueError("limit must be between 1 and 200.")
        if self.cursor is not None and not isinstance(self.cursor, str):
            raise ValueError("cursor must be string or None.")


@dataclass(frozen=True)
class IssueReceiptHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    payload: dict
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be dict.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class IssueQuoteHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    payload: dict
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be dict.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class IssueInvoiceHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    payload: dict
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be dict.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class FeatureFlagSetHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    flag_key: str
    status: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not self.flag_key or not isinstance(self.flag_key, str):
            raise ValueError("flag_key must be a non-empty string.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class FeatureFlagClearHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    flag_key: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not self.flag_key or not isinstance(self.flag_key, str):
            raise ValueError("flag_key must be a non-empty string.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class ComplianceProfileUpsertHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    ruleset: tuple
    branch_id: Optional[uuid.UUID] = None
    status: str = "ACTIVE"
    version: Optional[int] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
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
    actor: ActorMetadata | None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class DocumentTemplateUpsertHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    doc_type: str
    layout_spec: dict
    branch_id: Optional[uuid.UUID] = None
    status: str = "ACTIVE"
    version: Optional[int] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
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
    actor: ActorMetadata | None
    doc_type: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not self.doc_type or not isinstance(self.doc_type, str):
            raise ValueError("doc_type must be a non-empty string.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class ApiKeyCreateHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    actor_id: str
    actor_type: str
    allowed_business_ids: tuple[str, ...]
    allowed_branch_ids_by_business: dict[str, tuple[str, ...]]
    label: str | None = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not self.actor_id or not isinstance(self.actor_id, str):
            raise ValueError("actor_id must be a non-empty string.")
        if not self.actor_type or not isinstance(self.actor_type, str):
            raise ValueError("actor_type must be a non-empty string.")
        if not isinstance(self.allowed_business_ids, tuple):
            raise ValueError("allowed_business_ids must be a tuple.")
        if not isinstance(self.allowed_branch_ids_by_business, dict):
            raise ValueError("allowed_branch_ids_by_business must be a dict.")
        if self.label is not None and not isinstance(self.label, str):
            raise ValueError("label must be a string or None.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class ApiKeyRevokeHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    key_id: Optional[uuid.UUID] = None
    key_hash: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if self.key_id is None and (self.key_hash is None or not self.key_hash.strip()):
            raise ValueError("Either key_id or key_hash must be provided.")
        if self.key_hash is not None and not isinstance(self.key_hash, str):
            raise ValueError("key_hash must be a string or None.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class ApiKeyRotateHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    key_id: Optional[uuid.UUID] = None
    key_hash: Optional[str] = None
    label: str | None = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if self.key_id is None and (self.key_hash is None or not self.key_hash.strip()):
            raise ValueError("Either key_id or key_hash must be provided.")
        if self.key_hash is not None and not isinstance(self.key_hash, str):
            raise ValueError("key_hash must be a string or None.")
        if self.label is not None and not isinstance(self.label, str):
            raise ValueError("label must be a string or None.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class IdentityBootstrapHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    business_name: str
    default_currency: str = "USD"
    default_language: str = "en"
    branches: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    admin_actor_id: str | None = None
    cashier_actor_id: str | None = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not self.business_name or not isinstance(self.business_name, str):
            raise ValueError("business_name must be a non-empty string.")
        if not isinstance(self.default_currency, str) or not self.default_currency.strip():
            raise ValueError("default_currency must be a non-empty string.")
        if not isinstance(self.default_language, str) or not self.default_language.strip():
            raise ValueError("default_language must be a non-empty string.")
        if not isinstance(self.branches, tuple):
            raise ValueError("branches must be a tuple.")
        for branch in self.branches:
            if not isinstance(branch, dict):
                raise ValueError("branches values must be objects.")
        if self.admin_actor_id is not None and (
            not isinstance(self.admin_actor_id, str) or not self.admin_actor_id.strip()
        ):
            raise ValueError("admin_actor_id must be a non-empty string or None.")
        if self.cashier_actor_id is not None and (
            not isinstance(self.cashier_actor_id, str) or not self.cashier_actor_id.strip()
        ):
            raise ValueError("cashier_actor_id must be a non-empty string or None.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class RoleAssignHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    actor_id: str
    actor_type: str
    role_name: str
    display_name: str | None = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not self.actor_id or not isinstance(self.actor_id, str):
            raise ValueError("actor_id must be a non-empty string.")
        if not self.actor_type or not isinstance(self.actor_type, str):
            raise ValueError("actor_type must be a non-empty string.")
        if not self.role_name or not isinstance(self.role_name, str):
            raise ValueError("role_name must be a non-empty string.")
        if self.display_name is not None and not isinstance(self.display_name, str):
            raise ValueError("display_name must be a string or None.")
        if self.branch_id is not None and not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID or None.")


@dataclass(frozen=True)
class RoleRevokeHttpRequest:
    business_id: uuid.UUID
    actor: ActorMetadata | None
    actor_id: str
    role_name: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if self.actor is not None and not isinstance(self.actor, ActorMetadata):
            raise ValueError("actor must be ActorMetadata.")
        if not self.actor_id or not isinstance(self.actor_id, str):
            raise ValueError("actor_id must be a non-empty string.")
        if not self.role_name or not isinstance(self.role_name, str):
            raise ValueError("role_name must be a non-empty string.")
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
    meta: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        if self.ok:
            response: dict[str, Any] = {"ok": True, "data": self.data}
            if self.meta is not None:
                response["meta"] = dict(self.meta)
            return response
        if self.error is None:
            raise ValueError("error must be set when ok is False.")
        response = {"ok": False, "error": self.error.to_dict()}
        if self.meta is not None:
            response["meta"] = dict(self.meta)
        return response
