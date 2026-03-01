"""BOS Hotel Channel Engine — Event Types"""
from __future__ import annotations

CHANNEL_CONNECTED_V1     = "hotel.channel.connected.v1"
CHANNEL_DISCONNECTED_V1  = "hotel.channel.disconnected.v1"
CHANNEL_DEGRADED_V1      = "hotel.channel.degraded.v1"
ROOM_MAPPED_V1           = "hotel.channel.room_mapped.v1"
RATE_MAPPED_V1           = "hotel.channel.rate_mapped.v1"
SYNC_JOB_STARTED_V1      = "hotel.channel.sync_started.v1"
SYNC_JOB_COMPLETED_V1    = "hotel.channel.sync_completed.v1"
SYNC_JOB_FAILED_V1       = "hotel.channel.sync_failed.v1"
WEBHOOK_RECEIVED_V1      = "hotel.channel.webhook_received.v1"
RECONCILE_RUN_V1         = "hotel.channel.reconcile_run.v1"
SYNC_MODE_UPDATED_V1     = "hotel.channel.sync_mode_updated.v1"

HOTEL_CHANNEL_EVENT_TYPES = (
    CHANNEL_CONNECTED_V1, CHANNEL_DISCONNECTED_V1, CHANNEL_DEGRADED_V1,
    ROOM_MAPPED_V1, RATE_MAPPED_V1,
    SYNC_JOB_STARTED_V1, SYNC_JOB_COMPLETED_V1, SYNC_JOB_FAILED_V1,
    WEBHOOK_RECEIVED_V1, RECONCILE_RUN_V1, SYNC_MODE_UPDATED_V1,
)

VALID_SYNC_MODES = frozenset({
    "PULL_ONLY",           # safest — pull reservations, no outbound push
    "PULL_AVAILABILITY",   # pull + push availability
    "FULL_SYNC",           # pull + push ARI (BOS Master mode)
})
VALID_PROVIDERS = frozenset({"channex", "beds24", "siteminder", "cultswitch"})
