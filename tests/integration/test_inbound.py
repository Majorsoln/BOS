"""
Tests — Inbound Adapter Framework
=====================================
Validates, translates, dispatches external events to BOS command bus.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import pytest

from integration.adapters import TranslationError, ValidationError
from integration.audit_log import IntegrationAuditLog
from integration.inbound import (
    InboundAdapter,
    InboundAdapterRegistry,
    InboundDispatcher,
    InboundResult,
)


# ── Test Doubles ─────────────────────────────────────────────

BIZ = uuid.uuid4()
T0 = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class FakePaymentAdapter(InboundAdapter):
    """Test adapter simulating a payment gateway."""

    @property
    def system_id(self) -> str:
        return "stripe"

    @property
    def system_type(self) -> str:
        return "payment_gateway"

    def validate(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if "amount" not in payload:
            return False, "Missing 'amount' field."
        if payload["amount"] <= 0:
            return False, "Amount must be positive."
        return True, None

    def translate_to_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "command_type": "cash.payment.record.request",
            "business_id": str(payload["business_id"]),
            "payload": {
                "amount": payload["amount"],
                "currency": payload.get("currency", "USD"),
                "external_payment_id": payload.get("event_id"),
            },
            "actor_id": "system.integration.stripe",
        }


class FailingTranslateAdapter(InboundAdapter):
    @property
    def system_id(self) -> str:
        return "bad_translator"

    @property
    def system_type(self) -> str:
        return "test"

    def validate(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None

    def translate_to_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise TranslationError("Cannot map this event", system_id="bad_translator")


class StubCommandDispatch:
    def __init__(self, should_fail: bool = False):
        self.dispatched = []
        self._should_fail = should_fail

    def dispatch(self, command: Dict[str, Any]) -> Any:
        if self._should_fail:
            raise RuntimeError("Command bus down")
        self.dispatched.append(command)
        return {"status": "ACCEPTED"}


# ══════════════════════════════════════════════════════════════
# REGISTRY
# ══════════════════════════════════════════════════════════════


class TestInboundRegistry:
    def test_register_and_get(self):
        reg = InboundAdapterRegistry()
        adapter = FakePaymentAdapter()
        reg.register(adapter)
        assert reg.get("stripe") is adapter

    def test_get_unknown_returns_none(self):
        reg = InboundAdapterRegistry()
        assert reg.get("unknown") is None

    def test_list_system_ids(self):
        reg = InboundAdapterRegistry()
        reg.register(FakePaymentAdapter())
        assert "stripe" in reg.list_system_ids()


# ══════════════════════════════════════════════════════════════
# INBOUND DISPATCHER — HAPPY PATH
# ══════════════════════════════════════════════════════════════


class TestInboundDispatcherHappy:
    def _setup(self):
        reg = InboundAdapterRegistry()
        reg.register(FakePaymentAdapter())
        dispatch = StubCommandDispatch()
        audit = IntegrationAuditLog()
        dispatcher = InboundDispatcher(reg, dispatch, audit)
        return dispatcher, dispatch, audit

    def test_successful_processing(self):
        disp, cmd_bus, audit = self._setup()
        payload = {
            "event_id": "evt_123",
            "business_id": str(BIZ),
            "amount": 500,
            "currency": "EUR",
        }
        result = disp.process("stripe", payload, T0)
        assert result.success is True
        assert result.command is not None
        assert result.command["command_type"] == "cash.payment.record.request"
        assert len(cmd_bus.dispatched) == 1

    def test_audit_logged_on_success(self):
        disp, _, audit = self._setup()
        payload = {"event_id": "evt_1", "business_id": str(BIZ), "amount": 100}
        disp.process("stripe", payload, T0)
        entries = audit.query_by_business(BIZ)
        assert len(entries) == 1
        assert entries[0].status == "SUCCESS"
        assert entries[0].external_system_id == "stripe"


# ══════════════════════════════════════════════════════════════
# INBOUND DISPATCHER — ERROR PATHS
# ══════════════════════════════════════════════════════════════


class TestInboundDispatcherErrors:
    def _setup(self, **kwargs):
        reg = InboundAdapterRegistry()
        reg.register(FakePaymentAdapter())
        reg.register(FailingTranslateAdapter())
        dispatch = StubCommandDispatch(**kwargs)
        audit = IntegrationAuditLog()
        dispatcher = InboundDispatcher(reg, dispatch, audit)
        return dispatcher, dispatch, audit

    def test_unknown_system_id(self):
        disp, _, _ = self._setup()
        result = disp.process("nonexistent", {"business_id": str(BIZ)}, T0)
        assert result.success is False
        assert result.error_code == "UNKNOWN_SYSTEM"

    def test_missing_business_id(self):
        disp, _, _ = self._setup()
        result = disp.process("stripe", {"amount": 100}, T0)
        assert result.success is False
        assert result.error_code == "MISSING_BUSINESS_ID"

    def test_invalid_business_id(self):
        disp, _, _ = self._setup()
        result = disp.process("stripe", {"business_id": "not-a-uuid", "amount": 100}, T0)
        assert result.success is False
        assert result.error_code == "INVALID_BUSINESS_ID"

    def test_validation_failure(self):
        disp, _, audit = self._setup()
        payload = {"business_id": str(BIZ)}  # missing amount
        result = disp.process("stripe", payload, T0)
        assert result.success is False
        assert result.error_code == "VALIDATION_FAILED"
        assert "amount" in result.error_message.lower()
        # Audit logged
        failures = audit.query_failures(BIZ)
        assert len(failures) == 1

    def test_translation_failure(self):
        disp, _, audit = self._setup()
        payload = {"business_id": str(BIZ), "event_id": "x"}
        result = disp.process("bad_translator", payload, T0)
        assert result.success is False
        assert result.error_code == "TRANSLATION_FAILED"

    def test_dispatch_failure(self):
        disp, _, audit = self._setup(should_fail=True)
        payload = {"business_id": str(BIZ), "amount": 100, "event_id": "e1"}
        result = disp.process("stripe", payload, T0)
        assert result.success is False
        assert result.error_code == "DISPATCH_FAILED"
        failures = audit.query_failures(BIZ)
        assert len(failures) == 1
