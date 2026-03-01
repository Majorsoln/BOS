"""
BOS Hotel Property Engine — Request Commands
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from engines.hotel_property.events import (
    VALID_BED_CONFIGS, VALID_RATE_CODES, VALID_MEAL_PLANS,
    VALID_CANCEL_POLICIES, VALID_ROOM_STATUSES,
)

# ── Command type strings ──────────────────────────────────────

HOTEL_PROPERTY_CONFIGURE_REQUEST    = "hotel.property.configure.request"
HOTEL_ROOM_TYPE_DEFINE_REQUEST      = "hotel.room_type.define.request"
HOTEL_ROOM_TYPE_UPDATE_REQUEST      = "hotel.room_type.update.request"
HOTEL_ROOM_CREATE_REQUEST           = "hotel.room.create.request"
HOTEL_ROOM_CHANGE_STATUS_REQUEST    = "hotel.room.change_status.request"
HOTEL_ROOM_SET_OUT_OF_ORDER_REQUEST = "hotel.room.set_out_of_order.request"
HOTEL_ROOM_RETURN_TO_SERVICE_REQUEST= "hotel.room.return_to_service.request"
HOTEL_RATE_PLAN_CREATE_REQUEST      = "hotel.rate_plan.create.request"
HOTEL_RATE_PLAN_UPDATE_REQUEST      = "hotel.rate_plan.update.request"
HOTEL_RATE_PLAN_DEACTIVATE_REQUEST  = "hotel.rate_plan.deactivate.request"
HOTEL_SEASONAL_RATE_SET_REQUEST     = "hotel.seasonal_rate.set.request"

HOTEL_PROPERTY_COMMAND_TYPES = frozenset({
    HOTEL_PROPERTY_CONFIGURE_REQUEST,
    HOTEL_ROOM_TYPE_DEFINE_REQUEST,
    HOTEL_ROOM_TYPE_UPDATE_REQUEST,
    HOTEL_ROOM_CREATE_REQUEST,
    HOTEL_ROOM_CHANGE_STATUS_REQUEST,
    HOTEL_ROOM_SET_OUT_OF_ORDER_REQUEST,
    HOTEL_ROOM_RETURN_TO_SERVICE_REQUEST,
    HOTEL_RATE_PLAN_CREATE_REQUEST,
    HOTEL_RATE_PLAN_UPDATE_REQUEST,
    HOTEL_RATE_PLAN_DEACTIVATE_REQUEST,
    HOTEL_SEASONAL_RATE_SET_REQUEST,
})


# ── Shared command namespace ──────────────────────────────────

class _Cmd:
    """Minimal command namespace matching BOS Command duck-type."""
    __slots__ = ("command_type", "payload", "business_id",
                 "branch_id", "actor_id", "issued_at")

    def __init__(self, command_type, payload, *,
                 business_id, branch_id, actor_id, issued_at):
        self.command_type = command_type
        self.payload      = payload
        self.business_id  = business_id
        self.branch_id    = branch_id
        self.actor_id     = actor_id
        self.issued_at    = issued_at


# ── Request dataclasses ───────────────────────────────────────

@dataclass(frozen=True)
class ConfigurePropertyRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    property_id:    str
    property_name:  str
    actor_id:       str
    issued_at:      datetime
    property_type:  str = "HOTEL"
    star_rating:    int = 0
    address:        Dict[str, Any] = field(default_factory=dict)
    timezone:       str = "UTC"
    default_currency: str = "USD"
    check_in_time:  str = "14:00"
    check_out_time: str = "11:00"

    def __post_init__(self):
        if not self.property_id:
            raise ValueError("property_id must be non-empty.")
        if not self.property_name:
            raise ValueError("property_name must be non-empty.")
        if not isinstance(self.star_rating, int) or not (0 <= self.star_rating <= 5):
            raise ValueError("star_rating must be integer 0-5.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_PROPERTY_CONFIGURE_REQUEST, {
            "property_id": self.property_id,
            "property_name": self.property_name,
            "property_type": self.property_type,
            "star_rating": self.star_rating,
            "address": self.address,
            "timezone": self.timezone,
            "default_currency": self.default_currency,
            "check_in_time": self.check_in_time,
            "check_out_time": self.check_out_time,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class DefineRoomTypeRequest:
    business_id:     uuid.UUID
    branch_id:       uuid.UUID
    room_type_id:    str
    name:            str
    bed_configuration: str
    max_adults:      int
    actor_id:        str
    issued_at:       datetime
    description:     str = ""
    max_children:    int = 0
    amenities:       Tuple[str, ...] = ()
    total_rooms:     int = 0

    def __post_init__(self):
        if not self.room_type_id:
            raise ValueError("room_type_id must be non-empty.")
        if not self.name:
            raise ValueError("name must be non-empty.")
        if self.bed_configuration not in VALID_BED_CONFIGS:
            raise ValueError(
                f"bed_configuration must be one of {sorted(VALID_BED_CONFIGS)}.")
        if not isinstance(self.max_adults, int) or self.max_adults < 1:
            raise ValueError("max_adults must be >= 1.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_ROOM_TYPE_DEFINE_REQUEST, {
            "room_type_id": self.room_type_id,
            "name": self.name,
            "description": self.description,
            "bed_configuration": self.bed_configuration,
            "max_adults": self.max_adults,
            "max_children": self.max_children,
            "amenities": list(self.amenities),
            "total_rooms": self.total_rooms,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class CreateRoomRequest:
    business_id:  uuid.UUID
    branch_id:    uuid.UUID
    room_id:      str
    room_number:  str
    room_type_id: str
    actor_id:     str
    issued_at:    datetime
    floor:        int = 1
    building:     str = "MAIN"
    notes:        str = ""

    def __post_init__(self):
        if not self.room_id:
            raise ValueError("room_id must be non-empty.")
        if not self.room_number:
            raise ValueError("room_number must be non-empty.")
        if not self.room_type_id:
            raise ValueError("room_type_id must be non-empty.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_ROOM_CREATE_REQUEST, {
            "room_id": self.room_id,
            "room_number": self.room_number,
            "room_type_id": self.room_type_id,
            "floor": self.floor,
            "building": self.building,
            "notes": self.notes,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class ChangeRoomStatusRequest:
    business_id: uuid.UUID
    branch_id:   uuid.UUID
    room_id:     str
    new_status:  str
    actor_id:    str
    issued_at:   datetime
    old_status:  str = ""
    reason:      str = ""

    def __post_init__(self):
        if not self.room_id:
            raise ValueError("room_id must be non-empty.")
        if self.new_status not in VALID_ROOM_STATUSES:
            raise ValueError(
                f"new_status must be one of {sorted(VALID_ROOM_STATUSES)}.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_ROOM_CHANGE_STATUS_REQUEST, {
            "room_id": self.room_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "reason": self.reason,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class SetRoomOutOfOrderRequest:
    business_id: uuid.UUID
    branch_id:   uuid.UUID
    room_id:     str
    reason:      str
    from_date:   str
    actor_id:    str
    issued_at:   datetime
    to_date:     Optional[str] = None

    def __post_init__(self):
        if not self.room_id:
            raise ValueError("room_id must be non-empty.")
        if not self.reason:
            raise ValueError("reason must be non-empty.")
        if not self.from_date:
            raise ValueError("from_date must be non-empty.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_ROOM_SET_OUT_OF_ORDER_REQUEST, {
            "room_id": self.room_id,
            "reason": self.reason,
            "from_date": self.from_date,
            "to_date": self.to_date,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class ReturnRoomToServiceRequest:
    business_id: uuid.UUID
    branch_id:   uuid.UUID
    room_id:     str
    actor_id:    str
    issued_at:   datetime

    def __post_init__(self):
        if not self.room_id:
            raise ValueError("room_id must be non-empty.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_ROOM_RETURN_TO_SERVICE_REQUEST, {
            "room_id": self.room_id,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class CreateRatePlanRequest:
    business_id:   uuid.UUID
    branch_id:     uuid.UUID
    rate_plan_id:  str
    name:          str
    code:          str
    actor_id:      str
    issued_at:     datetime
    meal_plan:     str = "RO"
    cancel_policy: str = "FREE_CANCEL"
    deposit_required: bool = False
    deposit_percent:  int = 0
    min_los:          int = 1
    is_derived:       bool = False
    derived_from_plan_id: Optional[str] = None
    derived_discount_bps: int = 0

    def __post_init__(self):
        if not self.rate_plan_id:
            raise ValueError("rate_plan_id must be non-empty.")
        if not self.name:
            raise ValueError("name must be non-empty.")
        if self.code not in VALID_RATE_CODES:
            raise ValueError(f"code must be one of {sorted(VALID_RATE_CODES)}.")
        if self.meal_plan not in VALID_MEAL_PLANS:
            raise ValueError(f"meal_plan must be one of {sorted(VALID_MEAL_PLANS)}.")
        if self.cancel_policy not in VALID_CANCEL_POLICIES:
            raise ValueError(
                f"cancel_policy must be one of {sorted(VALID_CANCEL_POLICIES)}.")
        if not isinstance(self.min_los, int) or self.min_los < 1:
            raise ValueError("min_los must be >= 1.")
        if self.is_derived and not self.derived_from_plan_id:
            raise ValueError(
                "derived_from_plan_id required when is_derived=True.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_RATE_PLAN_CREATE_REQUEST, {
            "rate_plan_id": self.rate_plan_id,
            "name": self.name,
            "code": self.code,
            "meal_plan": self.meal_plan,
            "cancel_policy": self.cancel_policy,
            "deposit_required": self.deposit_required,
            "deposit_percent": self.deposit_percent,
            "min_los": self.min_los,
            "is_derived": self.is_derived,
            "derived_from_plan_id": self.derived_from_plan_id,
            "derived_discount_bps": self.derived_discount_bps,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class SetSeasonalRateRequest:
    business_id:      uuid.UUID
    branch_id:        uuid.UUID
    seasonal_rate_id: str
    rate_plan_id:     str
    room_type_id:     str
    from_date:        str
    to_date:          str
    nightly_rate:     int
    currency:         str
    actor_id:         str
    issued_at:        datetime

    def __post_init__(self):
        if not self.seasonal_rate_id:
            raise ValueError("seasonal_rate_id must be non-empty.")
        if not self.rate_plan_id:
            raise ValueError("rate_plan_id must be non-empty.")
        if not self.room_type_id:
            raise ValueError("room_type_id must be non-empty.")
        if not self.from_date or not self.to_date:
            raise ValueError("from_date and to_date must be non-empty.")
        if not isinstance(self.nightly_rate, int) or self.nightly_rate <= 0:
            raise ValueError("nightly_rate must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO 4217 code.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_SEASONAL_RATE_SET_REQUEST, {
            "seasonal_rate_id": self.seasonal_rate_id,
            "rate_plan_id": self.rate_plan_id,
            "room_type_id": self.room_type_id,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "nightly_rate": self.nightly_rate,
            "currency": self.currency,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)
