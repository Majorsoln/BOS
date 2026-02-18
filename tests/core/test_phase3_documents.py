"""
BOS Phase 3 - Document Engine Tests
=====================================
Tests for:
  3.2 Block System
  3.3 Document Hashing
  3.3 HTML Preview Renderer
  3.4 PDF Renderer
  3.5 Numbering Engine
  3.6 Verification Portal
  Issuance integration (hash + doc_number in events/projections)

Doctrine compliance:
  - Determinism: same input → same output for all renderers/hashers
  - Tenant isolation: cross-business verification returns NOT_FOUND
  - No randomness
  - Additive only (no changes to existing test contracts)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

# Load core.commands FIRST to break circular import chain:
#   core.documents → core.commands.rejection → core.commands.__init__
#   → core.commands.dispatcher → core.policy.document_policy → core.documents
from core.commands.base import Command  # noqa: F401
from core.commands.dispatcher import CommandDispatcher  # noqa: F401

# ---------------------------------------------------------------------------
# 3.2 Block System
# ---------------------------------------------------------------------------

from core.documents.blocks import (
    BLOCK_HEADER,
    BLOCK_ITEM_TABLE,
    BLOCK_NOTES,
    BLOCK_QR,
    BLOCK_TOTALS,
    VALID_BLOCK_TYPES,
    BlockSpec,
    extract_block_data,
    parse_blocks_from_layout_spec,
)


class TestBlockSystem:
    def test_valid_block_types_are_all_non_empty(self):
        for bt in VALID_BLOCK_TYPES:
            assert isinstance(bt, str) and bt

    def test_block_spec_valid(self):
        spec = BlockSpec(block_type=BLOCK_HEADER, enabled=True, label_override="Invoice Header")
        assert spec.block_type == BLOCK_HEADER
        assert spec.enabled is True
        assert spec.effective_data_key() == "header"

    def test_block_spec_custom_data_key(self):
        spec = BlockSpec(block_type=BLOCK_TOTALS, data_key="my_totals")
        assert spec.effective_data_key() == "my_totals"

    def test_block_spec_invalid_type_raises(self):
        with pytest.raises(ValueError, match="block_type"):
            BlockSpec(block_type="INVALID_BLOCK")

    def test_parse_blocks_from_layout_spec_empty(self):
        result = parse_blocks_from_layout_spec({"header_fields": []})
        assert result == ()

    def test_parse_blocks_from_layout_spec_valid(self):
        layout = {
            "blocks": [
                {"block_type": "HEADER"},
                {"block_type": "ITEM_TABLE", "enabled": True},
                {"block_type": "TOTALS", "label_override": "Grand Total"},
            ]
        }
        blocks = parse_blocks_from_layout_spec(layout)
        assert len(blocks) == 3
        assert blocks[0].block_type == "HEADER"
        assert blocks[2].label_override == "Grand Total"

    def test_parse_blocks_duplicate_raises(self):
        layout = {
            "blocks": [
                {"block_type": "HEADER"},
                {"block_type": "HEADER"},
            ]
        }
        with pytest.raises(ValueError, match="more than once"):
            parse_blocks_from_layout_spec(layout)

    def test_parse_blocks_invalid_type_raises(self):
        layout = {"blocks": [{"block_type": "NOT_A_BLOCK"}]}
        with pytest.raises(ValueError):
            parse_blocks_from_layout_spec(layout)

    def test_extract_block_data_legacy_header(self):
        render_plan = {
            "header": {"invoice_no": "INV-001", "issued_at": "2026-01-01"},
            "totals": {"grand_total": 100},
        }
        spec = BlockSpec(block_type=BLOCK_HEADER)
        data = extract_block_data(render_plan, spec)
        assert data.get("invoice_no") == "INV-001"

    def test_extract_block_data_structured_blocks(self):
        render_plan = {
            "blocks": {
                "totals": {"grand_total": 500, "currency": "USD"},
            }
        }
        spec = BlockSpec(block_type=BLOCK_TOTALS)
        data = extract_block_data(render_plan, spec)
        assert data.get("grand_total") == 500

    def test_block_field_definitions_present_for_all_types(self):
        from core.documents.blocks import BLOCK_FIELD_DEFINITIONS
        for block_type in VALID_BLOCK_TYPES:
            assert block_type in BLOCK_FIELD_DEFINITIONS


# ---------------------------------------------------------------------------
# 3.3 Document Hashing
# ---------------------------------------------------------------------------

from core.documents.hashing import (
    canonical_json,
    compute_render_plan_hash,
    verify_render_plan_hash,
)


class TestDocumentHashing:
    def test_hash_is_deterministic(self):
        plan = {"doc_type": "RECEIPT", "header": {"no": "001"}, "totals": {"total": 100}}
        h1 = compute_render_plan_hash(plan)
        h2 = compute_render_plan_hash(plan)
        assert h1 == h2

    def test_hash_is_64_chars_hex(self):
        plan = {"doc_type": "INVOICE"}
        h = compute_render_plan_hash(plan)
        assert len(h) == 64
        int(h, 16)  # Must be valid hex

    def test_different_plans_different_hash(self):
        plan_a = {"doc_type": "RECEIPT", "totals": {"total": 100}}
        plan_b = {"doc_type": "RECEIPT", "totals": {"total": 101}}
        assert compute_render_plan_hash(plan_a) != compute_render_plan_hash(plan_b)

    def test_hash_key_order_irrelevant(self):
        plan_a = {"b": 2, "a": 1}
        plan_b = {"a": 1, "b": 2}
        assert compute_render_plan_hash(plan_a) == compute_render_plan_hash(plan_b)

    def test_verify_hash_valid(self):
        plan = {"doc_type": "QUOTE", "totals": {"grand_total": 999}}
        h = compute_render_plan_hash(plan)
        assert verify_render_plan_hash(plan, h) is True

    def test_verify_hash_invalid(self):
        plan = {"doc_type": "QUOTE", "totals": {"grand_total": 999}}
        assert verify_render_plan_hash(plan, "a" * 64) is False

    def test_verify_hash_wrong_length_returns_false(self):
        plan = {"doc_type": "QUOTE"}
        assert verify_render_plan_hash(plan, "short") is False

    def test_canonical_json_sorts_keys(self):
        result = canonical_json({"z": 1, "a": 2})
        assert result.index('"a"') < result.index('"z"')

    def test_hash_requires_dict(self):
        with pytest.raises(ValueError):
            compute_render_plan_hash("not a dict")


# ---------------------------------------------------------------------------
# 3.3 HTML Preview Renderer
# ---------------------------------------------------------------------------

from core.documents.renderer.html_renderer import render_html


SAMPLE_RENDER_PLAN = {
    "doc_type": "RECEIPT",
    "template_id": "default.receipt.v1",
    "template_version": 1,
    "schema_version": 1,
    "header": {
        "receipt_no": "RCP-00001",
        "issued_at": "2026-02-18T10:00:00Z",
        "cashier": "Alice",
    },
    "line_items": [
        {"name": "Coffee", "quantity": 2, "unit_price": 3.5, "line_total": 7.0},
        {"name": "Cake", "quantity": 1, "unit_price": 5.0, "line_total": 5.0},
    ],
    "totals": {"subtotal": 12.0, "tax_total": 0.96, "grand_total": 12.96},
    "footer": {"notes": "Thank you for your business!"},
}


class TestHtmlRenderer:
    def test_render_returns_string(self):
        html = render_html(SAMPLE_RENDER_PLAN)
        assert isinstance(html, str)

    def test_render_contains_doctype(self):
        html = render_html(SAMPLE_RENDER_PLAN)
        assert "<!DOCTYPE html>" in html

    def test_render_contains_doc_type(self):
        html = render_html(SAMPLE_RENDER_PLAN)
        assert "RECEIPT" in html

    def test_render_contains_doc_number(self):
        html = render_html(SAMPLE_RENDER_PLAN)
        assert "RCP-00001" in html

    def test_render_is_deterministic(self):
        html1 = render_html(SAMPLE_RENDER_PLAN)
        html2 = render_html(SAMPLE_RENDER_PLAN)
        assert html1 == html2

    def test_xss_escaped_in_content(self):
        plan = dict(SAMPLE_RENDER_PLAN)
        plan = {**plan, "header": {"receipt_no": "<script>alert(1)</script>"}}
        html = render_html(plan)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_render_with_doc_hash_in_footer(self):
        h = "a" * 64
        html = render_html(SAMPLE_RENDER_PLAN, doc_hash=h)
        assert "aaaaaaaaaaaaaaa" in html  # first 16 chars in footer

    def test_render_with_block_layout(self):
        layout = {
            "blocks": [
                {"block_type": "HEADER"},
                {"block_type": "ITEM_TABLE"},
                {"block_type": "TOTALS"},
                {"block_type": "NOTES"},
            ]
        }
        plan = {
            **SAMPLE_RENDER_PLAN,
            "blocks": {
                "header": SAMPLE_RENDER_PLAN["header"],
                "item_table": {"line_items": SAMPLE_RENDER_PLAN["line_items"]},
                "totals": SAMPLE_RENDER_PLAN["totals"],
                "notes": SAMPLE_RENDER_PLAN["footer"],
            }
        }
        html = render_html(plan, layout_spec=layout)
        assert "<!DOCTYPE html>" in html
        assert "RECEIPT" in html

    def test_render_requires_dict(self):
        with pytest.raises(ValueError):
            render_html("not a dict")

    def test_line_items_rendered_as_table(self):
        html = render_html(SAMPLE_RENDER_PLAN)
        assert "<table" in html
        assert "Coffee" in html

    def test_grand_total_appears(self):
        html = render_html(SAMPLE_RENDER_PLAN)
        assert "12.96" in html


# ---------------------------------------------------------------------------
# 3.4 PDF Renderer
# ---------------------------------------------------------------------------

from core.documents.renderer.pdf_renderer import render_pdf


class TestPdfRenderer:
    def test_render_returns_bytes(self):
        pdf = render_pdf(SAMPLE_RENDER_PLAN)
        assert isinstance(pdf, bytes)

    def test_render_starts_with_pdf_header(self):
        pdf = render_pdf(SAMPLE_RENDER_PLAN)
        assert pdf.startswith(b"%PDF-")

    def test_render_ends_with_eof(self):
        pdf = render_pdf(SAMPLE_RENDER_PLAN)
        assert b"%%EOF" in pdf

    def test_render_is_deterministic(self):
        pdf1 = render_pdf(SAMPLE_RENDER_PLAN)
        pdf2 = render_pdf(SAMPLE_RENDER_PLAN)
        assert pdf1 == pdf2

    def test_render_requires_dict(self):
        with pytest.raises(ValueError):
            render_pdf("not a dict")

    def test_render_minimal_plan(self):
        plan = {"doc_type": "INVOICE", "template_id": "t1", "template_version": 1}
        pdf = render_pdf(plan)
        assert b"%PDF-" in pdf

    def test_render_with_hash(self):
        pdf = render_pdf(SAMPLE_RENDER_PLAN, doc_hash="a" * 64)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 100

    def test_render_non_empty(self):
        pdf = render_pdf(SAMPLE_RENDER_PLAN)
        assert len(pdf) > 500  # A valid PDF with content is at least a few hundred bytes


# ---------------------------------------------------------------------------
# 3.5 Numbering Engine
# ---------------------------------------------------------------------------

from core.documents.numbering import (
    RESET_DAILY,
    RESET_MONTHLY,
    RESET_NEVER,
    RESET_YEARLY,
    InMemoryNumberingProvider,
    NumberingPolicy,
    SequenceState,
    period_key,
)

BIZ_ID = str(uuid.UUID(int=1))
BRANCH_ID = str(uuid.UUID(int=2))


def _policy(
    *,
    prefix="INV-",
    suffix="",
    padding=5,
    reset_period=RESET_NEVER,
    doc_type="INVOICE",
    branch_id_str=None,
) -> NumberingPolicy:
    return NumberingPolicy(
        policy_id=f"pol-{doc_type.lower()}-{reset_period.lower()}",
        business_id_str=BIZ_ID,
        doc_type=doc_type,
        prefix=prefix,
        suffix=suffix,
        padding=padding,
        reset_period=reset_period,
        branch_id_str=branch_id_str,
    )


class TestNumberingPolicy:
    def test_format_number(self):
        pol = _policy(prefix="RCP-", padding=5)
        assert pol.format_number(1) == "RCP-00001"
        assert pol.format_number(42) == "RCP-00042"

    def test_format_number_with_suffix(self):
        pol = _policy(prefix="INV-", suffix="/2026", padding=4)
        assert pol.format_number(7) == "INV-0007/2026"

    def test_invalid_policy_missing_id(self):
        with pytest.raises(ValueError):
            NumberingPolicy(
                policy_id="",
                business_id_str=BIZ_ID,
                doc_type="INVOICE",
            )

    def test_invalid_reset_period(self):
        with pytest.raises(ValueError, match="reset_period"):
            NumberingPolicy(
                policy_id="x",
                business_id_str=BIZ_ID,
                doc_type="INVOICE",
                reset_period="HOURLY",
            )

    def test_invalid_padding(self):
        with pytest.raises(ValueError):
            NumberingPolicy(
                policy_id="x",
                business_id_str=BIZ_ID,
                doc_type="INVOICE",
                padding=0,
            )


class TestPeriodKey:
    _dt = datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc)

    def test_never_is_empty_string(self):
        pol = _policy(reset_period=RESET_NEVER)
        assert period_key(pol, self._dt) == ""

    def test_daily_key(self):
        pol = _policy(reset_period=RESET_DAILY)
        assert period_key(pol, self._dt) == "2026-02-18"

    def test_monthly_key(self):
        pol = _policy(reset_period=RESET_MONTHLY)
        assert period_key(pol, self._dt) == "2026-02"

    def test_yearly_key(self):
        pol = _policy(reset_period=RESET_YEARLY)
        assert period_key(pol, self._dt) == "2026"


class TestSequenceState:
    _dt = datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc)

    def test_first_number(self):
        pol = _policy(prefix="RCP-", padding=5)
        state = SequenceState(pol)
        doc_no, new_state = state.next_number(self._dt)
        assert doc_no == "RCP-00001"
        assert new_state.current_sequence == 2

    def test_sequential_numbers(self):
        pol = _policy(prefix="INV-", padding=4)
        state = SequenceState(pol)
        numbers = []
        for _ in range(5):
            doc_no, state = state.next_number(self._dt)
            numbers.append(doc_no)
        assert numbers == ["INV-0001", "INV-0002", "INV-0003", "INV-0004", "INV-0005"]

    def test_period_reset_daily(self):
        pol = _policy(prefix="RCP-", padding=3, reset_period=RESET_DAILY)
        state = SequenceState(pol)
        dt_day1 = datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc)
        dt_day2 = datetime(2026, 2, 19, 10, 0, 0, tzinfo=timezone.utc)

        no1, state = state.next_number(dt_day1)
        no2, state = state.next_number(dt_day1)
        no3, state = state.next_number(dt_day2)  # New day → reset
        assert no1 == "RCP-001"
        assert no2 == "RCP-002"
        assert no3 == "RCP-001"  # Reset

    def test_period_reset_monthly(self):
        pol = _policy(prefix="Q-", padding=3, reset_period=RESET_MONTHLY)
        state = SequenceState(pol)
        dt_jan = datetime(2026, 1, 31, tzinfo=timezone.utc)
        dt_feb = datetime(2026, 2, 1, tzinfo=timezone.utc)

        no1, state = state.next_number(dt_jan)
        no2, state = state.next_number(dt_feb)  # New month → reset
        assert no1 == "Q-001"
        assert no2 == "Q-001"

    def test_deterministic_same_state_same_result(self):
        pol = _policy(prefix="D-", padding=3)
        state1 = SequenceState(pol)
        state2 = SequenceState(pol)
        no1, _ = state1.next_number(self._dt)
        no2, _ = state2.next_number(self._dt)
        assert no1 == no2


class TestInMemoryNumberingProvider:
    _dt = datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc)

    def test_get_policy_found(self):
        pol = _policy(prefix="INV-", padding=5)
        provider = InMemoryNumberingProvider(policies=(pol,))
        found = provider.get_policy(business_id_str=BIZ_ID, doc_type="INVOICE")
        assert found is pol

    def test_get_policy_not_found_returns_none(self):
        provider = InMemoryNumberingProvider()
        assert provider.get_policy(business_id_str=BIZ_ID, doc_type="RECEIPT") is None

    def test_get_and_advance_increments(self):
        pol = _policy(prefix="RCP-", padding=5)
        provider = InMemoryNumberingProvider(policies=(pol,))
        no1 = provider.get_and_advance(policy=pol, issued_at=self._dt)
        no2 = provider.get_and_advance(policy=pol, issued_at=self._dt)
        assert no1 == "RCP-00001"
        assert no2 == "RCP-00002"

    def test_branch_policy_takes_precedence(self):
        business_pol = _policy(prefix="B-", padding=3)
        branch_pol = NumberingPolicy(
            policy_id="pol-invoice-branch",
            business_id_str=BIZ_ID,
            doc_type="INVOICE",
            prefix="BR-",
            padding=3,
            branch_id_str=BRANCH_ID,
        )
        provider = InMemoryNumberingProvider(policies=(business_pol, branch_pol))
        found = provider.get_policy(
            business_id_str=BIZ_ID,
            doc_type="INVOICE",
            branch_id_str=BRANCH_ID,
        )
        assert found is branch_pol

    def test_fallback_to_business_policy_when_no_branch_policy(self):
        business_pol = _policy(prefix="B-", padding=3)
        provider = InMemoryNumberingProvider(policies=(business_pol,))
        found = provider.get_policy(
            business_id_str=BIZ_ID,
            doc_type="INVOICE",
            branch_id_str=BRANCH_ID,
        )
        assert found is business_pol


# ---------------------------------------------------------------------------
# 3.6 Verification Portal
# ---------------------------------------------------------------------------

from core.documents.hashing import compute_render_plan_hash
from core.documents.verification import (
    VERIFICATION_NOT_FOUND,
    VERIFICATION_TAMPERED,
    VERIFICATION_VALID,
    VerificationResult,
    verify_document,
)


class _FakeRecord:
    """Minimal verifiable record stub."""
    def __init__(self, *, business_id, branch_id=None, doc_type="RECEIPT", render_plan=None, tamper=False):
        self.document_id = uuid.uuid4()
        self.business_id = business_id
        self.branch_id = branch_id
        self.doc_type = doc_type
        self.issued_at = datetime(2026, 2, 18, tzinfo=timezone.utc)
        self.actor_id = "cashier-1"
        self.render_plan = render_plan or {"doc_type": doc_type, "totals": {"grand_total": 100}}
        self.render_plan_hash = (
            "a" * 64 if tamper else compute_render_plan_hash(self.render_plan)
        )
        self.doc_number = "RCP-00001"


_BIZ_UUID = uuid.UUID(int=10)
_OTHER_BIZ = uuid.UUID(int=99)


class TestVerification:
    def test_valid_document(self):
        rec = _FakeRecord(business_id=_BIZ_UUID)
        result = verify_document(
            document_id=rec.document_id,
            business_id=_BIZ_UUID,
            record=rec,
        )
        assert result.status == VERIFICATION_VALID
        assert result.is_valid()

    def test_tampered_document(self):
        rec = _FakeRecord(business_id=_BIZ_UUID, tamper=True)
        result = verify_document(
            document_id=rec.document_id,
            business_id=_BIZ_UUID,
            record=rec,
        )
        assert result.status == VERIFICATION_TAMPERED
        assert not result.is_valid()

    def test_not_found(self):
        result = verify_document(
            document_id=uuid.uuid4(),
            business_id=_BIZ_UUID,
            record=None,
        )
        assert result.status == VERIFICATION_NOT_FOUND

    def test_cross_tenant_returns_not_found(self):
        """Cross-business access must not reveal document existence."""
        rec = _FakeRecord(business_id=_BIZ_UUID)
        result = verify_document(
            document_id=rec.document_id,
            business_id=_OTHER_BIZ,  # wrong business
            record=rec,
        )
        assert result.status == VERIFICATION_NOT_FOUND

    def test_result_as_dict(self):
        rec = _FakeRecord(business_id=_BIZ_UUID)
        result = verify_document(
            document_id=rec.document_id,
            business_id=_BIZ_UUID,
            record=rec,
        )
        d = result.as_dict()
        assert d["status"] == VERIFICATION_VALID
        assert "document_id" in d
        assert "stored_hash" in d
        assert "computed_hash" in d

    def test_no_stored_hash_returns_tampered(self):
        rec = _FakeRecord(business_id=_BIZ_UUID)
        rec.render_plan_hash = None  # override
        result = verify_document(
            document_id=rec.document_id,
            business_id=_BIZ_UUID,
            record=rec,
        )
        assert result.status == VERIFICATION_TAMPERED

    def test_verification_result_is_frozen(self):
        result = VerificationResult(
            status=VERIFICATION_VALID,
            document_id="abc",
            doc_type="RECEIPT",
            doc_number=None,
            business_id="b1",
            branch_id=None,
            issued_at="2026-01-01",
            actor_id="u1",
            stored_hash="a" * 64,
            computed_hash="a" * 64,
        )
        with pytest.raises((AttributeError, TypeError)):
            result.status = "TAMPERED"


# ---------------------------------------------------------------------------
# Issuance integration: hash + doc_number in event payload and projection
# ---------------------------------------------------------------------------

from core.document_issuance.events import build_document_issued_payload
from core.document_issuance.projections import (
    DocumentIssuanceProjectionStore,
    IssuedDocumentRecord,
)
from core.document_issuance.registry import DOC_RECEIPT_ISSUED_V1
from core.documents.hashing import compute_render_plan_hash


def _make_command_stub():
    class _Cmd:
        business_id = uuid.UUID(int=5)
        branch_id = uuid.UUID(int=6)
        actor_id = "cashier-test"
        correlation_id = uuid.UUID(int=7)
        issued_at = datetime(2026, 2, 18, tzinfo=timezone.utc)
        payload = {
            "document_id": uuid.UUID(int=8),
            "doc_type": "RECEIPT",
        }
    return _Cmd()


_RENDER_PLAN = {
    "doc_type": "RECEIPT",
    "template_id": "default.receipt.v1",
    "template_version": 1,
    "schema_version": 1,
    "header": {"receipt_no": "RCP-00001"},
    "line_items": [],
    "totals": {"grand_total": 50},
    "footer": {},
}


class TestIssuanceHashIntegration:
    def test_event_payload_contains_render_plan_hash(self):
        cmd = _make_command_stub()
        payload = build_document_issued_payload(
            command=cmd,
            doc_type="RECEIPT",
            render_plan=_RENDER_PLAN,
        )
        assert "render_plan_hash" in payload
        assert len(payload["render_plan_hash"]) == 64

    def test_event_payload_hash_matches_render_plan(self):
        cmd = _make_command_stub()
        payload = build_document_issued_payload(
            command=cmd,
            doc_type="RECEIPT",
            render_plan=_RENDER_PLAN,
        )
        expected_hash = compute_render_plan_hash(_RENDER_PLAN)
        assert payload["render_plan_hash"] == expected_hash

    def test_event_payload_doc_number_stored(self):
        cmd = _make_command_stub()
        payload = build_document_issued_payload(
            command=cmd,
            doc_type="RECEIPT",
            render_plan=_RENDER_PLAN,
            doc_number="RCP-00042",
        )
        assert payload["doc_number"] == "RCP-00042"

    def test_event_payload_no_doc_number_is_none(self):
        cmd = _make_command_stub()
        payload = build_document_issued_payload(
            command=cmd,
            doc_type="RECEIPT",
            render_plan=_RENDER_PLAN,
        )
        assert payload["doc_number"] is None

    def test_projection_stores_render_plan_and_hash(self):
        cmd = _make_command_stub()
        payload = build_document_issued_payload(
            command=cmd,
            doc_type="RECEIPT",
            render_plan=_RENDER_PLAN,
            doc_number="RCP-00001",
        )
        # Fix non-serialisable types for projection
        payload["business_id"] = str(payload["business_id"])
        payload["branch_id"] = str(payload["branch_id"])
        payload["document_id"] = str(payload["document_id"])
        payload["correlation_id"] = str(payload["correlation_id"])

        store = DocumentIssuanceProjectionStore()
        store.apply(event_type=DOC_RECEIPT_ISSUED_V1, payload=payload)

        records = store.list_documents(
            business_id=uuid.UUID(int=5),
        )
        assert len(records) == 1
        record = records[0]
        assert record.render_plan_hash is not None
        assert len(record.render_plan_hash) == 64
        assert record.doc_number == "RCP-00001"
        assert isinstance(record.render_plan, dict)

    def test_projection_can_verify_stored_hash(self):
        cmd = _make_command_stub()
        payload = build_document_issued_payload(
            command=cmd,
            doc_type="RECEIPT",
            render_plan=_RENDER_PLAN,
        )
        payload["business_id"] = str(payload["business_id"])
        payload["branch_id"] = str(payload["branch_id"])
        payload["document_id"] = str(payload["document_id"])
        payload["correlation_id"] = str(payload["correlation_id"])

        store = DocumentIssuanceProjectionStore()
        store.apply(event_type=DOC_RECEIPT_ISSUED_V1, payload=payload)
        records = store.list_documents(business_id=uuid.UUID(int=5))
        record = records[0]

        assert verify_render_plan_hash(record.render_plan, record.render_plan_hash)


# ---------------------------------------------------------------------------
# Numbering integration: doc_number flows through issuance service
# ---------------------------------------------------------------------------

class TestNumberingEngineIntegration:
    """Ensure the numbering engine produces deterministic sequential numbers."""

    def test_sequential_issuance_numbers(self):
        pol = NumberingPolicy(
            policy_id="pol-rcpt-seq",
            business_id_str=BIZ_ID,
            doc_type="RECEIPT",
            prefix="R-",
            padding=4,
        )
        provider = InMemoryNumberingProvider(policies=(pol,))
        dt = datetime(2026, 2, 18, tzinfo=timezone.utc)

        numbers = [
            provider.get_and_advance(policy=pol, issued_at=dt)
            for _ in range(5)
        ]
        assert numbers == ["R-0001", "R-0002", "R-0003", "R-0004", "R-0005"]

    def test_numbering_respects_yearly_reset(self):
        pol = NumberingPolicy(
            policy_id="pol-inv-yearly",
            business_id_str=BIZ_ID,
            doc_type="INVOICE",
            prefix="INV-",
            padding=4,
            reset_period=RESET_YEARLY,
        )
        provider = InMemoryNumberingProvider(policies=(pol,))
        dt_2025 = datetime(2025, 12, 31, tzinfo=timezone.utc)
        dt_2026 = datetime(2026, 1, 1, tzinfo=timezone.utc)

        no1 = provider.get_and_advance(policy=pol, issued_at=dt_2025)
        no2 = provider.get_and_advance(policy=pol, issued_at=dt_2025)
        no3 = provider.get_and_advance(policy=pol, issued_at=dt_2026)  # Reset

        assert no1 == "INV-0001"
        assert no2 == "INV-0002"
        assert no3 == "INV-0001"  # Reset to start
