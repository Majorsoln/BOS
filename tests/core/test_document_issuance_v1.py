from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
from core.document_issuance.projections import DocumentIssuanceProjectionStore
from core.document_issuance.registry import DOC_RECEIPT_ISSUED_V1
from core.document_issuance.repository import DocumentIssuanceRepository
from core.document_issuance.service import DocumentIssuanceService
from core.documents import DOCUMENT_RECEIPT, DocumentTemplate, InMemoryDocumentProvider
from core.feature_flags import (
    FEATURE_DISABLED,
    FEATURE_ENABLED,
    FeatureFlag,
    InMemoryFeatureFlagProvider,
)
from core.feature_flags.registry import (
    FLAG_ENABLE_COMPLIANCE_ENGINE,
    FLAG_ENABLE_DOCUMENT_DESIGNER,
)
from core.http_api.auth.provider import AuthPrincipal, InMemoryAuthProvider
from core.http_api.contracts import ActorMetadata, IssueReceiptHttpRequest
from core.http_api.dependencies import HttpApiDependencies
from core.http_api.handlers import post_issue_receipt
from core.permissions import (
    InMemoryPermissionProvider,
    PERMISSION_DOC_ISSUE,
    Role,
    ScopeGrant,
)


BUSINESS_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-doc-issuance-business")
BRANCH_ID = uuid.uuid5(uuid.NAMESPACE_URL, "bos-doc-issuance-branch")
ACTOR_ID = "doc-issuer"
ISSUED_AT = datetime(2026, 2, 18, 10, 0, tzinfo=timezone.utc)
ACTOR = ActorMetadata(actor_type="HUMAN", actor_id=ACTOR_ID)


class StubContext:
    def has_active_context(self) -> bool:
        return True

    def get_active_business_id(self):
        return BUSINESS_ID

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        return branch_id in {BRANCH_ID}

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
        self.persisted_events: list[dict] = []

    def __call__(self, event_data: dict, context, registry, **kwargs):
        self.persisted_events.append(event_data)
        return {"accepted": True}


class FixedIdProvider:
    def __init__(self):
        self._command_counter = 0
        self._correlation_counter = 0
        self._document_counter = 0

    def new_command_id(self) -> uuid.UUID:
        value = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"bos-doc-issuance:command:{self._command_counter}",
        )
        self._command_counter += 1
        return value

    def new_document_id(self) -> uuid.UUID:
        value = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"bos-doc-issuance:document:{self._document_counter}",
        )
        self._document_counter += 1
        return value

    def new_correlation_id(self) -> uuid.UUID:
        value = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"bos-doc-issuance:correlation:{self._correlation_counter}",
        )
        self._correlation_counter += 1
        return value


class FixedClock:
    def __init__(self, issued_at: datetime):
        self._issued_at = issued_at

    def now_issued_at(self) -> datetime:
        return self._issued_at


def _doc_issue_permission_provider(
    actor_id: str = ACTOR_ID,
) -> InMemoryPermissionProvider:
    role = Role(role_id="doc-role", permissions=(PERMISSION_DOC_ISSUE,))
    grant = ScopeGrant(
        actor_id=actor_id,
        role_id=role.role_id,
        business_id=BUSINESS_ID,
    )
    return InMemoryPermissionProvider(roles=(role,), grants=(grant,))


def _deterministic_event_factory(*, command, event_type: str, payload: dict) -> dict:
    return {
        "event_id": command.command_id,
        "event_type": event_type,
        "event_version": 1,
        "business_id": command.business_id,
        "branch_id": command.branch_id,
        "source_engine": command.source_engine,
        "actor_type": command.actor_type,
        "actor_id": command.actor_id,
        "correlation_id": command.correlation_id,
        "causation_id": None,
        "payload": dict(payload),
        "reference": {},
        "created_at": command.issued_at,
        "status": "FINAL",
        "correction_of": None,
    }


def _receipt_render_inputs() -> dict:
    return {
        "receipt_no": "RCT-001",
        "issued_at": "2026-02-18T10:00:00Z",
        "cashier": "Alice",
        "line_items": (
            {
                "name": "Item A",
                "quantity": 1,
                "unit_price": 10,
                "line_total": 10,
            },
        ),
        "subtotal": 10,
        "tax_total": 1,
        "grand_total": 11,
        "notes": "Paid",
    }


def _receipt_template(template_id: str = "custom.receipt.v1") -> DocumentTemplate:
    return DocumentTemplate(
        template_id=template_id,
        business_id=BUSINESS_ID,
        branch_id=None,
        doc_type=DOCUMENT_RECEIPT,
        version=1,
        status="ACTIVE",
        schema_version=1,
        layout_spec={
            "header_fields": ("receipt_no", "issued_at", "cashier"),
            "line_items_path": "line_items",
            "line_item_fields": ("name", "quantity", "unit_price", "line_total"),
            "total_fields": ("subtotal", "tax_total", "grand_total"),
            "footer_fields": ("notes",),
        },
        created_by_actor_id=ACTOR_ID,
        created_at=None,
    )


def _build_dependencies(
    *,
    permission_provider=None,
    feature_flag_provider=None,
    compliance_provider=None,
    document_provider=None,
    auth_provider=None,
    id_provider=None,
    clock=None,
):
    context = StubContext()
    permission_provider = permission_provider or _doc_issue_permission_provider()
    persist_stub = PersistEventStub()
    event_type_registry = StubEventTypeRegistry()
    projection_store = DocumentIssuanceProjectionStore()
    repository = DocumentIssuanceRepository(projection_store)

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
    issuance_service = DocumentIssuanceService(
        business_context=context,
        dispatcher=dispatcher,
        command_bus=command_bus,
        event_factory=_deterministic_event_factory,
        persist_event=persist_stub,
        event_type_registry=event_type_registry,
        projection_store=projection_store,
        document_provider=document_provider,
    )
    dependencies = HttpApiDependencies(
        admin_service=object(),
        admin_repository=object(),
        id_provider=id_provider or FixedIdProvider(),
        clock=clock or FixedClock(ISSUED_AT),
        auth_provider=auth_provider,
        permission_provider=permission_provider,
        document_issuance_service=issuance_service,
        document_issuance_repository=repository,
    )
    return dependencies, persist_stub, projection_store


def test_auth_enabled_issue_receipt_succeeds_for_actor_with_doc_issue_permission():
    principal = AuthPrincipal(
        actor_id=ACTOR_ID,
        actor_type="USER",
        allowed_business_ids=(str(BUSINESS_ID),),
        allowed_branch_ids_by_business={},
    )
    dependencies, persist_stub, _ = _build_dependencies(
        auth_provider=InMemoryAuthProvider({"valid-key": principal})
    )

    response = post_issue_receipt(
        IssueReceiptHttpRequest(
            business_id=BUSINESS_ID,
            actor=None,
            payload=_receipt_render_inputs(),
        ),
        dependencies,
        headers={
            "X-API-KEY": "valid-key",
            "X-BUSINESS-ID": str(BUSINESS_ID),
        },
    )

    assert response["ok"] is True
    assert response["data"]["doc_type"] == DOCUMENT_RECEIPT
    assert len(persist_stub.persisted_events) == 1
    assert persist_stub.persisted_events[0]["event_type"] == DOC_RECEIPT_ISSUED_V1


def test_permission_denied_when_actor_lacks_doc_issue():
    dependencies, _, _ = _build_dependencies(
        permission_provider=InMemoryPermissionProvider()
    )

    response = post_issue_receipt(
        IssueReceiptHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            payload=_receipt_render_inputs(),
        ),
        dependencies,
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "PERMISSION_DENIED"


def test_feature_disabled_rejects_with_document_feature_code():
    dependencies, _, _ = _build_dependencies(
        feature_flag_provider=InMemoryFeatureFlagProvider(
            flags=(
                FeatureFlag(
                    flag_key=FLAG_ENABLE_DOCUMENT_DESIGNER,
                    business_id=BUSINESS_ID,
                    status=FEATURE_DISABLED,
                ),
            )
        )
    )

    response = post_issue_receipt(
        IssueReceiptHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            payload=_receipt_render_inputs(),
        ),
        dependencies,
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "DOCUMENT_FEATURE_DISABLED"


def test_compliance_block_rejects_deterministically():
    profile = ComplianceProfile(
        profile_id="cmp-receipt-block-v1",
        business_id=BUSINESS_ID,
        branch_id=None,
        status=PROFILE_ACTIVE,
        version=1,
        ruleset=(
            ComplianceRule(
                rule_key="CMP-RECEIPT-001",
                applies_to="DOCUMENT:RECEIPT",
                severity=RULE_BLOCK,
                predicate={"field": "command.command_type", "op": OP_EXISTS},
                message="Receipt blocked by compliance.",
            ),
        ),
    )
    dependencies, _, _ = _build_dependencies(
        feature_flag_provider=InMemoryFeatureFlagProvider(
            flags=(
                FeatureFlag(
                    flag_key=FLAG_ENABLE_COMPLIANCE_ENGINE,
                    business_id=BUSINESS_ID,
                    status=FEATURE_ENABLED,
                ),
            )
        ),
        compliance_provider=InMemoryComplianceProvider(profiles=(profile,)),
    )

    response = post_issue_receipt(
        IssueReceiptHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            payload=_receipt_render_inputs(),
        ),
        dependencies,
    )

    assert response["ok"] is False
    assert response["error"]["code"] == "COMPLIANCE_VIOLATION"
    assert response["error"]["message"] == "Receipt blocked by compliance."


def test_issuance_uses_defaults_when_document_provider_missing():
    dependencies, persist_stub, _ = _build_dependencies(document_provider=None)

    response = post_issue_receipt(
        IssueReceiptHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            payload=_receipt_render_inputs(),
        ),
        dependencies,
    )

    assert response["ok"] is True
    payload = persist_stub.persisted_events[0]["payload"]
    assert payload["template_id"] == "default.receipt.v1"


def test_same_template_and_payload_yield_identical_render_plan():
    provider = InMemoryDocumentProvider(templates=(_receipt_template(),))
    dependencies, persist_stub, _ = _build_dependencies(document_provider=provider)

    first = post_issue_receipt(
        IssueReceiptHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            payload=_receipt_render_inputs(),
        ),
        dependencies,
    )
    second = post_issue_receipt(
        IssueReceiptHttpRequest(
            business_id=BUSINESS_ID,
            actor=ACTOR,
            payload=_receipt_render_inputs(),
        ),
        dependencies,
    )

    assert first["ok"] is True
    assert second["ok"] is True
    first_plan = persist_stub.persisted_events[0]["payload"]["render_plan"]
    second_plan = persist_stub.persisted_events[1]["payload"]["render_plan"]
    assert first_plan == second_plan


def test_projection_list_ordering_is_stable():
    store = DocumentIssuanceProjectionStore()
    t0 = ISSUED_AT
    t1 = ISSUED_AT + timedelta(minutes=1)
    doc_a = uuid.uuid5(uuid.NAMESPACE_URL, "projection-doc-a")
    doc_b = uuid.uuid5(uuid.NAMESPACE_URL, "projection-doc-b")
    doc_c = uuid.uuid5(uuid.NAMESPACE_URL, "projection-doc-c")

    store.apply(
        event_type=DOC_RECEIPT_ISSUED_V1,
        payload={
            "business_id": BUSINESS_ID,
            "branch_id": None,
            "document_id": doc_b,
            "doc_type": DOCUMENT_RECEIPT,
            "template_id": "tpl",
            "template_version": 1,
            "schema_version": 1,
            "issued_at": t1,
            "actor_id": ACTOR_ID,
            "status": "ISSUED",
        },
    )
    store.apply(
        event_type=DOC_RECEIPT_ISSUED_V1,
        payload={
            "business_id": BUSINESS_ID,
            "branch_id": None,
            "document_id": doc_c,
            "doc_type": DOCUMENT_RECEIPT,
            "template_id": "tpl",
            "template_version": 1,
            "schema_version": 1,
            "issued_at": t0,
            "actor_id": ACTOR_ID,
            "status": "ISSUED",
        },
    )
    store.apply(
        event_type=DOC_RECEIPT_ISSUED_V1,
        payload={
            "business_id": BUSINESS_ID,
            "branch_id": None,
            "document_id": doc_a,
            "doc_type": DOCUMENT_RECEIPT,
            "template_id": "tpl",
            "template_version": 1,
            "schema_version": 1,
            "issued_at": t0,
            "actor_id": ACTOR_ID,
            "status": "ISSUED",
        },
    )

    records = store.list_documents(BUSINESS_ID)
    ordered_ids = tuple(str(record.document_id) for record in records)
    expected_ids = tuple(
        str(item[1])
        for item in sorted(
            ((t1, doc_b), (t0, doc_c), (t0, doc_a)),
            key=lambda pair: (pair[0], str(pair[1])),
        )
    )
    assert ordered_ids == expected_ids


def test_replay_module_has_no_document_issuance_references():
    source = Path("core/replay/event_replayer.py").read_text(encoding="utf-8").lower()
    assert "document_issuance" not in source
    assert "doc.receipt.issued.v1" not in source
