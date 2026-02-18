"""
BOS Identity Store - Deterministic Service Layer
================================================
DB-backed identity CRUD used by admin handlers and adapter bootstrap.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from django.db import IntegrityError, transaction

from core.identity_store.models import (
    Actor,
    Branch,
    Business,
    IdentityActorType,
    Role,
    RoleAssignment,
    RoleAssignmentStatus,
)
from core.permissions.constants import (
    PERMISSION_ADMIN_CONFIGURE,
    PERMISSION_CASH_MOVE,
    PERMISSION_CMD_EXECUTE_GENERIC,
    PERMISSION_DOC_ISSUE,
    PERMISSION_INVENTORY_MOVE,
    PERMISSION_POS_SELL,
    VALID_PERMISSIONS,
)
from core.permissions_store.models import RolePermission

DEFAULT_ADMIN_ROLE = "ADMIN"
DEFAULT_CASHIER_ROLE = "CASHIER"

DEFAULT_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    DEFAULT_ADMIN_ROLE: tuple(
        sorted(
            {
                PERMISSION_ADMIN_CONFIGURE,
                PERMISSION_CASH_MOVE,
                PERMISSION_CMD_EXECUTE_GENERIC,
                PERMISSION_DOC_ISSUE,
                PERMISSION_INVENTORY_MOVE,
                PERMISSION_POS_SELL,
            }
        )
    ),
    DEFAULT_CASHIER_ROLE: tuple(
        sorted(
            {
                PERMISSION_CASH_MOVE,
                PERMISSION_DOC_ISSUE,
                PERMISSION_POS_SELL,
            }
        )
    ),
}

_ACTOR_TYPE_NORMALIZATION = {
    "USER": IdentityActorType.HUMAN,
}
_VALID_ACTOR_TYPES = frozenset(
    {
        IdentityActorType.HUMAN,
        IdentityActorType.SYSTEM,
        IdentityActorType.DEVICE,
        IdentityActorType.AI,
    }
)


def _clean_string(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return cleaned


def _clean_optional_string(value: Any, *, default: str) -> str:
    if value is None:
        return default
    cleaned = str(value).strip()
    return cleaned or default


def _canonical_uuid(value: Any, *, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value).strip())
    except Exception as exc:
        raise ValueError(f"{field_name} must be a valid UUID.") from exc


def _canonical_optional_uuid(value: Any, *, field_name: str) -> uuid.UUID | None:
    if value is None:
        return None
    return _canonical_uuid(value, field_name=field_name)


def _normalize_actor_type(actor_type: str) -> str:
    normalized = _clean_string(actor_type, field_name="actor_type").upper()
    normalized = _ACTOR_TYPE_NORMALIZATION.get(normalized, normalized)
    if normalized not in _VALID_ACTOR_TYPES:
        raise ValueError("actor_type must be one of HUMAN, SYSTEM, DEVICE, AI.")
    return normalized


def _normalize_role_name(role_name: str) -> str:
    return _clean_string(role_name, field_name="role_name").upper()


def _deterministic_uuid(seed: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, seed)


def _deterministic_role_id(*, business_id: uuid.UUID, role_name: str) -> uuid.UUID:
    return _deterministic_uuid(f"bos.identity.role:{business_id}:{role_name}")


def _deterministic_branch_id(
    *,
    business_id: uuid.UUID,
    branch_name: str,
    index: int,
) -> uuid.UUID:
    return _deterministic_uuid(
        f"bos.identity.branch:{business_id}:{index}:{branch_name.upper()}"
    )


def _deterministic_assignment_id(
    *,
    business_id: uuid.UUID,
    branch_id: uuid.UUID | None,
    actor_id: str,
    role_id: uuid.UUID,
) -> uuid.UUID:
    branch_token = str(branch_id) if branch_id is not None else "BUSINESS"
    return _deterministic_uuid(
        f"bos.identity.assignment:{business_id}:{branch_token}:{actor_id}:{role_id}"
    )


def _default_branch_specs(business_id: uuid.UUID) -> tuple[dict[str, Any], ...]:
    defaults = (
        {"name": "MAIN", "timezone": "UTC"},
        {"name": "BACKOFFICE", "timezone": "UTC"},
    )
    normalized: list[dict[str, Any]] = []
    for index, branch in enumerate(defaults):
        normalized.append(
            {
                "branch_id": _deterministic_branch_id(
                    business_id=business_id,
                    branch_name=branch["name"],
                    index=index,
                ),
                "name": branch["name"],
                "timezone": branch["timezone"],
            }
        )
    return tuple(normalized)


def _normalize_branch_specs(
    *,
    business_id: uuid.UUID,
    branches: Iterable[Mapping[str, Any]] | None,
) -> tuple[dict[str, Any], ...]:
    if branches is None:
        return _default_branch_specs(business_id)

    if isinstance(branches, (str, bytes)):
        raise ValueError("branches must be a list/tuple of objects.")

    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(branches):
        if not isinstance(raw, Mapping):
            raise ValueError("branches items must be objects.")
        branch_name = _clean_string(
            raw.get("name"),
            field_name=f"branches[{index}].name",
        )
        timezone_value = _clean_optional_string(
            raw.get("timezone"),
            default="UTC",
        )
        raw_branch_id = raw.get("branch_id")
        if raw_branch_id is None:
            branch_id = _deterministic_branch_id(
                business_id=business_id,
                branch_name=branch_name,
                index=index,
            )
        else:
            branch_id = _canonical_uuid(
                raw_branch_id,
                field_name=f"branches[{index}].branch_id",
            )
        normalized.append(
            {
                "branch_id": branch_id,
                "name": branch_name,
                "timezone": timezone_value,
            }
        )

    ordered = sorted(normalized, key=lambda item: str(item["branch_id"]))
    deduplicated: list[dict[str, Any]] = []
    seen_branch_ids: set[uuid.UUID] = set()
    for item in ordered:
        if item["branch_id"] in seen_branch_ids:
            continue
        seen_branch_ids.add(item["branch_id"])
        deduplicated.append(item)
    return tuple(deduplicated)


def _upsert_business(
    *,
    business_id: uuid.UUID,
    name: str,
    default_currency: str,
    default_language: str,
) -> Business:
    business, created = Business.objects.get_or_create(
        business_id=business_id,
        defaults={
            "name": name,
            "default_currency": default_currency,
            "default_language": default_language,
        },
    )
    if created:
        return business

    update_fields: list[str] = []
    if business.name != name:
        business.name = name
        update_fields.append("name")
    if business.default_currency != default_currency:
        business.default_currency = default_currency
        update_fields.append("default_currency")
    if business.default_language != default_language:
        business.default_language = default_language
        update_fields.append("default_language")
    if update_fields:
        update_fields.append("updated_at")
        business.save(update_fields=update_fields)
    return business


def _upsert_branch(
    *,
    business: Business,
    branch_id: uuid.UUID,
    name: str,
    timezone_value: str,
) -> Branch:
    branch, created = Branch.objects.get_or_create(
        branch_id=branch_id,
        defaults={
            "business": business,
            "name": name,
            "timezone": timezone_value,
        },
    )
    if created:
        return branch

    if branch.business_id != business.business_id:
        raise ValueError("branch_id already belongs to a different business.")

    update_fields: list[str] = []
    if branch.name != name:
        branch.name = name
        update_fields.append("name")
    if branch.timezone != timezone_value:
        branch.timezone = timezone_value
        update_fields.append("timezone")
    if update_fields:
        update_fields.append("updated_at")
        branch.save(update_fields=update_fields)
    return branch


def _get_or_create_role(*, business: Business, role_name: str) -> Role:
    role, _ = Role.objects.get_or_create(
        business=business,
        name=role_name,
        defaults={
            "role_id": _deterministic_role_id(
                business_id=business.business_id,
                role_name=role_name,
            )
        },
    )
    return role


def _sync_role_permissions(
    *,
    role: Role,
    permissions: Iterable[str],
) -> None:
    normalized = tuple(
        sorted(
            {
                _clean_string(permission, field_name="permission_key")
                for permission in permissions
                if permission in VALID_PERMISSIONS
            }
        )
    )
    for permission_key in normalized:
        RolePermission.objects.get_or_create(
            role=role,
            permission_key=permission_key,
        )


def _get_or_create_actor(
    *,
    actor_id: str,
    actor_type: str,
    display_name: str | None,
) -> Actor:
    normalized_actor_id = _clean_string(actor_id, field_name="actor_id")
    normalized_actor_type = _normalize_actor_type(actor_type)
    normalized_display_name = (
        normalized_actor_id
        if display_name is None
        else _clean_optional_string(display_name, default=normalized_actor_id)
    )

    actor, created = Actor.objects.get_or_create(
        actor_id=normalized_actor_id,
        defaults={
            "actor_type": normalized_actor_type,
            "display_name": normalized_display_name,
        },
    )
    if created:
        return actor

    if actor.actor_type != normalized_actor_type:
        raise ValueError(
            f"actor_id '{normalized_actor_id}' exists with different actor_type."
        )

    if normalized_display_name and actor.display_name != normalized_display_name:
        actor.display_name = normalized_display_name
        actor.save(update_fields=["display_name", "updated_at"])
    return actor


def _resolve_business(business_id: uuid.UUID | str) -> Business:
    canonical_business_id = _canonical_uuid(
        business_id,
        field_name="business_id",
    )
    business = Business.objects.filter(business_id=canonical_business_id).first()
    if business is None:
        raise ValueError(f"business_id '{canonical_business_id}' was not found.")
    return business


def _resolve_branch_for_business(
    *,
    business: Business,
    branch_id: uuid.UUID | str | None,
) -> Branch | None:
    canonical_branch_id = _canonical_optional_uuid(
        branch_id,
        field_name="branch_id",
    )
    if canonical_branch_id is None:
        return None

    branch = Branch.objects.filter(
        branch_id=canonical_branch_id,
        business_id=business.business_id,
    ).first()
    if branch is None:
        raise ValueError(
            f"branch_id '{canonical_branch_id}' is not in business '{business.business_id}'."
        )
    return branch


def _resolve_role_for_business(*, business: Business, role_name: str) -> Role:
    normalized_role_name = _normalize_role_name(role_name)
    role = Role.objects.filter(
        business_id=business.business_id,
        name=normalized_role_name,
    ).first()
    if role is None:
        raise ValueError(
            f"role_name '{normalized_role_name}' was not found for business '{business.business_id}'."
        )
    return role


def _upsert_assignment(
    *,
    business: Business,
    branch: Branch | None,
    actor: Actor,
    role: Role,
    status: str,
) -> RoleAssignment:
    qs = RoleAssignment.objects.filter(
        business=business,
        branch=branch,
        actor=actor,
        role=role,
    ).order_by("id")
    assignment = qs.first()
    if assignment is None:
        deterministic_id = _deterministic_assignment_id(
            business_id=business.business_id,
            branch_id=None if branch is None else branch.branch_id,
            actor_id=actor.actor_id,
            role_id=role.role_id,
        )
        try:
            assignment = RoleAssignment.objects.create(
                id=deterministic_id,
                business=business,
                branch=branch,
                actor=actor,
                role=role,
                status=status,
            )
        except IntegrityError:
            assignment = qs.first()
            if assignment is None:
                raise

    if assignment.status != status:
        assignment.status = status
        assignment.save(update_fields=["status", "updated_at"])
    return assignment


def _permission_map_for_roles(role_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, tuple[str, ...]]:
    permissions_by_role: dict[uuid.UUID, list[str]] = defaultdict(list)
    rows = RolePermission.objects.filter(role_id__in=tuple(role_ids)).order_by(
        "role_id",
        "permission_key",
    )
    for row in rows:
        permissions_by_role[row.role_id].append(row.permission_key)
    return {
        role_id: tuple(sorted(permission_values))
        for role_id, permission_values in permissions_by_role.items()
    }


def serialize_business(business: Business) -> dict[str, Any]:
    return {
        "business_id": str(business.business_id),
        "name": business.name,
        "default_currency": business.default_currency,
        "default_language": business.default_language,
    }


def serialize_branch(branch: Branch) -> dict[str, Any]:
    return {
        "branch_id": str(branch.branch_id),
        "business_id": str(branch.business_id),
        "name": branch.name,
        "timezone": branch.timezone,
    }


def serialize_role(role: Role, *, permissions: tuple[str, ...]) -> dict[str, Any]:
    return {
        "role_id": str(role.role_id),
        "business_id": str(role.business_id),
        "name": role.name,
        "permissions": tuple(permissions),
    }


def serialize_role_assignment(
    assignment: RoleAssignment,
    *,
    role_permissions: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "id": str(assignment.id),
        "business_id": str(assignment.business_id),
        "branch_id": None if assignment.branch_id is None else str(assignment.branch_id),
        "actor_id": assignment.actor_id,
        "actor_type": assignment.actor.actor_type,
        "role_id": str(assignment.role_id),
        "role_name": assignment.role.name,
        "role_permissions": tuple(role_permissions),
        "status": assignment.status,
    }


def serialize_actor(
    actor: Actor,
    *,
    assignments: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    return {
        "actor_id": actor.actor_id,
        "actor_type": actor.actor_type,
        "display_name": actor.display_name or None,
        "assignments": assignments,
    }


@transaction.atomic
def bootstrap_identity(
    *,
    business_id: uuid.UUID | str,
    business_name: str,
    default_currency: str = "USD",
    default_language: str = "en",
    branches: Iterable[Mapping[str, Any]] | None = None,
    admin_actor_id: str | None = None,
    cashier_actor_id: str | None = None,
) -> dict[str, Any]:
    canonical_business_id = _canonical_uuid(business_id, field_name="business_id")
    canonical_business_name = _clean_string(business_name, field_name="business_name")
    canonical_currency = _clean_optional_string(default_currency, default="USD").upper()
    canonical_language = _clean_optional_string(default_language, default="en").lower()

    business = _upsert_business(
        business_id=canonical_business_id,
        name=canonical_business_name,
        default_currency=canonical_currency,
        default_language=canonical_language,
    )

    branch_specs = _normalize_branch_specs(
        business_id=business.business_id,
        branches=branches,
    )
    stored_branches: list[Branch] = []
    for spec in branch_specs:
        stored_branches.append(
            _upsert_branch(
                business=business,
                branch_id=spec["branch_id"],
                name=spec["name"],
                timezone_value=spec["timezone"],
            )
        )
    stored_branches = sorted(stored_branches, key=lambda branch: str(branch.branch_id))

    roles: dict[str, Role] = {}
    for role_name in sorted(DEFAULT_ROLE_PERMISSIONS):
        role = _get_or_create_role(business=business, role_name=role_name)
        _sync_role_permissions(
            role=role,
            permissions=DEFAULT_ROLE_PERMISSIONS[role_name],
        )
        roles[role_name] = role

    assignments: list[RoleAssignment] = []
    if admin_actor_id is not None:
        admin_actor = _get_or_create_actor(
            actor_id=admin_actor_id,
            actor_type=IdentityActorType.HUMAN,
            display_name=admin_actor_id,
        )
        assignments.append(
            _upsert_assignment(
                business=business,
                branch=None,
                actor=admin_actor,
                role=roles[DEFAULT_ADMIN_ROLE],
                status=RoleAssignmentStatus.ACTIVE,
            )
        )

    if cashier_actor_id is not None and stored_branches:
        cashier_actor = _get_or_create_actor(
            actor_id=cashier_actor_id,
            actor_type=IdentityActorType.HUMAN,
            display_name=cashier_actor_id,
        )
        assignments.append(
            _upsert_assignment(
                business=business,
                branch=stored_branches[0],
                actor=cashier_actor,
                role=roles[DEFAULT_CASHIER_ROLE],
                status=RoleAssignmentStatus.ACTIVE,
            )
        )

    ordered_roles = tuple(
        sorted(roles.values(), key=lambda role: (role.name, str(role.role_id)))
    )
    permission_map = _permission_map_for_roles(role.role_id for role in ordered_roles)
    ordered_assignments = tuple(
        sorted(
            assignments,
            key=lambda row: (
                row.actor_id,
                "" if row.branch_id is None else str(row.branch_id),
                row.role.name,
                str(row.id),
            ),
        )
    )

    return {
        "business": serialize_business(business),
        "branches": tuple(serialize_branch(branch) for branch in stored_branches),
        "roles": tuple(
            serialize_role(
                role,
                permissions=permission_map.get(role.role_id, tuple()),
            )
            for role in ordered_roles
        ),
        "assignments": tuple(
            serialize_role_assignment(
                assignment,
                role_permissions=permission_map.get(assignment.role_id, tuple()),
            )
            for assignment in ordered_assignments
        ),
    }


@transaction.atomic
def assign_role(
    *,
    business_id: uuid.UUID | str,
    actor_id: str,
    actor_type: str,
    role_name: str,
    branch_id: uuid.UUID | str | None = None,
    display_name: str | None = None,
) -> dict[str, Any]:
    business = _resolve_business(business_id)
    role = _resolve_role_for_business(business=business, role_name=role_name)
    branch = _resolve_branch_for_business(
        business=business,
        branch_id=branch_id,
    )
    actor = _get_or_create_actor(
        actor_id=actor_id,
        actor_type=actor_type,
        display_name=display_name,
    )
    assignment = _upsert_assignment(
        business=business,
        branch=branch,
        actor=actor,
        role=role,
        status=RoleAssignmentStatus.ACTIVE,
    )
    permission_map = _permission_map_for_roles((role.role_id,))
    return serialize_role_assignment(
        assignment,
        role_permissions=permission_map.get(role.role_id, tuple()),
    )


@transaction.atomic
def revoke_role(
    *,
    business_id: uuid.UUID | str,
    actor_id: str,
    role_name: str,
    branch_id: uuid.UUID | str | None = None,
) -> dict[str, Any] | None:
    business = _resolve_business(business_id)
    role = _resolve_role_for_business(business=business, role_name=role_name)
    branch = _resolve_branch_for_business(
        business=business,
        branch_id=branch_id,
    )
    normalized_actor_id = _clean_string(actor_id, field_name="actor_id")

    assignment = (
        RoleAssignment.objects.select_related("actor", "role")
        .filter(
            business_id=business.business_id,
            branch=branch,
            actor_id=normalized_actor_id,
            role_id=role.role_id,
        )
        .order_by("id")
        .first()
    )
    if assignment is None:
        return None

    if assignment.status != RoleAssignmentStatus.INACTIVE:
        assignment.status = RoleAssignmentStatus.INACTIVE
        assignment.save(update_fields=["status", "updated_at"])

    permission_map = _permission_map_for_roles((assignment.role_id,))
    return serialize_role_assignment(
        assignment,
        role_permissions=permission_map.get(assignment.role_id, tuple()),
    )


def list_roles_for_business(
    business_id: uuid.UUID | str,
) -> tuple[dict[str, Any], ...]:
    business = _resolve_business(business_id)
    roles = tuple(
        Role.objects.filter(business_id=business.business_id).order_by(
            "name",
            "role_id",
        )
    )
    permission_map = _permission_map_for_roles(role.role_id for role in roles)
    return tuple(
        serialize_role(role, permissions=permission_map.get(role.role_id, tuple()))
        for role in roles
    )


def list_role_assignments_for_business(
    business_id: uuid.UUID | str,
) -> tuple[dict[str, Any], ...]:
    business = _resolve_business(business_id)
    assignments = tuple(
        RoleAssignment.objects.select_related("actor", "role")
        .filter(business_id=business.business_id)
        .order_by(
            "actor_id",
            "branch_id",
            "role__name",
            "id",
        )
    )
    permission_map = _permission_map_for_roles(
        assignment.role_id for assignment in assignments
    )
    return tuple(
        serialize_role_assignment(
            assignment,
            role_permissions=permission_map.get(assignment.role_id, tuple()),
        )
        for assignment in assignments
    )


def list_actors_for_business(
    business_id: uuid.UUID | str,
) -> tuple[dict[str, Any], ...]:
    business = _resolve_business(business_id)
    assignments = tuple(
        RoleAssignment.objects.select_related("actor", "role")
        .filter(business_id=business.business_id)
        .order_by(
            "actor_id",
            "branch_id",
            "role__name",
            "id",
        )
    )
    permission_map = _permission_map_for_roles(
        assignment.role_id for assignment in assignments
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    actors: dict[str, Actor] = {}
    for assignment in assignments:
        actors[assignment.actor_id] = assignment.actor
        grouped[assignment.actor_id].append(
            serialize_role_assignment(
                assignment,
                role_permissions=permission_map.get(assignment.role_id, tuple()),
            )
        )

    ordered_actor_ids = sorted(grouped.keys())
    return tuple(
        serialize_actor(
            actors[actor_id],
            assignments=tuple(grouped[actor_id]),
        )
        for actor_id in ordered_actor_ids
    )
