"""
Tests — Integration Audit Log
=================================
Verifies immutable, append-only audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from integration.adapters import Direction
from integration.audit_log import IntegrationAuditEntry, IntegrationAuditLog


BIZ_A = uuid.uuid4()
BIZ_B = uuid.uuid4()
T0 = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestAuditEntry:
    def test_frozen(self):
        entry = IntegrationAuditEntry(
            audit_id=uuid.uuid4(),
            business_id=BIZ_A,
            external_system_id="stripe",
            direction=Direction.INBOUND,
            event_type="payment.completed",
            actor_id="system.integration.stripe",
            payload_hash="abc123",
            status="SUCCESS",
            occurred_at=T0,
        )
        with pytest.raises(AttributeError):
            entry.status = "FAILED"

    def test_to_dict(self):
        entry = IntegrationAuditEntry(
            audit_id=uuid.uuid4(),
            business_id=BIZ_A,
            external_system_id="kds",
            direction=Direction.OUTBOUND,
            event_type="kitchen.ticket.sent",
            actor_id="system.integration.outbound",
            payload_hash="def456",
            status="FAILED",
            occurred_at=T0,
            error_code="TIMEOUT",
            error_message="KDS unreachable",
        )
        d = entry.to_dict()
        assert d["direction"] == "OUTBOUND"
        assert d["status"] == "FAILED"
        assert d["error_code"] == "TIMEOUT"


class TestAuditLog:
    def test_append_only(self):
        log = IntegrationAuditLog()
        assert len(log.entries) == 0

        log.record_success(
            business_id=BIZ_A,
            external_system_id="stripe",
            direction=Direction.INBOUND,
            event_type="payment.completed",
            actor_id="system",
            payload_hash="abc",
            occurred_at=T0,
        )
        assert len(log.entries) == 1

    def test_record_failure(self):
        log = IntegrationAuditLog()
        entry = log.record_failure(
            business_id=BIZ_A,
            external_system_id="kds",
            direction=Direction.OUTBOUND,
            event_type="ticket.sent",
            actor_id="system",
            payload_hash="xyz",
            occurred_at=T0,
            error_code="TIMEOUT",
            error_message="unreachable",
            retry_count=3,
        )
        assert entry.status == "FAILED"
        assert entry.retry_count == 3

    def test_query_by_business_is_tenant_scoped(self):
        log = IntegrationAuditLog()
        log.record_success(
            business_id=BIZ_A, external_system_id="s1",
            direction=Direction.INBOUND, event_type="e1",
            actor_id="a", payload_hash="h1", occurred_at=T0,
        )
        log.record_success(
            business_id=BIZ_B, external_system_id="s2",
            direction=Direction.INBOUND, event_type="e2",
            actor_id="a", payload_hash="h2", occurred_at=T0,
        )
        assert len(log.query_by_business(BIZ_A)) == 1
        assert len(log.query_by_business(BIZ_B)) == 1

    def test_query_by_system(self):
        log = IntegrationAuditLog()
        log.record_success(
            business_id=BIZ_A, external_system_id="stripe",
            direction=Direction.INBOUND, event_type="e1",
            actor_id="a", payload_hash="h1", occurred_at=T0,
        )
        log.record_success(
            business_id=BIZ_A, external_system_id="kds",
            direction=Direction.OUTBOUND, event_type="e2",
            actor_id="a", payload_hash="h2", occurred_at=T0,
        )
        assert len(log.query_by_system(BIZ_A, "stripe")) == 1
        assert len(log.query_by_system(BIZ_A, "kds")) == 1

    def test_query_failures(self):
        log = IntegrationAuditLog()
        log.record_success(
            business_id=BIZ_A, external_system_id="s1",
            direction=Direction.INBOUND, event_type="e1",
            actor_id="a", payload_hash="h1", occurred_at=T0,
        )
        log.record_failure(
            business_id=BIZ_A, external_system_id="s1",
            direction=Direction.OUTBOUND, event_type="e2",
            actor_id="a", payload_hash="h2", occurred_at=T0,
            error_code="ERR", error_message="boom",
        )
        failures = log.query_failures(BIZ_A)
        assert len(failures) == 1
        assert failures[0].error_code == "ERR"
