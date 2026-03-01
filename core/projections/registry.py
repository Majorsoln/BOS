"""
BOS Core Projections — Projection Registry
==============================================
Central catalog of all projections in the system.

Tracks: name, event types consumed, schema version,
health status, last rebuild timestamp.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, FrozenSet, List, Optional


# ══════════════════════════════════════════════════════════════
# PROJECTION INFO
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ProjectionInfo:
    """Metadata about a registered projection."""

    projection_name: str
    event_types: FrozenSet[str]
    schema_version: int = 1
    description: str = ""

    # Mutable health tracking stored separately in registry


@dataclass
class ProjectionHealth:
    """Mutable health status for a projection."""

    last_rebuild_at: Optional[datetime] = None
    events_processed: int = 0
    last_event_at: Optional[datetime] = None
    is_healthy: bool = True
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_rebuild_at": self.last_rebuild_at.isoformat() if self.last_rebuild_at else None,
            "events_processed": self.events_processed,
            "last_event_at": self.last_event_at.isoformat() if self.last_event_at else None,
            "is_healthy": self.is_healthy,
            "error_message": self.error_message,
        }


# ══════════════════════════════════════════════════════════════
# PROJECTION REGISTRY
# ══════════════════════════════════════════════════════════════

class ProjectionRegistry:
    """
    Central catalog of all projections in the system.

    Used for:
    - Discovering which projections handle which event types
    - Monitoring projection health
    - Triggering selective rebuilds by domain
    - Schema version tracking for migrations
    """

    def __init__(self) -> None:
        self._projections: Dict[str, ProjectionInfo] = {}
        self._health: Dict[str, ProjectionHealth] = {}
        self._event_index: Dict[str, List[str]] = {}  # event_type → [projection_names]

    def register(self, info: ProjectionInfo) -> None:
        """Register a projection with its metadata."""
        self._projections[info.projection_name] = info
        self._health.setdefault(info.projection_name, ProjectionHealth())

        for event_type in info.event_types:
            self._event_index.setdefault(event_type, [])
            if info.projection_name not in self._event_index[event_type]:
                self._event_index[event_type].append(info.projection_name)

    def get(self, projection_name: str) -> Optional[ProjectionInfo]:
        return self._projections.get(projection_name)

    def get_health(self, projection_name: str) -> Optional[ProjectionHealth]:
        return self._health.get(projection_name)

    def get_projections_for_event(self, event_type: str) -> List[ProjectionInfo]:
        """Find all projections that consume a given event type."""
        names = self._event_index.get(event_type, [])
        return [self._projections[n] for n in names if n in self._projections]

    def list_all(self) -> List[ProjectionInfo]:
        return list(self._projections.values())

    def list_unhealthy(self) -> List[str]:
        return [
            name for name, health in self._health.items()
            if not health.is_healthy
        ]

    def record_event_processed(
        self, projection_name: str, event_at: datetime
    ) -> None:
        """Record that a projection processed an event."""
        health = self._health.get(projection_name)
        if health:
            health.events_processed += 1
            health.last_event_at = event_at

    def record_rebuild(
        self, projection_name: str, rebuilt_at: datetime
    ) -> None:
        health = self._health.get(projection_name)
        if health:
            health.last_rebuild_at = rebuilt_at
            health.is_healthy = True
            health.error_message = ""

    def record_error(
        self, projection_name: str, error_message: str
    ) -> None:
        health = self._health.get(projection_name)
        if health:
            health.is_healthy = False
            health.error_message = error_message

    def summary(self) -> Dict[str, Any]:
        """Return a summary of all projections and their health."""
        return {
            name: {
                "event_types": list(info.event_types),
                "schema_version": info.schema_version,
                "health": self._health[name].to_dict() if name in self._health else None,
            }
            for name, info in self._projections.items()
        }
