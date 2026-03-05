"""
BOS Platform — Observability Plane
====================================
SLO metric tracking for platform health.

Metrics are immutable observations (events). The projection
holds the latest rolling state per metric per tenant/region.

SLOs Tracked:
  persist_event.success_rate   — write SLO  ≥ 99.9 %
  hash_chain.integrity_violations — integrity SLO = 0
  command_latency.p95_ms       — latency SLO  ≤ 200 ms
  command_latency.p99_ms       — latency SLO  ≤ 500 ms
  api.error_rate_5xx           — availability SLO ≤ 0.1 %
  replay.duration_seconds      — replay SLO  ≤ 30 s
  db.events_per_day            — capacity signal (no hard SLO)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ══════════════════════════════════════════════════════════════
# OBSERVABILITY EVENT TYPES
# ══════════════════════════════════════════════════════════════

PLATFORM_METRIC_RECORDED_V1  = "platform.metric.recorded.v1"
PLATFORM_SLO_BREACHED_V1     = "platform.slo.breached.v1"
PLATFORM_SLO_RECOVERED_V1    = "platform.slo.recovered.v1"
PLATFORM_HEALTH_SNAPSHOT_V1  = "platform.health.snapshot.v1"

OBSERVABILITY_EVENT_TYPES = (
    PLATFORM_METRIC_RECORDED_V1,
    PLATFORM_SLO_BREACHED_V1,
    PLATFORM_SLO_RECOVERED_V1,
    PLATFORM_HEALTH_SNAPSHOT_V1,
)


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class MetricKind(Enum):
    COUNTER   = "COUNTER"    # cumulative count
    GAUGE     = "GAUGE"      # point-in-time value
    HISTOGRAM = "HISTOGRAM"  # latency distribution (p50/p95/p99)
    RATE      = "RATE"       # events per second / minute


class SLOStatus(Enum):
    OK      = "OK"
    WARNING = "WARNING"
    BREACHED = "BREACHED"
    UNKNOWN  = "UNKNOWN"


# ══════════════════════════════════════════════════════════════
# SLO DEFINITIONS  (platform defaults — immutable)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SLODefinition:
    slo_id: str
    name: str
    metric_name: str
    threshold: float
    comparison: str             # "gte" | "lte" | "eq"
    warning_threshold: Optional[float] = None
    unit: str = ""


PLATFORM_SLOS: Dict[str, SLODefinition] = {
    "persist_event.success_rate": SLODefinition(
        slo_id="persist_event.success_rate",
        name="Event Persistence Success Rate",
        metric_name="persist_event.success_rate",
        threshold=99.9,
        comparison="gte",
        warning_threshold=99.5,
        unit="%",
    ),
    "hash_chain.integrity_violations": SLODefinition(
        slo_id="hash_chain.integrity_violations",
        name="Hash Chain Integrity Violations",
        metric_name="hash_chain.integrity_violations",
        threshold=0.0,
        comparison="lte",
        unit="violations",
    ),
    "command_latency.p95_ms": SLODefinition(
        slo_id="command_latency.p95_ms",
        name="Command Latency p95",
        metric_name="command_latency.p95_ms",
        threshold=200.0,
        comparison="lte",
        warning_threshold=150.0,
        unit="ms",
    ),
    "command_latency.p99_ms": SLODefinition(
        slo_id="command_latency.p99_ms",
        name="Command Latency p99",
        metric_name="command_latency.p99_ms",
        threshold=500.0,
        comparison="lte",
        warning_threshold=350.0,
        unit="ms",
    ),
    "api.error_rate_5xx": SLODefinition(
        slo_id="api.error_rate_5xx",
        name="API 5xx Error Rate",
        metric_name="api.error_rate_5xx",
        threshold=0.1,
        comparison="lte",
        warning_threshold=0.05,
        unit="%",
    ),
    "replay.duration_seconds": SLODefinition(
        slo_id="replay.duration_seconds",
        name="Tenant Event Replay Duration",
        metric_name="replay.duration_seconds",
        threshold=30.0,
        comparison="lte",
        unit="s",
    ),
}


# ══════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MetricSample:
    metric_name: str
    value: float
    kind: MetricKind
    recorded_at: datetime
    tenant_id: Optional[str] = None
    region_code: Optional[str] = None
    labels: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class SLOBreach:
    breach_id: uuid.UUID
    slo_id: str
    metric_name: str
    observed_value: float
    threshold: float
    region_code: Optional[str]
    tenant_id: Optional[str]
    breached_at: datetime
    recovered_at: Optional[datetime] = None


@dataclass(frozen=True)
class PlatformHealthSnapshot:
    snapshot_id: uuid.UUID
    taken_at: datetime
    overall_status: SLOStatus
    slo_statuses: Dict[str, str]    # slo_id → SLOStatus.value
    active_breaches: int
    metrics_summary: Dict[str, float]


# ══════════════════════════════════════════════════════════════
# PROJECTION
# ══════════════════════════════════════════════════════════════

class ObservabilityProjection:
    """
    Tracks current platform metric state and SLO breach status.
    Rebuilt deterministically from observability events.
    """

    projection_name = "observability_projection"

    def __init__(self) -> None:
        # "{tenant_id|_}:{metric_name}" → latest MetricSample
        self._metrics: Dict[str, MetricSample] = {}
        # breach_id → SLOBreach (full history)
        self._breaches: Dict[uuid.UUID, SLOBreach] = {}
        # slo_id → SLOBreach (currently active only)
        self._active_breaches: Dict[str, SLOBreach] = {}
        self._snapshots: List[PlatformHealthSnapshot] = []

    # ── apply ──────────────────────────────────────────────────

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == PLATFORM_METRIC_RECORDED_V1:
            self._apply_metric(payload)
        elif event_type == PLATFORM_SLO_BREACHED_V1:
            self._apply_breach(payload)
        elif event_type == PLATFORM_SLO_RECOVERED_V1:
            self._apply_recovery(payload)
        elif event_type == PLATFORM_HEALTH_SNAPSHOT_V1:
            self._apply_snapshot(payload)

    def _apply_metric(self, payload: Dict[str, Any]) -> None:
        name = payload["metric_name"]
        kind = MetricKind(payload.get("kind", "GAUGE"))
        sample = MetricSample(
            metric_name=name,
            value=float(payload["value"]),
            kind=kind,
            recorded_at=payload.get("recorded_at", datetime.utcnow()),
            tenant_id=payload.get("tenant_id"),
            region_code=payload.get("region_code"),
            labels=payload.get("labels"),
        )
        key = f"{payload.get('tenant_id') or '_'}:{name}"
        self._metrics[key] = sample

    def _apply_breach(self, payload: Dict[str, Any]) -> None:
        breach_id = uuid.UUID(str(payload["breach_id"]))
        breach = SLOBreach(
            breach_id=breach_id,
            slo_id=payload["slo_id"],
            metric_name=payload["metric_name"],
            observed_value=float(payload["observed_value"]),
            threshold=float(payload["threshold"]),
            region_code=payload.get("region_code"),
            tenant_id=payload.get("tenant_id"),
            breached_at=payload.get("breached_at", datetime.utcnow()),
        )
        self._breaches[breach_id] = breach
        self._active_breaches[payload["slo_id"]] = breach

    def _apply_recovery(self, payload: Dict[str, Any]) -> None:
        slo_id = payload["slo_id"]
        breach = self._active_breaches.pop(slo_id, None)
        if breach is not None:
            recovered = SLOBreach(
                breach_id=breach.breach_id,
                slo_id=breach.slo_id,
                metric_name=breach.metric_name,
                observed_value=breach.observed_value,
                threshold=breach.threshold,
                region_code=breach.region_code,
                tenant_id=breach.tenant_id,
                breached_at=breach.breached_at,
                recovered_at=payload.get("recovered_at", datetime.utcnow()),
            )
            self._breaches[recovered.breach_id] = recovered

    def _apply_snapshot(self, payload: Dict[str, Any]) -> None:
        snap_id = uuid.UUID(str(payload["snapshot_id"]))
        slo_statuses = payload.get("slo_statuses", {})
        overall = SLOStatus(payload.get("overall_status", "UNKNOWN"))
        snapshot = PlatformHealthSnapshot(
            snapshot_id=snap_id,
            taken_at=payload.get("taken_at", datetime.utcnow()),
            overall_status=overall,
            slo_statuses=slo_statuses,
            active_breaches=payload.get("active_breaches", 0),
            metrics_summary=payload.get("metrics_summary", {}),
        )
        self._snapshots.append(snapshot)
        # keep only last 100 snapshots in memory
        if len(self._snapshots) > 100:
            self._snapshots = self._snapshots[-100:]

    # ── queries ────────────────────────────────────────────────

    def get_latest_metric(
        self, metric_name: str, tenant_id: Optional[str] = None
    ) -> Optional[MetricSample]:
        key = f"{tenant_id or '_'}:{metric_name}"
        return self._metrics.get(key)

    def get_active_breaches(self) -> List[SLOBreach]:
        return list(self._active_breaches.values())

    def get_breach_history(self) -> List[SLOBreach]:
        return list(self._breaches.values())

    def get_latest_snapshot(self) -> Optional[PlatformHealthSnapshot]:
        return self._snapshots[-1] if self._snapshots else None

    def evaluate_slo_status(self, slo_id: str) -> SLOStatus:
        """Evaluate current SLO status from the latest recorded metric."""
        slo_def = PLATFORM_SLOS.get(slo_id)
        if slo_def is None:
            return SLOStatus.UNKNOWN
        sample = self.get_latest_metric(slo_def.metric_name)
        if sample is None:
            return SLOStatus.UNKNOWN

        def _passes(value: float, threshold: float, comparison: str) -> bool:
            if comparison == "gte":
                return value >= threshold
            if comparison == "lte":
                return value <= threshold
            return value == threshold

        v = sample.value
        # Evaluation semantics per comparison type:
        #  "gte" (higher is better — e.g., success rate):
        #    OK      = value ≥ threshold
        #    WARNING = warning_threshold ≤ value < threshold
        #    BREACHED = value < warning_threshold (or threshold if no warning)
        #  "lte" (lower is better — e.g., latency):
        #    OK      = value ≤ warning_threshold (within safe zone)
        #    WARNING = warning_threshold < value ≤ threshold
        #    BREACHED = value > threshold
        #  "eq": OK = exact match, BREACHED otherwise
        if slo_def.comparison == "gte":
            if v >= slo_def.threshold:
                return SLOStatus.OK
            if slo_def.warning_threshold is not None and v >= slo_def.warning_threshold:
                return SLOStatus.WARNING
            return SLOStatus.BREACHED
        if slo_def.comparison == "lte":
            if slo_def.warning_threshold is not None:
                if v <= slo_def.warning_threshold:
                    return SLOStatus.OK
                if v <= slo_def.threshold:
                    return SLOStatus.WARNING
                return SLOStatus.BREACHED
            return SLOStatus.OK if v <= slo_def.threshold else SLOStatus.BREACHED
        # "eq"
        return SLOStatus.OK if v == slo_def.threshold else SLOStatus.BREACHED

    def truncate(self) -> None:
        self._metrics.clear()
        self._breaches.clear()
        self._active_breaches.clear()
        self._snapshots.clear()


# ══════════════════════════════════════════════════════════════
# SERVICE
# ══════════════════════════════════════════════════════════════

class ObservabilityService:
    """
    Records platform metrics and auto-evaluates SLO health.
    All mutations produce events (additive-only).
    """

    def __init__(self, projection: ObservabilityProjection) -> None:
        self._projection = projection

    def record_metric(
        self,
        metric_name: str,
        value: float,
        kind: str = "GAUGE",
        tenant_id: Optional[str] = None,
        region_code: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        recorded_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Record one metric observation. Auto-raises SLO breach/recovery events."""
        ts = recorded_at or datetime.utcnow()
        payload: Dict[str, Any] = {
            "metric_name": metric_name,
            "value": value,
            "kind": kind,
            "recorded_at": ts,
        }
        if tenant_id:
            payload["tenant_id"] = tenant_id
        if region_code:
            payload["region_code"] = region_code
        if labels:
            payload["labels"] = labels

        self._projection.apply(PLATFORM_METRIC_RECORDED_V1, payload)
        events = [{"event_type": PLATFORM_METRIC_RECORDED_V1, "payload": payload}]

        # Auto-evaluate every SLO that watches this metric
        active_slo_ids = {b.slo_id for b in self._projection.get_active_breaches()}
        for slo_id, slo_def in PLATFORM_SLOS.items():
            if slo_def.metric_name != metric_name:
                continue
            status = self._projection.evaluate_slo_status(slo_id)
            is_active = slo_id in active_slo_ids

            if status == SLOStatus.BREACHED and not is_active:
                breach_payload: Dict[str, Any] = {
                    "breach_id": str(uuid.uuid4()),
                    "slo_id": slo_id,
                    "metric_name": metric_name,
                    "observed_value": value,
                    "threshold": slo_def.threshold,
                    "breached_at": ts,
                }
                if region_code:
                    breach_payload["region_code"] = region_code
                if tenant_id:
                    breach_payload["tenant_id"] = tenant_id
                self._projection.apply(PLATFORM_SLO_BREACHED_V1, breach_payload)
                events.append({
                    "event_type": PLATFORM_SLO_BREACHED_V1,
                    "payload": breach_payload,
                })

            elif status == SLOStatus.OK and is_active:
                recover_payload: Dict[str, Any] = {
                    "slo_id": slo_id,
                    "metric_name": metric_name,
                    "recovered_at": ts,
                }
                if region_code:
                    recover_payload["region_code"] = region_code
                if tenant_id:
                    recover_payload["tenant_id"] = tenant_id
                self._projection.apply(PLATFORM_SLO_RECOVERED_V1, recover_payload)
                events.append({
                    "event_type": PLATFORM_SLO_RECOVERED_V1,
                    "payload": recover_payload,
                })

        return {"events": events}

    def take_health_snapshot(
        self, taken_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Produce a health snapshot event summarising all SLO statuses."""
        ts = taken_at or datetime.utcnow()
        slo_statuses = {
            slo_id: self._projection.evaluate_slo_status(slo_id).value
            for slo_id in PLATFORM_SLOS
        }
        active_breach_count = len(self._projection.get_active_breaches())

        statuses_set = set(slo_statuses.values())
        if SLOStatus.BREACHED.value in statuses_set:
            overall = SLOStatus.BREACHED
        elif SLOStatus.WARNING.value in statuses_set:
            overall = SLOStatus.WARNING
        elif statuses_set == {SLOStatus.UNKNOWN.value}:
            overall = SLOStatus.UNKNOWN
        else:
            overall = SLOStatus.OK

        metrics_summary: Dict[str, float] = {}
        for slo_def in PLATFORM_SLOS.values():
            sample = self._projection.get_latest_metric(slo_def.metric_name)
            if sample is not None:
                metrics_summary[slo_def.metric_name] = sample.value

        payload: Dict[str, Any] = {
            "snapshot_id": str(uuid.uuid4()),
            "taken_at": ts,
            "overall_status": overall.value,
            "slo_statuses": slo_statuses,
            "active_breaches": active_breach_count,
            "metrics_summary": metrics_summary,
        }
        self._projection.apply(PLATFORM_HEALTH_SNAPSHOT_V1, payload)
        return {
            "snapshot_id": uuid.UUID(payload["snapshot_id"]),
            "overall_status": overall.value,
            "active_breaches": active_breach_count,
            "slo_statuses": slo_statuses,
            "events": [{"event_type": PLATFORM_HEALTH_SNAPSHOT_V1, "payload": payload}],
        }

    def get_health_summary(self) -> Dict[str, Any]:
        """Return current platform health without producing an event."""
        slo_statuses = {
            slo_id: self._projection.evaluate_slo_status(slo_id).value
            for slo_id in PLATFORM_SLOS
        }
        latest = self._projection.get_latest_snapshot()
        return {
            "slo_statuses": slo_statuses,
            "active_breaches": [
                {
                    "slo_id": b.slo_id,
                    "observed_value": b.observed_value,
                    "threshold": b.threshold,
                    "breached_at": b.breached_at,
                }
                for b in self._projection.get_active_breaches()
            ],
            "latest_snapshot": (
                {
                    "taken_at": latest.taken_at,
                    "overall_status": latest.overall_status.value,
                }
                if latest else None
            ),
        }
