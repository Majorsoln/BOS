"""Tests for core/platform/platform_audit.py"""
from datetime import datetime

import pytest

from core.platform.platform_audit import (
    PlatformAuditProjection,
    PlatformAuditService,
    RecordAuditEntryRequest,
    PLATFORM_TENANT_ONBOARDED_V1,
    PLATFORM_TENANT_SUSPENDED_V1,
    PLATFORM_TENANT_TERMINATED_V1,
    PLATFORM_KILL_SWITCH_ACTIVATED_V1,
    PLATFORM_FLAG_TOGGLED_V1,
)

NOW = datetime(2026, 3, 5, 12, 0, 0)
ADMIN = "platform-admin-001"
TENANT_ID = "tenant-abc-123"


@pytest.fixture
def projection():
    return PlatformAuditProjection()


@pytest.fixture
def service(projection):
    return PlatformAuditService(projection)


class TestRecordEntry:
    def test_record_creates_entry(self, service, projection):
        result = service.record(RecordAuditEntryRequest(
            event_type=PLATFORM_TENANT_ONBOARDED_V1,
            actor_id=ADMIN,
            actor_type="PLATFORM_ADMIN",
            issued_at=NOW,
            subject_type="TENANT",
            subject_id=TENANT_ID,
            payload={"business_name": "Test Shop", "region_code": "KE"},
        ))
        entry_id = result["entry_id"]
        entry = projection.get_entry(entry_id)
        assert entry is not None
        assert entry.event_type == PLATFORM_TENANT_ONBOARDED_V1
        assert entry.actor_id == ADMIN
        assert entry.subject_id == TENANT_ID

    def test_record_returns_event(self, service):
        result = service.record(RecordAuditEntryRequest(
            event_type=PLATFORM_TENANT_ONBOARDED_V1,
            actor_id=ADMIN,
            actor_type="PLATFORM_ADMIN",
            issued_at=NOW,
            subject_type="TENANT",
            subject_id=TENANT_ID,
            payload={},
        ))
        assert len(result["events"]) == 1
        assert result["events"][0]["event_type"] == PLATFORM_TENANT_ONBOARDED_V1

    def test_record_with_correlation_id(self, service, projection):
        result = service.record(RecordAuditEntryRequest(
            event_type=PLATFORM_TENANT_SUSPENDED_V1,
            actor_id=ADMIN,
            actor_type="PLATFORM_ADMIN",
            issued_at=NOW,
            subject_type="TENANT",
            subject_id=TENANT_ID,
            payload={"reason": "NON_PAYMENT"},
            correlation_id="corr-001",
        ))
        entry = projection.get_entry(result["entry_id"])
        assert entry.correlation_id == "corr-001"


class TestConvenienceMethods:
    def test_record_tenant_onboarded(self, service, projection):
        result = service.record_tenant_onboarded(
            tenant_id=TENANT_ID,
            business_name="Mama Mboga",
            region_code="KE",
            actor_id=ADMIN,
            issued_at=NOW,
        )
        entry = projection.get_entry(result["entry_id"])
        assert entry.event_type == PLATFORM_TENANT_ONBOARDED_V1
        assert entry.payload["region_code"] == "KE"
        assert entry.region_code == "KE"

    def test_record_tenant_suspended(self, service, projection):
        result = service.record_tenant_suspended(
            tenant_id=TENANT_ID,
            reason="NON_PAYMENT",
            actor_id=ADMIN,
            issued_at=NOW,
        )
        entry = projection.get_entry(result["entry_id"])
        assert entry.event_type == PLATFORM_TENANT_SUSPENDED_V1
        assert entry.payload["reason"] == "NON_PAYMENT"

    def test_record_tenant_terminated(self, service, projection):
        result = service.record_tenant_terminated(
            tenant_id=TENANT_ID,
            reason="FRAUD",
            actor_id=ADMIN,
            issued_at=NOW,
        )
        entry = projection.get_entry(result["entry_id"])
        assert entry.event_type == PLATFORM_TENANT_TERMINATED_V1
        assert entry.notes is not None and "KILL SWITCH" in entry.notes

    def test_record_kill_switch(self, service, projection):
        result = service.record_kill_switch(
            tenant_id=TENANT_ID,
            reason="Malicious use",
            actor_id=ADMIN,
            issued_at=NOW,
        )
        entry = projection.get_entry(result["entry_id"])
        assert entry.event_type == PLATFORM_KILL_SWITCH_ACTIVATED_V1

    def test_record_flag_toggled(self, service, projection):
        result = service.record_flag_toggled(
            flag_name="FLAG_ENABLE_DOCUMENT_ENGINE",
            enabled=True,
            scope="TENANT",
            scope_id=TENANT_ID,
            actor_id=ADMIN,
            issued_at=NOW,
        )
        entry = projection.get_entry(result["entry_id"])
        assert entry.event_type == PLATFORM_FLAG_TOGGLED_V1
        assert entry.payload["enabled"] is True

    def test_record_region_pack_applied(self, service, projection):
        result = service.record_region_pack_applied(
            business_id=TENANT_ID,
            region_code="KE",
            pack_version=2,
            actor_id=ADMIN,
            issued_at=NOW,
        )
        entry = projection.get_entry(result["entry_id"])
        assert entry.payload["pack_version"] == 2

    def test_record_schema_migrated(self, service, projection):
        result = service.record_schema_migrated(
            migration_id="0042_add_business_fields",
            version_from="0041",
            version_to="0042",
            actor_id="SYSTEM",
            issued_at=NOW,
            region_code="EU",
        )
        entry = projection.get_entry(result["entry_id"])
        assert entry.actor_id == "SYSTEM"
        assert entry.region_code == "EU"


class TestQueryHelpers:
    def test_get_tenant_history(self, service, projection):
        service.record_tenant_onboarded(TENANT_ID, "Test", "KE", ADMIN, NOW)
        service.record_tenant_suspended(TENANT_ID, "NON_PAYMENT", ADMIN, NOW)
        history = service.get_tenant_history(TENANT_ID)
        assert len(history) == 2

    def test_get_by_actor(self, service, projection):
        service.record_tenant_onboarded(TENANT_ID, "Test", "KE", ADMIN, NOW)
        service.record_tenant_onboarded("tenant-2", "Test2", "TZ", ADMIN, NOW)
        by_actor = projection.get_by_actor(ADMIN)
        assert len(by_actor) == 2

    def test_get_by_event_type(self, service, projection):
        service.record_tenant_onboarded(TENANT_ID, "Test", "KE", ADMIN, NOW)
        service.record_tenant_suspended(TENANT_ID, "NON_PAYMENT", ADMIN, NOW)
        onboarded = projection.get_by_event_type(PLATFORM_TENANT_ONBOARDED_V1)
        assert len(onboarded) == 1

    def test_get_recent_events(self, service, projection):
        for i in range(5):
            service.record_tenant_onboarded(f"tenant-{i}", "X", "KE", ADMIN, NOW)
        recent = service.get_recent_platform_events(limit=3)
        assert len(recent) == 3

    def test_multiple_entries_append_only(self, service, projection):
        for i in range(10):
            service.record_tenant_onboarded(f"t-{i}", "X", "KE", ADMIN, NOW)
        all_entries = projection.get_recent(100)
        assert len(all_entries) == 10
        # all unique entry_ids
        ids = [e.entry_id for e in all_entries]
        assert len(ids) == len(set(ids))
