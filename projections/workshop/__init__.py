"""
BOS Projections — Workshop Read Model
=========================================
Cross-engine read model for job tracking,
material consumption, and waste analysis.

Built from events:
- workshop.job.created.v1
- workshop.job.completed.v1
- workshop.material.consumed.v1
- workshop.offcut.recorded.v1
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class JobSummary:
    job_id: str
    status: str  # CREATED | COMPLETED
    material_cost: Decimal = Decimal(0)
    offcut_count: int = 0


class WorkshopReadModel:
    """
    Aggregated workshop read model for dashboards.

    Implements ProjectionProtocol for rebuild support.
    """

    projection_name = "workshop_read_model"

    def __init__(self) -> None:
        self._jobs: Dict[str, JobSummary] = {}
        self._by_business: Dict[uuid.UUID, List[str]] = defaultdict(list)
        self._material_consumed: Dict[uuid.UUID, Decimal] = defaultdict(Decimal)
        self._offcut_total: Dict[uuid.UUID, int] = defaultdict(int)

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        biz_id = payload.get("business_id")
        if isinstance(biz_id, str):
            biz_id = uuid.UUID(biz_id)
        if biz_id is None:
            return

        if event_type == "workshop.job.created.v1":
            job_id = payload.get("job_id", "")
            self._jobs[job_id] = JobSummary(job_id=job_id, status="CREATED")
            self._by_business[biz_id].append(job_id)

        elif event_type == "workshop.job.completed.v1":
            job_id = payload.get("job_id", "")
            if job_id in self._jobs:
                self._jobs[job_id].status = "COMPLETED"

        elif event_type == "workshop.material.consumed.v1":
            cost = Decimal(str(payload.get("cost", 0)))
            job_id = payload.get("job_id", "")
            self._material_consumed[biz_id] += cost
            if job_id in self._jobs:
                self._jobs[job_id].material_cost += cost

        elif event_type == "workshop.offcut.recorded.v1":
            job_id = payload.get("job_id", "")
            self._offcut_total[biz_id] += 1
            if job_id in self._jobs:
                self._jobs[job_id].offcut_count += 1

    def get_job_count(self, business_id: uuid.UUID) -> int:
        return len(self._by_business.get(business_id, []))

    def get_material_consumed(self, business_id: uuid.UUID) -> Decimal:
        return self._material_consumed.get(business_id, Decimal(0))

    def get_offcut_count(self, business_id: uuid.UUID) -> int:
        return self._offcut_total.get(business_id, 0)

    def truncate(self, business_id: Optional[uuid.UUID] = None) -> None:
        if business_id:
            job_ids = self._by_business.pop(business_id, [])
            for jid in job_ids:
                self._jobs.pop(jid, None)
            self._material_consumed.pop(business_id, None)
            self._offcut_total.pop(business_id, None)
        else:
            self._jobs.clear()
            self._by_business.clear()
            self._material_consumed.clear()
            self._offcut_total.clear()

    def snapshot(self, business_id: uuid.UUID) -> Dict[str, Any]:
        return {
            "job_count": self.get_job_count(business_id),
            "material_consumed": str(self.get_material_consumed(business_id)),
            "offcut_count": self.get_offcut_count(business_id),
        }
