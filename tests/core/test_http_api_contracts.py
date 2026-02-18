from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from core.admin.projections import AdminProjectionStore
from core.admin.repository import AdminRepository
from core.admin.service import AdminDataService
from core.commands.bus import CommandBus, CommandResult
from core.commands.dispatcher import CommandDispatcher
from core.commands.outcomes import CommandOutcome, CommandStatus
from core.commands.rejection import RejectionReason
from core.compliance import OP_EXISTS, RULE_BLOCK, ComplianceRule
from core.context.actor_context import ActorContext
from core.document_issuance.projections import DocumentIssuanceProjectionStore
from core.document_issuance.registry import (
    DOC_INVOICE_ISSUED_V1,
    DOC_QUOTE_ISSUED_V1,
    DOC_RECEIPT_ISSUED_V1,
)
from core.document_issuance.repository import DocumentIssuanceRepository
from core.documents.models import DOCUMENT_INVOICE, DOCUMENT_QUOTE
from core.feature_flags.models import FEATURE_ENABLED
from core.http_api.auth.provider import AuthPrincipal, InMemoryAuthProvider
from core.http_api.contracts import (
    ActorMetadata,
    BusinessReadRequest,
    ComplianceProfileUpsertHttpRequest,
    DocumentTemplateUpsertHttpRequest,
    FeatureFlagSetHttpRequest,
    IssueReceiptHttpRequest,
    IssuedDocumentsReadRequest,
)
from core.http_api.dependencies import HttpApiDependencies
from core.http_api.errors import map_rejection_reason, rejection_response
from core.http_api.handlers import (
    list_compliance_profiles,
    list_document_templates,
    list_feature_flags,
    list_issued_documents,
    post_issue_receipt,
    post_compliance_profile_upsert,
    post_document_template_upsert,
    post_feature_flag_set,
)
from core.permissions import (
    InMemoryPermissionProvider,
    PERMISSION_ADMIN_CONFIGURE,
    Role,
    ScopeGrant,
)


BUSINESS_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-business")
BRANCH_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-branch")
OTHER_BRANCH_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-other-branch")
ACTOR_ID = "http-admin-user"
FIXED_ISSUED_AT = datetime(2026, 2, 1, 9, 30, tzinfo=timezone.utc)
ACTOR = ActorMetadata(actor_type="HUMAN", actor_id=ACTOR_ID)


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


class FixedIdProvider:
    def __init__(self):
        self._command_counter = 0
        self._correlation_counter = 0

    def new_command_id(self) -> uuid.UUID:
        value = uuid.uuid5(
            uuid.NAMESPACE_URL, f"bos-http:command:{self._command_counter}"
        )
        self._command_counter += 1
        return value

    def new_correlation_id(self) -> uuid.UUID:
        value = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"bos-http:correlation:{self._correlation_counter}",
        )
        self._correlation_counter += 1
        return value


class FixedClock:
    def __init__(self, issued_at: datetime):
        self._issued_at = issued_at

    def now_issued_at(self) -> datetime:
        return self._issued_at


def _admin_permission_provider() -> InMemoryPermissionProvider:
    role = Role(
        role_id="admin-role",
        permissions=(PERMISSION_ADMIN_CONFIGURE,),
    )
    grant = ScopeGrant(
        actor_id=ACTOR_ID,
        role_id="admin-role",
        business_id=BUSINESS_ID,
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


def _build_dependencies(
    *,
    permission_provider=None,
    context=None,
    id_provider=None,
    clock=None,
    auth_provider=None,
    document_issuance_repository=None,
):
    projection_store = AdminProjectionStore()
    repository = AdminRepository(projection_store)
    context = context or StubContext()
    permission_provider = permission_provider or _admin_permission_provider()
    persist_stub = PersistEventStub()
    registry = StubEventTypeRegistry()

    dispatcher = CommandDispatcher(
        context=context,
        permission_provider=permission_provider,
    )
    command_bus = CommandBus(
        dispatcher=dispatcher,
        persist_event=persist_stub,
        context=context,
        event_type_registry=registry,
    )
    admin_service = AdminDataService(
        business_context=context,
        dispatcher=dispatcher,
        command_bus=command_bus,
        event_factory=_deterministic_event_factory,
        persist_event=persist_stub,
        event_type_registry=registry,
        projection_store=projection_store,
    )
    dependencies = HttpApiDependencies(
        admin_service=admin_service,
        admin_repository=repository,
        id_provider=id_provider or FixedIdProvider(),
        clock=clock or FixedClock(FIXED_ISSUED_AT),
        auth_provider=auth_provider,
        document_issuance_repository=document_issuance_repository,
    )
    return dependencies, persist_stub


def _rule(seed: str) -> ComplianceRule:
    return ComplianceRule(
        rule_key=f"HTTP-{seed}",
        applies_to="DOCUMENT:INVOICE",
        severity=RULE_BLOCK,
        predicate={"field": "command.command_type", "op": OP_EXISTS},
        message="blocked",
    )


def _layout(seed: str) -> dict:
    return {
        "header_fields": [f"{seed}-header"],
        "line_items_path": "items",
        "total_fields": [f"{seed}-total"],
        "footer_fields": [f"{seed}-footer"],
    }


def test_write_handler_uses_fixed_id_and_clock_providers_deterministically():
    dependencies, persist_stub = _build_dependencies()

    response = post_feature_flag_set(
        FeatureFlagSetHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            flag_key="ENABLE_DOCUMENT_DESIGNER",
            status=FEATURE_ENABLED,
        ),
        dependencies,
    )

    expected_command_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, "bos-http:command:0")
    )
    expected_correlation_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, "bos-http:correlation:0")
    )

    assert response["ok"] is True
    assert response["data"]["command_id"] == expected_command_id
    assert response["data"]["correlation_id"] == expected_correlation_id
    assert len(persist_stub.persisted_events) == 1
    persisted = persist_stub.persisted_events[0]
    assert str(persisted["event_id"]) == response["data"]["command_id"]
    assert str(persisted["correlation_id"]) == response["data"]["correlation_id"]
    assert persisted["issued_at"] == FIXED_ISSUED_AT


def test_write_handlers_update_projection_and_read_handler_observes_changes():
    dependencies, _ = _build_dependencies()

    set_response = post_feature_flag_set(
        FeatureFlagSetHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            flag_key="ENABLE_WORKSHOP_ENGINE",
            status=FEATURE_ENABLED,
            branch_id=BRANCH_ID,
        ),
        dependencies,
    )
    read_response = list_feature_flags(
        BusinessReadRequest(business_id=BUSINESS_ID),
        dependencies,
    )

    assert set_response["ok"] is True
    assert read_response["ok"] is True
    assert read_response["data"]["count"] == 1
    item = read_response["data"]["items"][0]
    assert item["flag_key"] == "ENABLE_WORKSHOP_ENGINE"
    assert item["branch_id"] == str(BRANCH_ID)


def test_read_handlers_return_deterministic_sorted_output():
    dependencies, _ = _build_dependencies()

    post_feature_flag_set(
        FeatureFlagSetHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            flag_key="ZZZ_FLAG",
            status=FEATURE_ENABLED,
        ),
        dependencies,
    )
    post_feature_flag_set(
        FeatureFlagSetHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            flag_key="AAA_FLAG",
            status=FEATURE_ENABLED,
            branch_id=BRANCH_ID,
        ),
        dependencies,
    )
    post_compliance_profile_upsert(
        ComplianceProfileUpsertHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            ruleset=(_rule("BIZ"),),
            branch_id=None,
        ),
        dependencies,
    )
    post_compliance_profile_upsert(
        ComplianceProfileUpsertHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            ruleset=(_rule("BRANCH"),),
            branch_id=BRANCH_ID,
        ),
        dependencies,
    )
    post_document_template_upsert(
        DocumentTemplateUpsertHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            doc_type=DOCUMENT_QUOTE,
            layout_spec=_layout("quote"),
            branch_id=None,
        ),
        dependencies,
    )
    post_document_template_upsert(
        DocumentTemplateUpsertHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            doc_type=DOCUMENT_INVOICE,
            layout_spec=_layout("invoice"),
            branch_id=BRANCH_ID,
        ),
        dependencies,
    )

    flags = list_feature_flags(BusinessReadRequest(business_id=BUSINESS_ID), dependencies)
    profiles = list_compliance_profiles(
        BusinessReadRequest(business_id=BUSINESS_ID), dependencies
    )
    templates = list_document_templates(
        BusinessReadRequest(business_id=BUSINESS_ID), dependencies
    )

    assert flags["ok"] is True
    assert profiles["ok"] is True
    assert templates["ok"] is True

    flag_keys = [item["flag_key"] for item in flags["data"]["items"]]
    assert flag_keys == sorted(flag_keys)

    profile_sort_keys = [
        (
            item["business_id"],
            "" if item["branch_id"] is None else item["branch_id"],
            item["profile_id"],
            item["version"],
        )
        for item in profiles["data"]["items"]
    ]
    assert profile_sort_keys == sorted(profile_sort_keys)

    template_sort_keys = [
        (
            item["business_id"],
            "" if item["branch_id"] is None else item["branch_id"],
            item["doc_type"],
            item["version"],
            item["template_id"],
        )
        for item in templates["data"]["items"]
    ]
    assert template_sort_keys == sorted(template_sort_keys)


def test_admin_version_conflict_error_mapping():
    dependencies, _ = _build_dependencies()

    response = post_compliance_profile_upsert(
        ComplianceProfileUpsertHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            ruleset=(_rule("CONFLICT"),),
            version=2,
        ),
        dependencies,
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "ADMIN_VERSION_CONFLICT"
    assert response["error"]["details"]["status"] == "REJECTED"


def test_permission_denied_error_mapping():
    dependencies, _ = _build_dependencies(
        permission_provider=InMemoryPermissionProvider()
    )

    response = post_feature_flag_set(
        FeatureFlagSetHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            flag_key="ENABLE_COMPLIANCE_ENGINE",
            status=FEATURE_ENABLED,
        ),
        dependencies,
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "PERMISSION_DENIED"
    assert response["error"]["details"]["status"] == "REJECTED"


def test_rejection_mapper_supports_feature_and_compliance_codes():
    feature_reason = RejectionReason(
        code="FEATURE_DISABLED",
        message="feature off",
        policy_name="feature_flag_authorization_guard",
    )
    compliance_reason = RejectionReason(
        code="COMPLIANCE_VIOLATION",
        message="compliance failed",
        policy_name="compliance_authorization_guard",
    )

    feature_error = map_rejection_reason(feature_reason).to_dict()
    compliance_response = rejection_response(compliance_reason)

    assert feature_error["code"] == "FEATURE_DISABLED"
    assert feature_error["details"]["policy_name"] == "feature_flag_authorization_guard"
    assert compliance_response["ok"] is False
    assert compliance_response["error"]["code"] == "COMPLIANCE_VIOLATION"


def test_replay_module_has_no_http_api_references():
    replay_file = Path("core/replay/event_replayer.py")
    source = replay_file.read_text(encoding="utf-8").lower()
    assert "http_api" not in source
    assert "core.http_api" not in source


def test_dual_mode_auth_disabled_keeps_legacy_body_actor_flow():
    dependencies, _ = _build_dependencies(auth_provider=None)

    response = post_feature_flag_set(
        FeatureFlagSetHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            flag_key="ENABLE_ADVANCED_POLICY_ESCALATION",
            status=FEATURE_ENABLED,
        ),
        dependencies,
    )

    assert response["ok"] is True


def test_auth_enabled_read_write_path_uses_headers_and_ignores_body_actor():
    principal = AuthPrincipal(
        actor_id=ACTOR_ID,
        actor_type="USER",
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={},
    )
    auth_provider = InMemoryAuthProvider({"valid-key": principal})
    dependencies, _ = _build_dependencies(auth_provider=auth_provider)
    headers = {
        "X-API-KEY": "valid-key",
        "X-BUSINESS-ID": str(BUSINESS_ID),
    }

    write_response = post_feature_flag_set(
        FeatureFlagSetHttpRequest(
            business_id=BUSINESS_ID,
            actor=None,
            flag_key="ENABLE_ADVANCED_POLICY_ESCALATION",
            status=FEATURE_ENABLED,
        ),
        dependencies,
        headers=headers,
    )
    read_response = list_feature_flags(
        BusinessReadRequest(business_id=BUSINESS_ID),
        dependencies,
        headers=headers,
    )

    assert write_response["ok"] is True
    assert read_response["ok"] is True
    assert read_response["data"]["count"] >= 1


def test_issue_receipt_contract_requires_payload_dict():
    try:
        IssueReceiptHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            payload=("not", "a", "dict"),
        )
    except ValueError as exc:
        assert "payload must be dict." in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid payload type.")


def test_issue_handler_falls_back_to_new_command_id_when_new_document_id_missing():
    class LegacyIdProvider:
        def __init__(self):
            self._command_counter = 0
            self._correlation_counter = 0

        def new_command_id(self) -> uuid.UUID:
            value = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"bos-http-legacy-doc:command:{self._command_counter}",
            )
            self._command_counter += 1
            return value

        def new_correlation_id(self) -> uuid.UUID:
            value = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"bos-http-legacy-doc:correlation:{self._correlation_counter}",
            )
            self._correlation_counter += 1
            return value

    class StubIssuanceService:
        def __init__(self):
            self.calls = []

        def issue_receipt(self, **kwargs):
            self.calls.append(kwargs)
            outcome = CommandOutcome(
                command_id=kwargs["command_id"],
                status=CommandStatus.ACCEPTED,
                reason=None,
                occurred_at=kwargs["issued_at"],
            )
            execution = SimpleNamespace(
                event_type="doc.receipt.issued.v1",
                event_data={
                    "payload": {
                        "document_id": kwargs["document_id"],
                        "doc_type": "RECEIPT",
                        "issued_at": kwargs["issued_at"],
                    }
                },
                projection_applied=True,
            )
            return CommandResult(outcome=outcome, execution_result=execution)

    legacy_provider = LegacyIdProvider()
    issuance_service = StubIssuanceService()
    dependencies = HttpApiDependencies(
        admin_service=object(),
        admin_repository=object(),
        id_provider=legacy_provider,
        clock=FixedClock(FIXED_ISSUED_AT),
        auth_provider=None,
        document_issuance_service=issuance_service,
        document_issuance_repository=object(),
    )

    response = post_issue_receipt(
        IssueReceiptHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            payload={
                "receipt_no": "RCT-001",
                "issued_at": "2026-02-18T09:30:00Z",
                "cashier": "http-user",
                "line_items": (
                    {
                        "name": "Item",
                        "quantity": 1,
                        "unit_price": 10,
                        "line_total": 10,
                    },
                ),
                "subtotal": 10,
                "tax_total": 1,
                "grand_total": 11,
                "notes": "ok",
            },
        ),
        dependencies,
    )

    expected_document_id = str(
        uuid.uuid5(uuid.NAMESPACE_URL, "bos-http-legacy-doc:command:0")
    )
    expected_command_id = uuid.uuid5(
        uuid.NAMESPACE_URL, "bos-http-legacy-doc:command:1"
    )

    assert response["ok"] is True
    assert response["data"]["document_id"] == expected_document_id
    assert len(issuance_service.calls) == 1
    assert str(issuance_service.calls[0]["document_id"]) == expected_document_id
    assert issuance_service.calls[0]["command_id"] == expected_command_id


def _build_document_issuance_repository_for_http_tests():
    projection_store = DocumentIssuanceProjectionStore()
    t0 = datetime(2026, 2, 18, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 2, 18, 10, 1, tzinfo=timezone.utc)
    doc_id_1 = uuid.UUID("10000000-0000-0000-0000-000000000000")
    doc_id_2 = uuid.UUID("20000000-0000-0000-0000-000000000000")
    doc_id_3 = uuid.UUID("30000000-0000-0000-0000-000000000000")

    projection_store.apply(
        event_type=DOC_INVOICE_ISSUED_V1,
        payload={
            "business_id": BUSINESS_ID,
            "branch_id": BRANCH_ID,
            "document_id": doc_id_3,
            "doc_type": "INVOICE",
            "template_id": "default.invoice.v1",
            "template_version": 1,
            "schema_version": 1,
            "issued_at": t1,
            "actor_id": ACTOR_ID,
            "correlation_id": uuid.UUID(
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            ),
            "status": "ISSUED",
            "render_plan": {"totals": {"grand_total": 33, "currency": "USD"}},
        },
    )
    projection_store.apply(
        event_type=DOC_RECEIPT_ISSUED_V1,
        payload={
            "business_id": BUSINESS_ID,
            "branch_id": BRANCH_ID,
            "document_id": doc_id_2,
            "doc_type": "RECEIPT",
            "template_id": "default.receipt.v1",
            "template_version": 1,
            "schema_version": 1,
            "issued_at": t0,
            "actor_id": ACTOR_ID,
            "correlation_id": uuid.UUID(
                "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
            ),
            "status": "ISSUED",
            "render_plan": {"totals": {"grand_total": 22, "currency": "USD"}},
        },
    )
    projection_store.apply(
        event_type=DOC_QUOTE_ISSUED_V1,
        payload={
            "business_id": BUSINESS_ID,
            "branch_id": BRANCH_ID,
            "document_id": doc_id_1,
            "doc_type": "QUOTE",
            "template_id": "default.quote.v1",
            "template_version": 1,
            "schema_version": 1,
            "issued_at": t0,
            "actor_id": ACTOR_ID,
            "correlation_id": uuid.UUID(
                "cccccccc-cccc-cccc-cccc-cccccccccccc"
            ),
            "status": "ISSUED",
            "render_plan": {"totals": {"grand_total": 11, "currency": "USD"}},
        },
    )

    return DocumentIssuanceRepository(projection_store), (doc_id_1, doc_id_2, doc_id_3)


def test_docs_list_contract_is_core_minimal_and_deterministic_ordered():
    repository, expected_order = _build_document_issuance_repository_for_http_tests()
    dependencies, _ = _build_dependencies(document_issuance_repository=repository)
    response = list_issued_documents(
        IssuedDocumentsReadRequest(business_id=BUSINESS_ID),
        dependencies,
    )

    assert response["ok"] is True
    assert set(response["data"].keys()) == {"items", "count", "next_cursor"}
    assert response["data"]["count"] == 3
    assert response["data"]["next_cursor"] is None

    items = response["data"]["items"]
    assert tuple(item["doc_id"] for item in items) == tuple(str(item) for item in expected_order)

    expected_fields = {
        "doc_id",
        "doc_type",
        "status",
        "business_id",
        "branch_id",
        "issued_at",
        "issued_by_actor_id",
        "correlation_id",
        "template_id",
        "template_version",
        "schema_version",
        "totals",
        "links",
    }
    for item in items:
        assert set(item.keys()) == expected_fields
        assert set(item["links"].keys()) == {"self", "render_plan"}
        assert item["links"]["self"] == f"/v1/docs/{item['doc_id']}"
        assert item["links"]["render_plan"] == f"/v1/docs/{item['doc_id']}/render-plan"
        assert item["business_id"] == str(BUSINESS_ID)
        assert item["branch_id"] == str(BRANCH_ID)
        uuid.UUID(item["doc_id"])
        uuid.UUID(item["correlation_id"])
        uuid.UUID(item["template_id"])
        assert isinstance(item["totals"], dict)
        assert "grand_total" in item["totals"]
        assert "currency" in item["totals"]


def test_docs_list_pagination_returns_deterministic_next_cursor():
    repository, expected_order = _build_document_issuance_repository_for_http_tests()
    dependencies, _ = _build_dependencies(document_issuance_repository=repository)

    first_page = list_issued_documents(
        IssuedDocumentsReadRequest(business_id=BUSINESS_ID, limit=2),
        dependencies,
    )
    second_page = list_issued_documents(
        IssuedDocumentsReadRequest(
            business_id=BUSINESS_ID,
            limit=2,
            cursor=first_page["data"]["next_cursor"],
        ),
        dependencies,
    )
    first_page_again = list_issued_documents(
        IssuedDocumentsReadRequest(business_id=BUSINESS_ID, limit=2),
        dependencies,
    )

    assert first_page["ok"] is True
    assert second_page["ok"] is True
    assert first_page_again["ok"] is True

    assert tuple(item["doc_id"] for item in first_page["data"]["items"]) == tuple(
        str(item) for item in expected_order[:2]
    )
    assert tuple(item["doc_id"] for item in second_page["data"]["items"]) == (
        str(expected_order[2]),
    )
    assert second_page["data"]["next_cursor"] is None
    assert first_page["data"]["next_cursor"] == first_page_again["data"]["next_cursor"]


def test_docs_list_invalid_cursor_returns_invalid_request():
    repository, _ = _build_document_issuance_repository_for_http_tests()
    dependencies, _ = _build_dependencies(document_issuance_repository=repository)

    response = list_issued_documents(
        IssuedDocumentsReadRequest(
            business_id=BUSINESS_ID,
            cursor="not-a-valid-cursor",
        ),
        dependencies,
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "INVALID_REQUEST"


def test_docs_list_legacy_mode_still_works():
    repository, _ = _build_document_issuance_repository_for_http_tests()
    dependencies, _ = _build_dependencies(
        auth_provider=None,
        document_issuance_repository=repository,
    )

    response = list_issued_documents(
        IssuedDocumentsReadRequest(business_id=BUSINESS_ID),
        dependencies,
    )

    assert response["ok"] is True
    assert response["data"]["count"] == 3


def test_docs_list_auth_mode_requires_api_key():
    repository, _ = _build_document_issuance_repository_for_http_tests()
    principal = AuthPrincipal(
        actor_id=ACTOR_ID,
        actor_type="USER",
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={},
    )
    dependencies, _ = _build_dependencies(
        auth_provider=InMemoryAuthProvider({"valid-key": principal}),
        document_issuance_repository=repository,
    )

    missing_key = list_issued_documents(
        IssuedDocumentsReadRequest(business_id=BUSINESS_ID),
        dependencies,
        headers={"X-BUSINESS-ID": str(BUSINESS_ID)},
    )
    allowed = list_issued_documents(
        IssuedDocumentsReadRequest(business_id=BUSINESS_ID),
        dependencies,
        headers={
            "X-API-KEY": "valid-key",
            "X-BUSINESS-ID": str(BUSINESS_ID),
        },
    )

    assert missing_key["ok"] is False
    assert missing_key["error"]["code"] == "ACTOR_REQUIRED_MISSING"
    assert allowed["ok"] is True
