"""
BOS Core Projections — Snapshot Storage
===========================================
Persist projection state at key timestamps for time-travel queries.

Doctrine: Snapshots are optimization artifacts — always rebuildable
from events. They enable fast point-in-time queries without full replay.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ══════════════════════════════════════════════════════════════
# SNAPSHOT ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SnapshotEntry:
    """
    A point-in-time snapshot of projection state.

    Immutable once created. Append-only storage.
    """

    snapshot_id: uuid.UUID
    projection_name: str
    business_id: uuid.UUID
    snapshot_at: datetime           # The point in time this represents
    created_at: datetime            # When the snapshot was taken
    schema_version: int
    data: Dict[str, Any]            # Serialized projection state
    event_count: int = 0            # Number of events applied up to this point
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": str(self.snapshot_id),
            "projection_name": self.projection_name,
            "business_id": str(self.business_id),
            "snapshot_at": self.snapshot_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "schema_version": self.schema_version,
            "data": self.data,
            "event_count": self.event_count,
        }


# ══════════════════════════════════════════════════════════════
# SNAPSHOT STORE (append-only)
# ══════════════════════════════════════════════════════════════

class SnapshotStore:
    """
    Append-only snapshot storage.

    In-memory implementation for core layer.
    Production would persist to database.

    Supports:
    - Storing snapshots at arbitrary timestamps
    - Querying the closest snapshot before a given time
    - Listing all snapshots for a projection + business
    """

    def __init__(self) -> None:
        self._snapshots: List[SnapshotEntry] = []

    def save(self, snapshot: SnapshotEntry) -> None:
        """Append a snapshot. Never overwrites existing snapshots."""
        self._snapshots.append(snapshot)

    def create_snapshot(
        self,
        *,
        projection_name: str,
        business_id: uuid.UUID,
        snapshot_at: datetime,
        created_at: datetime,
        schema_version: int,
        data: Dict[str, Any],
        event_count: int = 0,
        metadata: Optional[Dict[str, str]] = None,
    ) -> SnapshotEntry:
        """Create and store a new snapshot."""
        entry = SnapshotEntry(
            snapshot_id=uuid.uuid4(),
            projection_name=projection_name,
            business_id=business_id,
            snapshot_at=snapshot_at,
            created_at=created_at,
            schema_version=schema_version,
            data=data,
            event_count=event_count,
            metadata=metadata or {},
        )
        self.save(entry)
        return entry

    def get_latest(
        self,
        projection_name: str,
        business_id: uuid.UUID,
    ) -> Optional[SnapshotEntry]:
        """Get the most recent snapshot for a projection + business."""
        matches = [
            s for s in self._snapshots
            if s.projection_name == projection_name
            and s.business_id == business_id
        ]
        if not matches:
            return None
        return max(matches, key=lambda s: s.snapshot_at)

    def get_at(
        self,
        projection_name: str,
        business_id: uuid.UUID,
        at: datetime,
    ) -> Optional[SnapshotEntry]:
        """
        Get the closest snapshot at or before the given timestamp.

        This enables time-travel queries: "What was the state on June 30?"
        """
        matches = [
            s for s in self._snapshots
            if s.projection_name == projection_name
            and s.business_id == business_id
            and s.snapshot_at <= at
        ]
        if not matches:
            return None
        return max(matches, key=lambda s: s.snapshot_at)

    def list_snapshots(
        self,
        projection_name: str,
        business_id: uuid.UUID,
    ) -> List[SnapshotEntry]:
        """List all snapshots for a projection + business, ordered by time."""
        matches = [
            s for s in self._snapshots
            if s.projection_name == projection_name
            and s.business_id == business_id
        ]
        return sorted(matches, key=lambda s: s.snapshot_at)

    @property
    def count(self) -> int:
        return len(self._snapshots)
