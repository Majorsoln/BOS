"""
BOS Projections — Workshop Style Catalog
=========================================
Read model for the Workshop Style Registry (Phase 16).

Rebuilt from events:
- workshop.style.registered.v1
- workshop.style.updated.v1
- workshop.style.deactivated.v1

Provides:
- get_style(style_id)        → StyleRecord | None
- get_active_style(style_id) → StyleRecord | None  (None if INACTIVE)
- list_styles(business_id)   → List[StyleRecord]
- snapshot(business_id)      → dict summary
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from engines.workshop.events import (
    WORKSHOP_STYLE_REGISTERED_V1,
    WORKSHOP_STYLE_UPDATED_V1,
    WORKSHOP_STYLE_DEACTIVATED_V1,
)


@dataclass
class StyleRecord:
    """
    In-memory representation of one registered style.

    components: list of dicts — each dict is a serialised StyleComponent:
        {component_id, name, shape_type, material_id, quantity,
         formula_length, formula_width, orientation, endpoint_type, offcut_mm}
    """
    style_id: str
    name: str
    components: List[dict]
    variables: Dict[str, str]   # {var_name: description}
    status: str                 # ACTIVE | INACTIVE
    registered_at: Any          # ISO string or datetime
    business_id: str


class StyleCatalogProjection:
    """
    Per-business catalog of window/door style definitions.

    Implements ProjectionProtocol: apply(event_type, payload) + truncate().
    """

    projection_name = "workshop_style_catalog"

    def __init__(self) -> None:
        # style_id → StyleRecord
        self._styles: Dict[str, StyleRecord] = {}
        # business_id (str) → [style_id, ...]
        self._by_business: Dict[str, List[str]] = {}

    # ──────────────────────────────────────────────────────────────
    # EVENT APPLICATION
    # ──────────────────────────────────────────────────────────────

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        bid = str(payload.get("business_id", ""))

        if event_type == WORKSHOP_STYLE_REGISTERED_V1:
            sid = payload["style_id"]
            self._styles[sid] = StyleRecord(
                style_id=sid,
                name=payload["name"],
                components=list(payload.get("components") or []),
                variables=dict(payload.get("variables") or {}),
                status="ACTIVE",
                registered_at=payload.get("registered_at"),
                business_id=bid,
            )
            self._by_business.setdefault(bid, [])
            if sid not in self._by_business[bid]:
                self._by_business[bid].append(sid)

        elif event_type == WORKSHOP_STYLE_UPDATED_V1:
            sid = payload["style_id"]
            rec = self._styles.get(sid)
            if rec is None:
                return
            if payload.get("name") is not None:
                rec.name = payload["name"]
            if payload.get("components") is not None:
                rec.components = list(payload["components"])
            if payload.get("variables") is not None:
                rec.variables = dict(payload["variables"])

        elif event_type == WORKSHOP_STYLE_DEACTIVATED_V1:
            sid = payload["style_id"]
            rec = self._styles.get(sid)
            if rec is not None:
                rec.status = "INACTIVE"

    # ──────────────────────────────────────────────────────────────
    # QUERIES
    # ──────────────────────────────────────────────────────────────

    def get_style(self, style_id: str) -> Optional[StyleRecord]:
        """Return the style regardless of status."""
        return self._styles.get(style_id)

    def get_active_style(self, style_id: str) -> Optional[StyleRecord]:
        """Return the style only if status is ACTIVE."""
        rec = self._styles.get(style_id)
        if rec is not None and rec.status == "ACTIVE":
            return rec
        return None

    def list_styles(self, business_id) -> List[StyleRecord]:
        """Return all styles for a given business (ACTIVE and INACTIVE)."""
        bid = str(business_id)
        sids = self._by_business.get(bid, [])
        return [self._styles[s] for s in sids if s in self._styles]

    def list_active_styles(self, business_id) -> List[StyleRecord]:
        """Return only ACTIVE styles for a given business."""
        return [r for r in self.list_styles(business_id) if r.status == "ACTIVE"]

    def snapshot(self, business_id) -> Dict[str, Any]:
        """Summary dict for dashboards."""
        styles = self.list_styles(business_id)
        active = [s for s in styles if s.status == "ACTIVE"]
        inactive = [s for s in styles if s.status == "INACTIVE"]
        return {
            "total": len(styles),
            "active": len(active),
            "inactive": len(inactive),
            "style_ids": [s.style_id for s in active],
        }

    # ──────────────────────────────────────────────────────────────
    # MAINTENANCE
    # ──────────────────────────────────────────────────────────────

    def truncate(self, business_id=None) -> None:
        if business_id is None:
            self._styles.clear()
            self._by_business.clear()
        else:
            bid = str(business_id)
            sids = self._by_business.pop(bid, [])
            for sid in sids:
                self._styles.pop(sid, None)
