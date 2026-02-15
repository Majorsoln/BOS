from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.admin.commands import AdminCommandContext
from core.admin.events import (
    ADMIN_COMPLIANCE_PROFILE_DEACTIVATED_V1,
    ADMIN_COMPLIANCE_PROFILE_UPSERTED_V1,
    ADMIN_DOCUMENT_TEMPLATE_DEACTIVATED_V1,
    ADMIN_DOCUMENT_TEMPLATE_UPSERTED_V1,
    ADMIN_FEATURE_FLAG_CLEARED_V1,
    ADMIN_FEATURE_FLAG_SET_V1,
)
from core.admin.projections import AdminProjectionStore
from core.admin.service import AdminDataService
from core.commands.bus import CommandBus
from core.commands.dispatcher import CommandDispatcher
from core.compliance import (
    OP_EXISTS,
    PROFILE_ACTIVE,
    RULE_BLOCK,
    ComplianceProfile,
    ComplianceRule,
    InMemoryComplianceProvider,
)
from core.context.actor_context import ActorContext
from core.documents.models import DOCUMENT_INVOICE
from core.feature_flags import (
    FEATURE_DISABLED,
    FEATURE_ENABLED,
    FLAG_ENABLE_COMPLIANCE_ENGINE,
    FeatureFlag,
    InMemoryFeatureFlagProvider,
)
from core.permissions import (
    InMemoryPermissionProvider,
    PERMISSION_ADMIN_CONFIGURE,
    Role,
    ScopeGrant,
)


BUSINESS_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-admin-business")
OTHER_BUSINESS_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-admin-other-business")
BRANCH_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-admin-branch")
OTHER_BRANCH_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-admin-other-branch")
ACTOR_ID = "admin-user-1"
ISSUED_AT = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)


class StubContext:
    def __init__(self, business_id=BUSINESS_ID, branches=None):
        self._business_id = business_id
        self._branches = set(branches or {BRANCH_ID, OTHER_BRANCH_ID})

    def has_active_context(self) -> bool:
        return True

    def get_active_business_id(self):
        return self._business_id

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        return branch_id in self._branches

    def get_business_lifecycle_state(self) -> str:
        return "ACTIVE"


class StubEventTypeRegistry:
    def __init__(self):
        self._registered = set()

    def register(self, event_type: str) -> None:
        self._registered.add(event_type)

    def is_registered(self, event_type: str) -> bool:
        return event_type in self._registered


class PersistEventStub:
    def __init__(self):
        self.persisted_events = []

    def __call__(self, event_data: dict, context, registry, **kwargs):
        self.persisted_events.append(event_data)
        return {"accepted": True}


def _deterministic_uuid(seed: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"bos-admin-tests:{seed}")


def _admin_command_context(
    seed: str,
    *,
    business_id: uuid.UUID = BUSINESS_ID,
    actor_id: str = ACTOR_ID,
) -> AdminCommandContext:
    actor_context = ActorContext(actor_type="HUMAN", actor_id=actor_id)
    return AdminCommandContext(
        business_id=business_id,
        actor_type="HUMAN",
        actor_id=actor_id,
        actor_context=actor_context,
        command_id=_deterministic_uuid(f"{seed}:command"),
        correlation_id=_deterministic_uuid(f"{seed}:correlation"),
        issued_at=ISSUED_AT,
    )


def _admin_permission_provider(
    *,
    actor_id: str = ACTOR_ID,
    business_id: uuid.UUID = BUSINESS_ID,
) -> InMemoryPermissionProvider:
    role = Role(
        role_id="admin-role",
        permissions=(PERMISSION_ADMIN_CONFIGURE,),
    )
    grant = ScopeGrant(
        actor_id=actor_id,
        role_id="admin-role",
        business_id=business_id,
    )
    return InMemoryPermissionProvider(roles=(role,), grants=(grant,))


def _deterministic_event_factory(*, command, event_type: str, payload: dict) -> dict:
    return {
        "event_id": command.command_id,
        "event_type": event_type,
        "business_id": command.business_id,
        "branch_id": command.branch_id,
        "correlation_id": command.correlation_id,
        "actor_id": command.actor_id,
        "payload": payload,
        "issued_at": command.issued_at,
    }


def _build_service(
    *,
    permission_provider=None,
    feature_flag_provider=None,
    compliance_provider=None,
    document_provider=None,
    context=None,
):
    context = context or StubContext()
    permission_provider = permission_provider or _admin_permission_provider(
        business_id=context.get_active_business_id()
    )
    persist_stub = PersistEventStub()
    event_type_registry = StubEventTypeRegistry()
    dispatcher = CommandDispatcher(
        context=context,
        permission_provider=permission_provider,
        feature_flag_provider=feature_flag_provider,
        compliance_provider=compliance_provider,
        document_provider=document_provider,
    )
    command_bus = CommandBus(
        dispatcher=dispatcher,
        persist_event=persist_stub,
        context=context,
        event_type_registry=event_type_registry,
    )
    service = AdminDataService(
        business_context=context,
        dispatcher=dispatcher,
        command_bus=command_bus,
        event_factory=_deterministic_event_factory,
        persist_event=persist_stub,
        event_type_registry=event_type_registry,
    )
    return service, persist_stub


def _rule(seed: str) -> ComplianceRule:
    return ComplianceRule(
        rule_key=f"RULE-{seed}",
        applies_to="DOCUMENT:INVOICE",
        severity=RULE_BLOCK,
        predicate={"field": "command.command_type", "op": OP_EXISTS},
        message="blocked",
    )


def _layout(label: str) -> dict:
    return {
        "header_fields": [f"{label}-header"],
        "line_items_path": "items",
        "total_fields": [f"{label}-total"],
        "footer_fields": [f"{label}-footer"],
    }


def test_set_feature_flag_appends_event_and_updates_business_and_branch_projections():
    service, _ = _build_service()
    business_context = _admin_command_context("flag-business")
    branch_context = _admin_command_context("flag-branch")

    business_result = service.set_feature_flag(
        business_context,
        flag_key="ENABLE_DOCUMENT_DESIGNER",
        status=FEATURE_ENABLED,
    )
    branch_result = service.set_feature_flag(
        branch_context,
        flag_key="ENABLE_DOCUMENT_DESIGNER",
        status=FEATURE_DISABLED,
        branch_id=BRANCH_ID,
    )

    assert business_result.is_accepted
    assert branch_result.is_accepted
    assert business_result.execution_result.event_type == ADMIN_FEATURE_FLAG_SET_V1
    assert branch_result.execution_result.event_type == ADMIN_FEATURE_FLAG_SET_V1
    assert service.projection_snapshot()["feature_flags"] == (
        (str(BUSINESS_ID), "", "ENABLE_DOCUMENT_DESIGNER", FEATURE_ENABLED),
        (
            str(BUSINESS_ID),
            str(BRANCH_ID),
            "ENABLE_DOCUMENT_DESIGNER",
            FEATURE_DISABLED,
        ),
    )


def test_clear_feature_flag_existing_removes_record():
    service, _ = _build_service()
    set_context = _admin_command_context("flag-clear-set")
    clear_context = _admin_command_context("flag-clear-do")
    service.set_feature_flag(
        set_context,
        flag_key="ENABLE_COMPLIANCE_ENGINE",
        status=FEATURE_ENABLED,
    )

    result = service.clear_feature_flag(
        clear_context,
        flag_key="ENABLE_COMPLIANCE_ENGINE",
    )

    assert result.is_accepted
    assert result.execution_result.event_type == ADMIN_FEATURE_FLAG_CLEARED_V1
    assert result.execution_result.event_data["payload"]["no_op"] is False
    assert service.projection_snapshot()["feature_flags"] == tuple()


def test_clear_feature_flag_missing_appends_noop_and_projection_unchanged():
    service, _ = _build_service()
    before = service.projection_snapshot()

    result = service.clear_feature_flag(
        _admin_command_context("flag-clear-missing"),
        flag_key="ENABLE_WORKSHOP_ENGINE",
    )

    after = service.projection_snapshot()
    assert result.is_accepted
    assert result.execution_result.event_type == ADMIN_FEATURE_FLAG_CLEARED_V1
    assert result.execution_result.event_data["payload"]["no_op"] is True
    assert before == after


def test_compliance_upsert_versioning_and_branch_override_scope():
    service, _ = _build_service()
    business_result = service.upsert_compliance_profile(
        _admin_command_context("compliance-business"),
        branch_id=None,
        ruleset=(_rule("BUSINESS"),),
        status=PROFILE_ACTIVE,
    )
    branch_result = service.upsert_compliance_profile(
        _admin_command_context("compliance-branch"),
        branch_id=BRANCH_ID,
        ruleset=(_rule("BRANCH"),),
        status=PROFILE_ACTIVE,
    )

    assert business_result.is_accepted
    assert branch_result.is_accepted
    assert business_result.execution_result.event_type == ADMIN_COMPLIANCE_PROFILE_UPSERTED_V1
    assert branch_result.execution_result.event_type == ADMIN_COMPLIANCE_PROFILE_UPSERTED_V1
    assert service.projection_snapshot()["compliance_profiles"] == (
        (
            str(BUSINESS_ID),
            "",
            1,
            f"admin.compliance.{BUSINESS_ID}.business.v1",
            "ACTIVE",
        ),
        (
            str(BUSINESS_ID),
            str(BRANCH_ID),
            1,
            f"admin.compliance.{BUSINESS_ID}.{BRANCH_ID}.v1",
            "ACTIVE",
        ),
    )


def test_compliance_deactivate_existing_and_missing_noop():
    service, _ = _build_service()
    service.upsert_compliance_profile(
        _admin_command_context("compliance-upsert"),
        branch_id=None,
        ruleset=(_rule("UPSERT"),),
    )
    deactivate_existing = service.deactivate_compliance_profile(
        _admin_command_context("compliance-deactivate"),
        branch_id=None,
    )
    deactivate_missing = service.deactivate_compliance_profile(
        _admin_command_context("compliance-deactivate-missing"),
        branch_id=BRANCH_ID,
    )

    assert deactivate_existing.is_accepted
    assert deactivate_existing.execution_result.event_type == ADMIN_COMPLIANCE_PROFILE_DEACTIVATED_V1
    assert deactivate_existing.execution_result.event_data["payload"]["no_op"] is False
    assert deactivate_missing.is_accepted
    assert deactivate_missing.execution_result.event_data["payload"]["no_op"] is True
    assert service.projection_snapshot()["compliance_profiles"] == (
        (
            str(BUSINESS_ID),
            "",
            1,
            f"admin.compliance.{BUSINESS_ID}.business.v1",
            "INACTIVE",
        ),
    )


def test_document_upsert_and_deactivate_respects_exact_branch_scope():
    service, _ = _build_service()
    business_upsert = service.upsert_document_template(
        _admin_command_context("doc-upsert-business"),
        doc_type=DOCUMENT_INVOICE,
        branch_id=None,
        layout_spec=_layout("business"),
    )
    branch_upsert = service.upsert_document_template(
        _admin_command_context("doc-upsert-branch"),
        doc_type=DOCUMENT_INVOICE,
        branch_id=BRANCH_ID,
        layout_spec=_layout("branch"),
    )
    branch_deactivate = service.deactivate_document_template(
        _admin_command_context("doc-deactivate-branch"),
        doc_type=DOCUMENT_INVOICE,
        branch_id=BRANCH_ID,
    )

    assert business_upsert.is_accepted
    assert branch_upsert.is_accepted
    assert branch_deactivate.is_accepted
    assert business_upsert.execution_result.event_type == ADMIN_DOCUMENT_TEMPLATE_UPSERTED_V1
    assert branch_upsert.execution_result.event_type == ADMIN_DOCUMENT_TEMPLATE_UPSERTED_V1
    assert branch_deactivate.execution_result.event_type == ADMIN_DOCUMENT_TEMPLATE_DEACTIVATED_V1
    assert branch_deactivate.execution_result.event_data["payload"]["no_op"] is False
    assert service.projection_snapshot()["document_templates"] == (
        (
            str(BUSINESS_ID),
            "",
            DOCUMENT_INVOICE,
            1,
            f"admin.document.invoice.{BUSINESS_ID}.business.v1",
            "ACTIVE",
        ),
        (
            str(BUSINESS_ID),
            str(BRANCH_ID),
            DOCUMENT_INVOICE,
            1,
            f"admin.document.invoice.{BUSINESS_ID}.{BRANCH_ID}.v1",
            "INACTIVE",
        ),
    )


def test_document_deactivate_missing_appends_noop_event_and_keeps_projection():
    service, _ = _build_service()
    before = service.projection_snapshot()

    result = service.deactivate_document_template(
        _admin_command_context("doc-deactivate-missing"),
        doc_type=DOCUMENT_INVOICE,
        branch_id=BRANCH_ID,
    )

    after = service.projection_snapshot()
    assert result.is_accepted
    assert result.execution_result.event_type == ADMIN_DOCUMENT_TEMPLATE_DEACTIVATED_V1
    assert result.execution_result.event_data["payload"]["no_op"] is True
    assert before == after


def test_compliance_upsert_version_conflict_rejects_with_admin_version_conflict():
    service, _ = _build_service()

    result = service.upsert_compliance_profile(
        _admin_command_context("compliance-version-conflict"),
        branch_id=None,
        ruleset=(_rule("CONFLICT"),),
        version=2,
    )

    assert result.is_rejected
    assert result.outcome.reason.code == "ADMIN_VERSION_CONFLICT"
    assert service.get_recorded_events() == tuple()


def test_document_upsert_version_conflict_rejects_with_admin_version_conflict():
    service, _ = _build_service()

    result = service.upsert_document_template(
        _admin_command_context("doc-version-conflict"),
        doc_type=DOCUMENT_INVOICE,
        branch_id=None,
        layout_spec=_layout("conflict"),
        version=3,
    )

    assert result.is_rejected
    assert result.outcome.reason.code == "ADMIN_VERSION_CONFLICT"
    assert service.get_recorded_events() == tuple()


def test_cross_business_attempt_rejected_by_tenant_boundary():
    service, _ = _build_service(context=StubContext(business_id=BUSINESS_ID))

    result = service.set_feature_flag(
        _admin_command_context(
            "cross-business",
            business_id=OTHER_BUSINESS_ID,
        ),
        flag_key="ENABLE_WORKSHOP_ENGINE",
        status=FEATURE_ENABLED,
    )

    assert result.is_rejected
    assert result.outcome.reason.code == "BUSINESS_ID_MISMATCH"


def test_missing_admin_permission_rejected_deterministically():
    service, _ = _build_service(permission_provider=InMemoryPermissionProvider())

    result = service.set_feature_flag(
        _admin_command_context("permission-denied"),
        flag_key="ENABLE_WORKSHOP_ENGINE",
        status=FEATURE_ENABLED,
    )

    assert result.is_rejected
    assert result.outcome.reason.code == "PERMISSION_DENIED"


def test_admin_commands_not_blocked_by_feature_document_or_compliance_gates():
    enabled_compliance_flag = FeatureFlag(
        flag_key=FLAG_ENABLE_COMPLIANCE_ENGINE,
        business_id=BUSINESS_ID,
        status=FEATURE_ENABLED,
    )
    compliance_provider = InMemoryComplianceProvider(
        profiles=(
            ComplianceProfile(
                profile_id="admin-block",
                business_id=BUSINESS_ID,
                branch_id=None,
                status=PROFILE_ACTIVE,
                version=1,
                ruleset=(
                    ComplianceRule(
                        rule_key="BLOCK-ADMIN",
                        applies_to="COMMAND_TYPE:admin.*",
                        severity=RULE_BLOCK,
                        predicate={"field": "command.command_type", "op": OP_EXISTS},
                        message="admin blocked",
                    ),
                ),
            ),
        ),
    )

    class BrokenDocumentProvider:
        def get_templates_for_business(self, business_id):
            raise RuntimeError("should not be called for admin commands")

    service, _ = _build_service(
        feature_flag_provider=InMemoryFeatureFlagProvider(
            flags=(enabled_compliance_flag,)
        ),
        compliance_provider=compliance_provider,
        document_provider=BrokenDocumentProvider(),
    )

    result = service.upsert_compliance_profile(
        _admin_command_context("admin-gates-bypass"),
        branch_id=None,
        ruleset=(_rule("ADMIN"),),
    )

    assert result.is_accepted


def test_replay_rebuild_reproduces_identical_projection_snapshot():
    service, _ = _build_service()
    service.set_feature_flag(
        _admin_command_context("replay-flag"),
        flag_key="ENABLE_DOCUMENT_DESIGNER",
        status=FEATURE_ENABLED,
    )
    service.upsert_compliance_profile(
        _admin_command_context("replay-compliance"),
        branch_id=BRANCH_ID,
        ruleset=(_rule("REPLAY"),),
    )
    service.upsert_document_template(
        _admin_command_context("replay-document"),
        doc_type=DOCUMENT_INVOICE,
        branch_id=BRANCH_ID,
        layout_spec=_layout("replay"),
    )

    recorded_events = service.get_recorded_events()
    rebuilt_store = AdminProjectionStore()
    for event_data in recorded_events:
        rebuilt_store.apply(event_data)

    assert rebuilt_store.snapshot() == service.projection_snapshot()


def test_replay_module_has_no_admin_guard_references():
    replay_file = Path("core/replay/event_replayer.py")
    source = replay_file.read_text(encoding="utf-8").lower()
    assert "core.admin" not in source
    assert "admin_version_invariant_guard" not in source
