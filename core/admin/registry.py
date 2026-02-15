"""
BOS Admin - Command Registry
============================
Canonical command types for admin data management.
"""

from __future__ import annotations


ADMIN_FEATURE_FLAG_SET_REQUEST = "admin.feature_flag.set.request"
ADMIN_FEATURE_FLAG_CLEAR_REQUEST = "admin.feature_flag.clear.request"
ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST = (
    "admin.compliance_profile.upsert.request"
)
ADMIN_COMPLIANCE_PROFILE_DEACTIVATE_REQUEST = (
    "admin.compliance_profile.deactivate.request"
)
ADMIN_DOCUMENT_TEMPLATE_UPSERT_REQUEST = (
    "admin.document_template.upsert.request"
)
ADMIN_DOCUMENT_TEMPLATE_DEACTIVATE_REQUEST = (
    "admin.document_template.deactivate.request"
)

ADMIN_COMMAND_TYPES = frozenset(
    {
        ADMIN_FEATURE_FLAG_SET_REQUEST,
        ADMIN_FEATURE_FLAG_CLEAR_REQUEST,
        ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST,
        ADMIN_COMPLIANCE_PROFILE_DEACTIVATE_REQUEST,
        ADMIN_DOCUMENT_TEMPLATE_UPSERT_REQUEST,
        ADMIN_DOCUMENT_TEMPLATE_DEACTIVATE_REQUEST,
    }
)

ADMIN_COMPLIANCE_COMMAND_TYPES = frozenset(
    {
        ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST,
        ADMIN_COMPLIANCE_PROFILE_DEACTIVATE_REQUEST,
    }
)

ADMIN_UPSERT_COMMAND_TYPES = frozenset(
    {
        ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST,
        ADMIN_DOCUMENT_TEMPLATE_UPSERT_REQUEST,
    }
)


def is_admin_command_type(command_type: str) -> bool:
    return command_type in ADMIN_COMMAND_TYPES


def is_admin_compliance_command_type(command_type: str) -> bool:
    return command_type in ADMIN_COMPLIANCE_COMMAND_TYPES


def is_admin_upsert_command_type(command_type: str) -> bool:
    return command_type in ADMIN_UPSERT_COMMAND_TYPES

