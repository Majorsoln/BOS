"""
Tests for projections/bi/subscriptions.py

Covers:
  RP-02  handle_cash_session_closed
  RP-11  handle_workshop_quote_{generated,accepted,rejected}
"""

import types
import uuid

import pytest

from projections.bi import kpi_store
from projections.bi.subscriptions import (
    handle_cash_session_closed,
    handle_workshop_quote_accepted,
    handle_workshop_quote_generated,
    handle_workshop_quote_rejected,
)


# ── Helpers ────────────────────────────────────────────────────

def _make_event(*, event_type: str, payload: dict, business_id=None):
    ev = types.SimpleNamespace()
    ev.event_id = uuid.uuid4()
    ev.event_type = event_type
    ev.business_id = business_id or uuid.uuid4()
    ev.payload = payload
    return ev


@pytest.fixture(autouse=True)
def clear_kpi_store():
    kpi_store.reset()
    yield
    kpi_store.reset()


# ══════════════════════════════════════════════════════════════
# RP-02 — Cash Session
# ══════════════════════════════════════════════════════════════

class TestHandleCashSessionClosed:
    def test_increments_sessions_closed(self):
        biz_id = uuid.uuid4()
        handle_cash_session_closed(
            _make_event(
                event_type="cash.session.closed.v1",
                payload={"variance": 0},
                business_id=biz_id,
            )
        )

        assert kpi_store.get_kpi(str(biz_id), "CASH_SESSIONS_CLOSED") == 1

    def test_accumulates_multiple_sessions(self):
        biz_id = uuid.uuid4()
        for _ in range(3):
            handle_cash_session_closed(
                _make_event(
                    event_type="cash.session.closed.v1",
                    payload={"variance": 0},
                    business_id=biz_id,
                )
            )

        assert kpi_store.get_kpi(str(biz_id), "CASH_SESSIONS_CLOSED") == 3

    def test_records_absolute_variance_positive(self):
        biz_id = uuid.uuid4()
        handle_cash_session_closed(
            _make_event(
                event_type="cash.session.closed.v1",
                payload={"variance": 200},
                business_id=biz_id,
            )
        )

        assert kpi_store.get_kpi(str(biz_id), "CASH_SESSION_VARIANCE") == 200

    def test_records_absolute_variance_negative(self):
        biz_id = uuid.uuid4()
        handle_cash_session_closed(
            _make_event(
                event_type="cash.session.closed.v1",
                payload={"variance": -350},
                business_id=biz_id,
            )
        )

        assert kpi_store.get_kpi(str(biz_id), "CASH_SESSION_VARIANCE") == 350

    def test_zero_variance_not_recorded(self):
        biz_id = uuid.uuid4()
        handle_cash_session_closed(
            _make_event(
                event_type="cash.session.closed.v1",
                payload={"variance": 0},
                business_id=biz_id,
            )
        )

        assert kpi_store.get_kpi(str(biz_id), "CASH_SESSION_VARIANCE") == 0

    def test_variance_accumulates_across_sessions(self):
        biz_id = uuid.uuid4()
        for v in [100, -200, 50]:
            handle_cash_session_closed(
                _make_event(
                    event_type="cash.session.closed.v1",
                    payload={"variance": v},
                    business_id=biz_id,
                )
            )

        assert kpi_store.get_kpi(str(biz_id), "CASH_SESSION_VARIANCE") == 350

    def test_different_businesses_isolated(self):
        biz_a, biz_b = uuid.uuid4(), uuid.uuid4()
        handle_cash_session_closed(
            _make_event(
                event_type="cash.session.closed.v1",
                payload={"variance": 0},
                business_id=biz_a,
            )
        )

        assert kpi_store.get_kpi(str(biz_a), "CASH_SESSIONS_CLOSED") == 1
        assert kpi_store.get_kpi(str(biz_b), "CASH_SESSIONS_CLOSED") == 0


# ══════════════════════════════════════════════════════════════
# RP-11 — Workshop Quote Pipeline
# ══════════════════════════════════════════════════════════════

class TestWorkshopQuotePipeline:
    def test_quote_generated_increments_count(self):
        biz_id = uuid.uuid4()
        handle_workshop_quote_generated(
            _make_event(
                event_type="workshop.quote.generated.v1",
                payload={"quote_id": "Q-001", "quote_value": 10_000},
                business_id=biz_id,
            )
        )

        assert kpi_store.get_kpi(str(biz_id), "QUOTES_GENERATED") == 1

    def test_quote_generated_accumulates_value(self):
        biz_id = uuid.uuid4()
        for v in [5_000, 7_500, 2_500]:
            handle_workshop_quote_generated(
                _make_event(
                    event_type="workshop.quote.generated.v1",
                    payload={"quote_value": v},
                    business_id=biz_id,
                )
            )

        assert kpi_store.get_kpi(str(biz_id), "QUOTES_GENERATED") == 3
        assert kpi_store.get_kpi(str(biz_id), "QUOTE_VALUE") == 15_000

    def test_quote_accepted_increments_count_and_value(self):
        biz_id = uuid.uuid4()
        handle_workshop_quote_accepted(
            _make_event(
                event_type="workshop.quote.accepted.v1",
                payload={"quote_id": "Q-002", "quote_value": 8_000},
                business_id=biz_id,
            )
        )

        assert kpi_store.get_kpi(str(biz_id), "QUOTES_ACCEPTED") == 1
        assert kpi_store.get_kpi(str(biz_id), "QUOTE_ACCEPTED_VALUE") == 8_000

    def test_quote_rejected_increments_count(self):
        biz_id = uuid.uuid4()
        handle_workshop_quote_rejected(
            _make_event(
                event_type="workshop.quote.rejected.v1",
                payload={"quote_id": "Q-003", "reason": "price"},
                business_id=biz_id,
            )
        )

        assert kpi_store.get_kpi(str(biz_id), "QUOTES_REJECTED") == 1

    def test_full_pipeline_conversion_rate_trackable(self):
        biz_id = uuid.uuid4()

        # 3 quotes generated
        for i in range(3):
            handle_workshop_quote_generated(
                _make_event(
                    event_type="workshop.quote.generated.v1",
                    payload={"quote_value": 10_000},
                    business_id=biz_id,
                )
            )

        # 2 accepted
        for i in range(2):
            handle_workshop_quote_accepted(
                _make_event(
                    event_type="workshop.quote.accepted.v1",
                    payload={"quote_value": 10_000},
                    business_id=biz_id,
                )
            )

        # 1 rejected
        handle_workshop_quote_rejected(
            _make_event(
                event_type="workshop.quote.rejected.v1",
                payload={},
                business_id=biz_id,
            )
        )

        kpis = kpi_store.get_kpis(str(biz_id))
        assert kpis["QUOTES_GENERATED"] == 3
        assert kpis["QUOTES_ACCEPTED"] == 2
        assert kpis["QUOTES_REJECTED"] == 1
        assert kpis["QUOTE_VALUE"] == 30_000
        assert kpis["QUOTE_ACCEPTED_VALUE"] == 20_000

    def test_quote_generated_with_no_value_does_not_increment_value_kpi(self):
        biz_id = uuid.uuid4()
        handle_workshop_quote_generated(
            _make_event(
                event_type="workshop.quote.generated.v1",
                payload={"quote_id": "Q-NO-VAL"},
                business_id=biz_id,
            )
        )

        assert kpi_store.get_kpi(str(biz_id), "QUOTES_GENERATED") == 1
        assert kpi_store.get_kpi(str(biz_id), "QUOTE_VALUE") == 0
