"""Tests for engines/hotel_channel/services/ota_manager.py"""
from datetime import datetime

import pytest

from engines.hotel_channel.services.ota_manager import (
    OTAChannelProjection,
    OTAChannelStatus,
    OTAManagerService,
    ConnectOTARequest,
    DisconnectOTARequest,
    UpdateSyncModeRequest,
    AddRoomMappingRequest,
    AddRateMappingRequest,
    MarkOTADegradedRequest,
)

NOW = datetime(2026, 3, 5, 12, 0, 0)
ADMIN = "hotel-admin-001"
PROPERTY_ID = "prop-nairobi-001"
PROVIDER = "channex"


@pytest.fixture
def projection():
    return OTAChannelProjection()


@pytest.fixture
def service(projection):
    return OTAManagerService(projection)


def _connect(service, provider=PROVIDER, sync_mode="PULL_ONLY"):
    return service.connect_ota(ConnectOTARequest(
        property_id=PROPERTY_ID,
        provider=provider,
        sync_mode=sync_mode,
        api_key_ref="secret/channex/prop-001",
        actor_id=ADMIN,
        issued_at=NOW,
    ))


class TestConnectOTA:
    def test_connect_valid_provider(self, service, projection):
        result = _connect(service)
        assert "rejected" not in result
        channel = projection.get_channel(PROPERTY_ID, PROVIDER)
        assert channel is not None
        assert channel.status == OTAChannelStatus.ACTIVE
        assert channel.sync_mode == "PULL_ONLY"

    def test_connect_invalid_provider_rejected(self, service):
        result = service.connect_ota(ConnectOTARequest(
            property_id=PROPERTY_ID,
            provider="fake_ota",
            sync_mode="PULL_ONLY",
            api_key_ref="x",
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert "rejected" in result
        assert result["rejected"].code == "INVALID_OTA_PROVIDER"

    def test_connect_invalid_sync_mode_rejected(self, service):
        result = service.connect_ota(ConnectOTARequest(
            property_id=PROPERTY_ID,
            provider=PROVIDER,
            sync_mode="MANUAL",
            api_key_ref="x",
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert "rejected" in result
        assert result["rejected"].code == "INVALID_SYNC_MODE"

    def test_connect_with_webhook(self, service, projection):
        service.connect_ota(ConnectOTARequest(
            property_id=PROPERTY_ID,
            provider=PROVIDER,
            sync_mode="FULL_SYNC",
            api_key_ref="secret/channex",
            actor_id=ADMIN,
            issued_at=NOW,
            webhook_url="https://example.com/webhook",
        ))
        channel = projection.get_channel(PROPERTY_ID, PROVIDER)
        assert channel.webhook_url == "https://example.com/webhook"

    def test_multiple_otas_for_same_property(self, service, projection):
        _connect(service, provider="channex")
        _connect(service, provider="beds24")
        channels = projection.list_channels_for_property(PROPERTY_ID)
        assert len(channels) == 2
        providers = {c.provider for c in channels}
        assert providers == {"channex", "beds24"}

    def test_reconnect_preserves_mappings(self, service, projection):
        _connect(service)
        service.add_room_mapping(AddRoomMappingRequest(
            property_id=PROPERTY_ID,
            provider=PROVIDER,
            bos_room_type_id="room-deluxe",
            ota_room_type_code="DBL",
            ota_room_type_name="Double Room",
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        # Reconnect (e.g. after reconnecting with new credentials)
        _connect(service)
        channel = projection.get_channel(PROPERTY_ID, PROVIDER)
        assert "room-deluxe" in channel.room_mappings


class TestDisconnectOTA:
    def test_disconnect_connected_channel(self, service, projection):
        _connect(service)
        err = service.disconnect_ota(DisconnectOTARequest(
            property_id=PROPERTY_ID,
            provider=PROVIDER,
            actor_id=ADMIN,
            issued_at=NOW,
            reason="Switching to beds24",
        ))
        assert err is None
        channel = projection.get_channel(PROPERTY_ID, PROVIDER)
        assert channel.status == OTAChannelStatus.DISCONNECTED
        assert channel.disconnection_reason == "Switching to beds24"
        # api_key_ref cleared for security
        assert channel.api_key_ref is None

    def test_disconnect_nonexistent_rejected(self, service):
        err = service.disconnect_ota(DisconnectOTARequest(
            property_id="no-property",
            provider=PROVIDER,
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert err is not None
        assert err.code == "OTA_CHANNEL_NOT_FOUND"

    def test_disconnect_already_disconnected_rejected(self, service):
        _connect(service)
        service.disconnect_ota(DisconnectOTARequest(
            property_id=PROPERTY_ID, provider=PROVIDER,
            actor_id=ADMIN, issued_at=NOW,
        ))
        err = service.disconnect_ota(DisconnectOTARequest(
            property_id=PROPERTY_ID, provider=PROVIDER,
            actor_id=ADMIN, issued_at=NOW,
        ))
        assert err is not None
        assert err.code == "OTA_ALREADY_DISCONNECTED"


class TestSyncMode:
    def test_update_sync_mode(self, service, projection):
        _connect(service, sync_mode="PULL_ONLY")
        err = service.update_sync_mode(UpdateSyncModeRequest(
            property_id=PROPERTY_ID,
            provider=PROVIDER,
            sync_mode="FULL_SYNC",
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert err is None
        channel = projection.get_channel(PROPERTY_ID, PROVIDER)
        assert channel.sync_mode == "FULL_SYNC"

    def test_invalid_sync_mode_rejected(self, service):
        _connect(service)
        err = service.update_sync_mode(UpdateSyncModeRequest(
            property_id=PROPERTY_ID,
            provider=PROVIDER,
            sync_mode="TURBO",
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert err is not None
        assert err.code == "INVALID_SYNC_MODE"

    def test_cannot_update_disconnected_channel(self, service):
        _connect(service)
        service.disconnect_ota(DisconnectOTARequest(
            property_id=PROPERTY_ID, provider=PROVIDER,
            actor_id=ADMIN, issued_at=NOW,
        ))
        err = service.update_sync_mode(UpdateSyncModeRequest(
            property_id=PROPERTY_ID, provider=PROVIDER,
            sync_mode="PULL_ONLY", actor_id=ADMIN, issued_at=NOW,
        ))
        assert err is not None
        assert err.code == "OTA_NOT_CONNECTED"


class TestMappings:
    def test_add_room_mapping(self, service, projection):
        _connect(service)
        err = service.add_room_mapping(AddRoomMappingRequest(
            property_id=PROPERTY_ID,
            provider=PROVIDER,
            bos_room_type_id="room-deluxe",
            ota_room_type_code="DBL",
            ota_room_type_name="Double Deluxe",
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert err is None
        mapping = projection.get_room_mapping(PROPERTY_ID, PROVIDER, "room-deluxe")
        assert mapping is not None
        assert mapping.ota_room_type_code == "DBL"

    def test_add_rate_mapping(self, service, projection):
        _connect(service)
        err = service.add_rate_mapping(AddRateMappingRequest(
            property_id=PROPERTY_ID,
            provider=PROVIDER,
            bos_rate_plan_id="rate-bed-breakfast",
            ota_rate_plan_code="BB",
            ota_rate_plan_name="Bed & Breakfast",
            actor_id=ADMIN,
            issued_at=NOW,
        ))
        assert err is None
        mapping = projection.get_rate_mapping(PROPERTY_ID, PROVIDER, "rate-bed-breakfast")
        assert mapping is not None
        assert mapping.ota_rate_plan_code == "BB"

    def test_add_multiple_room_mappings(self, service, projection):
        _connect(service)
        for room_id, code in [("deluxe", "DBL"), ("suite", "SUT"), ("twin", "TWN")]:
            service.add_room_mapping(AddRoomMappingRequest(
                property_id=PROPERTY_ID,
                provider=PROVIDER,
                bos_room_type_id=f"room-{room_id}",
                ota_room_type_code=code,
                ota_room_type_name=code,
                actor_id=ADMIN,
                issued_at=NOW,
            ))
        channel = projection.get_channel(PROPERTY_ID, PROVIDER)
        assert len(channel.room_mappings) == 3

    def test_room_mapping_overwrite(self, service, projection):
        _connect(service)
        service.add_room_mapping(AddRoomMappingRequest(
            property_id=PROPERTY_ID, provider=PROVIDER,
            bos_room_type_id="room-a", ota_room_type_code="OLD",
            ota_room_type_name="Old Code",
            actor_id=ADMIN, issued_at=NOW,
        ))
        service.add_room_mapping(AddRoomMappingRequest(
            property_id=PROPERTY_ID, provider=PROVIDER,
            bos_room_type_id="room-a", ota_room_type_code="NEW",
            ota_room_type_name="New Code",
            actor_id=ADMIN, issued_at=NOW,
        ))
        mapping = projection.get_room_mapping(PROPERTY_ID, PROVIDER, "room-a")
        assert mapping.ota_room_type_code == "NEW"


class TestDegradation:
    def test_mark_channel_degraded(self, service, projection):
        _connect(service)
        err = service.mark_degraded(MarkOTADegradedRequest(
            property_id=PROPERTY_ID,
            provider=PROVIDER,
            reason="API timeout during sync",
            actor_id="SYSTEM",
            issued_at=NOW,
        ))
        assert err is None
        channel = projection.get_channel(PROPERTY_ID, PROVIDER)
        assert channel.status == OTAChannelStatus.DEGRADED
        assert channel.degradation_reason == "API timeout during sync"

    def test_reconnect_clears_degraded_status(self, service, projection):
        _connect(service)
        service.mark_degraded(MarkOTADegradedRequest(
            property_id=PROPERTY_ID, provider=PROVIDER,
            reason="timeout", actor_id="SYSTEM", issued_at=NOW,
        ))
        _connect(service)  # reconnect
        channel = projection.get_channel(PROPERTY_ID, PROVIDER)
        assert channel.status == OTAChannelStatus.ACTIVE
        assert channel.degradation_reason is None


class TestPropertySummary:
    def test_summary_for_property(self, service):
        _connect(service, provider="channex")
        _connect(service, provider="beds24")
        service.mark_degraded(MarkOTADegradedRequest(
            property_id=PROPERTY_ID, provider="beds24",
            reason="API issue", actor_id="SYSTEM", issued_at=NOW,
        ))
        summary = service.get_property_ota_summary(PROPERTY_ID)
        assert summary["total_channels"] == 2
        assert summary["active_channels"] == 1  # beds24 is DEGRADED, not ACTIVE
        assert len(summary["channels"]) == 2

    def test_empty_summary_for_unknown_property(self, service):
        summary = service.get_property_ota_summary("unknown-property")
        assert summary["total_channels"] == 0
        assert summary["active_channels"] == 0
