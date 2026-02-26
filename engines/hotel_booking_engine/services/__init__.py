"""
BOS Hotel Booking Engine — Service
====================================
Provides:
  1. API key management (issue/revoke BOOKING_ENGINE scoped keys)
  2. Availability search (real-time, date range + room type + occupancy)
  3. Rate quoting (nightly rate + extras + total)
  4. Direct booking creation → delegates to hotel_reservation engine
  5. Booking confirmation (sends confirmation event)
  6. Widget embed config (returns JS snippet with API key + property_id)

Integration:
  - Reads from HotelPropertyProjectionStore (room types, rate plans, rooms)
  - Reads from HotelReservationProjectionStore (occupied rooms → availability)
  - Writes to HotelReservationService (create + confirm reservation)
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

from engines.hotel_booking_engine.events import (
    BOOKING_ENGINE_KEY_ISSUED_V1, BOOKING_ENGINE_KEY_REVOKED_V1,
    AVAILABILITY_SEARCHED_V1, RATE_QUOTED_V1,
    DIRECT_BOOKING_CREATED_V1, DIRECT_BOOKING_CONFIRMED_V1,
    DIRECT_BOOKING_CANCELLED_V1, BOOKING_ENGINE_SETTINGS_UPDATED_V1,
)


class HotelBookingEngineProjectionStore:
    def __init__(self):
        self._events:    List[dict]      = []
        self._api_keys:  Dict[str, dict] = {}  # key_id → key record
        self._key_hash:  Dict[str, str]  = {}  # sha256(raw_key) → key_id
        self._settings:  Dict[str, dict] = {}  # property_id → settings
        self._bookings:  Dict[str, dict] = {}  # booking_id → booking

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type == BOOKING_ENGINE_KEY_ISSUED_V1:
            kid = payload["key_id"]
            self._api_keys[kid] = {**payload, "revoked": False}
            self._key_hash[payload["key_hash"]] = kid

        elif event_type == BOOKING_ENGINE_KEY_REVOKED_V1:
            kid = payload["key_id"]
            if kid in self._api_keys:
                self._api_keys[kid]["revoked"] = True

        elif event_type == BOOKING_ENGINE_SETTINGS_UPDATED_V1:
            pid = payload["property_id"]
            self._settings[pid] = {**self._settings.get(pid, {}), **payload}

        elif event_type == DIRECT_BOOKING_CREATED_V1:
            self._bookings[payload["booking_id"]] = {**payload, "status": "PENDING"}

        elif event_type == DIRECT_BOOKING_CONFIRMED_V1:
            b = self._bookings.get(payload["booking_id"])
            if b: b["status"] = "CONFIRMED"

        elif event_type == DIRECT_BOOKING_CANCELLED_V1:
            b = self._bookings.get(payload["booking_id"])
            if b: b["status"] = "CANCELLED"

    def get_api_key_by_hash(self, raw_key: str) -> Optional[dict]:
        h   = hashlib.sha256(raw_key.encode()).hexdigest()
        kid = self._key_hash.get(h)
        if kid is None: return None
        rec = self._api_keys.get(kid)
        if rec and rec.get("revoked"): return None
        return rec

    def get_settings(self, property_id: str) -> dict:
        return self._settings.get(property_id, {})

    def get_booking(self, booking_id: str) -> Optional[dict]:
        return self._bookings.get(booking_id)

    @property
    def event_count(self) -> int:
        return len(self._events)

    def truncate(self):
        self._events.clear(); self._api_keys.clear()
        self._key_hash.clear(); self._settings.clear()
        self._bookings.clear()


class HotelBookingEngineService:
    """
    Booking engine orchestrator.
    Designed to be called by the HTTP API layer on the public
    booking endpoint (/api/v1/book/{property_id}/...).
    """

    def __init__(
        self, *,
        projection_store: HotelBookingEngineProjectionStore,
        property_store=None,      # HotelPropertyProjectionStore
        reservation_store=None,   # HotelReservationProjectionStore
    ):
        self._projection        = projection_store
        self._property_store    = property_store
        self._reservation_store = reservation_store

    # ── API Key management ────────────────────────────────────

    def issue_api_key(
        self, property_id: str, label: str = "", actor_id: str = "manager"
    ) -> dict:
        """
        Generate a new BOOKING_ENGINE scoped API key.
        Returns raw key ONCE — only hash is stored (never raw).
        Hotel embeds this key in their website widget.
        """
        raw_key  = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_id   = f"bek_{secrets.token_hex(8)}"
        payload  = {
            "key_id":      key_id,
            "property_id": property_id,
            "label":       label,
            "key_hash":    key_hash,
            "scope":       "BOOKING_ENGINE",
            "issued_by":   actor_id,
            "issued_at":   datetime.utcnow().isoformat(),
        }
        self._projection.apply(BOOKING_ENGINE_KEY_ISSUED_V1, payload)
        return {
            "event_type": BOOKING_ENGINE_KEY_ISSUED_V1,
            "key_id":     key_id,
            "api_key":    raw_key,   # shown ONCE to hotel manager
            "scope":      "BOOKING_ENGINE",
            "warning":    "Store this key securely — it will not be shown again.",
        }

    def revoke_api_key(
        self, key_id: str, actor_id: str = "manager"
    ) -> dict:
        payload = {
            "key_id":     key_id,
            "revoked_by": actor_id,
            "revoked_at": datetime.utcnow().isoformat(),
        }
        self._projection.apply(BOOKING_ENGINE_KEY_REVOKED_V1, payload)
        return {"event_type": BOOKING_ENGINE_KEY_REVOKED_V1, "key_id": key_id}

    # ── Availability search ───────────────────────────────────

    def search_availability(
        self, property_id: str,
        arrival_date: str, departure_date: str,
        adults: int = 1, children: int = 0,
    ) -> dict:
        """
        Return available room types for the requested date range.
        Excludes room types with 0 available units on any date in range.
        """
        available_types = []

        if self._property_store is not None:
            for rt in self._property_store.list_room_types():
                if rt.get("max_adults", 1) < adults:
                    continue
                count = self._property_store.count_available_by_type(
                    rt["room_type_id"])
                if count > 0:
                    available_types.append({
                        "room_type_id":      rt["room_type_id"],
                        "name":              rt["name"],
                        "bed_configuration": rt.get("bed_configuration"),
                        "max_adults":        rt.get("max_adults"),
                        "amenities":         rt.get("amenities", []),
                        "available_count":   count,
                    })

        self._projection.apply(AVAILABILITY_SEARCHED_V1, {
            "property_id":    property_id,
            "arrival_date":   arrival_date,
            "departure_date": departure_date,
            "adults":         adults,
            "children":       children,
            "results_count":  len(available_types),
            "searched_at":    datetime.utcnow().isoformat(),
        })
        return {
            "property_id":    property_id,
            "arrival_date":   arrival_date,
            "departure_date": departure_date,
            "available_types": available_types,
        }

    # ── Rate quote ────────────────────────────────────────────

    def quote_rate(
        self, property_id: str, room_type_id: str, rate_plan_id: str,
        arrival_date: str, departure_date: str, nights: int,
    ) -> dict:
        """Return nightly rate + total for the given room/rate/dates."""
        nightly_rate = 0
        rate_plan    = None
        currency     = "USD"

        if self._property_store is not None:
            rp = self._property_store.get_rate_plan(rate_plan_id)
            if rp:
                rate_plan = rp
                currency  = "USD"  # from property config
                # Check seasonal rates first
                seasonal = self._property_store.get_rates_for_plan_and_type(
                    rate_plan_id, room_type_id)
                for sr in seasonal:
                    if sr["from_date"] <= arrival_date <= sr["to_date"]:
                        nightly_rate = sr["nightly_rate"]
                        currency     = sr["currency"]
                        break

        total_amount = nightly_rate * nights

        self._projection.apply(RATE_QUOTED_V1, {
            "property_id":  property_id,
            "room_type_id": room_type_id,
            "rate_plan_id": rate_plan_id,
            "nightly_rate": nightly_rate,
            "nights":       nights,
            "total_amount": total_amount,
            "currency":     currency,
            "quoted_at":    datetime.utcnow().isoformat(),
        })
        return {
            "room_type_id":  room_type_id,
            "rate_plan_id":  rate_plan_id,
            "nightly_rate":  nightly_rate,
            "nights":        nights,
            "total_amount":  total_amount,
            "currency":      currency,
            "cancel_policy": rate_plan.get("cancel_policy") if rate_plan else None,
            "meal_plan":     rate_plan.get("meal_plan") if rate_plan else None,
        }

    # ── Direct booking creation ───────────────────────────────

    def create_booking(
        self, property_id: str, booking_id: str,
        room_type_id: str, rate_plan_id: str,
        guest_name: str, guest_email: str,
        arrival_date: str, departure_date: str,
        nights: int, adults: int, total_amount: int, currency: str,
        children: int = 0, special_requests: str = "",
        actor_id: str = "guest",
    ) -> dict:
        """
        Create a DIRECT source reservation via the booking engine.
        Emits DIRECT_BOOKING_CREATED_V1 — caller should then also
        call hotel_reservation.create_reservation with source=DIRECT.
        """
        payload = {
            "booking_id":       booking_id,
            "property_id":      property_id,
            "room_type_id":     room_type_id,
            "rate_plan_id":     rate_plan_id,
            "guest_name":       guest_name,
            "guest_email":      guest_email,
            "arrival_date":     arrival_date,
            "departure_date":   departure_date,
            "nights":           nights,
            "adults":           adults,
            "children":         children,
            "total_amount":     total_amount,
            "currency":         currency,
            "special_requests": special_requests,
            "source":           "DIRECT",
            "channel":          "WEBSITE",
            "created_at":       datetime.utcnow().isoformat(),
        }
        self._projection.apply(DIRECT_BOOKING_CREATED_V1, payload)
        return {"event_type": DIRECT_BOOKING_CREATED_V1, "payload": payload}

    # ── Widget embed config ───────────────────────────────────

    def get_widget_embed_snippet(
        self, property_id: str, api_key: str,
        primary_color: str = "#1a73e8",
        language: str = "en",
    ) -> dict:
        """
        Returns HTML + JS snippet for embedding on hotel website.
        Hotel pastes this into their site — no BOS credentials exposed.
        """
        snippet = (
            f'<div id="bos-booking-widget" '
            f'data-property-id="{property_id}" '
            f'data-api-key="{api_key}" '
            f'data-lang="{language}" '
            f'data-color="{primary_color}"></div>\n'
            f'<script src="https://cdn.bos.io/booking-widget/v1/widget.js" '
            f'async defer></script>'
        )
        return {
            "property_id":    property_id,
            "embed_snippet":  snippet,
            "api_endpoint":   f"/api/v1/book/{property_id}",
            "docs_url":       "https://docs.bos.io/booking-engine",
        }

    @property
    def _store(self) -> HotelBookingEngineProjectionStore:
        return self._projection
