"""
BOS Policy - Document Authorization Guard
=========================================
Document feature gating and deterministic template/build validation.
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import ReasonCode, RejectionReason
from core.documents.builder import DocumentBuilder, DocumentBuilderError
from core.documents.registry import resolve_document_type
from core.feature_flags.evaluator import FeatureFlagEvaluator
from core.feature_flags.registry import FLAG_ENABLE_DOCUMENT_DESIGNER
from core.identity.requirements import SYSTEM_ALLOWED


def _resolve_document_provider(context, doc_provider):
    if doc_provider is not None:
        return doc_provider

    getter = getattr(context, "get_document_provider", None)
    if getter is None:
        return None

    resolved = getter()
    if callable(resolved):
        return resolved()
    return resolved


def _resolve_feature_flag_provider(context, feature_flag_provider):
    if feature_flag_provider is not None:
        return feature_flag_provider

    getter = getattr(context, "get_feature_flag_provider", None)
    if getter is None:
        return None

    resolved = getter()
    if callable(resolved):
        return resolved()
    return resolved


def document_authorization_guard(
    command: Command,
    context,
    doc_provider=None,
    feature_flag_provider=None,
) -> Optional[RejectionReason]:
    if command.actor_requirement == SYSTEM_ALLOWED:
        return None

    doc_type = resolve_document_type(command.command_type)
    if doc_type is None:
        return None

    resolved_feature_provider = _resolve_feature_flag_provider(
        context=context,
        feature_flag_provider=feature_flag_provider,
    )
    try:
        feature_result = FeatureFlagEvaluator.evaluate_for_flag_key(
            flag_key=FLAG_ENABLE_DOCUMENT_DESIGNER,
            command=command,
            provider=resolved_feature_provider,
        )
    except Exception:
        # Governance layer fail-open.
        return None

    if not feature_result.allowed:
        return RejectionReason(
            code=ReasonCode.DOCUMENT_FEATURE_DISABLED,
            message=feature_result.message or "Document feature is disabled.",
            policy_name="document_authorization_guard",
        )

    resolved_doc_provider = _resolve_document_provider(
        context=context,
        doc_provider=doc_provider,
    )

    try:
        # Internal-only artifact in v1: no contract expansion.
        DocumentBuilder.build_for_command(
            command=command,
            doc_type=doc_type,
            provider=resolved_doc_provider,
        )
    except DocumentBuilderError as exc:
        return RejectionReason(
            code=exc.code,
            message=exc.message,
            policy_name="document_authorization_guard",
        )
    except Exception:
        return RejectionReason(
            code=ReasonCode.DOCUMENT_TEMPLATE_INVALID,
            message="Document template evaluation failed.",
            policy_name="document_authorization_guard",
        )

    return None
