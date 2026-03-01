"""
BOS Hotel Property Engine — Event Types and Payload Builders
=============================================================
Engine: hotel_property
Scope:  Property setup, room types, rooms, rate plans, meal plans.
        This is the configuration layer — all other hotel engines
        reference room_type_id, room_id, rate_plan_id defined here.
"""

from __future__ import annotations

# ── Event Type Constants ──────────────────────────────────────

PROPERTY_CONFIGURED_V1       = "hotel.property.configured.v1"
ROOM_TYPE_DEFINED_V1         = "hotel.room_type.defined.v1"
ROOM_TYPE_UPDATED_V1         = "hotel.room_type.updated.v1"
ROOM_CREATED_V1              = "hotel.room.created.v1"
ROOM_STATUS_CHANGED_V1       = "hotel.room.status_changed.v1"
ROOM_SET_OUT_OF_ORDER_V1     = "hotel.room.out_of_order.v1"
ROOM_RETURNED_TO_SERVICE_V1  = "hotel.room.returned_to_service.v1"
RATE_PLAN_CREATED_V1         = "hotel.rate_plan.created.v1"
RATE_PLAN_UPDATED_V1         = "hotel.rate_plan.updated.v1"
RATE_PLAN_DEACTIVATED_V1     = "hotel.rate_plan.deactivated.v1"
SEASONAL_RATE_SET_V1         = "hotel.seasonal_rate.set.v1"

HOTEL_PROPERTY_EVENT_TYPES = (
    PROPERTY_CONFIGURED_V1,
    ROOM_TYPE_DEFINED_V1,
    ROOM_TYPE_UPDATED_V1,
    ROOM_CREATED_V1,
    ROOM_STATUS_CHANGED_V1,
    ROOM_SET_OUT_OF_ORDER_V1,
    ROOM_RETURNED_TO_SERVICE_V1,
    RATE_PLAN_CREATED_V1,
    RATE_PLAN_UPDATED_V1,
    RATE_PLAN_DEACTIVATED_V1,
    SEASONAL_RATE_SET_V1,
)

COMMAND_TO_EVENT_TYPE = {
    "hotel.property.configure.request":     PROPERTY_CONFIGURED_V1,
    "hotel.room_type.define.request":       ROOM_TYPE_DEFINED_V1,
    "hotel.room_type.update.request":       ROOM_TYPE_UPDATED_V1,
    "hotel.room.create.request":            ROOM_CREATED_V1,
    "hotel.room.change_status.request":     ROOM_STATUS_CHANGED_V1,
    "hotel.room.set_out_of_order.request":  ROOM_SET_OUT_OF_ORDER_V1,
    "hotel.room.return_to_service.request": ROOM_RETURNED_TO_SERVICE_V1,
    "hotel.rate_plan.create.request":       RATE_PLAN_CREATED_V1,
    "hotel.rate_plan.update.request":       RATE_PLAN_UPDATED_V1,
    "hotel.rate_plan.deactivate.request":   RATE_PLAN_DEACTIVATED_V1,
    "hotel.seasonal_rate.set.request":      SEASONAL_RATE_SET_V1,
}

# ── Valid Vocabulary ──────────────────────────────────────────

VALID_ROOM_STATUSES = frozenset({
    "AVAILABLE", "OCCUPIED", "CLEANING", "INSPECTED",
    "MAINTENANCE", "BLOCKED", "OUT_OF_ORDER",
})
VALID_BED_CONFIGS = frozenset({
    "SINGLE", "TWIN", "DOUBLE", "QUEEN", "KING",
    "TWIN_DOUBLE", "TRIPLE", "DORMITORY",
})
VALID_RATE_CODES = frozenset({
    "BAR", "NON_REF", "BB", "HB", "FB", "AI",
    "CORP", "GOV", "PKG", "PROMO", "GROUP",
})
VALID_MEAL_PLANS    = frozenset({"RO", "BB", "HB", "FB", "AI"})
VALID_CANCEL_POLICIES = frozenset({"FREE_CANCEL", "NON_REFUNDABLE", "PARTIAL_REFUND"})

# ── Payload Builders ──────────────────────────────────────────

def build_property_configured_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "property_id":       p["property_id"],
        "property_name":     p["property_name"],
        "property_type":     p.get("property_type", "HOTEL"),
        "star_rating":       p.get("star_rating", 0),
        "address":           p.get("address", {}),
        "timezone":          p.get("timezone", "UTC"),
        "default_currency":  p.get("default_currency", "USD"),
        "check_in_time":     p.get("check_in_time", "14:00"),
        "check_out_time":    p.get("check_out_time", "11:00"),
        "configured_at":     cmd.issued_at,
    }


def build_room_type_defined_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "room_type_id":      p["room_type_id"],
        "name":              p["name"],
        "description":       p.get("description", ""),
        "bed_configuration": p["bed_configuration"],
        "max_adults":        p["max_adults"],
        "max_children":      p.get("max_children", 0),
        "amenities":         list(p.get("amenities", [])),
        "total_rooms":       p.get("total_rooms", 0),
        "defined_at":        cmd.issued_at,
    }


def build_room_type_updated_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "room_type_id": p["room_type_id"],
        "updates":      p.get("updates", {}),
        "updated_at":   cmd.issued_at,
    }


def build_room_created_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "room_id":       p["room_id"],
        "room_number":   p["room_number"],
        "room_type_id":  p["room_type_id"],
        "floor":         p.get("floor", 1),
        "building":      p.get("building", "MAIN"),
        "notes":         p.get("notes", ""),
        "status":        "AVAILABLE",
        "created_at":    cmd.issued_at,
    }


def build_room_status_changed_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "room_id":    p["room_id"],
        "old_status": p.get("old_status", ""),
        "new_status": p["new_status"],
        "reason":     p.get("reason", ""),
        "changed_by": cmd.actor_id,
        "changed_at": cmd.issued_at,
    }


def build_room_out_of_order_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "room_id":    p["room_id"],
        "reason":     p["reason"],
        "from_date":  p["from_date"],
        "to_date":    p.get("to_date"),
        "set_by":     cmd.actor_id,
        "set_at":     cmd.issued_at,
    }


def build_room_returned_to_service_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "room_id":      p["room_id"],
        "returned_by":  cmd.actor_id,
        "returned_at":  cmd.issued_at,
    }


def build_rate_plan_created_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "rate_plan_id":         p["rate_plan_id"],
        "name":                 p["name"],
        "code":                 p["code"],
        "meal_plan":            p.get("meal_plan", "RO"),
        "cancel_policy":        p.get("cancel_policy", "FREE_CANCEL"),
        "deposit_required":     p.get("deposit_required", False),
        "deposit_percent":      p.get("deposit_percent", 0),
        "min_los":              p.get("min_los", 1),
        "is_derived":           p.get("is_derived", False),
        "derived_from_plan_id": p.get("derived_from_plan_id"),
        "derived_discount_bps": p.get("derived_discount_bps", 0),
        "is_active":            True,
        "created_at":           cmd.issued_at,
    }


def build_rate_plan_updated_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "rate_plan_id": p["rate_plan_id"],
        "updates":      p.get("updates", {}),
        "updated_at":   cmd.issued_at,
    }


def build_rate_plan_deactivated_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "rate_plan_id":   p["rate_plan_id"],
        "reason":         p.get("reason", ""),
        "deactivated_at": cmd.issued_at,
    }


def build_seasonal_rate_set_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "seasonal_rate_id": p["seasonal_rate_id"],
        "rate_plan_id":     p["rate_plan_id"],
        "room_type_id":     p["room_type_id"],
        "from_date":        p["from_date"],
        "to_date":          p["to_date"],
        "nightly_rate":     p["nightly_rate"],
        "currency":         p["currency"],
        "set_at":           cmd.issued_at,
    }


PAYLOAD_BUILDERS = {
    PROPERTY_CONFIGURED_V1:      build_property_configured_payload,
    ROOM_TYPE_DEFINED_V1:        build_room_type_defined_payload,
    ROOM_TYPE_UPDATED_V1:        build_room_type_updated_payload,
    ROOM_CREATED_V1:             build_room_created_payload,
    ROOM_STATUS_CHANGED_V1:      build_room_status_changed_payload,
    ROOM_SET_OUT_OF_ORDER_V1:    build_room_out_of_order_payload,
    ROOM_RETURNED_TO_SERVICE_V1: build_room_returned_to_service_payload,
    RATE_PLAN_CREATED_V1:        build_rate_plan_created_payload,
    RATE_PLAN_UPDATED_V1:        build_rate_plan_updated_payload,
    RATE_PLAN_DEACTIVATED_V1:    build_rate_plan_deactivated_payload,
    SEASONAL_RATE_SET_V1:        build_seasonal_rate_set_payload,
}
