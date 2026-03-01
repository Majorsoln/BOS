"""
BOS Core Projections — Registry, Snapshots & Metrics
========================================================
Central infrastructure for managing projections at scale.

Doctrine: Projections are disposable, derived from events,
and rebuilt deterministically. This module makes that scalable.
"""

from core.projections.registry import ProjectionInfo, ProjectionRegistry
from core.projections.snapshots import SnapshotEntry, SnapshotStore
from core.projections.metrics import ProjectionMetrics, MetricsCollector

__all__ = [
    "ProjectionInfo",
    "ProjectionRegistry",
    "SnapshotEntry",
    "SnapshotStore",
    "ProjectionMetrics",
    "MetricsCollector",
]
