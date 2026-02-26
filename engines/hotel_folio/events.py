"""
BOS Hotel Folio Engine — Event Types and Payload Builders
=========================================================
Engine: hotel_folio
Scope:  Guest running tab. Aggregates all charges (room nights,
        restaurant, room service, minibar, laundry, misc) from the
        moment of check-in to final settlement at check-out.
        Night Audit auto-posts room-night charges for every open folio.
"""
from __future__ import annotations

FOLIO_OPENED_V1             = "hotel.folio.opened.v1"
FOLIO_CHARGE_POSTED_V1      = "hotel.folio.charge_posted.v1"
FOLIO_PAYMENT_RECEIVED_V1   = "hotel.folio.payment_received.v1"
FOLIO_CREDIT_APPLIED_V1     = "hotel.folio.credit_applied.v1"
FOLIO_ADJUSTED_V1           = "hotel.folio.adjusted.v1"
FOLIO_TRANSFERRED_V1        = "hotel.folio.transferred.v1"
FOLIO_SPLIT_V1              = "hotel.folio.split.v1"
FOLIO_SETTLED_V1            = "hotel.folio.settled.v1"
NIGHT_AUDIT_RUN_V1          = "hotel.night_audit.run.v1"
ROOM_NIGHT_CHARGE_POSTED_V1 = "hotel.room_night.charge_posted.v1"

HOTEL_FOLIO_EVENT_TYPES = (
    FOLIO_OPENED_V1, FOLIO_CHARGE_POSTED_V1, FOLIO_PAYMENT_RECEIVED_V1,
    FOLIO_CREDIT_APPLIED_V1, FOLIO_ADJUSTED_V1, FOLIO_TRANSFERRED_V1,
    FOLIO_SPLIT_V1, FOLIO_SETTLED_V1,
    NIGHT_AUDIT_RUN_V1, ROOM_NIGHT_CHARGE_POSTED_V1,
)

COMMAND_TO_EVENT_TYPE = {
    "hotel.folio.open.request":             FOLIO_OPENED_V1,
    "hotel.folio.post_charge.request":      FOLIO_CHARGE_POSTED_V1,
    "hotel.folio.receive_payment.request":  FOLIO_PAYMENT_RECEIVED_V1,
    "hotel.folio.apply_credit.request":     FOLIO_CREDIT_APPLIED_V1,
    "hotel.folio.adjust.request":           FOLIO_ADJUSTED_V1,
    "hotel.folio.transfer.request":         FOLIO_TRANSFERRED_V1,
    "hotel.folio.split.request":            FOLIO_SPLIT_V1,
    "hotel.folio.settle.request":           FOLIO_SETTLED_V1,
    "hotel.night_audit.run.request":        NIGHT_AUDIT_RUN_V1,
    "hotel.room_night.post_charge.request": ROOM_NIGHT_CHARGE_POSTED_V1,
}

VALID_CHARGE_TYPES = frozenset({
    "ROOM_NIGHT", "RESTAURANT", "ROOM_SERVICE", "MINIBAR",
    "LAUNDRY", "SPA", "PARKING", "TELEPHONE",
    "DEPOSIT", "CANCELLATION_FEE",
    "EARLY_CHECKIN_FEE", "LATE_CHECKOUT_FEE", "MISCELLANEOUS",
})
VALID_PAYMENT_METHODS = frozenset({
    "CASH", "CARD", "MOBILE", "BANK_TRANSFER", "CREDIT", "SPLIT",
})
VALID_ADJUSTMENT_TYPES = frozenset({"CREDIT", "DEBIT"})


def build_folio_opened_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "folio_id":       p["folio_id"],
        "reservation_id": p["reservation_id"],
        "guest_id":       p.get("guest_id"),
        "guest_name":     p.get("guest_name", ""),
        "room_id":        p["room_id"],
        "currency":       p["currency"],
        "balance":        0,
        "opened_by":      cmd.actor_id,
        "opened_at":      cmd.issued_at,
    }


def build_charge_posted_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "folio_id":     p["folio_id"],
        "charge_id":    p["charge_id"],
        "charge_type":  p["charge_type"],
        "description":  p.get("description", ""),
        "amount":       p["amount"],
        "currency":     p["currency"],
        "source_ref":   p.get("source_ref", ""),
        "posted_by":    cmd.actor_id,
        "posted_at":    cmd.issued_at,
    }


def build_payment_received_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "folio_id":       p["folio_id"],
        "payment_id":     p["payment_id"],
        "amount":         p["amount"],
        "currency":       p["currency"],
        "payment_method": p["payment_method"],
        "reference":      p.get("reference", ""),
        "received_by":    cmd.actor_id,
        "received_at":    cmd.issued_at,
    }


def build_credit_applied_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "folio_id":     p["folio_id"],
        "credit_id":    p["credit_id"],
        "amount":       p["amount"],
        "currency":     p["currency"],
        "source":       p.get("source", "WALLET"),
        "applied_by":   cmd.actor_id,
        "applied_at":   cmd.issued_at,
    }


def build_folio_adjusted_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "folio_id":        p["folio_id"],
        "adjustment_id":   p["adjustment_id"],
        "adjustment_type": p["adjustment_type"],
        "amount":          p["amount"],
        "reason":          p.get("reason", ""),
        "adjusted_by":     cmd.actor_id,
        "adjusted_at":     cmd.issued_at,
    }


def build_folio_transferred_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "from_folio_id": p["from_folio_id"],
        "to_folio_id":   p["to_folio_id"],
        "charge_ids":    list(p.get("charge_ids", [])),
        "amount":        p["amount"],
        "reason":        p.get("reason", ""),
        "transferred_by": cmd.actor_id,
        "transferred_at": cmd.issued_at,
    }


def build_folio_split_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "folio_id":      p["folio_id"],
        "split_id":      p["split_id"],
        "new_folio_ids": list(p.get("new_folio_ids", [])),
        "split_type":    p.get("split_type", "BY_GUEST"),
        "splits":        list(p.get("splits", [])),
        "split_by":      cmd.actor_id,
        "split_at":      cmd.issued_at,
    }


def build_folio_settled_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "folio_id":       p["folio_id"],
        "total_charges":  p["total_charges"],
        "total_payments": p["total_payments"],
        "balance_due":    p["balance_due"],
        "payment_method": p.get("payment_method", "CARD"),
        "currency":       p["currency"],
        "settled_by":     cmd.actor_id,
        "settled_at":     cmd.issued_at,
    }


def build_night_audit_run_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "audit_id":         p["audit_id"],
        "business_date":    p["business_date"],
        "folios_processed": p.get("folios_processed", 0),
        "total_room_revenue": p.get("total_room_revenue", 0),
        "run_by":           cmd.actor_id,
        "run_at":           cmd.issued_at,
    }


def build_room_night_charge_posted_payload(cmd) -> dict:
    p = cmd.payload
    return {
        "folio_id":      p["folio_id"],
        "charge_id":     p["charge_id"],
        "reservation_id": p["reservation_id"],
        "room_id":       p["room_id"],
        "business_date": p["business_date"],
        "rate_plan_id":  p["rate_plan_id"],
        "nightly_rate":  p["nightly_rate"],
        "currency":      p["currency"],
        "posted_at":     cmd.issued_at,
    }


PAYLOAD_BUILDERS = {
    FOLIO_OPENED_V1:             build_folio_opened_payload,
    FOLIO_CHARGE_POSTED_V1:      build_charge_posted_payload,
    FOLIO_PAYMENT_RECEIVED_V1:   build_payment_received_payload,
    FOLIO_CREDIT_APPLIED_V1:     build_credit_applied_payload,
    FOLIO_ADJUSTED_V1:           build_folio_adjusted_payload,
    FOLIO_TRANSFERRED_V1:        build_folio_transferred_payload,
    FOLIO_SPLIT_V1:              build_folio_split_payload,
    FOLIO_SETTLED_V1:            build_folio_settled_payload,
    NIGHT_AUDIT_RUN_V1:          build_night_audit_run_payload,
    ROOM_NIGHT_CHARGE_POSTED_V1: build_room_night_charge_posted_payload,
}
