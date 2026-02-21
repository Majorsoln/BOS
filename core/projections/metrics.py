"""
BOS Core Projections — Performance Metrics
==============================================
Track projection processing speed, cache performance,
and system capacity indicators.

All metrics are in-memory counters — disposable and rebuildable.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


# ══════════════════════════════════════════════════════════════
# PROJECTION METRICS
# ══════════════════════════════════════════════════════════════

@dataclass
class ProjectionMetrics:
    """Performance metrics for a single projection."""

    projection_name: str
    events_per_second: float = 0.0
    last_rebuild_duration_ms: float = 0.0
    total_events_processed: int = 0
    avg_apply_duration_ms: float = 0.0
    peak_apply_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "projection_name": self.projection_name,
            "events_per_second": round(self.events_per_second, 2),
            "last_rebuild_duration_ms": round(self.last_rebuild_duration_ms, 2),
            "total_events_processed": self.total_events_processed,
            "avg_apply_duration_ms": round(self.avg_apply_duration_ms, 4),
            "peak_apply_duration_ms": round(self.peak_apply_duration_ms, 4),
        }


# ══════════════════════════════════════════════════════════════
# METRICS COLLECTOR
# ══════════════════════════════════════════════════════════════

class MetricsCollector:
    """
    Collects performance metrics for all projections.

    Lightweight — designed for monitoring, not auditing.
    All data is disposable (restart resets metrics).
    """

    def __init__(self) -> None:
        self._metrics: Dict[str, ProjectionMetrics] = {}
        self._apply_durations: Dict[str, List[float]] = {}  # projection → recent durations (ms)
        self._max_samples: int = 1000

    def _ensure(self, projection_name: str) -> ProjectionMetrics:
        if projection_name not in self._metrics:
            self._metrics[projection_name] = ProjectionMetrics(
                projection_name=projection_name
            )
            self._apply_durations[projection_name] = []
        return self._metrics[projection_name]

    def record_event_applied(
        self,
        projection_name: str,
        duration_ms: float,
    ) -> None:
        """Record that a projection processed an event."""
        m = self._ensure(projection_name)
        m.total_events_processed += 1

        durations = self._apply_durations[projection_name]
        durations.append(duration_ms)
        if len(durations) > self._max_samples:
            durations.pop(0)

        m.avg_apply_duration_ms = sum(durations) / len(durations)
        m.peak_apply_duration_ms = max(m.peak_apply_duration_ms, duration_ms)

    def record_rebuild(
        self,
        projection_name: str,
        duration_ms: float,
        events_count: int,
    ) -> None:
        """Record a projection rebuild completion."""
        m = self._ensure(projection_name)
        m.last_rebuild_duration_ms = duration_ms
        if duration_ms > 0:
            m.events_per_second = (events_count / duration_ms) * 1000

    def get(self, projection_name: str) -> Optional[ProjectionMetrics]:
        return self._metrics.get(projection_name)

    def summary(self) -> Dict[str, Any]:
        """Return metrics for all projections."""
        return {
            name: m.to_dict()
            for name, m in self._metrics.items()
        }

    def slowest_projections(self, top_n: int = 5) -> List[ProjectionMetrics]:
        """Return the slowest projections by average apply duration."""
        ranked = sorted(
            self._metrics.values(),
            key=lambda m: m.avg_apply_duration_ms,
            reverse=True,
        )
        return ranked[:top_n]
