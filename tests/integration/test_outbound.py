"""
Tests — Outbound Publisher Framework
=========================================
Subscribes to BOS events, translates, delivers to external systems.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Set

import pytest

from integration.adapters import TransientError
from integration.audit_log import IntegrationAuditLog
from integration.outbound import (
    OutboundEventDispatcher,
    OutboundPublisher,
    OutboundPublisherRegistry,
    OutboundResult,
)


# ── Test Doubles ─────────────────────────────────────────────

BIZ = uuid.uuid4()
T0 = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class FakeKDSPublisher(OutboundPublisher):
    """Simulates publishing to a Kitchen Display System."""

    def __init__(self, should_fail: bool = False, transient_failures: int = 0):
        self._should_fail = should_fail
        self._transient_remaining = transient_failures
        self.delivered: list = []

    @property
    def system_id(self) -> str:
        return "kds_vendor_x"

    @property
    def handled_event_types(self) -> Set[str]:
        return {"restaurant.kitchen.ticket.sent.v1"}

    def translate(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "kds_order_id": event.get("payload", {}).get("order_id"),
            "items": event.get("payload", {}).get("items", []),
        }

    def deliver(self, translated_payload: Dict[str, Any]) -> bool:
        if self._transient_remaining > 0:
            self._transient_remaining -= 1
            raise TransientError("KDS temporarily unavailable", system_id="kds_vendor_x")
        if self._should_fail:
            raise RuntimeError("KDS permanently down")
        self.delivered.append(translated_payload)
        return True


class FakeAccountingPublisher(OutboundPublisher):
    def __init__(self):
        self.delivered: list = []

    @property
    def system_id(self) -> str:
        return "accounting_erp"

    @property
    def handled_event_types(self) -> Set[str]:
        return {"accounting.journal.posted.v1"}

    def translate(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return {"journal_id": event.get("payload", {}).get("journal_id")}

    def deliver(self, translated_payload: Dict[str, Any]) -> bool:
        self.delivered.append(translated_payload)
        return True


class FailTranslatePublisher(OutboundPublisher):
    @property
    def system_id(self) -> str:
        return "bad_pub"

    @property
    def handled_event_types(self) -> Set[str]:
        return {"test.event.v1"}

    def translate(self, event: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError("Cannot translate")

    def deliver(self, translated_payload: Dict[str, Any]) -> bool:
        return True


# ══════════════════════════════════════════════════════════════
# REGISTRY
# ══════════════════════════════════════════════════════════════


class TestOutboundRegistry:
    def test_register_and_get(self):
        reg = OutboundPublisherRegistry()
        pub = FakeKDSPublisher()
        reg.register(pub)
        assert reg.get("kds_vendor_x") is pub

    def test_event_routing(self):
        reg = OutboundPublisherRegistry()
        reg.register(FakeKDSPublisher())
        pubs = reg.get_publishers_for_event("restaurant.kitchen.ticket.sent.v1")
        assert len(pubs) == 1
        assert pubs[0].system_id == "kds_vendor_x"

    def test_no_publishers_for_unknown_event(self):
        reg = OutboundPublisherRegistry()
        reg.register(FakeKDSPublisher())
        pubs = reg.get_publishers_for_event("unknown.event.v1")
        assert len(pubs) == 0

    def test_multiple_publishers_for_same_event(self):
        reg = OutboundPublisherRegistry()
        # Both handle accounting events
        class Pub2(FakeAccountingPublisher):
            @property
            def system_id(self):
                return "bi_warehouse"
        reg.register(FakeAccountingPublisher())
        reg.register(Pub2())
        pubs = reg.get_publishers_for_event("accounting.journal.posted.v1")
        assert len(pubs) == 2


# ══════════════════════════════════════════════════════════════
# OUTBOUND DISPATCHER — HAPPY PATH
# ══════════════════════════════════════════════════════════════


class TestOutboundDispatcherHappy:
    def _setup(self):
        reg = OutboundPublisherRegistry()
        kds = FakeKDSPublisher()
        reg.register(kds)
        audit = IntegrationAuditLog()
        disp = OutboundEventDispatcher(reg, audit)
        return disp, kds, audit

    def test_successful_publish(self):
        disp, kds, audit = self._setup()
        event = {
            "event_type": "restaurant.kitchen.ticket.sent.v1",
            "business_id": str(BIZ),
            "payload": {"order_id": "ORD-1", "items": ["burger"]},
        }
        results = disp.publish(event, T0)
        assert len(results) == 1
        assert results[0].success is True
        assert len(kds.delivered) == 1

    def test_audit_logged_on_success(self):
        disp, _, audit = self._setup()
        event = {
            "event_type": "restaurant.kitchen.ticket.sent.v1",
            "business_id": str(BIZ),
            "payload": {"order_id": "O1"},
        }
        disp.publish(event, T0)
        entries = audit.query_by_business(BIZ)
        assert len(entries) == 1
        assert entries[0].status == "SUCCESS"

    def test_no_publishers_returns_empty(self):
        disp, _, _ = self._setup()
        event = {"event_type": "unknown.event.v1", "business_id": str(BIZ), "payload": {}}
        results = disp.publish(event, T0)
        assert results == []


# ══════════════════════════════════════════════════════════════
# OUTBOUND DISPATCHER — RETRY
# ══════════════════════════════════════════════════════════════


class TestOutboundRetry:
    def test_transient_error_retried_and_succeeds(self):
        reg = OutboundPublisherRegistry()
        kds = FakeKDSPublisher(transient_failures=2)  # fail 2x, succeed 3rd
        reg.register(kds)
        audit = IntegrationAuditLog()
        disp = OutboundEventDispatcher(reg, audit, max_retries=3)

        event = {
            "event_type": "restaurant.kitchen.ticket.sent.v1",
            "business_id": str(BIZ),
            "payload": {"order_id": "O1"},
        }
        results = disp.publish(event, T0)
        assert results[0].success is True
        assert results[0].retry_count == 2  # succeeded on 3rd attempt

    def test_all_retries_exhausted(self):
        reg = OutboundPublisherRegistry()
        kds = FakeKDSPublisher(transient_failures=10)  # never succeeds
        reg.register(kds)
        audit = IntegrationAuditLog()
        disp = OutboundEventDispatcher(reg, audit, max_retries=2)

        event = {
            "event_type": "restaurant.kitchen.ticket.sent.v1",
            "business_id": str(BIZ),
            "payload": {"order_id": "O1"},
        }
        results = disp.publish(event, T0)
        assert results[0].success is False
        assert results[0].error_code == "DELIVERY_FAILED"
        failures = audit.query_failures(BIZ)
        assert len(failures) == 1


# ══════════════════════════════════════════════════════════════
# OUTBOUND DISPATCHER — ERRORS
# ══════════════════════════════════════════════════════════════


class TestOutboundErrors:
    def test_permanent_failure(self):
        reg = OutboundPublisherRegistry()
        kds = FakeKDSPublisher(should_fail=True)
        reg.register(kds)
        audit = IntegrationAuditLog()
        disp = OutboundEventDispatcher(reg, audit, max_retries=2)

        event = {
            "event_type": "restaurant.kitchen.ticket.sent.v1",
            "business_id": str(BIZ),
            "payload": {},
        }
        results = disp.publish(event, T0)
        assert results[0].success is False
        assert "permanently down" in results[0].error_message

    def test_translation_failure(self):
        reg = OutboundPublisherRegistry()
        reg.register(FailTranslatePublisher())
        audit = IntegrationAuditLog()
        disp = OutboundEventDispatcher(reg, audit)

        event = {
            "event_type": "test.event.v1",
            "business_id": str(BIZ),
            "payload": {},
        }
        results = disp.publish(event, T0)
        assert results[0].success is False
        assert results[0].error_code == "TRANSLATION_FAILED"
