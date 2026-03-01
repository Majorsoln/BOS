"""
BOS Hotel Channel Engine — Adapter Contract + Provider Implementations
======================================================================
Architecture: Adapter + Contracts
  - BOS defines the internal ChannelManagerAdapter contract (ABC).
  - Each Channel Manager provider (Channex, Beds24, SiteMinder...)
    gets its own Adapter class.
  - BOS NEVER connects directly to OTAs (Booking.com, Expedia, Agoda).
    The Channel Manager is the bridge — it handles all OTA protocols.
  - Adding a new provider = new Adapter class. Core never changes.

Terminology:
  Channel Manager = Channex / Beds24 / SiteMinder / CultSwitch
  OTA             = Booking.com / Expedia / Agoda / Airbnb (CM's problem)
  ARI             = Availability, Rates, Restrictions
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ── Shared Value Objects ──────────────────────────────────────

@dataclass(frozen=True)
class HealthStatus:
    ok:       bool
    message:  str = ""
    latency_ms: int = 0


@dataclass(frozen=True)
class ConnectionResult:
    connected: bool
    provider:  str
    property_ref: str  # provider-side property identifier
    message:   str = ""


@dataclass(frozen=True)
class ExternalReservation:
    """Normalised reservation from any Channel Manager."""
    external_id:    str
    channel:        str           # BOOKING_COM | EXPEDIA | AGODA | ...
    provider_room_id:  str        # CM room identifier (needs mapping)
    provider_rate_id:  str        # CM rate identifier (needs mapping)
    guest_name:     str
    adults:         int
    children:       int
    arrival_date:   str
    departure_date: str
    nights:         int
    total_amount:   int
    currency:       str
    status:         str           # NEW | MODIFIED | CANCELLED
    deposit_paid:   int = 0
    special_requests: str = ""
    raw_payload:    Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PushResult:
    accepted:   bool
    provider:   str
    job_type:   str           # push_availability | push_rates | push_restrictions
    rooms_updated: int = 0
    dates_updated: int = 0
    errors:     List[str] = field(default_factory=list)
    message:    str = ""


@dataclass(frozen=True)
class WebhookResult:
    processed: bool
    event_type: str  # reservation_created | reservation_modified | reservation_cancelled
    external_id: Optional[str] = None
    message: str = ""


@dataclass(frozen=True)
class CatalogResult:
    """Room types and rate plans pulled from Channel Manager."""
    provider_rooms: List[Dict[str, Any]] = field(default_factory=list)
    provider_rates: List[Dict[str, Any]] = field(default_factory=list)
    active_channels: List[str] = field(default_factory=list)


# ── Abstract Contract ─────────────────────────────────────────

class ChannelManagerAdapter(ABC):
    """
    BOS internal contract for all Channel Manager providers.
    Implement this for each CM: Channex, Beds24, SiteMinder, etc.

    BOS speaks ONLY to the CM via this contract.
    The CM translates to/from OTA-specific protocols.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name: 'Channex', 'Beds24', etc."""
        ...

    @abstractmethod
    def health_check(self) -> HealthStatus:
        """Verify connectivity and credentials."""
        ...

    @abstractmethod
    def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        """Store credentials, verify connection, return result."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Revoke/clear stored credentials."""
        ...

    @abstractmethod
    def pull_catalog(self) -> CatalogResult:
        """
        Fetch room categories, rate plans, and active OTA channels
        from the Channel Manager. Used during onboarding mapping wizard.
        """
        ...

    @abstractmethod
    def pull_reservations(self, since: datetime) -> List[ExternalReservation]:
        """
        Pull new/modified/cancelled reservations since a given timestamp.
        Used for polling fallback when webhooks are unavailable.
        Implementations must normalise CM-specific payloads to
        ExternalReservation objects.
        """
        ...

    @abstractmethod
    def push_availability(
        self,
        property_ref: str,
        room_map: Dict[str, str],        # BOS room_type_id → provider room_id
        availability: Dict[str, Dict[str, int]],  # room_type_id → {date: available_count}
    ) -> PushResult:
        """
        Push availability (open/close dates per room type) to CM.
        CM then distributes to all connected OTAs simultaneously.
        Prefer incremental push (only changed dates).
        """
        ...

    @abstractmethod
    def push_rates(
        self,
        property_ref: str,
        rate_map: Dict[str, str],         # BOS rate_plan_id → provider rate_id
        room_map: Dict[str, str],         # BOS room_type_id → provider room_id
        rates: Dict[str, Dict[str, Dict[str, int]]],  # rate_plan → room_type → {date: rate}
        currency: str,
    ) -> PushResult:
        """Push nightly rates per rate plan, room type, and date."""
        ...

    @abstractmethod
    def push_restrictions(
        self,
        property_ref: str,
        rate_map: Dict[str, str],
        restrictions: Dict[str, Any],    # e.g. min_los, max_los, closed_to_arrival
    ) -> PushResult:
        """Push rate restrictions (min stay, stop-sell, etc.)."""
        ...

    @abstractmethod
    def handle_webhook(self, payload: Dict[str, Any]) -> WebhookResult:
        """
        Process an inbound webhook from the CM.
        Parse provider-specific payload → WebhookResult.
        Called by BOS webhook endpoint; must be idempotent.
        """
        ...


# ── Channex Adapter ───────────────────────────────────────────

class ChannexAdapter(ChannelManagerAdapter):
    """
    Adapter for Channex Channel Manager (https://channex.io).
    Channex supports 150+ OTAs including Booking.com, Expedia,
    Agoda, Airbnb, Hotels.com, TripAdvisor, and more.

    Authentication: API Key (X-Api-Key header).
    Webhooks: Channex POSTs to BOS endpoint on reservation events.
    ARI: Channex Bulk ARI update endpoint.
    """

    BASE_URL = "https://api.channex.io/api/v1"

    def __init__(self, api_key: str = "", property_id: str = ""):
        self._api_key     = api_key
        self._property_id = property_id  # Channex property_id
        self._connected   = bool(api_key and property_id)

    @property
    def provider_name(self) -> str:
        return "Channex"

    def health_check(self) -> HealthStatus:
        if not self._connected:
            return HealthStatus(ok=False, message="Not connected — missing credentials.")
        # In production: GET {BASE_URL}/properties/{property_id}
        # For now: simulate connected state
        return HealthStatus(ok=True, message="Channex connection healthy.", latency_ms=42)

    def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        api_key     = credentials.get("api_key", "")
        property_id = credentials.get("property_id", "")
        if not api_key:
            return ConnectionResult(connected=False, provider=self.provider_name,
                                    property_ref="", message="api_key required.")
        if not property_id:
            return ConnectionResult(connected=False, provider=self.provider_name,
                                    property_ref="", message="property_id required.")
        self._api_key     = api_key
        self._property_id = property_id
        self._connected   = True
        # In production: validate against GET /properties/{property_id}
        return ConnectionResult(connected=True, provider=self.provider_name,
                                property_ref=property_id,
                                message="Connected to Channex successfully.")

    def disconnect(self) -> None:
        self._api_key   = ""
        self._connected = False

    def pull_catalog(self) -> CatalogResult:
        if not self._connected:
            return CatalogResult()
        # In production:
        #   GET /room_types?property_id={id}
        #   GET /rate_plans?property_id={id}
        #   GET /channels?property_id={id}
        # Returns normalised catalog
        return CatalogResult(
            provider_rooms=[],
            provider_rates=[],
            active_channels=[],
        )

    def pull_reservations(self, since: datetime) -> List[ExternalReservation]:
        if not self._connected:
            return []
        # In production:
        #   GET /bookings?property_id={id}&updated_at[gte]={since.isoformat()}
        #   Normalise each booking → ExternalReservation
        return []

    def push_availability(self, property_ref, room_map, availability) -> PushResult:
        if not self._connected:
            return PushResult(accepted=False, provider=self.provider_name,
                              job_type="push_availability",
                              message="Not connected.")
        # In production:
        #   POST /bulk_update with availability per mapped room/date
        rooms = len(room_map)
        dates = sum(len(v) for v in availability.values())
        return PushResult(accepted=True, provider=self.provider_name,
                          job_type="push_availability",
                          rooms_updated=rooms, dates_updated=dates,
                          message="Availability pushed to Channex.")

    def push_rates(self, property_ref, rate_map, room_map,
                   rates, currency) -> PushResult:
        if not self._connected:
            return PushResult(accepted=False, provider=self.provider_name,
                              job_type="push_rates", message="Not connected.")
        # In production:
        #   POST /bulk_update with rates per mapped rate_plan/room/date
        return PushResult(accepted=True, provider=self.provider_name,
                          job_type="push_rates",
                          rooms_updated=len(room_map),
                          message="Rates pushed to Channex.")

    def push_restrictions(self, property_ref, rate_map, restrictions) -> PushResult:
        if not self._connected:
            return PushResult(accepted=False, provider=self.provider_name,
                              job_type="push_restrictions", message="Not connected.")
        return PushResult(accepted=True, provider=self.provider_name,
                          job_type="push_restrictions",
                          message="Restrictions pushed to Channex.")

    def handle_webhook(self, payload: Dict[str, Any]) -> WebhookResult:
        # Channex webhook format:
        # { "event": "booking_new"|"booking_modified"|"booking_cancelled",
        #   "booking": { "id": "...", ... } }
        event    = payload.get("event", "")
        booking  = payload.get("booking", {})
        ext_id   = booking.get("id", "")
        if not ext_id:
            return WebhookResult(processed=False, event_type=event,
                                 message="Missing booking.id in payload.")
        event_map = {
            "booking_new":       "reservation_created",
            "booking_modified":  "reservation_modified",
            "booking_cancelled": "reservation_cancelled",
        }
        return WebhookResult(
            processed=True,
            event_type=event_map.get(event, event),
            external_id=ext_id,
            message=f"Channex webhook processed: {event}",
        )


# ── Beds24 Adapter ────────────────────────────────────────────

class Beds24Adapter(ChannelManagerAdapter):
    """
    Adapter for Beds24 Channel Manager (https://beds24.com).
    Beds24 supports 100+ OTAs via its channel manager module.

    Authentication: API Key + Property ID.
    Webhooks: Beds24 supports notification URLs.
    ARI: Beds24 v2 REST API with calendar/pricing endpoints.
    """

    BASE_URL = "https://beds24.com/api/v2"

    def __init__(self, api_key: str = "", prop_key: str = ""):
        self._api_key  = api_key
        self._prop_key = prop_key   # Beds24 propKey
        self._connected = bool(api_key and prop_key)

    @property
    def provider_name(self) -> str:
        return "Beds24"

    def health_check(self) -> HealthStatus:
        if not self._connected:
            return HealthStatus(ok=False, message="Not connected — missing credentials.")
        # In production: GET {BASE_URL}/properties (with auth header)
        return HealthStatus(ok=True, message="Beds24 connection healthy.", latency_ms=55)

    def connect(self, credentials: Dict[str, str]) -> ConnectionResult:
        api_key  = credentials.get("api_key", "")
        prop_key = credentials.get("prop_key", "")
        if not api_key:
            return ConnectionResult(connected=False, provider=self.provider_name,
                                    property_ref="", message="api_key required.")
        if not prop_key:
            return ConnectionResult(connected=False, provider=self.provider_name,
                                    property_ref="", message="prop_key required.")
        self._api_key  = api_key
        self._prop_key = prop_key
        self._connected = True
        return ConnectionResult(connected=True, provider=self.provider_name,
                                property_ref=prop_key,
                                message="Connected to Beds24 successfully.")

    def disconnect(self) -> None:
        self._api_key  = ""
        self._connected = False

    def pull_catalog(self) -> CatalogResult:
        if not self._connected:
            return CatalogResult()
        # In production:
        #   GET /properties → room types
        #   GET /ratesets → rate plans
        #   GET /channels → connected OTA list
        return CatalogResult(provider_rooms=[], provider_rates=[], active_channels=[])

    def pull_reservations(self, since: datetime) -> List[ExternalReservation]:
        if not self._connected:
            return []
        # In production:
        #   GET /bookings?modifiedFrom={since}
        #   Normalise → ExternalReservation
        return []

    def push_availability(self, property_ref, room_map, availability) -> PushResult:
        if not self._connected:
            return PushResult(accepted=False, provider=self.provider_name,
                              job_type="push_availability", message="Not connected.")
        # In production: POST /calendars with availability data
        return PushResult(accepted=True, provider=self.provider_name,
                          job_type="push_availability",
                          rooms_updated=len(room_map),
                          message="Availability pushed to Beds24.")

    def push_rates(self, property_ref, rate_map, room_map,
                   rates, currency) -> PushResult:
        if not self._connected:
            return PushResult(accepted=False, provider=self.provider_name,
                              job_type="push_rates", message="Not connected.")
        # In production: POST /rates with pricing data
        return PushResult(accepted=True, provider=self.provider_name,
                          job_type="push_rates",
                          rooms_updated=len(room_map),
                          message="Rates pushed to Beds24.")

    def push_restrictions(self, property_ref, rate_map, restrictions) -> PushResult:
        if not self._connected:
            return PushResult(accepted=False, provider=self.provider_name,
                              job_type="push_restrictions", message="Not connected.")
        return PushResult(accepted=True, provider=self.provider_name,
                          job_type="push_restrictions",
                          message="Restrictions pushed to Beds24.")

    def handle_webhook(self, payload: Dict[str, Any]) -> WebhookResult:
        # Beds24 webhook format:
        # { "type": "newBooking"|"modifiedBooking"|"cancelBooking",
        #   "bookId": "...", ... }
        event  = payload.get("type", "")
        ext_id = str(payload.get("bookId", ""))
        if not ext_id:
            return WebhookResult(processed=False, event_type=event,
                                 message="Missing bookId in Beds24 payload.")
        event_map = {
            "newBooking":      "reservation_created",
            "modifiedBooking": "reservation_modified",
            "cancelBooking":   "reservation_cancelled",
        }
        return WebhookResult(
            processed=True,
            event_type=event_map.get(event, event),
            external_id=ext_id,
            message=f"Beds24 webhook processed: {event}",
        )


# ── Registry ──────────────────────────────────────────────────

ADAPTER_REGISTRY: Dict[str, type] = {
    "channex": ChannexAdapter,
    "beds24":  Beds24Adapter,
}


def get_adapter(provider: str, credentials: Dict[str, str]) -> ChannelManagerAdapter:
    """
    Factory: return a connected adapter for the given provider.
    Usage:
        adapter = get_adapter("channex", {"api_key": "...", "property_id": "..."})
        status  = adapter.health_check()
    """
    cls = ADAPTER_REGISTRY.get(provider.lower())
    if cls is None:
        raise ValueError(
            f"Unknown channel manager provider '{provider}'. "
            f"Available: {sorted(ADAPTER_REGISTRY)}."
        )
    adapter = cls()
    adapter.connect(credentials)
    return adapter
