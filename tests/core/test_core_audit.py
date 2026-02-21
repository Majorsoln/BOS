"""
Tests for core.audit — Audit log entries and consent tracking.
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta

from core.audit.models import AuditEntry, ConsentRecord
from core.audit.functions import create_audit_entry, grant_consent, revoke_consent


BIZ_ID = uuid.uuid4()
BRANCH_ID = uuid.uuid4()
NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


# ── AuditEntry Tests ─────────────────────────────────────────

class TestAuditEntry:
    def test_create_valid_entry(self):
        entry = AuditEntry(
            entry_id=uuid.uuid4(),
            event_id=uuid.uuid4(),
            actor_id="user-1",
            actor_type="HUMAN",
            action="cash.cashin.create",
            resource_type="CashIn",
            resource_id="ci-001",
            business_id=BIZ_ID,
            branch_id=BRANCH_ID,
            status="EXECUTED",
            occurred_at=NOW,
        )
        assert entry.status == "EXECUTED"
        assert entry.business_id == BIZ_ID

    def test_frozen_immutability(self):
        entry = AuditEntry(
            entry_id=uuid.uuid4(),
            event_id=uuid.uuid4(),
            actor_id="user-1",
            actor_type="HUMAN",
            action="test",
            resource_type="Test",
            resource_id="t-1",
            business_id=BIZ_ID,
            branch_id=None,
            status="EXECUTED",
            occurred_at=NOW,
        )
        with pytest.raises(AttributeError):
            entry.status = "REJECTED"

    def test_invalid_status_rejected(self):
        with pytest.raises(ValueError, match="EXECUTED|REJECTED|ERROR"):
            AuditEntry(
                entry_id=uuid.uuid4(),
                event_id=uuid.uuid4(),
                actor_id="user-1",
                actor_type="HUMAN",
                action="test",
                resource_type="Test",
                resource_id="t-1",
                business_id=BIZ_ID,
                branch_id=None,
                status="INVALID",
                occurred_at=NOW,
            )


# ── ConsentRecord Tests ──────────────────────────────────────

class TestConsentRecord:
    def test_valid_consent(self):
        record = ConsentRecord(
            consent_id=uuid.uuid4(),
            subject_id="user-1",
            consent_type="BIOMETRIC_CAPTURE",
            business_id=BIZ_ID,
            granted_at=NOW,
        )
        assert record.is_valid(NOW)

    def test_expired_consent(self):
        record = ConsentRecord(
            consent_id=uuid.uuid4(),
            subject_id="user-1",
            consent_type="DATA_PROCESSING",
            business_id=BIZ_ID,
            granted_at=NOW,
            expires_at=NOW + timedelta(hours=1),
        )
        assert record.is_valid(NOW)
        assert not record.is_valid(NOW + timedelta(hours=2))

    def test_revoked_consent(self):
        record = ConsentRecord(
            consent_id=uuid.uuid4(),
            subject_id="user-1",
            consent_type="MARKETING",
            business_id=BIZ_ID,
            granted_at=NOW,
            revoked_at=NOW + timedelta(minutes=30),
        )
        assert not record.is_valid(NOW + timedelta(hours=1))

    def test_frozen_immutability(self):
        record = ConsentRecord(
            consent_id=uuid.uuid4(),
            subject_id="user-1",
            consent_type="MARKETING",
            business_id=BIZ_ID,
            granted_at=NOW,
        )
        with pytest.raises(AttributeError):
            record.revoked_at = NOW


# ── Factory Function Tests ───────────────────────────────────

class TestAuditFunctions:
    def test_create_audit_entry(self):
        event_id = uuid.uuid4()
        entry = create_audit_entry(
            event_id=event_id,
            actor_id="user-1",
            actor_type="HUMAN",
            action="retail.sale.create",
            resource_type="Sale",
            resource_id="s-001",
            business_id=BIZ_ID,
            status="EXECUTED",
            occurred_at=NOW,
            branch_id=BRANCH_ID,
        )
        assert entry.event_id == event_id
        assert entry.entry_id is not None
        assert entry.branch_id == BRANCH_ID

    def test_grant_consent(self):
        record = grant_consent(
            subject_id="user-1",
            consent_type="BIOMETRIC_CAPTURE",
            business_id=BIZ_ID,
            granted_at=NOW,
            expires_at=NOW + timedelta(days=365),
        )
        assert record.consent_id is not None
        assert record.is_valid(NOW)

    def test_revoke_consent_creates_new_record(self):
        original = grant_consent(
            subject_id="user-1",
            consent_type="DATA_PROCESSING",
            business_id=BIZ_ID,
            granted_at=NOW,
        )
        revoked = revoke_consent(original, revoked_at=NOW + timedelta(hours=1))
        assert original.revoked_at is None  # Original unchanged
        assert revoked.revoked_at is not None
        assert not revoked.is_valid(NOW + timedelta(hours=2))
        assert revoked.consent_id == original.consent_id
