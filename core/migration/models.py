"""
BOS Data Migration — Models & Value Objects
============================================
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class EntityType(str, Enum):
    CUSTOMER = "CUSTOMER"
    PRODUCT = "PRODUCT"
    SUPPLIER = "SUPPLIER"
    OPENING_BALANCE = "OPENING_BALANCE"
    TRANSACTION = "TRANSACTION"


class JobStatus(str, Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RowStatus(str, Enum):
    SUCCESS = "SUCCESS"
    SKIPPED = "SKIPPED"       # duplicate external_id
    ERROR = "ERROR"           # validation or import failure


VALID_ENTITY_TYPES = frozenset(e.value for e in EntityType)
VALID_SOURCE_SYSTEMS = frozenset({
    "quickbooks", "xero", "sage", "odoo", "erpnext",
    "tally", "wave", "zoho_books", "freshbooks",
    "csv_generic", "json_generic", "excel_generic",
    "custom",
})


# ══════════════════════════════════════════════════════════════
# MIGRATION JOB
# ══════════════════════════════════════════════════════════════

@dataclass
class MigrationJob:
    """
    Tracks a bulk data migration from an external ERP into BOS.
    One job per entity type per source system.
    """
    job_id: uuid.UUID
    business_id: uuid.UUID
    source_system: str             # e.g. "quickbooks", "csv_generic"
    entity_type: str               # EntityType value
    status: str = JobStatus.CREATED.value
    total_rows: int = 0
    imported_rows: int = 0
    skipped_rows: int = 0
    error_rows: int = 0
    created_by: str = ""           # actor_id who initiated
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    completed_at: Optional[datetime] = None
    error_summary: str = ""

    def mark_in_progress(self) -> None:
        self.status = JobStatus.IN_PROGRESS.value

    def mark_completed(self) -> None:
        self.status = JobStatus.COMPLETED.value
        self.completed_at = datetime.now(tz=timezone.utc)

    def mark_failed(self, reason: str) -> None:
        self.status = JobStatus.FAILED.value
        self.error_summary = reason
        self.completed_at = datetime.now(tz=timezone.utc)

    def record_row(self, status: RowStatus) -> None:
        self.total_rows += 1
        if status == RowStatus.SUCCESS:
            self.imported_rows += 1
        elif status == RowStatus.SKIPPED:
            self.skipped_rows += 1
        elif status == RowStatus.ERROR:
            self.error_rows += 1


# ══════════════════════════════════════════════════════════════
# IMPORT ROW RESULT
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ImportRowResult:
    """Result of importing a single row."""
    row_index: int
    external_id: str
    status: str            # RowStatus value
    bos_id: Optional[str] = None   # UUID assigned by BOS
    error_message: str = ""


# ══════════════════════════════════════════════════════════════
# ID MAPPING (external ERP ID → BOS UUID)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class IdMapping:
    """
    Maps an external system's entity ID to the BOS UUID.
    Used for cross-referencing after migration.
    """
    business_id: uuid.UUID
    source_system: str
    entity_type: str
    external_id: str
    bos_id: uuid.UUID
    imported_at: datetime


# ══════════════════════════════════════════════════════════════
# BATCH REQUEST / RESPONSE
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MigrationBatchRequest:
    """A batch of rows to import for a given job."""
    job_id: uuid.UUID
    business_id: uuid.UUID
    entity_type: str
    rows: tuple               # tuple of dicts, each representing one entity
    actor_id: str = ""

    def __post_init__(self):
        if not self.rows:
            raise ValueError("rows must not be empty.")
        if self.entity_type not in VALID_ENTITY_TYPES:
            raise ValueError(f"Invalid entity_type: {self.entity_type}")


@dataclass(frozen=True)
class MigrationBatchResult:
    """Result of processing a batch."""
    job_id: uuid.UUID
    total: int
    imported: int
    skipped: int
    errors: int
    row_results: tuple    # tuple of ImportRowResult
