"""
Tests — Integration Adapter Utilities
=========================================
Error hierarchy, signature verification, external event reference.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from integration.adapters import (
    AdapterConfig,
    AuthenticationError,
    Direction,
    ExternalEventReference,
    IntegrationError,
    TransientError,
    TranslationError,
    ValidationError,
    verify_hmac_signature,
)


# ══════════════════════════════════════════════════════════════
# ERROR HIERARCHY
# ══════════════════════════════════════════════════════════════


class TestErrorHierarchy:
    def test_all_errors_are_integration_errors(self):
        assert issubclass(ValidationError, IntegrationError)
        assert issubclass(TranslationError, IntegrationError)
        assert issubclass(AuthenticationError, IntegrationError)
        assert issubclass(TransientError, IntegrationError)

    def test_validation_error_not_retryable(self):
        e = ValidationError("bad payload", system_id="stripe")
        assert e.retryable is False
        assert e.system_id == "stripe"

    def test_transient_error_is_retryable(self):
        e = TransientError("timeout", system_id="kds")
        assert e.retryable is True

    def test_authentication_error_not_retryable(self):
        e = AuthenticationError("bad signature")
        assert e.retryable is False


# ══════════════════════════════════════════════════════════════
# EXTERNAL EVENT REFERENCE
# ══════════════════════════════════════════════════════════════


class TestExternalEventReference:
    def test_is_frozen(self):
        ref = ExternalEventReference(
            external_event_id="evt_123",
            system_id="stripe",
            received_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            business_id=uuid.uuid4(),
        )
        with pytest.raises(AttributeError):
            ref.system_id = "other"

    def test_payload_hash_deterministic(self):
        payload = {"amount": 100, "currency": "USD"}
        h1 = ExternalEventReference.compute_payload_hash(payload)
        h2 = ExternalEventReference.compute_payload_hash(payload)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_payload_hash_differs_for_different_data(self):
        h1 = ExternalEventReference.compute_payload_hash({"a": 1})
        h2 = ExternalEventReference.compute_payload_hash({"a": 2})
        assert h1 != h2

    def test_payload_hash_key_order_independent(self):
        h1 = ExternalEventReference.compute_payload_hash({"b": 2, "a": 1})
        h2 = ExternalEventReference.compute_payload_hash({"a": 1, "b": 2})
        assert h1 == h2


# ══════════════════════════════════════════════════════════════
# HMAC SIGNATURE VERIFICATION
# ══════════════════════════════════════════════════════════════


class TestHmacSignature:
    def test_valid_sha256_signature(self):
        import hashlib, hmac
        secret = "test-secret"
        payload = b'{"event": "payment.completed"}'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert verify_hmac_signature(payload, sig, secret, "sha256") is True

    def test_invalid_signature_rejected(self):
        payload = b'{"event": "payment.completed"}'
        assert verify_hmac_signature(payload, "bad-sig", "secret", "sha256") is False

    def test_sha1_algorithm(self):
        import hashlib, hmac
        secret = "s1-secret"
        payload = b"test-body"
        sig = hmac.new(secret.encode(), payload, hashlib.sha1).hexdigest()
        assert verify_hmac_signature(payload, sig, secret, "sha1") is True

    def test_unknown_algorithm_rejected(self):
        assert verify_hmac_signature(b"x", "sig", "sec", "md5") is False


# ══════════════════════════════════════════════════════════════
# ADAPTER CONFIG
# ══════════════════════════════════════════════════════════════


class TestAdapterConfig:
    def test_frozen(self):
        cfg = AdapterConfig(
            adapter_id=uuid.uuid4(),
            system_id="stripe",
            system_type="payment_gateway",
            business_id=uuid.uuid4(),
        )
        with pytest.raises(AttributeError):
            cfg.enabled = False

    def test_defaults(self):
        cfg = AdapterConfig(
            adapter_id=uuid.uuid4(),
            system_id="x",
            system_type="y",
            business_id=uuid.uuid4(),
        )
        assert cfg.enabled is True
        assert cfg.direction == Direction.INBOUND
        assert cfg.max_retries == 3
