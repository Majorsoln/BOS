"""
BOS Hotel Reservation Engine — Request Commands
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from engines.hotel_reservation.events import (
    VALID_SOURCES, VALID_CHANNELS, VALID_CANCEL_REASONS, VALID_PAYMENT_METHODS,
)

HOTEL_RESERVATION_CREATE_REQUEST  = "hotel.reservation.create.request"
HOTEL_RESERVATION_CONFIRM_REQUEST = "hotel.reservation.confirm.request"
HOTEL_RESERVATION_MODIFY_REQUEST  = "hotel.reservation.modify.request"
HOTEL_RESERVATION_CANCEL_REQUEST  = "hotel.reservation.cancel.request"
HOTEL_RESERVATION_NO_SHOW_REQUEST = "hotel.reservation.no_show.request"
HOTEL_GUEST_CHECK_IN_REQUEST      = "hotel.guest.check_in.request"
HOTEL_GUEST_CHECK_OUT_REQUEST     = "hotel.guest.check_out.request"
HOTEL_STAY_EXTEND_REQUEST         = "hotel.stay.extend.request"
HOTEL_EARLY_DEPARTURE_REQUEST     = "hotel.early_departure.request"
HOTEL_ROOM_MOVE_REQUEST           = "hotel.room.move.request"

HOTEL_RESERVATION_COMMAND_TYPES = frozenset({
    HOTEL_RESERVATION_CREATE_REQUEST, HOTEL_RESERVATION_CONFIRM_REQUEST,
    HOTEL_RESERVATION_MODIFY_REQUEST, HOTEL_RESERVATION_CANCEL_REQUEST,
    HOTEL_RESERVATION_NO_SHOW_REQUEST, HOTEL_GUEST_CHECK_IN_REQUEST,
    HOTEL_GUEST_CHECK_OUT_REQUEST, HOTEL_STAY_EXTEND_REQUEST,
    HOTEL_EARLY_DEPARTURE_REQUEST, HOTEL_ROOM_MOVE_REQUEST,
})


class _Cmd:
    __slots__ = ("command_type","payload","business_id","branch_id","actor_id","issued_at")
    def __init__(self,command_type,payload,*,business_id,branch_id,actor_id,issued_at):
        self.command_type=command_type; self.payload=payload
        self.business_id=business_id;  self.branch_id=branch_id
        self.actor_id=actor_id;        self.issued_at=issued_at


@dataclass(frozen=True)
class CreateReservationRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    reservation_id: str
    property_id:    str
    room_type_id:   str
    rate_plan_id:   str
    source:         str
    adults:         int
    arrival_date:   str
    departure_date: str
    nights:         int
    nightly_rate:   int
    total_amount:   int
    currency:       str
    actor_id:       str
    issued_at:      datetime
    channel:        str = "FRONT_DESK"
    guest_id:       Optional[str] = None
    guest_name:     str = ""
    children:       int = 0
    deposit_due:    int = 0
    special_requests: str = ""
    external_id:    Optional[str] = None

    def __post_init__(self):
        if not self.reservation_id: raise ValueError("reservation_id must be non-empty.")
        if not self.property_id:    raise ValueError("property_id must be non-empty.")
        if not self.room_type_id:   raise ValueError("room_type_id must be non-empty.")
        if not self.rate_plan_id:   raise ValueError("rate_plan_id must be non-empty.")
        if self.source not in VALID_SOURCES:
            raise ValueError(f"source must be one of {sorted(VALID_SOURCES)}.")
        if self.channel not in VALID_CHANNELS:
            raise ValueError(f"channel must be one of {sorted(VALID_CHANNELS)}.")
        if not isinstance(self.adults, int) or self.adults < 1:
            raise ValueError("adults must be >= 1.")
        if not isinstance(self.nights, int) or self.nights < 1:
            raise ValueError("nights must be >= 1.")
        if not isinstance(self.nightly_rate, int) or self.nightly_rate <= 0:
            raise ValueError("nightly_rate must be positive integer.")
        if not isinstance(self.total_amount, int) or self.total_amount <= 0:
            raise ValueError("total_amount must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")
        if not self.arrival_date or not self.departure_date:
            raise ValueError("arrival_date and departure_date are required.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_RESERVATION_CREATE_REQUEST, {
            "reservation_id": self.reservation_id,
            "external_id": self.external_id,
            "source": self.source, "channel": self.channel,
            "property_id": self.property_id,
            "room_type_id": self.room_type_id, "rate_plan_id": self.rate_plan_id,
            "guest_id": self.guest_id, "guest_name": self.guest_name,
            "adults": self.adults, "children": self.children,
            "arrival_date": self.arrival_date, "departure_date": self.departure_date,
            "nights": self.nights, "nightly_rate": self.nightly_rate,
            "total_amount": self.total_amount, "currency": self.currency,
            "deposit_due": self.deposit_due,
            "special_requests": self.special_requests,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class ConfirmReservationRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    reservation_id: str
    actor_id:       str
    issued_at:      datetime
    deposit_paid:   int = 0
    payment_ref:    str = ""

    def __post_init__(self):
        if not self.reservation_id: raise ValueError("reservation_id must be non-empty.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_RESERVATION_CONFIRM_REQUEST, {
            "reservation_id": self.reservation_id,
            "deposit_paid": self.deposit_paid, "payment_ref": self.payment_ref,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class CancelReservationRequest:
    business_id:           uuid.UUID
    branch_id:             uuid.UUID
    reservation_id:        str
    reason:                str
    actor_id:              str
    issued_at:             datetime
    cancellation_charge:   int = 0
    refund_amount:         int = 0

    def __post_init__(self):
        if not self.reservation_id: raise ValueError("reservation_id must be non-empty.")
        if self.reason not in VALID_CANCEL_REASONS:
            raise ValueError(f"reason must be one of {sorted(VALID_CANCEL_REASONS)}.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_RESERVATION_CANCEL_REQUEST, {
            "reservation_id": self.reservation_id, "reason": self.reason,
            "cancellation_charge": self.cancellation_charge,
            "refund_amount": self.refund_amount,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class CheckInRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    reservation_id: str
    room_id:        str
    folio_id:       str
    actor_id:       str
    issued_at:      datetime
    room_number:    str = ""
    key_issued:     bool = True

    def __post_init__(self):
        if not self.reservation_id: raise ValueError("reservation_id must be non-empty.")
        if not self.room_id:        raise ValueError("room_id must be non-empty.")
        if not self.folio_id:       raise ValueError("folio_id must be non-empty.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_GUEST_CHECK_IN_REQUEST, {
            "reservation_id": self.reservation_id, "room_id": self.room_id,
            "room_number": self.room_number, "folio_id": self.folio_id,
            "key_issued": self.key_issued,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class CheckOutRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    reservation_id: str
    room_id:        str
    folio_id:       str
    actor_id:       str
    issued_at:      datetime
    folio_total:    int = 0
    payment_method: str = "CARD"

    def __post_init__(self):
        if not self.reservation_id: raise ValueError("reservation_id must be non-empty.")
        if not self.room_id:        raise ValueError("room_id must be non-empty.")
        if not self.folio_id:       raise ValueError("folio_id must be non-empty.")
        if self.payment_method not in VALID_PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {sorted(VALID_PAYMENT_METHODS)}.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_GUEST_CHECK_OUT_REQUEST, {
            "reservation_id": self.reservation_id, "room_id": self.room_id,
            "folio_id": self.folio_id, "folio_total": self.folio_total,
            "payment_method": self.payment_method,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class NoShowRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    reservation_id: str
    actor_id:       str
    issued_at:      datetime
    no_show_charge: int = 0

    def __post_init__(self):
        if not self.reservation_id: raise ValueError("reservation_id must be non-empty.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_RESERVATION_NO_SHOW_REQUEST, {
            "reservation_id": self.reservation_id,
            "no_show_charge": self.no_show_charge,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class ExtendStayRequest:
    business_id:        uuid.UUID
    branch_id:          uuid.UUID
    reservation_id:     str
    old_departure_date: str
    new_departure_date: str
    extra_nights:       int
    actor_id:           str
    issued_at:          datetime
    extra_amount:       int = 0

    def __post_init__(self):
        if not self.reservation_id: raise ValueError("reservation_id must be non-empty.")
        if not isinstance(self.extra_nights, int) or self.extra_nights < 1:
            raise ValueError("extra_nights must be >= 1.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_STAY_EXTEND_REQUEST, {
            "reservation_id": self.reservation_id,
            "old_departure_date": self.old_departure_date,
            "new_departure_date": self.new_departure_date,
            "extra_nights": self.extra_nights, "extra_amount": self.extra_amount,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class MoveRoomRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    reservation_id: str
    old_room_id:    str
    new_room_id:    str
    actor_id:       str
    issued_at:      datetime
    new_room_number: str = ""
    reason:          str = ""

    def __post_init__(self):
        if not self.reservation_id: raise ValueError("reservation_id must be non-empty.")
        if not self.old_room_id:    raise ValueError("old_room_id must be non-empty.")
        if not self.new_room_id:    raise ValueError("new_room_id must be non-empty.")
        if self.old_room_id == self.new_room_id:
            raise ValueError("new_room_id must differ from old_room_id.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_ROOM_MOVE_REQUEST, {
            "reservation_id": self.reservation_id,
            "old_room_id": self.old_room_id, "new_room_id": self.new_room_id,
            "new_room_number": self.new_room_number, "reason": self.reason,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)
