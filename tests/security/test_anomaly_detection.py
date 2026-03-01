"""
Tests — Anomaly Detection
============================
Verifies rule-based anomaly detection.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from core.security.anomaly_detection import (
    ActivityRecord,
    AnomalyDetector,
    AnomalyResult,
    AnomalySeverity,
)


# ── Helpers ──────────────────────────────────────────────────

BIZ = uuid.uuid4()
BRANCH_1 = uuid.uuid4()
BRANCH_2 = uuid.uuid4()
BRANCH_3 = uuid.uuid4()
BRANCH_4 = uuid.uuid4()
T0 = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _record(
    actor_id: str = "actor-1",
    business_id: uuid.UUID = BIZ,
    branch_id: uuid.UUID | None = BRANCH_1,
    command_type: str = "CASH:OPEN_SESSION",
    offset_seconds: int = 0,
    was_rejected: bool = False,
) -> ActivityRecord:
    return ActivityRecord(
        actor_id=actor_id,
        business_id=business_id,
        branch_id=branch_id,
        command_type=command_type,
        occurred_at=T0 + timedelta(seconds=offset_seconds),
        was_rejected=was_rejected,
    )


# ══════════════════════════════════════════════════════════════
# CLEAN STATE
# ══════════════════════════════════════════════════════════════


class TestAnomalyClean:
    def test_no_anomaly_on_first_command(self):
        det = AnomalyDetector()
        result = det.check("actor-1", BIZ, BRANCH_1, "CASH:OPEN_SESSION", T0)
        assert result.detected is False

    def test_clean_factory(self):
        r = AnomalyResult.clean()
        assert r.detected is False
        assert r.anomaly_type == ""


# ══════════════════════════════════════════════════════════════
# HIGH VELOCITY
# ══════════════════════════════════════════════════════════════


class TestHighVelocity:
    def test_triggers_at_threshold(self):
        det = AnomalyDetector(high_velocity_threshold=10)
        # Record 10 activities
        for i in range(10):
            det.record_activity(_record(offset_seconds=i))

        result = det.check("actor-1", BIZ, BRANCH_1, "CASH:OPEN_SESSION", T0 + timedelta(seconds=10))
        assert result.detected is True
        assert result.anomaly_type == "HIGH_VELOCITY"
        assert result.severity == AnomalySeverity.WARN

    def test_does_not_trigger_below_threshold(self):
        det = AnomalyDetector(high_velocity_threshold=10)
        for i in range(5):
            det.record_activity(_record(offset_seconds=i))

        result = det.check("actor-1", BIZ, BRANCH_1, "CASH:OPEN_SESSION", T0 + timedelta(seconds=5))
        assert result.detected is False

    def test_old_records_evicted(self):
        det = AnomalyDetector(high_velocity_threshold=5)
        # Record 5 activities at T0
        for i in range(5):
            det.record_activity(_record(offset_seconds=i))

        # Would trigger at T0+10, but check at T0+120 (all evicted)
        result = det.check("actor-1", BIZ, BRANCH_1, "X", T0 + timedelta(seconds=120))
        assert result.detected is False


# ══════════════════════════════════════════════════════════════
# RAPID BRANCH SWITCHING
# ══════════════════════════════════════════════════════════════


class TestRapidBranchSwitch:
    def test_triggers_on_many_branches(self):
        det = AnomalyDetector(rapid_branch_switch_threshold=3, rapid_branch_window_seconds=30)
        # Activity on 3 different branches in 30 seconds
        det.record_activity(_record(branch_id=BRANCH_1, offset_seconds=0))
        det.record_activity(_record(branch_id=BRANCH_2, offset_seconds=5))
        det.record_activity(_record(branch_id=BRANCH_3, offset_seconds=10))

        # Now try a 4th branch — triggers
        result = det.check("actor-1", BIZ, BRANCH_4, "X", T0 + timedelta(seconds=15))
        assert result.detected is True
        assert result.anomaly_type == "RAPID_BRANCH_SWITCH"
        assert result.severity == AnomalySeverity.BLOCK

    def test_does_not_trigger_under_threshold(self):
        det = AnomalyDetector(rapid_branch_switch_threshold=3)
        det.record_activity(_record(branch_id=BRANCH_1, offset_seconds=0))
        det.record_activity(_record(branch_id=BRANCH_2, offset_seconds=5))

        result = det.check("actor-1", BIZ, BRANCH_3, "X", T0 + timedelta(seconds=10))
        assert result.detected is False

    def test_no_branch_id_skips_check(self):
        det = AnomalyDetector(rapid_branch_switch_threshold=1)
        det.record_activity(_record(branch_id=BRANCH_1, offset_seconds=0))
        det.record_activity(_record(branch_id=BRANCH_2, offset_seconds=1))

        result = det.check("actor-1", BIZ, None, "X", T0 + timedelta(seconds=2))
        # branch_id=None → branch switch check skipped
        assert result.anomaly_type != "RAPID_BRANCH_SWITCH"


# ══════════════════════════════════════════════════════════════
# REPEATED REJECTIONS
# ══════════════════════════════════════════════════════════════


class TestRepeatedRejections:
    def test_triggers_on_rejection_threshold(self):
        det = AnomalyDetector(repeated_rejection_threshold=3)
        for i in range(3):
            det.record_activity(_record(
                command_type="CASH:OPEN_SESSION",
                offset_seconds=i,
                was_rejected=True,
            ))

        result = det.check("actor-1", BIZ, BRANCH_1, "CASH:OPEN_SESSION", T0 + timedelta(seconds=3))
        assert result.detected is True
        assert result.anomaly_type == "REPEATED_REJECTIONS"
        assert result.severity == AnomalySeverity.WARN

    def test_does_not_trigger_for_different_command_type(self):
        det = AnomalyDetector(repeated_rejection_threshold=3)
        for i in range(3):
            det.record_activity(_record(
                command_type="CASH:OPEN_SESSION",
                offset_seconds=i,
                was_rejected=True,
            ))

        # Different command type — should not trigger
        result = det.check("actor-1", BIZ, BRANCH_1, "CASH:CLOSE_SESSION", T0 + timedelta(seconds=3))
        assert result.anomaly_type != "REPEATED_REJECTIONS"

    def test_does_not_trigger_for_allowed_commands(self):
        det = AnomalyDetector(repeated_rejection_threshold=3)
        for i in range(5):
            det.record_activity(_record(
                command_type="CASH:OPEN_SESSION",
                offset_seconds=i,
                was_rejected=False,  # not rejected
            ))

        result = det.check("actor-1", BIZ, BRANCH_1, "CASH:OPEN_SESSION", T0 + timedelta(seconds=5))
        assert result.anomaly_type != "REPEATED_REJECTIONS"


# ══════════════════════════════════════════════════════════════
# SEVERITY ORDERING
# ══════════════════════════════════════════════════════════════


class TestSeverityOrdering:
    def test_block_beats_warn(self):
        det = AnomalyDetector(
            high_velocity_threshold=3,       # WARN
            rapid_branch_switch_threshold=2,  # BLOCK
        )
        # Trigger both
        det.record_activity(_record(branch_id=BRANCH_1, offset_seconds=0))
        det.record_activity(_record(branch_id=BRANCH_2, offset_seconds=1))
        det.record_activity(_record(branch_id=BRANCH_3, offset_seconds=2))

        result = det.check("actor-1", BIZ, BRANCH_4, "X", T0 + timedelta(seconds=3))
        assert result.detected is True
        assert result.severity == AnomalySeverity.BLOCK
        assert result.anomaly_type == "RAPID_BRANCH_SWITCH"
