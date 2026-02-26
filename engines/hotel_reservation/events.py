"""
BOS Hotel Reservation Engine — Event Types and Payload Builders
================================================================
Engine: hotel_reservation
Scope:  Full booking lifecycle — create, confirm, modify, cancel,
        check-in, check-out, no-show, room moves, stay extensions.
        Sources: DIRECT, WALK_IN, OTA, CORPORATE, GROUP.
"""

from __future__ import annotations

RESERVATION_CREATED_V1    = "hotel.reservation.created.v1"
RESERVATION_CONFIRMED_V1  = "hotel.reservation.confirmed.v1"
RESERVATION_MODIFIED_V1   = "hotel.reservation.modified.v1"
RESERVATION_CANCELLED_V1  = "hotel.reservation.cancelled.v1"
RESERVATION_NO_SHOW_V1    = "hotel.reservation.no_show.v1"
GUEST_CHECKED_IN_V1       = "hotel.guest.checked_in.v1"
GUEST_CHECKED_OUT_V1      = "hotel.guest.checked_out.v1"
STAY_EXTENDED_V1          = "hotel.stay.extended.v1"
EARLY_DEPARTURE_V1        = "hotel.early_departure.v1"
ROOM_MOVED_V1             = "hotel.room.moved.v1"

HOTEL_RESERVATION_EVENT_TYPES = (
    RESERVATION_CREATED_V1, RESERVATION_CONFIRMED_V1,
    RESERVATION_MODIFIED_V1, RESERVATION_CANCELLED_V1,
    RESERVATION_NO_SHOW_V1, GUEST_CHECKED_IN_V1,
    GUEST_CHECKED_OUT_V1, STAY_EXTENDED_V1,
    EARLY_DEPARTURE_V1, ROOM_MOVED_V1,
)

COMMAND_TO_EVENT_TYPE = {
    "hotel.reservation.create.request":  RESERVATION_CREATED_V1,
    "hotel.reservation.confirm.request": RESERVATION_CONFIRMED_V1,
    "hotel.reservation.modify.request":  RESERVATION_MODIFIED_V1,
    "hotel.reservation.cancel.request":  RESERVATION_CANCELLED_V1,
    "hotel.reservation.no_show.request": RESERVATION_NO_SHOW_V1,
    "hotel.guest.check_in.request":      GUEST_CHECKED_IN_V1,
    "hotel.guest.check_out.request":     GUEST_CHECKED_OUT_V1,
    "hotel.stay.extend.request":         STAY_EXTENDED_V1,
    "hotel.early_departure.request":     EARLY_DEPARTURE_V1,
    "hotel.room.move.request":           ROOM_MOVED_V1,
}

VALID_SOURCES = frozenset({
    "DIRECT", "WALK_IN", "OTA", "CORPORATE", "GROUP",
})
VALID_CHANNELS = frozenset({
    "WEBSITE", "PHONE", "FRONT_DESK", "OTA", "CORPORATE_PORTAL",
    "BOOKING_COM", "EXPEDIA", "AGODA", "AIRBNB", "HOTELS_COM",
    "TRIP_COM", "OTHER_OTA",
})
VALID_CANCEL_REASONS = frozenset({
    "GUEST_REQUEST", "NO_PAYMENT", "DUPLICATE", "OVERBOOKING",
    "FORCE_MAJEURE", "PROPERTY_CLOSURE", "SYSTEM_CANCEL",
})
VALID_PAYMENT_METHODS = frozenset({
    "CASH", "CARD", "MOBILE", "BANK_TRANSFER", "CREDIT", "SPLIT",
})


def build_reservation_created_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "reservation_id":   p["reservation_id"],
        "external_id":      p.get("external_id"),
        "source":           p["source"],
        "channel":          p.get("channel", "FRONT_DESK"),
        "property_id":      p["property_id"],
        "room_type_id":     p["room_type_id"],
        "rate_plan_id":     p["rate_plan_id"],
        "guest_id":         p.get("guest_id"),
        "guest_name":       p.get("guest_name", ""),
        "adults":           p["adults"],
        "children":         p.get("children", 0),
        "arrival_date":     p["arrival_date"],
        "departure_date":   p["departure_date"],
        "nights":           p["nights"],
        "nightly_rate":     p["nightly_rate"],
        "total_amount":     p["total_amount"],
        "currency":         p["currency"],
        "deposit_due":      p.get("deposit_due", 0),
        "special_requests": p.get("special_requests", ""),
        "status":           "PENDING",
        "created_at":       cmd.issued_at,
    }


def build_reservation_confirmed_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "reservation_id": p["reservation_id"],
        "deposit_paid":   p.get("deposit_paid", 0),
        "payment_ref":    p.get("payment_ref", ""),
        "confirmed_by":   cmd.actor_id,
        "confirmed_at":   cmd.issued_at,
    }


def build_reservation_modified_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "reservation_id": p["reservation_id"],
        "changes":        p.get("changes", {}),
        "modified_by":    cmd.actor_id,
        "modified_at":    cmd.issued_at,
    }


def build_reservation_cancelled_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "reservation_id":      p["reservation_id"],
        "reason":              p["reason"],
        "cancellation_charge": p.get("cancellation_charge", 0),
        "refund_amount":       p.get("refund_amount", 0),
        "cancelled_by":        cmd.actor_id,
        "cancelled_at":        cmd.issued_at,
    }


def build_reservation_no_show_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "reservation_id": p["reservation_id"],
        "no_show_charge": p.get("no_show_charge", 0),
        "recorded_by":    cmd.actor_id,
        "recorded_at":    cmd.issued_at,
    }


def build_guest_checked_in_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "reservation_id": p["reservation_id"],
        "room_id":        p["room_id"],
        "room_number":    p.get("room_number", ""),
        "folio_id":       p["folio_id"],
        "key_issued":     p.get("key_issued", True),
        "checked_in_by":  cmd.actor_id,
        "checked_in_at":  cmd.issued_at,
    }


def build_guest_checked_out_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "reservation_id": p["reservation_id"],
        "room_id":        p["room_id"],
        "folio_id":       p["folio_id"],
        "folio_total":    p.get("folio_total", 0),
        "payment_method": p.get("payment_method", "CARD"),
        "checked_out_by": cmd.actor_id,
        "checked_out_at": cmd.issued_at,
    }


def build_stay_extended_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "reservation_id":     p["reservation_id"],
        "old_departure_date": p["old_departure_date"],
        "new_departure_date": p["new_departure_date"],
        "extra_nights":       p["extra_nights"],
        "extra_amount":       p.get("extra_amount", 0),
        "extended_by":        cmd.actor_id,
        "extended_at":        cmd.issued_at,
    }


def build_early_departure_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "reservation_id":      p["reservation_id"],
        "old_departure_date":  p["old_departure_date"],
        "actual_departure":    p["actual_departure"],
        "early_depart_charge": p.get("early_depart_charge", 0),
        "recorded_by":         cmd.actor_id,
        "recorded_at":         cmd.issued_at,
    }


def build_room_moved_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "reservation_id":  p["reservation_id"],
        "old_room_id":     p["old_room_id"],
        "new_room_id":     p["new_room_id"],
        "new_room_number": p.get("new_room_number", ""),
        "reason":          p.get("reason", ""),
        "moved_by":        cmd.actor_id,
        "moved_at":        cmd.issued_at,
    }


PAYLOAD_BUILDERS = {
    RESERVATION_CREATED_V1:   build_reservation_created_payload,
    RESERVATION_CONFIRMED_V1: build_reservation_confirmed_payload,
    RESERVATION_MODIFIED_V1:  build_reservation_modified_payload,
    RESERVATION_CANCELLED_V1: build_reservation_cancelled_payload,
    RESERVATION_NO_SHOW_V1:   build_reservation_no_show_payload,
    GUEST_CHECKED_IN_V1:      build_guest_checked_in_payload,
    GUEST_CHECKED_OUT_V1:     build_guest_checked_out_payload,
    STAY_EXTENDED_V1:         build_stay_extended_payload,
    EARLY_DEPARTURE_V1:       build_early_departure_payload,
    ROOM_MOVED_V1:            build_room_moved_payload,
}
