"""BOS Hotel Folio Engine — Request Commands"""
from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from engines.hotel_folio.events import (
    VALID_CHARGE_TYPES, VALID_PAYMENT_METHODS, VALID_ADJUSTMENT_TYPES,
)

HOTEL_FOLIO_OPEN_REQUEST            = "hotel.folio.open.request"
HOTEL_FOLIO_POST_CHARGE_REQUEST     = "hotel.folio.post_charge.request"
HOTEL_FOLIO_RECEIVE_PAYMENT_REQUEST = "hotel.folio.receive_payment.request"
HOTEL_FOLIO_APPLY_CREDIT_REQUEST    = "hotel.folio.apply_credit.request"
HOTEL_FOLIO_ADJUST_REQUEST          = "hotel.folio.adjust.request"
HOTEL_FOLIO_SETTLE_REQUEST          = "hotel.folio.settle.request"
HOTEL_NIGHT_AUDIT_RUN_REQUEST       = "hotel.night_audit.run.request"
HOTEL_ROOM_NIGHT_POST_CHARGE_REQUEST= "hotel.room_night.post_charge.request"

HOTEL_FOLIO_COMMAND_TYPES = frozenset({
    HOTEL_FOLIO_OPEN_REQUEST, HOTEL_FOLIO_POST_CHARGE_REQUEST,
    HOTEL_FOLIO_RECEIVE_PAYMENT_REQUEST, HOTEL_FOLIO_APPLY_CREDIT_REQUEST,
    HOTEL_FOLIO_ADJUST_REQUEST, HOTEL_FOLIO_SETTLE_REQUEST,
    HOTEL_NIGHT_AUDIT_RUN_REQUEST, HOTEL_ROOM_NIGHT_POST_CHARGE_REQUEST,
})


class _Cmd:
    __slots__ = ("command_type","payload","business_id","branch_id","actor_id","issued_at")
    def __init__(self,command_type,payload,*,business_id,branch_id,actor_id,issued_at):
        self.command_type=command_type; self.payload=payload
        self.business_id=business_id; self.branch_id=branch_id
        self.actor_id=actor_id; self.issued_at=issued_at


@dataclass(frozen=True)
class OpenFolioRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    folio_id:       str
    reservation_id: str
    room_id:        str
    currency:       str
    actor_id:       str
    issued_at:      datetime
    guest_id:       Optional[str] = None
    guest_name:     str = ""

    def __post_init__(self):
        if not self.folio_id:       raise ValueError("folio_id must be non-empty.")
        if not self.reservation_id: raise ValueError("reservation_id must be non-empty.")
        if not self.room_id:        raise ValueError("room_id must be non-empty.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO code.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_FOLIO_OPEN_REQUEST, {
            "folio_id": self.folio_id, "reservation_id": self.reservation_id,
            "room_id": self.room_id, "currency": self.currency,
            "guest_id": self.guest_id, "guest_name": self.guest_name,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class PostChargeRequest:
    business_id: uuid.UUID
    branch_id:   uuid.UUID
    folio_id:    str
    charge_id:   str
    charge_type: str
    amount:      int
    currency:    str
    actor_id:    str
    issued_at:   datetime
    description: str = ""
    source_ref:  str = ""

    def __post_init__(self):
        if not self.folio_id:   raise ValueError("folio_id must be non-empty.")
        if not self.charge_id:  raise ValueError("charge_id must be non-empty.")
        if self.charge_type not in VALID_CHARGE_TYPES:
            raise ValueError(f"charge_type must be one of {sorted(VALID_CHARGE_TYPES)}.")
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError("amount must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO code.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_FOLIO_POST_CHARGE_REQUEST, {
            "folio_id": self.folio_id, "charge_id": self.charge_id,
            "charge_type": self.charge_type, "amount": self.amount,
            "currency": self.currency, "description": self.description,
            "source_ref": self.source_ref,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class ReceivePaymentRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    folio_id:       str
    payment_id:     str
    amount:         int
    currency:       str
    payment_method: str
    actor_id:       str
    issued_at:      datetime
    reference:      str = ""

    def __post_init__(self):
        if not self.folio_id:   raise ValueError("folio_id must be non-empty.")
        if not self.payment_id: raise ValueError("payment_id must be non-empty.")
        if not isinstance(self.amount, int) or self.amount <= 0:
            raise ValueError("amount must be positive integer.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO code.")
        if self.payment_method not in VALID_PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {sorted(VALID_PAYMENT_METHODS)}.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_FOLIO_RECEIVE_PAYMENT_REQUEST, {
            "folio_id": self.folio_id, "payment_id": self.payment_id,
            "amount": self.amount, "currency": self.currency,
            "payment_method": self.payment_method, "reference": self.reference,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class SettleFolioRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    folio_id:       str
    total_charges:  int
    total_payments: int
    balance_due:    int
    currency:       str
    actor_id:       str
    issued_at:      datetime
    payment_method: str = "CARD"

    def __post_init__(self):
        if not self.folio_id: raise ValueError("folio_id must be non-empty.")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("currency must be 3-letter ISO code.")
        if self.payment_method not in VALID_PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {sorted(VALID_PAYMENT_METHODS)}.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_FOLIO_SETTLE_REQUEST, {
            "folio_id": self.folio_id, "total_charges": self.total_charges,
            "total_payments": self.total_payments, "balance_due": self.balance_due,
            "currency": self.currency, "payment_method": self.payment_method,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)


@dataclass(frozen=True)
class PostRoomNightChargeRequest:
    business_id:    uuid.UUID
    branch_id:      uuid.UUID
    folio_id:       str
    charge_id:      str
    reservation_id: str
    room_id:        str
    business_date:  str
    rate_plan_id:   str
    nightly_rate:   int
    currency:       str
    actor_id:       str
    issued_at:      datetime

    def __post_init__(self):
        if not self.folio_id:       raise ValueError("folio_id must be non-empty.")
        if not self.charge_id:      raise ValueError("charge_id must be non-empty.")
        if not self.reservation_id: raise ValueError("reservation_id must be non-empty.")
        if not isinstance(self.nightly_rate, int) or self.nightly_rate <= 0:
            raise ValueError("nightly_rate must be positive integer.")

    def to_command(self) -> _Cmd:
        return _Cmd(HOTEL_ROOM_NIGHT_POST_CHARGE_REQUEST, {
            "folio_id": self.folio_id, "charge_id": self.charge_id,
            "reservation_id": self.reservation_id, "room_id": self.room_id,
            "business_date": self.business_date, "rate_plan_id": self.rate_plan_id,
            "nightly_rate": self.nightly_rate, "currency": self.currency,
        }, business_id=self.business_id, branch_id=self.branch_id,
           actor_id=self.actor_id, issued_at=self.issued_at)
