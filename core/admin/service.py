"""
BOS Admin - Application Service
===============================
Admin CRUD orchestration over the existing command/event pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol

from core.admin.commands import (
    AdminCommandContext,
    ComplianceProfileDeactivateRequest,
    ComplianceProfileUpsertRequest,
    DocumentTemplateDeactivateRequest,
    DocumentTemplateUpsertRequest,
    FeatureFlagClearRequest,
    FeatureFlagSetRequest,
)
from core.admin.events import (
    build_compliance_profile_deactivated_payload,
    build_compliance_profile_upserted_payload,
    build_document_template_deactivated_payload,
    build_document_template_upserted_payload,
    build_feature_flag_cleared_payload,
    build_feature_flag_set_payload,
    register_admin_event_types,
    resolve_admin_event_type,
)
from core.admin.registry import (
    ADMIN_COMPLIANCE_PROFILE_DEACTIVATE_REQUEST,
    ADMIN_COMMAND_TYPES,
    ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST,
    ADMIN_DOCUMENT_TEMPLATE_DEACTIVATE_REQUEST,
    ADMIN_DOCUMENT_TEMPLATE_UPSERT_REQUEST,
    ADMIN_FEATURE_FLAG_CLEAR_REQUEST,
    ADMIN_FEATURE_FLAG_SET_REQUEST,
    is_admin_upsert_command_type,
)
from core.admin.projections import AdminProjectionStore
from core.commands.base import Command
from core.commands.rejection import ReasonCode, RejectionReason
from core.compliance.models import PROFILE_ACTIVE
from core.documents.models import TEMPLATE_ACTIVE


class EventFactoryProtocol(Protocol):
    def __call__(
        self,
        *,
        command: Command,
        event_type: str,
        payload: dict,
    ) -> dict:
        ...


class PersistEventProtocol(Protocol):
    def __call__(
        self,
        *,
        event_data: dict,
        context: Any,
        registry: Any,
        **kwargs: Any,
    ) -> Any:
        ...


@dataclass(frozen=True)
class AdminExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


class _AdminCommandHandler:
    def __init__(self, service: "AdminDataService"):
        self._service = service

    def execute(self, command: Command) -> AdminExecutionResult:
        return self._service._execute_admin_command(command)


class AdminDataService:
    def __init__(
        self,
        *,
        business_context,
        dispatcher,
        command_bus,
        event_factory: EventFactoryProtocol,
        persist_event: PersistEventProtocol,
        event_type_registry,
        projection_store: AdminProjectionStore | None = None,
    ):
        self._business_context = business_context
        self._dispatcher = dispatcher
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or AdminProjectionStore()
        self._recorded_events: list[dict] = []

        register_admin_event_types(self._event_type_registry)
        self._dispatcher.register_policy(self._admin_version_invariant_guard)
        self._register_handlers()

    def _register_handlers(self) -> None:
        handler = _AdminCommandHandler(self)
        for command_type in sorted(ADMIN_COMMAND_TYPES):
            self._command_bus.register_handler(command_type, handler)

    def _admin_version_invariant_guard(
        self,
        command: Command,
        context,
    ) -> Optional[RejectionReason]:
        if not is_admin_upsert_command_type(command.command_type):
            return None

        if command.command_type == ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST:
            expected = self._projection_store.compliance_profiles.next_version(
                business_id=command.business_id,
                branch_id=command.branch_id,
            )
        elif command.command_type == ADMIN_DOCUMENT_TEMPLATE_UPSERT_REQUEST:
            doc_type = command.payload.get("doc_type")
            expected = self._projection_store.document_templates.next_version(
                business_id=command.business_id,
                branch_id=command.branch_id,
                doc_type=doc_type,
            )
        else:
            return None

        provided_version = command.payload.get("version")
        if provided_version is None:
            return RejectionReason(
                code=ReasonCode.ADMIN_VERSION_CONFLICT,
                message=(
                    "Upsert version must be resolved before dispatch. "
                    f"expected={expected}, provided=None."
                ),
                policy_name="admin_version_invariant_guard",
            )

        if provided_version != expected:
            return RejectionReason(
                code=ReasonCode.ADMIN_VERSION_CONFLICT,
                message=(
                    "Provided version does not match deterministic next "
                    f"version for scope. expected={expected}, "
                    f"provided={provided_version}."
                ),
                policy_name="admin_version_invariant_guard",
            )

        return None

    def _build_profile_id(self, command: Command) -> str:
        scope_value = (
            "business" if command.branch_id is None else str(command.branch_id)
        )
        version = command.payload["version"]
        return (
            f"admin.compliance.{command.business_id}.{scope_value}.v{version}"
        )

    def _build_template_id(self, command: Command) -> str:
        scope_value = (
            "business" if command.branch_id is None else str(command.branch_id)
        )
        version = command.payload["version"]
        doc_type = str(command.payload["doc_type"]).lower()
        return (
            f"admin.document.{doc_type}.{command.business_id}."
            f"{scope_value}.v{version}"
        )

    def _build_admin_payload(self, command: Command) -> dict:
        if command.command_type == ADMIN_FEATURE_FLAG_SET_REQUEST:
            return build_feature_flag_set_payload(command)

        if command.command_type == ADMIN_FEATURE_FLAG_CLEAR_REQUEST:
            no_op = not self._projection_store.feature_flags.has_flag(
                business_id=command.business_id,
                branch_id=command.branch_id,
                flag_key=command.payload["flag_key"],
            )
            return build_feature_flag_cleared_payload(command, no_op=no_op)

        if command.command_type == ADMIN_COMPLIANCE_PROFILE_UPSERT_REQUEST:
            profile_id = self._build_profile_id(command)
            return build_compliance_profile_upserted_payload(
                command,
                profile_id=profile_id,
            )

        if command.command_type == ADMIN_COMPLIANCE_PROFILE_DEACTIVATE_REQUEST:
            target_version = (
                self._projection_store.compliance_profiles.latest_active_version(
                    business_id=command.business_id,
                    branch_id=command.branch_id,
                )
            )
            return build_compliance_profile_deactivated_payload(
                command,
                target_version=target_version,
                no_op=(target_version is None),
            )

        if command.command_type == ADMIN_DOCUMENT_TEMPLATE_UPSERT_REQUEST:
            template_id = self._build_template_id(command)
            return build_document_template_upserted_payload(
                command,
                template_id=template_id,
            )

        if command.command_type == ADMIN_DOCUMENT_TEMPLATE_DEACTIVATE_REQUEST:
            target_version = (
                self._projection_store.document_templates.latest_active_version(
                    business_id=command.business_id,
                    branch_id=command.branch_id,
                    doc_type=command.payload["doc_type"],
                )
            )
            return build_document_template_deactivated_payload(
                command,
                target_version=target_version,
                no_op=(target_version is None),
            )

        raise ValueError(
            f"Unsupported admin command type: {command.command_type}"
        )

    def _is_persist_accepted(self, persist_result: Any) -> bool:
        if hasattr(persist_result, "accepted"):
            return bool(getattr(persist_result, "accepted"))
        if isinstance(persist_result, dict):
            return bool(persist_result.get("accepted"))
        return bool(persist_result)

    def _execute_admin_command(self, command: Command) -> AdminExecutionResult:
        event_type = resolve_admin_event_type(command.command_type)
        if event_type is None:
            raise ValueError(
                f"Unsupported admin command type: {command.command_type}"
            )

        payload = self._build_admin_payload(command)
        event_data = self._event_factory(
            command=command,
            event_type=event_type,
            payload=payload,
        )
        persist_result = self._persist_event(
            event_data=event_data,
            context=self._business_context,
            registry=self._event_type_registry,
            scope_requirement=command.scope_requirement,
        )

        applied = False
        if self._is_persist_accepted(persist_result):
            self._projection_store.apply(event_data)
            self._recorded_events.append(event_data)
            applied = True

        return AdminExecutionResult(
            event_type=event_type,
            event_data=event_data,
            persist_result=persist_result,
            projection_applied=applied,
        )

    def get_recorded_events(self) -> tuple[dict, ...]:
        return tuple(self._recorded_events)

    def projection_snapshot(self) -> dict:
        return self._projection_store.snapshot()

    def set_feature_flag(
        self,
        context: AdminCommandContext,
        flag_key: str,
        status: str,
        branch_id=None,
    ):
        request = FeatureFlagSetRequest(
            flag_key=flag_key,
            status=status,
            branch_id=branch_id,
        )
        command = request.to_command(context)
        return self._command_bus.handle(command)

    def clear_feature_flag(
        self,
        context: AdminCommandContext,
        flag_key: str,
        branch_id=None,
    ):
        request = FeatureFlagClearRequest(
            flag_key=flag_key,
            branch_id=branch_id,
        )
        command = request.to_command(context)
        return self._command_bus.handle(command)

    def upsert_compliance_profile(
        self,
        context: AdminCommandContext,
        branch_id,
        ruleset,
        status: str = PROFILE_ACTIVE,
        version: int | None = None,
    ):
        request = ComplianceProfileUpsertRequest(
            ruleset=tuple(ruleset),
            branch_id=branch_id,
            status=status,
            version=version,
        )
        if request.version is None:
            resolved_version = self._projection_store.compliance_profiles.next_version(
                business_id=context.business_id,
                branch_id=branch_id,
            )
            request = request.with_resolved_version(resolved_version)
        command = request.to_command(context)
        return self._command_bus.handle(command)

    def deactivate_compliance_profile(
        self,
        context: AdminCommandContext,
        branch_id,
    ):
        request = ComplianceProfileDeactivateRequest(branch_id=branch_id)
        command = request.to_command(context)
        return self._command_bus.handle(command)

    def upsert_document_template(
        self,
        context: AdminCommandContext,
        doc_type: str,
        branch_id,
        layout_spec: dict,
        status: str = TEMPLATE_ACTIVE,
        version: int | None = None,
    ):
        request = DocumentTemplateUpsertRequest(
            doc_type=doc_type,
            layout_spec=layout_spec,
            branch_id=branch_id,
            status=status,
            version=version,
        )
        if request.version is None:
            resolved_version = self._projection_store.document_templates.next_version(
                business_id=context.business_id,
                branch_id=branch_id,
                doc_type=doc_type,
            )
            request = request.with_resolved_version(resolved_version)
        command = request.to_command(context)
        return self._command_bus.handle(command)

    def deactivate_document_template(
        self,
        context: AdminCommandContext,
        doc_type: str,
        branch_id,
    ):
        request = DocumentTemplateDeactivateRequest(
            doc_type=doc_type,
            branch_id=branch_id,
        )
        command = request.to_command(context)
        return self._command_bus.handle(command)
