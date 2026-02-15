from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.commands.base import Command
from core.commands.dispatcher import CommandDispatcher
from core.compliance import (
    OP_GT,
    PROFILE_ACTIVE,
    RULE_BLOCK,
    ComplianceProfile,
    ComplianceRule,
    InMemoryComplianceProvider,
)
from core.context.actor_context import ActorContext
from core.documents import (
    DOCUMENT_INVOICE,
    DocumentBuilder,
    DocumentTemplate,
    InMemoryDocumentProvider,
    resolve_document_type,
)
from core.feature_flags import (
    FEATURE_DISABLED as FLAG_STATUS_DISABLED,
    FLAG_ENABLE_DOCUMENT_DESIGNER,
    FeatureFlag,
    InMemoryFeatureFlagProvider,
    resolve_flag_for_command,
)
from core.identity.requirements import SYSTEM_ALLOWED
from core.permissions import (
    InMemoryPermissionProvider,
    PERMISSION_DOC_ISSUE,
    PERMISSION_INVENTORY_MOVE,
    Role,
    ScopeGrant,
)


BUSINESS_ID = uuid.uuid4()
BRANCH_ID = uuid.uuid4()
OTHER_BRANCH_ID = uuid.uuid4()


class StubContext:
    def has_active_context(self) -> bool:
        return True

    def get_active_business_id(self):
        return BUSINESS_ID

    def get_business_lifecycle_state(self) -> str:
        return "ACTIVE"

    def is_branch_in_business(self, branch_id, business_id) -> bool:
        return True


def _permission_provider(actor_id: str = "user-1") -> InMemoryPermissionProvider:
    role = Role(
        role_id="doc-role",
        permissions=(PERMISSION_DOC_ISSUE, PERMISSION_INVENTORY_MOVE),
    )
    grant = ScopeGrant(
        actor_id=actor_id,
        role_id="doc-role",
        business_id=BUSINESS_ID,
    )
    return InMemoryPermissionProvider(roles=(role,), grants=(grant,))


def _invoice_payload(
    *,
    amount: int = 12,
) -> dict:
    return {
        "invoice_no": "INV-001",
        "issued_at": "2026-02-15T10:00:00Z",
        "customer_name": "Acme Co",
        "line_items": [
            {
                "sku": "SKU-001",
                "description": "Desk",
                "quantity": 1,
                "tax": 2,
                "line_total": 12,
            }
        ],
        "subtotal": 10,
        "tax_total": 2,
        "grand_total": 12,
        "payment_terms": "NET30",
        "notes": "Thank you.",
        "amount": amount,
    }


def _command(
    *,
    command_type: str = "doc.invoice.issue.request",
    payload: dict | None = None,
    branch_id=None,
    actor_requirement: str | None = None,
    actor_type: str = "HUMAN",
    actor_id: str = "user-1",
) -> Command:
    kwargs = {}
    actor_context = ActorContext(actor_type=actor_type, actor_id=actor_id)

    if actor_requirement is not None:
        kwargs["actor_requirement"] = actor_requirement
        if actor_requirement == SYSTEM_ALLOWED:
            actor_type = "SYSTEM"
            actor_id = "kernel"
            actor_context = None

    return Command(
        command_id=uuid.uuid4(),
        command_type=command_type,
        business_id=BUSINESS_ID,
        branch_id=branch_id,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_context=actor_context,
        payload=payload or _invoice_payload(),
        issued_at=datetime.now(timezone.utc),
        correlation_id=uuid.uuid4(),
        source_engine="doc",
        **kwargs,
    )


def _template(
    *,
    template_id: str,
    version: int,
    branch_id=None,
    layout_spec: dict | None = None,
) -> DocumentTemplate:
    default_layout = {
        "header_fields": ("invoice_no", "issued_at", "customer_name"),
        "line_items_path": "line_items",
        "line_item_fields": (
            "sku",
            "description",
            "quantity",
            "tax",
            "line_total",
        ),
        "total_fields": ("subtotal", "tax_total", "grand_total"),
        "footer_fields": ("payment_terms", "notes"),
    }
    return DocumentTemplate(
        template_id=template_id,
        business_id=BUSINESS_ID,
        branch_id=branch_id,
        doc_type=DOCUMENT_INVOICE,
        version=version,
        status="ACTIVE",
        schema_version=1,
        layout_spec=layout_spec or default_layout,
        created_by_actor_id="user-1",
        created_at=None,
    )


def test_document_feature_disabled_rejects_mapped_command():
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider(),
        feature_flag_provider=InMemoryFeatureFlagProvider(
            flags=(
                FeatureFlag(
                    flag_key=FLAG_ENABLE_DOCUMENT_DESIGNER,
                    business_id=BUSINESS_ID,
                    status=FLAG_STATUS_DISABLED,
                ),
            )
        ),
    )

    outcome = dispatcher.dispatch(_command())

    assert outcome.is_rejected
    assert outcome.reason.code == "DOCUMENT_FEATURE_DISABLED"


def test_no_provider_uses_defaults_and_accepts():
    command = _command()
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider(),
    )

    outcome = dispatcher.dispatch(command)

    assert outcome.is_accepted
    plan = DocumentBuilder.build_for_command(
        command=command,
        doc_type=resolve_document_type(command.command_type),
        provider=None,
    )
    assert plan["template_id"] == "default.invoice.v1"


def test_business_template_selected_over_default():
    command = _command()
    provider = InMemoryDocumentProvider(
        templates=(
            _template(template_id="biz.invoice.v2", version=2),
        )
    )

    plan = DocumentBuilder.build_for_command(
        command=command,
        doc_type=DOCUMENT_INVOICE,
        provider=provider,
    )

    assert plan["template_id"] == "biz.invoice.v2"


def test_branch_override_template_wins_for_branch_scope():
    command = _command(branch_id=BRANCH_ID)
    provider = InMemoryDocumentProvider(
        templates=(
            _template(template_id="biz.invoice.v3", version=3),
            _template(
                template_id="branch.invoice.v1",
                version=1,
                branch_id=BRANCH_ID,
            ),
        )
    )

    plan = DocumentBuilder.build_for_command(
        command=command,
        doc_type=DOCUMENT_INVOICE,
        provider=provider,
    )

    assert plan["template_id"] == "branch.invoice.v1"


def test_invalid_layout_spec_rejected_deterministically():
    invalid_template = _template(
        template_id="invalid.invoice.v1",
        version=1,
        layout_spec={
            "header_fields": ("invoice_no", "issued_at", "customer_name"),
            "line_items_path": 123,
            "total_fields": ("subtotal", "tax_total", "grand_total"),
            "footer_fields": ("payment_terms", "notes"),
        },
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider(),
        document_provider=InMemoryDocumentProvider(templates=(invalid_template,)),
    )

    outcome = dispatcher.dispatch(_command())

    assert outcome.is_rejected
    assert outcome.reason.code == "DOCUMENT_TEMPLATE_INVALID"


def test_system_allowed_bypasses_document_guard():
    invalid_template = _template(
        template_id="invalid.invoice.v1",
        version=1,
        layout_spec={
            "header_fields": ("invoice_no", "issued_at", "customer_name"),
            "line_items_path": 123,
            "total_fields": ("subtotal", "tax_total", "grand_total"),
            "footer_fields": ("payment_terms", "notes"),
        },
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=InMemoryPermissionProvider(),
        feature_flag_provider=InMemoryFeatureFlagProvider(
            flags=(
                FeatureFlag(
                    flag_key=FLAG_ENABLE_DOCUMENT_DESIGNER,
                    business_id=BUSINESS_ID,
                    status=FLAG_STATUS_DISABLED,
                ),
            )
        ),
        document_provider=InMemoryDocumentProvider(templates=(invalid_template,)),
    )

    outcome = dispatcher.dispatch(
        _command(
            actor_requirement=SYSTEM_ALLOWED,
            actor_type="SYSTEM",
            actor_id="kernel",
        )
    )

    assert outcome.is_accepted


def test_render_plan_is_deterministic_for_same_input():
    command = _command()
    provider = InMemoryDocumentProvider(
        templates=(
            _template(template_id="biz.invoice.v2", version=2),
        )
    )

    plan_a = DocumentBuilder.build_for_command(
        command=command,
        doc_type=DOCUMENT_INVOICE,
        provider=provider,
    )
    plan_b = DocumentBuilder.build_for_command(
        command=command,
        doc_type=DOCUMENT_INVOICE,
        provider=provider,
    )

    assert plan_a == plan_b


def test_no_branch_inference_other_branch_template_not_applied():
    command = _command(branch_id=BRANCH_ID)
    provider = InMemoryDocumentProvider(
        templates=(
            _template(
                template_id="other-branch.invoice.v1",
                version=1,
                branch_id=OTHER_BRANCH_ID,
            ),
        )
    )

    plan = DocumentBuilder.build_for_command(
        command=command,
        doc_type=DOCUMENT_INVOICE,
        provider=provider,
    )

    assert plan["template_id"] == "default.invoice.v1"


def test_compliance_boundary_runs_before_document_guard():
    compliance_profile = ComplianceProfile(
        profile_id="cmp-doc-v1",
        business_id=BUSINESS_ID,
        branch_id=None,
        status=PROFILE_ACTIVE,
        version=1,
        ruleset=(
            ComplianceRule(
                rule_key="CMP-DOC-001",
                applies_to="DOCUMENT:INVOICE",
                severity=RULE_BLOCK,
                predicate={"field": "amount", "op": OP_GT, "value": 0},
                message="Compliance blocked invoice amount.",
            ),
        ),
    )
    invalid_template = _template(
        template_id="invalid.invoice.v1",
        version=1,
        layout_spec={
            "header_fields": ("invoice_no", "issued_at", "customer_name"),
            "line_items_path": 123,
            "total_fields": ("subtotal", "tax_total", "grand_total"),
            "footer_fields": ("payment_terms", "notes"),
        },
    )
    dispatcher = CommandDispatcher(
        context=StubContext(),
        permission_provider=_permission_provider(),
        compliance_provider=InMemoryComplianceProvider(
            profiles=(compliance_profile,)
        ),
        document_provider=InMemoryDocumentProvider(templates=(invalid_template,)),
    )

    outcome = dispatcher.dispatch(_command(payload=_invoice_payload(amount=99)))

    assert outcome.is_rejected
    assert outcome.reason.code == "COMPLIANCE_VIOLATION"


def test_feature_flag_mapping_semantics_unchanged_for_doc_issue_commands():
    assert resolve_flag_for_command("doc.invoice.issue.request") is None
    assert (
        resolve_flag_for_command("document.template.design.request")
        == FLAG_ENABLE_DOCUMENT_DESIGNER
    )


def test_replay_path_remains_untouched_by_document_guard():
    source = Path("core/replay/event_replayer.py").read_text(encoding="utf-8").lower()
    assert "document_authorization_guard" not in source
    assert "core.documents" not in source
