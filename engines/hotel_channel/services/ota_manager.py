"""
BOS Hotel Channel — Selective OTA Manager
==========================================
Per-hotel selective OTA channel configuration.

Each hotel property can:
  - Enable/disable specific OTA providers independently
  - Set a sync mode per OTA (PULL_ONLY | PULL_AVAILABILITY | FULL_SYNC)
  - Configure mapping: BOS room type → OTA room type, BOS rate → OTA rate
  - Pause a single OTA without affecting others
  - View sync health per OTA

Supported OTAs (extensible via VALID_PROVIDERS in events.py):
  channex      — channel management aggregator
  beds24       — direct PMS integration
  siteminder   — enterprise CRS/channel manager
  cultswitch   — EAC-focused channel manager
  booking_com  — direct Booking.com connectivity
  expedia      — direct Expedia connectivity

All state changes are events. Reconnecting after disconnection
creates a new CHANNEL_CONNECTED event — history is preserved.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional

from core.commands.rejection import RejectionReason
from engines.hotel_channel.events import (
    CHANNEL_CONNECTED_V1,
    CHANNEL_DISCONNECTED_V1,
    CHANNEL_DEGRADED_V1,
    ROOM_MAPPED_V1,
    RATE_MAPPED_V1,
    SYNC_MODE_UPDATED_V1,
    VALID_PROVIDERS,
    VALID_SYNC_MODES,
)


# ══════════════════════════════════════════════════════════════
# OTA CHANNEL STATUS
# ══════════════════════════════════════════════════════════════

class OTAChannelStatus(Enum):
    ACTIVE      = "ACTIVE"       # connected and syncing normally
    PAUSED      = "PAUSED"       # connected but sync suspended
    DEGRADED    = "DEGRADED"     # connected but errors observed
    DISCONNECTED = "DISCONNECTED"  # not connected


# ══════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RoomMapping:
    """Maps a BOS room_type_id to an OTA room type code."""
    bos_room_type_id: str
    ota_room_type_code: str
    ota_room_type_name: str


@dataclass(frozen=True)
class RateMapping:
    """Maps a BOS rate_plan_id to an OTA rate plan code."""
    bos_rate_plan_id: str
    ota_rate_plan_code: str
    ota_rate_plan_name: str


@dataclass(frozen=True)
class OTAChannelConfig:
    """
    Current configuration of one OTA channel for one hotel property.
    Rebuilt from events — immutable snapshot.
    """
    property_id: str            # hotel property UUID
    provider: str               # e.g. "channex"
    status: OTAChannelStatus
    sync_mode: str              # PULL_ONLY | PULL_AVAILABILITY | FULL_SYNC
    connected_at: Optional[datetime]
    last_sync_at: Optional[datetime]
    room_mappings: Dict[str, RoomMapping]   # bos_room_type_id → mapping
    rate_mappings: Dict[str, RateMapping]   # bos_rate_plan_id → mapping
    api_key_ref: Optional[str]              # reference to secret store (not the key itself)
    webhook_url: Optional[str]
    degradation_reason: Optional[str] = None
    disconnected_at: Optional[datetime] = None
    disconnection_reason: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ConnectOTARequest:
    property_id: str
    provider: str
    sync_mode: str
    api_key_ref: str            # reference/alias to secret store — NOT the key itself
    actor_id: str
    issued_at: datetime
    webhook_url: Optional[str] = None


@dataclass(frozen=True)
class DisconnectOTARequest:
    property_id: str
    provider: str
    actor_id: str
    issued_at: datetime
    reason: str = ""


@dataclass(frozen=True)
class UpdateSyncModeRequest:
    property_id: str
    provider: str
    sync_mode: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class AddRoomMappingRequest:
    property_id: str
    provider: str
    bos_room_type_id: str
    ota_room_type_code: str
    ota_room_type_name: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class AddRateMappingRequest:
    property_id: str
    provider: str
    bos_rate_plan_id: str
    ota_rate_plan_code: str
    ota_rate_plan_name: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class MarkOTADegradedRequest:
    property_id: str
    provider: str
    reason: str
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# OTA CHANNEL PROJECTION
# ══════════════════════════════════════════════════════════════

class OTAChannelProjection:
    """
    In-memory projection of OTA channel configurations per property.

    Key: "{property_id}:{provider}"
    Rebuilt deterministically from hotel_channel events.
    """

    projection_name = "ota_channel_projection"

    def __init__(self) -> None:
        # "{property_id}:{provider}" → OTAChannelConfig
        self._channels: Dict[str, OTAChannelConfig] = {}
        # property_id → set of active provider names
        self._property_providers: Dict[str, List[str]] = {}

    def _key(self, property_id: str, provider: str) -> str:
        return f"{property_id}:{provider}"

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        property_id = payload.get("property_id", "")
        provider = payload.get("provider", "")

        if event_type == CHANNEL_CONNECTED_V1:
            self._apply_connected(property_id, provider, payload)
        elif event_type == CHANNEL_DISCONNECTED_V1:
            self._apply_disconnected(property_id, provider, payload)
        elif event_type == CHANNEL_DEGRADED_V1:
            self._apply_degraded(property_id, provider, payload)
        elif event_type == ROOM_MAPPED_V1:
            self._apply_room_mapped(property_id, provider, payload)
        elif event_type == RATE_MAPPED_V1:
            self._apply_rate_mapped(property_id, provider, payload)
        elif event_type == SYNC_MODE_UPDATED_V1:
            self._apply_sync_mode_updated(property_id, provider, payload)

    def _apply_connected(
        self, property_id: str, provider: str, payload: Dict[str, Any]
    ) -> None:
        key = self._key(property_id, provider)
        old = self._channels.get(key)
        room_mappings = old.room_mappings if old else {}
        rate_mappings = old.rate_mappings if old else {}
        self._channels[key] = OTAChannelConfig(
            property_id=property_id,
            provider=provider,
            status=OTAChannelStatus.ACTIVE,
            sync_mode=payload.get("sync_mode", "PULL_ONLY"),
            connected_at=payload.get("issued_at"),
            last_sync_at=None,
            room_mappings=room_mappings,
            rate_mappings=rate_mappings,
            api_key_ref=payload.get("api_key_ref"),
            webhook_url=payload.get("webhook_url"),
        )
        providers = self._property_providers.setdefault(property_id, [])
        if provider not in providers:
            providers.append(provider)

    def _apply_disconnected(
        self, property_id: str, provider: str, payload: Dict[str, Any]
    ) -> None:
        key = self._key(property_id, provider)
        old = self._channels.get(key)
        if old is None:
            return
        self._channels[key] = OTAChannelConfig(
            property_id=old.property_id,
            provider=old.provider,
            status=OTAChannelStatus.DISCONNECTED,
            sync_mode=old.sync_mode,
            connected_at=old.connected_at,
            last_sync_at=old.last_sync_at,
            room_mappings=old.room_mappings,
            rate_mappings=old.rate_mappings,
            api_key_ref=None,           # clear credentials on disconnect
            webhook_url=old.webhook_url,
            disconnected_at=payload.get("issued_at"),
            disconnection_reason=payload.get("reason"),
        )

    def _apply_degraded(
        self, property_id: str, provider: str, payload: Dict[str, Any]
    ) -> None:
        key = self._key(property_id, provider)
        old = self._channels.get(key)
        if old is None:
            return
        self._channels[key] = OTAChannelConfig(
            property_id=old.property_id,
            provider=old.provider,
            status=OTAChannelStatus.DEGRADED,
            sync_mode=old.sync_mode,
            connected_at=old.connected_at,
            last_sync_at=old.last_sync_at,
            room_mappings=old.room_mappings,
            rate_mappings=old.rate_mappings,
            api_key_ref=old.api_key_ref,
            webhook_url=old.webhook_url,
            degradation_reason=payload.get("reason"),
        )

    def _apply_room_mapped(
        self, property_id: str, provider: str, payload: Dict[str, Any]
    ) -> None:
        key = self._key(property_id, provider)
        old = self._channels.get(key)
        if old is None:
            return
        bos_id = payload["bos_room_type_id"]
        mapping = RoomMapping(
            bos_room_type_id=bos_id,
            ota_room_type_code=payload["ota_room_type_code"],
            ota_room_type_name=payload.get("ota_room_type_name", ""),
        )
        new_mappings = dict(old.room_mappings)
        new_mappings[bos_id] = mapping
        self._channels[key] = OTAChannelConfig(
            property_id=old.property_id,
            provider=old.provider,
            status=old.status,
            sync_mode=old.sync_mode,
            connected_at=old.connected_at,
            last_sync_at=old.last_sync_at,
            room_mappings=new_mappings,
            rate_mappings=old.rate_mappings,
            api_key_ref=old.api_key_ref,
            webhook_url=old.webhook_url,
            degradation_reason=old.degradation_reason,
        )

    def _apply_rate_mapped(
        self, property_id: str, provider: str, payload: Dict[str, Any]
    ) -> None:
        key = self._key(property_id, provider)
        old = self._channels.get(key)
        if old is None:
            return
        bos_id = payload["bos_rate_plan_id"]
        mapping = RateMapping(
            bos_rate_plan_id=bos_id,
            ota_rate_plan_code=payload["ota_rate_plan_code"],
            ota_rate_plan_name=payload.get("ota_rate_plan_name", ""),
        )
        new_mappings = dict(old.rate_mappings)
        new_mappings[bos_id] = mapping
        self._channels[key] = OTAChannelConfig(
            property_id=old.property_id,
            provider=old.provider,
            status=old.status,
            sync_mode=old.sync_mode,
            connected_at=old.connected_at,
            last_sync_at=old.last_sync_at,
            room_mappings=old.room_mappings,
            rate_mappings=new_mappings,
            api_key_ref=old.api_key_ref,
            webhook_url=old.webhook_url,
            degradation_reason=old.degradation_reason,
        )

    def _apply_sync_mode_updated(
        self, property_id: str, provider: str, payload: Dict[str, Any]
    ) -> None:
        key = self._key(property_id, provider)
        old = self._channels.get(key)
        if old is None:
            return
        self._channels[key] = OTAChannelConfig(
            property_id=old.property_id,
            provider=old.provider,
            status=old.status,
            sync_mode=payload["sync_mode"],
            connected_at=old.connected_at,
            last_sync_at=old.last_sync_at,
            room_mappings=old.room_mappings,
            rate_mappings=old.rate_mappings,
            api_key_ref=old.api_key_ref,
            webhook_url=old.webhook_url,
            degradation_reason=old.degradation_reason,
        )

    # ── queries ───────────────────────────────────────────────

    def get_channel(
        self, property_id: str, provider: str
    ) -> Optional[OTAChannelConfig]:
        return self._channels.get(self._key(property_id, provider))

    def list_channels_for_property(
        self, property_id: str
    ) -> List[OTAChannelConfig]:
        providers = self._property_providers.get(property_id, [])
        return [
            self._channels[self._key(property_id, p)]
            for p in providers
            if self._key(property_id, p) in self._channels
        ]

    def list_active_channels_for_property(
        self, property_id: str
    ) -> List[OTAChannelConfig]:
        return [
            c for c in self.list_channels_for_property(property_id)
            if c.status == OTAChannelStatus.ACTIVE
        ]

    def get_room_mapping(
        self, property_id: str, provider: str, bos_room_type_id: str
    ) -> Optional[RoomMapping]:
        channel = self.get_channel(property_id, provider)
        if channel is None:
            return None
        return channel.room_mappings.get(bos_room_type_id)

    def get_rate_mapping(
        self, property_id: str, provider: str, bos_rate_plan_id: str
    ) -> Optional[RateMapping]:
        channel = self.get_channel(property_id, provider)
        if channel is None:
            return None
        return channel.rate_mappings.get(bos_rate_plan_id)

    def truncate(self) -> None:
        self._channels.clear()
        self._property_providers.clear()


# ══════════════════════════════════════════════════════════════
# OTA MANAGER SERVICE
# ══════════════════════════════════════════════════════════════

class OTAManagerService:
    """
    Manages selective OTA channel connections per hotel property.

    Hotels choose which OTAs to connect to and configure each one
    independently with the appropriate sync mode and mappings.
    All mutations produce events.
    """

    def __init__(self, projection: OTAChannelProjection) -> None:
        self._projection = projection

    def connect_ota(
        self, request: ConnectOTARequest
    ) -> Dict[str, Any]:
        """Connect a hotel property to an OTA provider."""
        if request.provider not in VALID_PROVIDERS:
            return {
                "rejected": RejectionReason(
                    code="INVALID_OTA_PROVIDER",
                    message=(
                        f"Unknown OTA provider: {request.provider}. "
                        f"Supported: {sorted(VALID_PROVIDERS)}."
                    ),
                    policy_name="connect_ota",
                ),
            }
        if request.sync_mode not in VALID_SYNC_MODES:
            return {
                "rejected": RejectionReason(
                    code="INVALID_SYNC_MODE",
                    message=(
                        f"Unknown sync mode: {request.sync_mode}. "
                        f"Valid: {sorted(VALID_SYNC_MODES)}."
                    ),
                    policy_name="connect_ota",
                ),
            }

        payload: Dict[str, Any] = {
            "property_id": request.property_id,
            "provider": request.provider,
            "sync_mode": request.sync_mode,
            "api_key_ref": request.api_key_ref,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        if request.webhook_url:
            payload["webhook_url"] = request.webhook_url

        self._projection.apply(CHANNEL_CONNECTED_V1, payload)
        return {
            "events": [{"event_type": CHANNEL_CONNECTED_V1, "payload": payload}],
        }

    def disconnect_ota(
        self, request: DisconnectOTARequest
    ) -> Optional[RejectionReason]:
        """Disconnect a hotel property from an OTA provider."""
        channel = self._projection.get_channel(request.property_id, request.provider)
        if channel is None:
            return RejectionReason(
                code="OTA_CHANNEL_NOT_FOUND",
                message=f"No channel found for property {request.property_id} / {request.provider}.",
                policy_name="disconnect_ota",
            )
        if channel.status == OTAChannelStatus.DISCONNECTED:
            return RejectionReason(
                code="OTA_ALREADY_DISCONNECTED",
                message=f"{request.provider} is already disconnected.",
                policy_name="disconnect_ota",
            )
        self._projection.apply(CHANNEL_DISCONNECTED_V1, {
            "property_id": request.property_id,
            "provider": request.provider,
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def update_sync_mode(
        self, request: UpdateSyncModeRequest
    ) -> Optional[RejectionReason]:
        """Change the sync mode for a connected OTA channel."""
        channel = self._projection.get_channel(request.property_id, request.provider)
        if channel is None:
            return RejectionReason(
                code="OTA_CHANNEL_NOT_FOUND",
                message=f"No channel found for {request.provider}.",
                policy_name="update_sync_mode",
            )
        if channel.status == OTAChannelStatus.DISCONNECTED:
            return RejectionReason(
                code="OTA_NOT_CONNECTED",
                message="Cannot change sync mode of a disconnected channel.",
                policy_name="update_sync_mode",
            )
        if request.sync_mode not in VALID_SYNC_MODES:
            return RejectionReason(
                code="INVALID_SYNC_MODE",
                message=f"Invalid sync mode: {request.sync_mode}.",
                policy_name="update_sync_mode",
            )
        self._projection.apply(SYNC_MODE_UPDATED_V1, {
            "property_id": request.property_id,
            "provider": request.provider,
            "sync_mode": request.sync_mode,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def add_room_mapping(
        self, request: AddRoomMappingRequest
    ) -> Optional[RejectionReason]:
        """Map a BOS room type to an OTA room type code."""
        channel = self._projection.get_channel(request.property_id, request.provider)
        if channel is None:
            return RejectionReason(
                code="OTA_CHANNEL_NOT_FOUND",
                message=f"No channel found for {request.provider}.",
                policy_name="add_room_mapping",
            )
        self._projection.apply(ROOM_MAPPED_V1, {
            "property_id": request.property_id,
            "provider": request.provider,
            "bos_room_type_id": request.bos_room_type_id,
            "ota_room_type_code": request.ota_room_type_code,
            "ota_room_type_name": request.ota_room_type_name,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def add_rate_mapping(
        self, request: AddRateMappingRequest
    ) -> Optional[RejectionReason]:
        """Map a BOS rate plan to an OTA rate plan code."""
        channel = self._projection.get_channel(request.property_id, request.provider)
        if channel is None:
            return RejectionReason(
                code="OTA_CHANNEL_NOT_FOUND",
                message=f"No channel found for {request.provider}.",
                policy_name="add_rate_mapping",
            )
        self._projection.apply(RATE_MAPPED_V1, {
            "property_id": request.property_id,
            "provider": request.provider,
            "bos_rate_plan_id": request.bos_rate_plan_id,
            "ota_rate_plan_code": request.ota_rate_plan_code,
            "ota_rate_plan_name": request.ota_rate_plan_name,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def mark_degraded(
        self, request: MarkOTADegradedRequest
    ) -> Optional[RejectionReason]:
        """Mark an OTA channel as degraded (errors observed during sync)."""
        channel = self._projection.get_channel(request.property_id, request.provider)
        if channel is None:
            return RejectionReason(
                code="OTA_CHANNEL_NOT_FOUND",
                message=f"No channel found for {request.provider}.",
                policy_name="mark_ota_degraded",
            )
        self._projection.apply(CHANNEL_DEGRADED_V1, {
            "property_id": request.property_id,
            "provider": request.provider,
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    # ── queries ───────────────────────────────────────────────

    def get_property_ota_summary(
        self, property_id: str
    ) -> Dict[str, Any]:
        """Return a summary of all OTA connections for a property."""
        channels = self._projection.list_channels_for_property(property_id)
        return {
            "property_id": property_id,
            "total_channels": len(channels),
            "active_channels": sum(
                1 for c in channels if c.status == OTAChannelStatus.ACTIVE
            ),
            "channels": [
                {
                    "provider": c.provider,
                    "status": c.status.value,
                    "sync_mode": c.sync_mode,
                    "room_mappings": len(c.room_mappings),
                    "rate_mappings": len(c.rate_mappings),
                    "connected_at": c.connected_at,
                    "degradation_reason": c.degradation_reason,
                }
                for c in channels
            ],
        }
