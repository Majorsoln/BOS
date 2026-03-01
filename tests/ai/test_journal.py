"""
Tests for ai.journal — Decision Journal (append-only AI decision log).
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta

from ai.journal.models import DecisionEntry, DecisionMode, DecisionOutcome
from ai.journal.store import DecisionJournal


BIZ_ID = uuid.uuid4()
NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_entry(**overrides) -> DecisionEntry:
    defaults = dict(
        decision_id=uuid.uuid4(),
        tenant_id=BIZ_ID,
        engine="inventory",
        advice_type="reorder_suggestion",
        advice={"item": "SKU-001", "qty": 100},
        mode=DecisionMode.ADVISORY,
        outcome=DecisionOutcome.PENDING,
        actor_type="AI",
        actor_id="inventory-advisor-v1",
        occurred_at=NOW,
    )
    defaults.update(overrides)
    return DecisionEntry(**defaults)


class TestDecisionEntry:
    def test_create_valid_entry(self):
        entry = _make_entry()
        assert entry.is_pending()
        assert not entry.is_resolved()

    def test_frozen_immutability(self):
        entry = _make_entry()
        with pytest.raises(AttributeError):
            entry.outcome = DecisionOutcome.ACCEPTED

    def test_requires_uuid_tenant(self):
        with pytest.raises(ValueError, match="UUID"):
            _make_entry(tenant_id="not-uuid")

    def test_requires_engine(self):
        with pytest.raises(ValueError, match="engine"):
            _make_entry(engine="")


class TestDecisionJournal:
    def test_record_and_retrieve(self):
        journal = DecisionJournal()
        entry = _make_entry()
        journal.record(entry)
        assert journal.get(entry.decision_id) == entry
        assert journal.count == 1

    def test_duplicate_rejected(self):
        journal = DecisionJournal()
        entry = _make_entry()
        journal.record(entry)
        with pytest.raises(ValueError, match="already exists"):
            journal.record(entry)

    def test_list_by_tenant(self):
        journal = DecisionJournal()
        e1 = _make_entry(engine="inventory")
        e2 = _make_entry(engine="cash")
        e3 = _make_entry(tenant_id=uuid.uuid4(), engine="inventory")
        journal.record(e1)
        journal.record(e2)
        journal.record(e3)

        biz_entries = journal.list_by_tenant(BIZ_ID)
        assert len(biz_entries) == 2

        inv_entries = journal.list_by_tenant(BIZ_ID, engine="inventory")
        assert len(inv_entries) == 1

    def test_list_pending(self):
        journal = DecisionJournal()
        pending = _make_entry(outcome=DecisionOutcome.PENDING)
        accepted = _make_entry(outcome=DecisionOutcome.ACCEPTED)
        journal.record(pending)
        journal.record(accepted)

        pending_list = journal.list_pending(BIZ_ID)
        assert len(pending_list) == 1
        assert pending_list[0].decision_id == pending.decision_id

    def test_resolve_pending_to_accepted(self):
        journal = DecisionJournal()
        entry = _make_entry()
        journal.record(entry)

        resolved = journal.resolve(
            decision_id=entry.decision_id,
            outcome=DecisionOutcome.ACCEPTED,
            reviewed_by="manager-1",
            reviewed_at=NOW + timedelta(hours=1),
        )
        assert resolved.outcome == DecisionOutcome.ACCEPTED
        assert resolved.reviewed_by == "manager-1"
        assert journal.list_pending(BIZ_ID) == []

    def test_resolve_pending_to_rejected(self):
        journal = DecisionJournal()
        entry = _make_entry()
        journal.record(entry)

        resolved = journal.resolve(
            decision_id=entry.decision_id,
            outcome=DecisionOutcome.REJECTED,
            reviewed_by="manager-1",
            reviewed_at=NOW + timedelta(hours=1),
        )
        assert resolved.outcome == DecisionOutcome.REJECTED

    def test_cannot_re_resolve(self):
        journal = DecisionJournal()
        entry = _make_entry()
        journal.record(entry)
        journal.resolve(
            decision_id=entry.decision_id,
            outcome=DecisionOutcome.ACCEPTED,
            reviewed_by="m1",
            reviewed_at=NOW,
        )
        with pytest.raises(ValueError, match="already"):
            journal.resolve(
                decision_id=entry.decision_id,
                outcome=DecisionOutcome.REJECTED,
                reviewed_by="m2",
                reviewed_at=NOW,
            )

    def test_resolve_nonexistent_raises(self):
        journal = DecisionJournal()
        with pytest.raises(ValueError, match="not found"):
            journal.resolve(
                decision_id=uuid.uuid4(),
                outcome=DecisionOutcome.ACCEPTED,
                reviewed_by="m1",
                reviewed_at=NOW,
            )
