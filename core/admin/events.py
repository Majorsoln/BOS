"""
BOS Admin - Event Types and Payload Builders
============================================
Admin builds payload only. Envelope/hash-chain remain external.
"""

from __future__ import annotations

from core.admin.registry import (
    ADMIN_COMPLIANCE_PROFILE_DEACTIVATE_REQUEST,
    ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST,
    ADMIN_DOCUMENT_TEMPLATE_DEACTIVATE_REQUEST,
    ADMIN_DOCUMENT_TEMPLATE_UPSERT_REQUEST,
    ADMIN_FEATURE_FLAG_CLEAR_REQUEST,
    ADMIN_FEATURE_FLAG_SET_REQUEST,
)
from core.commands.base import Command


ADMIN_FEATURE_FLAG_SET_V1 = "admin.feature_flag.set.v1"
ADMIN_FEATURE_FLAG_CLEARED_V1 = "admin.feature_flag.cleared.v1"
ADMIN_COMPLIANCE_PROFILE_UPSERTED_V1 = "admin.compliance_profile.upserted.v1"
ADMIN_COMPLIANCE_PROFILE_DEACTIVATED_V1 = (
    "admin.compliance_profile.deactivated.v1"
)
ADMIN_DOCUMENT_TEMPLATE_UPSERTED_V1 = "admin.document_template.upserted.v1"
ADMIN_DOCUMENT_TEMPLATE_DEACTIVATED_V1 = (
    "admin.document_template.deactivated.v1"
)

ADMIN_EVENT_TYPES = (
    ADMIN_FEATURE_FLAG_SET_V1,
    ADMIN_FEATURE_FLAG_CLEARED_V1,
    ADMIN_COMPLIANCE_PROFILE_UPSERTED_V1,
    ADMIN_COMPLIANCE_PROFILE_DEACTIVATED_V1,
    ADMIN_DOCUMENT_TEMPLATE_UPSERTED_V1,
    ADMIN_DOCUMENT_TEMPLATE_DEACTIVATED_V1,
)

COMMAND_TO_EVENT_TYPE = {
    ADMIN_FEATURE_FLAG_SET_REQUEST: ADMIN_FEATURE_FLAG_SET_V1,
    ADMIN_FEATURE_FLAG_CLEAR_REQUEST: ADMIN_FEATURE_FLAG_CLEARED_V1,
    ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST: ADMIN_COMPLIANCE_PROFILE_UPSERTED_V1,
    ADMIN_COMPLIANCE_PROFILE_DEACTIVATE_REQUEST: ADMIN_COMPLIANCE_PROFILE_DEACTIVATED_V1,
    ADMIN_DOCUMENT_TEMPLATE_UPSERT_REQUEST: ADMIN_DOCUMENT_TEMPLATE_UPSERTED_V1,
    ADMIN_DOCUMENT_TEMPLATE_DEACTIVATE_REQUEST: ADMIN_DOCUMENT_TEMPLATE_DEACTIVATED_V1,
}


def resolve_admin_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_admin_event_types(event_type_registry) -> None:
    for event_type in sorted(ADMIN_EVENT_TYPES):
        event_type_registry.register(event_type)


def _base_payload(command: Command) -> dict:
    return {
        "business_id": command.business_id,
        "branch_id": command.branch_id,
        "actor_id": command.actor_id,
        "actor_type": command.actor_type,
        "correlation_id": command.correlation_id,
        "command_id": command.command_id,
    }


def build_feature_flag_set_payload(command: Command) -> dict:
    payload = _base_payload(command)
    payload.update(
        {
            "flag_key": command.payload["flag_key"],
            "status": command.payload["status"],
        }
    )
    return payload


def build_feature_flag_cleared_payload(command: Command, *, no_op: bool) -> dict:
    payload = _base_payload(command)
    payload.update(
        {
            "flag_key": command.payload["flag_key"],
            "no_op": bool(no_op),
        }
    )
    return payload


def build_compliance_profile_upserted_payload(
    command: Command,
    *,
    profile_id: str,
) -> dict:
    payload = _base_payload(command)
    payload.update(
        {
            "profile_id": profile_id,
            "version": command.payload["version"],
            "ruleset": command.payload["ruleset"],
            "status": command.payload["status"],
            "updated_by_actor_id": command.actor_id,
        }
    )
    return payload


def build_compliance_profile_deactivated_payload(
    command: Command,
    *,
    target_version: int | None,
    no_op: bool,
) -> dict:
    payload = _base_payload(command)
    payload.update(
        {
            "target_version": target_version,
            "no_op": bool(no_op),
        }
    )
    return payload


def build_document_template_upserted_payload(
    command: Command,
    *,
    template_id: str,
) -> dict:
    payload = _base_payload(command)
    payload.update(
        {
            "template_id": template_id,
            "doc_type": command.payload["doc_type"],
            "layout_spec": command.payload["layout_spec"],
            "schema_version": command.payload["schema_version"],
            "version": command.payload["version"],
            "status": command.payload["status"],
            "created_by_actor_id": command.actor_id,
        }
    )
    return payload


def build_document_template_deactivated_payload(
    command: Command,
    *,
    target_version: int | None,
    no_op: bool,
) -> dict:
    payload = _base_payload(command)
    payload.update(
        {
            "doc_type": command.payload["doc_type"],
            "target_version": target_version,
            "no_op": bool(no_op),
        }
    )
    return payload

