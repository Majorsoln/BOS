"""
BOS Hotel Channel Engine — Projection Store + Service
=====================================================
Manages Channel Manager connections per property:
  - Connection lifecycle (connect / disconnect / health)
  - Room and rate plan mapping (BOS ↔ Provider)
  - Sync job logging (pull_reservations, push_availability, etc.)
  - Idempotent OTA reservation ingestion (external_id dedup)
  - Reconciliation run history
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from engines.hotel_channel.events import (
    CHANNEL_CONNECTED_V1, CHANNEL_DISCONNECTED_V1, CHANNEL_DEGRADED_V1,
    ROOM_MAPPED_V1, RATE_MAPPED_V1,
    SYNC_JOB_STARTED_V1, SYNC_JOB_COMPLETED_V1, SYNC_JOB_FAILED_V1,
    WEBHOOK_RECEIVED_V1, RECONCILE_RUN_V1, SYNC_MODE_UPDATED_V1,
)
from engines.hotel_channel.adapters import (
    ChannelManagerAdapter, get_adapter, ExternalReservation,
)


class HotelChannelProjectionStore:
    """
    Tracks connection state, mappings, sync logs, and webhook receipts
    for one or more Channel Manager connections per property.
    """

    def __init__(self):
        self._events:       List[dict]            = []
        self._connections:  Dict[str, dict]       = {}  # property_id → connection state
        self._room_maps:    Dict[str, dict]       = {}  # f"{property_id}:{bos_room_type_id}" → provider_room_id
        self._rate_maps:    Dict[str, dict]       = {}  # f"{property_id}:{bos_rate_plan_id}" → provider_rate_id
        self._sync_jobs:    Dict[str, dict]       = {}  # job_id → sync job record
        self._reconciles:   List[dict]            = []

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type == CHANNEL_CONNECTED_V1:
            pid = payload["property_id"]
            self._connections[pid] = {
                "property_id":  pid,
                "provider":     payload["provider"],
                "property_ref": payload["property_ref"],
                "sync_mode":    payload.get("sync_mode", "PULL_ONLY"),
                "status":       "CONNECTED",
                "connected_at": payload["connected_at"],
            }

        elif event_type == CHANNEL_DISCONNECTED_V1:
            pid = payload["property_id"]
            if pid in self._connections:
                self._connections[pid]["status"] = "DISCONNECTED"

        elif event_type == CHANNEL_DEGRADED_V1:
            pid = payload["property_id"]
            if pid in self._connections:
                self._connections[pid]["status"]      = "DEGRADED"
                self._connections[pid]["degraded_msg"] = payload.get("message", "")

        elif event_type == ROOM_MAPPED_V1:
            key = f"{payload['property_id']}:{payload['bos_room_type_id']}"
            self._room_maps[key] = dict(payload)

        elif event_type == RATE_MAPPED_V1:
            key = f"{payload['property_id']}:{payload['bos_rate_plan_id']}"
            self._rate_maps[key] = dict(payload)

        elif event_type == SYNC_JOB_STARTED_V1:
            self._sync_jobs[payload["job_id"]] = {**payload, "status": "RUNNING"}

        elif event_type == SYNC_JOB_COMPLETED_V1:
            job = self._sync_jobs.get(payload["job_id"])
            if job:
                job["status"]       = "COMPLETED"
                job["completed_at"] = payload.get("completed_at")
                job["records"]      = payload.get("records", 0)

        elif event_type == SYNC_JOB_FAILED_V1:
            job = self._sync_jobs.get(payload["job_id"])
            if job:
                job["status"]    = "FAILED"
                job["error"]     = payload.get("error", "")
                job["failed_at"] = payload.get("failed_at")

        elif event_type == RECONCILE_RUN_V1:
            self._reconciles.append(dict(payload))

        elif event_type == SYNC_MODE_UPDATED_V1:
            pid = payload["property_id"]
            if pid in self._connections:
                self._connections[pid]["sync_mode"] = payload["sync_mode"]

    def get_connection(self, property_id: str) -> Optional[dict]:
        return self._connections.get(property_id)

    def is_connected(self, property_id: str) -> bool:
        conn = self._connections.get(property_id)
        return conn is not None and conn.get("status") == "CONNECTED"

    def get_room_map(self, property_id: str) -> Dict[str, str]:
        """Returns {bos_room_type_id: provider_room_id} for given property."""
        prefix = f"{property_id}:"
        return {
            k[len(prefix):]: v["provider_room_id"]
            for k, v in self._room_maps.items()
            if k.startswith(prefix)
        }

    def get_rate_map(self, property_id: str) -> Dict[str, str]:
        """Returns {bos_rate_plan_id: provider_rate_id} for given property."""
        prefix = f"{property_id}:"
        return {
            k[len(prefix):]: v["provider_rate_id"]
            for k, v in self._rate_maps.items()
            if k.startswith(prefix)
        }

    def list_sync_jobs(self, property_id: str) -> List[dict]:
        return [j for j in self._sync_jobs.values()
                if j.get("property_id") == property_id]

    def last_reconcile(self, property_id: str) -> Optional[dict]:
        runs = [r for r in self._reconciles
                if r.get("property_id") == property_id]
        return runs[-1] if runs else None

    @property
    def event_count(self) -> int:
        return len(self._events)

    def truncate(self):
        self._events.clear(); self._connections.clear()
        self._room_maps.clear(); self._rate_maps.clear()
        self._sync_jobs.clear(); self._reconciles.clear()


class HotelChannelService:
    """
    Orchestrates Channel Manager interactions:
      - connect / disconnect / health_check
      - room + rate mapping
      - pull_reservations (with idempotency via reservation store)
      - push_availability / push_rates / push_restrictions
      - handle_webhook
      - reconcile
    """

    def __init__(
        self, *,
        projection_store: HotelChannelProjectionStore,
        reservation_store=None,   # HotelReservationProjectionStore (optional, for dedup)
    ):
        self._projection        = projection_store
        self._reservation_store = reservation_store
        self._adapters:  Dict[str, ChannelManagerAdapter] = {}

    # ── Connection management ─────────────────────────────────

    def connect(
        self, property_id: str, provider: str, credentials: Dict[str, Any],
        sync_mode: str = "PULL_ONLY", actor_id: str = "system",
    ) -> dict:
        adapter = get_adapter(provider, credentials)
        result  = adapter.health_check()
        if not result.ok:
            return {"connected": False, "message": result.message}
        self._adapters[property_id] = adapter
        payload = {
            "property_id":  property_id,
            "provider":     provider,
            "property_ref": credentials.get("property_id") or credentials.get("prop_key", ""),
            "sync_mode":    sync_mode,
            "connected_at": datetime.utcnow().isoformat(),
            "connected_by": actor_id,
        }
        self._projection.apply(CHANNEL_CONNECTED_V1, payload)
        return {"connected": True, "provider": provider,
                "event_type": CHANNEL_CONNECTED_V1}

    def health_check(self, property_id: str) -> dict:
        adapter = self._adapters.get(property_id)
        if adapter is None:
            return {"ok": False, "message": "No adapter found for property."}
        status = adapter.health_check()
        if not status.ok:
            self._projection.apply(CHANNEL_DEGRADED_V1, {
                "property_id": property_id,
                "message": status.message,
                "checked_at": datetime.utcnow().isoformat(),
            })
        return {"ok": status.ok, "message": status.message,
                "latency_ms": status.latency_ms}

    # ── Mapping ───────────────────────────────────────────────

    def map_room(
        self, property_id: str,
        bos_room_type_id: str, provider_room_id: str,
        bos_room_name: str = "", provider_room_name: str = "",
        actor_id: str = "system",
    ) -> dict:
        payload = {
            "property_id":       property_id,
            "bos_room_type_id":  bos_room_type_id,
            "provider_room_id":  provider_room_id,
            "bos_room_name":     bos_room_name,
            "provider_room_name": provider_room_name,
            "mapped_by":         actor_id,
            "mapped_at":         datetime.utcnow().isoformat(),
        }
        self._projection.apply(ROOM_MAPPED_V1, payload)
        return {"event_type": ROOM_MAPPED_V1, "payload": payload}

    def map_rate(
        self, property_id: str,
        bos_rate_plan_id: str, provider_rate_id: str,
        bos_rate_name: str = "", provider_rate_name: str = "",
        actor_id: str = "system",
    ) -> dict:
        payload = {
            "property_id":      property_id,
            "bos_rate_plan_id": bos_rate_plan_id,
            "provider_rate_id": provider_rate_id,
            "bos_rate_name":    bos_rate_name,
            "provider_rate_name": provider_rate_name,
            "mapped_by":        actor_id,
            "mapped_at":        datetime.utcnow().isoformat(),
        }
        self._projection.apply(RATE_MAPPED_V1, payload)
        return {"event_type": RATE_MAPPED_V1, "payload": payload}

    # ── Inbound: Pull reservations ────────────────────────────

    def pull_reservations(
        self, property_id: str, since: datetime, job_id: str,
    ) -> dict:
        """
        Pull reservations from Channel Manager since `since`.
        Idempotency: skips any external_id already in reservation_store.
        Returns count of new/modified/skipped reservations.
        """
        adapter = self._adapters.get(property_id)
        if adapter is None:
            return {"error": "No adapter for property.", "new": 0, "skipped": 0}

        self._projection.apply(SYNC_JOB_STARTED_V1, {
            "job_id": job_id, "property_id": property_id,
            "job_type": "pull_reservations",
            "started_at": datetime.utcnow().isoformat(),
        })

        try:
            reservations: List[ExternalReservation] = adapter.pull_reservations(since)
            new_count = skipped = 0

            for res in reservations:
                # Idempotency guard
                if (self._reservation_store is not None
                        and self._reservation_store.external_id_exists(res.external_id)):
                    skipped += 1
                    continue
                new_count += 1
                # Emit webhook received event for audit trail
                self._projection.apply(WEBHOOK_RECEIVED_V1, {
                    "property_id": property_id,
                    "external_id": res.external_id,
                    "channel":     res.channel,
                    "event_type":  res.status,
                    "received_at": datetime.utcnow().isoformat(),
                })

            self._projection.apply(SYNC_JOB_COMPLETED_V1, {
                "job_id": job_id, "property_id": property_id,
                "records": new_count,
                "completed_at": datetime.utcnow().isoformat(),
            })
            return {
                "event_type": SYNC_JOB_COMPLETED_V1,
                "new": new_count, "skipped": skipped,
                "reservations": reservations,
            }

        except Exception as exc:
            self._projection.apply(SYNC_JOB_FAILED_V1, {
                "job_id": job_id, "property_id": property_id,
                "error": str(exc),
                "failed_at": datetime.utcnow().isoformat(),
            })
            return {"event_type": SYNC_JOB_FAILED_V1, "error": str(exc)}

    # ── Outbound: Push ARI ────────────────────────────────────

    def push_availability(
        self, property_id: str, job_id: str,
        availability: Dict[str, Dict[str, int]],
    ) -> dict:
        adapter = self._adapters.get(property_id)
        if adapter is None:
            return {"error": "No adapter for property."}
        room_map = self._projection.get_room_map(property_id)
        conn     = self._projection.get_connection(property_id)
        prop_ref = conn["property_ref"] if conn else property_id
        result   = adapter.push_availability(prop_ref, room_map, availability)
        event    = SYNC_JOB_COMPLETED_V1 if result.accepted else SYNC_JOB_FAILED_V1
        self._projection.apply(event, {
            "job_id": job_id, "property_id": property_id,
            "records": result.rooms_updated,
            "completed_at": datetime.utcnow().isoformat(),
        })
        return {"event_type": event, "result": result}

    def push_rates(
        self, property_id: str, job_id: str,
        rates: Dict[str, Any], currency: str,
    ) -> dict:
        adapter = self._adapters.get(property_id)
        if adapter is None:
            return {"error": "No adapter for property."}
        room_map = self._projection.get_room_map(property_id)
        rate_map = self._projection.get_rate_map(property_id)
        conn     = self._projection.get_connection(property_id)
        prop_ref = conn["property_ref"] if conn else property_id
        result   = adapter.push_rates(prop_ref, rate_map, room_map, rates, currency)
        event    = SYNC_JOB_COMPLETED_V1 if result.accepted else SYNC_JOB_FAILED_V1
        self._projection.apply(event, {
            "job_id": job_id, "property_id": property_id,
            "records": result.rooms_updated,
            "completed_at": datetime.utcnow().isoformat(),
        })
        return {"event_type": event, "result": result}

    # ── Webhook ingestion ─────────────────────────────────────

    def handle_webhook(
        self, property_id: str, provider: str, payload: Dict[str, Any],
    ) -> dict:
        """
        Entry point for inbound CM webhooks.
        Looks up the adapter, processes the payload, records receipt.
        """
        adapter = self._adapters.get(property_id)
        if adapter is None:
            # Try to create adapter from provider name (no credentials in webhook path)
            return {"processed": False, "message": "No adapter configured for property."}
        result = adapter.handle_webhook(payload)
        self._projection.apply(WEBHOOK_RECEIVED_V1, {
            "property_id": property_id,
            "provider":    provider,
            "event_type":  result.event_type,
            "external_id": result.external_id,
            "processed":   result.processed,
            "received_at": datetime.utcnow().isoformat(),
        })
        return {
            "processed":   result.processed,
            "event_type":  result.event_type,
            "external_id": result.external_id,
        }

    @property
    def _store(self) -> HotelChannelProjectionStore:
        return self._projection
