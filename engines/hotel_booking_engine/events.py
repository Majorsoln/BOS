"""
BOS Hotel Booking Engine — Event Types
=======================================
Engine: hotel_booking_engine
Scope:  Direct booking channel. Hotels embed a booking widget or
        call the REST API to accept reservations via their website.
        Each hotel generates a scoped API key (BOOKING_ENGINE scope)
        from the BOS dashboard.
        Availability search → Rate quote → Reservation → Confirmation.
"""
from __future__ import annotations

BOOKING_ENGINE_KEY_ISSUED_V1    = "hotel.booking_engine.key_issued.v1"
BOOKING_ENGINE_KEY_REVOKED_V1   = "hotel.booking_engine.key_revoked.v1"
AVAILABILITY_SEARCHED_V1        = "hotel.booking_engine.availability_searched.v1"
RATE_QUOTED_V1                  = "hotel.booking_engine.rate_quoted.v1"
DIRECT_BOOKING_CREATED_V1       = "hotel.booking_engine.booking_created.v1"
DIRECT_BOOKING_CONFIRMED_V1     = "hotel.booking_engine.booking_confirmed.v1"
DIRECT_BOOKING_CANCELLED_V1     = "hotel.booking_engine.booking_cancelled.v1"
BOOKING_ENGINE_SETTINGS_UPDATED_V1 = "hotel.booking_engine.settings_updated.v1"

HOTEL_BOOKING_ENGINE_EVENT_TYPES = (
    BOOKING_ENGINE_KEY_ISSUED_V1, BOOKING_ENGINE_KEY_REVOKED_V1,
    AVAILABILITY_SEARCHED_V1, RATE_QUOTED_V1,
    DIRECT_BOOKING_CREATED_V1, DIRECT_BOOKING_CONFIRMED_V1,
    DIRECT_BOOKING_CANCELLED_V1, BOOKING_ENGINE_SETTINGS_UPDATED_V1,
)
