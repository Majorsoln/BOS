"""
BOS Data Migration — Service
==============================
Orchestrates bulk data imports from external ERPs into BOS.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from core.migration.importers import (
    ENTITY_IMPORTERS,
    IdMappingStore,
    import_customer,
    import_opening_balance,
    import_product,
    import_supplier,
)
from core.migration.models import (
    EntityType,
    IdMapping,
    JobStatus,
    MigrationBatchRequest,
    MigrationBatchResult,
    MigrationJob,
    RowStatus,
    VALID_ENTITY_TYPES,
    VALID_SOURCE_SYSTEMS,
)

logger = logging.getLogger("bos.migration.service")


# ══════════════════════════════════════════════════════════════
# IN-MEMORY ID MAPPING STORE (default — replace with DB in prod)
# ══════════════════════════════════════════════════════════════

class InMemoryIdMappingStore:
    """
    In-memory implementation of IdMappingStore.
    Replace with Django ORM-backed store for production persistence.
    """

    def __init__(self) -> None:
        self._store: Dict[str, IdMapping] = {}

    @staticmethod
    def _key(business_id: uuid.UUID, source_system: str,
             entity_type: str, external_id: str) -> str:
        return f"{business_id}:{source_system}:{entity_type}:{external_id}"

    def get(self, business_id: uuid.UUID, source_system: str,
            entity_type: str, external_id: str) -> Optional[IdMapping]:
        return self._store.get(self._key(business_id, source_system, entity_type, external_id))

    def put(self, mapping: IdMapping) -> None:
        key = self._key(mapping.business_id, mapping.source_system,
                        mapping.entity_type, mapping.external_id)
        self._store[key] = mapping

    def list_mappings(self, business_id: uuid.UUID, source_system: str,
                      entity_type: str) -> List[IdMapping]:
        prefix = f"{business_id}:{source_system}:{entity_type}:"
        return [m for k, m in self._store.items() if k.startswith(prefix)]


# ══════════════════════════════════════════════════════════════
# MIGRATION SERVICE
# ══════════════════════════════════════════════════════════════

class MigrationService:
    """
    Orchestrates data migration from external ERPs to BOS.

    Usage:
        svc = MigrationService(
            id_store=InMemoryIdMappingStore(),
            entity_create_fns={
                "CUSTOMER": identity_store.create_customer_profile,
                "PRODUCT":  inventory_service.create_item,
                "SUPPLIER": procurement_service.create_supplier,
                "OPENING_BALANCE": accounting_service.post_opening_balance,
            },
        )
        job = svc.create_job(business_id=..., source_system="quickbooks",
                             entity_type="CUSTOMER", actor_id="admin-001")
        result = svc.import_batch(batch_request)
    """

    def __init__(
        self,
        id_store: Optional[IdMappingStore] = None,
        entity_create_fns: Optional[Dict[str, Callable]] = None,
    ) -> None:
        self._id_store = id_store or InMemoryIdMappingStore()
        self._create_fns: Dict[str, Callable] = entity_create_fns or {}
        self._jobs: Dict[uuid.UUID, MigrationJob] = {}

    # ── Job Management ──────────────────────────────────────────

    def create_job(
        self,
        *,
        business_id: uuid.UUID,
        source_system: str,
        entity_type: str,
        actor_id: str = "",
    ) -> MigrationJob:
        """Create a new migration job."""
        if entity_type not in VALID_ENTITY_TYPES:
            raise ValueError(f"Invalid entity_type: {entity_type}")
        if source_system not in VALID_SOURCE_SYSTEMS:
            raise ValueError(
                f"Unknown source_system: {source_system}. "
                f"Valid: {sorted(VALID_SOURCE_SYSTEMS)}"
            )

        job = MigrationJob(
            job_id=uuid.uuid4(),
            business_id=business_id,
            source_system=source_system,
            entity_type=entity_type,
            created_by=actor_id,
        )
        self._jobs[job.job_id] = job
        logger.info(
            "Migration job created: %s entity=%s source=%s business=%s",
            job.job_id, entity_type, source_system, business_id,
        )
        return job

    def get_job(self, job_id: uuid.UUID) -> Optional[MigrationJob]:
        return self._jobs.get(job_id)

    def list_jobs(self, business_id: uuid.UUID) -> List[MigrationJob]:
        return [j for j in self._jobs.values() if j.business_id == business_id]

    def cancel_job(self, job_id: uuid.UUID) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        if job.status in (JobStatus.COMPLETED.value, JobStatus.CANCELLED.value):
            return False
        job.status = JobStatus.CANCELLED.value
        job.completed_at = datetime.now(tz=timezone.utc)
        return True

    # ── Batch Import ────────────────────────────────────────────

    def import_batch(self, request: MigrationBatchRequest) -> MigrationBatchResult:
        """
        Import a batch of rows for a given job.
        Each row is validated, dedup-checked, and imported individually.
        Errors on one row do NOT stop the batch.
        """
        job = self._jobs.get(request.job_id)
        if not job:
            raise ValueError(f"Job {request.job_id} not found")
        if job.status == JobStatus.CANCELLED.value:
            raise ValueError(f"Job {request.job_id} is cancelled")
        if job.business_id != request.business_id:
            raise ValueError("business_id mismatch with job")

        job.mark_in_progress()

        create_fn = self._create_fns.get(request.entity_type)
        if create_fn is None:
            job.mark_failed(f"No create function registered for {request.entity_type}")
            raise ValueError(f"No create function registered for entity type: {request.entity_type}")

        importer = ENTITY_IMPORTERS.get(request.entity_type)
        if importer is None:
            job.mark_failed(f"No importer for {request.entity_type}")
            raise ValueError(f"No importer for entity type: {request.entity_type}")

        results = []
        for i, row in enumerate(request.rows):
            # Determine the right kwarg name for the create function
            fn_kwarg = "post_fn" if request.entity_type == EntityType.OPENING_BALANCE.value else "create_fn"

            result = importer(
                business_id=request.business_id,
                source_system=job.source_system,
                row=row if isinstance(row, dict) else dict(row),
                row_index=i,
                id_store=self._id_store,
                **{fn_kwarg: create_fn},
            )
            results.append(result)
            job.record_row(RowStatus(result.status))

        # Check if job is fully done (no more batches expected)
        # Caller should call complete_job() when all batches uploaded
        imported = sum(1 for r in results if r.status == RowStatus.SUCCESS.value)
        skipped = sum(1 for r in results if r.status == RowStatus.SKIPPED.value)
        errors = sum(1 for r in results if r.status == RowStatus.ERROR.value)

        logger.info(
            "Migration batch processed: job=%s imported=%d skipped=%d errors=%d",
            request.job_id, imported, skipped, errors,
        )

        return MigrationBatchResult(
            job_id=request.job_id,
            total=len(results),
            imported=imported,
            skipped=skipped,
            errors=errors,
            row_results=tuple(results),
        )

    def complete_job(self, job_id: uuid.UUID) -> bool:
        """Mark a job as completed after all batches are uploaded."""
        job = self._jobs.get(job_id)
        if not job:
            return False
        if job.status != JobStatus.IN_PROGRESS.value:
            return False
        job.mark_completed()
        logger.info(
            "Migration job completed: %s total=%d imported=%d skipped=%d errors=%d",
            job_id, job.total_rows, job.imported_rows, job.skipped_rows, job.error_rows,
        )
        return True

    # ── ID Mapping Lookup ───────────────────────────────────────

    def lookup_bos_id(
        self,
        business_id: uuid.UUID,
        source_system: str,
        entity_type: str,
        external_id: str,
    ) -> Optional[str]:
        """Look up the BOS UUID for an external entity ID."""
        mapping = self._id_store.get(business_id, source_system, entity_type, external_id)
        if mapping:
            return str(mapping.bos_id)
        return None

    def list_mappings(
        self,
        business_id: uuid.UUID,
        source_system: str,
        entity_type: str,
    ) -> List[IdMapping]:
        """List all ID mappings for a given entity type."""
        if hasattr(self._id_store, "list_mappings"):
            return self._id_store.list_mappings(business_id, source_system, entity_type)
        return []
