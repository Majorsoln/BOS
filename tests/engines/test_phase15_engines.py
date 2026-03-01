"""
BOS Phase 15 — Hotel / Hospitality PMS Engine Tests
====================================================
Tests: hotel_property, hotel_reservation, hotel_folio,
       hotel_housekeeping, hotel_channel, hotel_booking_engine
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest

BIZ    = uuid.uuid4()
BRANCH = uuid.uuid4()
NOW    = datetime(2026, 2, 26, 9, 0, 0, tzinfo=timezone.utc)
TODAY  = "2026-02-26"
TOMORROW = "2026-02-27"
NEXT_WEEK = "2026-03-05"


# ── Stubs (same pattern as Phase 14) ─────────────────────────

class StubEventFactory:
    def create(self, event_type, payload, business_id, branch_id=None):
        return {"event_type": event_type, "payload": payload,
                "business_id": str(business_id)}


class StubPersist:
    def __call__(self, event_data): return True


class StubReg:
    def register(self, et): pass


def cmd_ns(cmd):
    return SimpleNamespace(
        command_type=cmd.command_type,
        payload=cmd.payload,
        business_id=getattr(cmd, "business_id", BIZ),
        branch_id=getattr(cmd, "branch_id", BRANCH),
        actor_id=getattr(cmd, "actor_id", "mgr"),
        issued_at=getattr(cmd, "issued_at", NOW),
    )


# ══════════════════════════════════════════════════════════════
# HOTEL PROPERTY ENGINE
# ══════════════════════════════════════════════════════════════

class TestHotelPropertyProjectionStore:
    def _store(self):
        from engines.hotel_property.services import HotelPropertyProjectionStore
        return HotelPropertyProjectionStore()

    def _configure(self, s):
        from engines.hotel_property.events import PROPERTY_CONFIGURED_V1
        s.apply(PROPERTY_CONFIGURED_V1, {
            "property_id": "prop-1", "property_name": "Serene Hotel",
            "property_type": "HOTEL", "star_rating": 4,
            "timezone": "Africa/Nairobi", "default_currency": "KES",
            "check_in_time": "14:00", "check_out_time": "11:00",
        })

    def _define_room_type(self, s, rtid="rt-1"):
        from engines.hotel_property.events import ROOM_TYPE_DEFINED_V1
        s.apply(ROOM_TYPE_DEFINED_V1, {
            "room_type_id": rtid, "name": "Deluxe Double",
            "bed_configuration": "DOUBLE", "max_adults": 2,
            "max_children": 1, "amenities": ["wifi", "ac"],
            "total_rooms": 5,
        })

    def _create_room(self, s, room_id="room-101", rtid="rt-1"):
        from engines.hotel_property.events import ROOM_CREATED_V1
        s.apply(ROOM_CREATED_V1, {
            "room_id": room_id, "room_number": "101",
            "room_type_id": rtid, "floor": 1,
            "building": "MAIN", "notes": "", "status": "AVAILABLE",
        })

    def _create_rate_plan(self, s, rpid="rp-1"):
        from engines.hotel_property.events import RATE_PLAN_CREATED_V1
        s.apply(RATE_PLAN_CREATED_V1, {
            "rate_plan_id": rpid, "name": "Best Available Rate",
            "code": "BAR", "meal_plan": "BB",
            "cancel_policy": "FREE_CANCEL",
            "deposit_required": False, "deposit_percent": 0,
            "min_los": 1, "is_derived": False,
            "derived_from_plan_id": None, "derived_discount_bps": 0,
            "is_active": True,
        })

    def test_configure_property(self):
        s = self._store()
        self._configure(s)
        prop = s.get_property()
        assert prop is not None
        assert prop["property_name"] == "Serene Hotel"
        assert prop["star_rating"] == 4

    def test_define_room_type(self):
        s = self._store()
        self._define_room_type(s)
        rt = s.get_room_type("rt-1")
        assert rt is not None
        assert rt["bed_configuration"] == "DOUBLE"
        assert rt["max_adults"] == 2

    def test_create_room(self):
        s = self._store()
        self._define_room_type(s)
        self._create_room(s)
        room = s.get_room("room-101")
        assert room is not None
        assert room["status"] == "AVAILABLE"
        assert room["room_type_id"] == "rt-1"

    def test_room_status_change(self):
        from engines.hotel_property.events import ROOM_STATUS_CHANGED_V1
        s = self._store()
        self._create_room(s)
        s.apply(ROOM_STATUS_CHANGED_V1, {
            "room_id": "room-101", "old_status": "AVAILABLE",
            "new_status": "OCCUPIED", "reason": "check-in",
        })
        assert s.get_room("room-101")["status"] == "OCCUPIED"

    def test_room_out_of_order_and_return(self):
        from engines.hotel_property.events import (
            ROOM_SET_OUT_OF_ORDER_V1, ROOM_RETURNED_TO_SERVICE_V1
        )
        s = self._store()
        self._create_room(s)
        s.apply(ROOM_SET_OUT_OF_ORDER_V1, {
            "room_id": "room-101", "reason": "Broken AC",
            "from_date": TODAY, "to_date": TOMORROW,
        })
        assert s.get_room("room-101")["status"] == "OUT_OF_ORDER"
        s.apply(ROOM_RETURNED_TO_SERVICE_V1, {"room_id": "room-101"})
        assert s.get_room("room-101")["status"] == "AVAILABLE"

    def test_rate_plan_created_and_deactivated(self):
        from engines.hotel_property.events import RATE_PLAN_DEACTIVATED_V1
        s = self._store()
        self._create_rate_plan(s)
        rp = s.get_rate_plan("rp-1")
        assert rp is not None
        assert rp["is_active"] is True
        s.apply(RATE_PLAN_DEACTIVATED_V1, {
            "rate_plan_id": "rp-1", "reason": "Replaced by new plan",
        })
        assert s.get_rate_plan("rp-1")["is_active"] is False

    def test_seasonal_rate_set(self):
        from engines.hotel_property.events import SEASONAL_RATE_SET_V1
        s = self._store()
        self._create_rate_plan(s)
        self._define_room_type(s)
        s.apply(SEASONAL_RATE_SET_V1, {
            "seasonal_rate_id": "sr-1", "rate_plan_id": "rp-1",
            "room_type_id": "rt-1", "from_date": TODAY,
            "to_date": NEXT_WEEK, "nightly_rate": 8000, "currency": "KES",
        })
        rates = s.get_rates_for_plan_and_type("rp-1", "rt-1")
        assert len(rates) == 1
        assert rates[0]["nightly_rate"] == 8000

    def test_count_available_by_type(self):
        from engines.hotel_property.events import ROOM_STATUS_CHANGED_V1
        s = self._store()
        self._define_room_type(s)
        self._create_room(s, "room-101")
        self._create_room(s, "room-102")
        assert s.count_available_by_type("rt-1") == 2
        s.apply(ROOM_STATUS_CHANGED_V1, {
            "room_id": "room-101", "new_status": "OCCUPIED"
        })
        assert s.count_available_by_type("rt-1") == 1

    def test_list_rooms_by_status(self):
        from engines.hotel_property.events import ROOM_STATUS_CHANGED_V1
        s = self._store()
        self._define_room_type(s)
        self._create_room(s, "r1")
        self._create_room(s, "r2")
        s.apply(ROOM_STATUS_CHANGED_V1, {"room_id": "r1", "new_status": "CLEANING"})
        available = s.list_rooms(status="AVAILABLE")
        cleaning  = s.list_rooms(status="CLEANING")
        assert len(available) == 1
        assert len(cleaning)  == 1

    def test_event_count_and_truncate(self):
        s = self._store()
        self._configure(s)
        self._define_room_type(s)
        assert s.event_count == 2
        s.truncate()
        assert s.get_property() is None
        assert s.event_count == 0


class TestHotelPropertyCommandValidation:
    def test_property_id_required(self):
        from engines.hotel_property.commands import ConfigurePropertyRequest
        with pytest.raises(ValueError, match="property_id"):
            ConfigurePropertyRequest(
                business_id=BIZ, branch_id=BRANCH,
                property_id="", property_name="Hotel X",
                actor_id="mgr", issued_at=NOW,
            )

    def test_star_rating_range(self):
        from engines.hotel_property.commands import ConfigurePropertyRequest
        with pytest.raises(ValueError, match="star_rating"):
            ConfigurePropertyRequest(
                business_id=BIZ, branch_id=BRANCH,
                property_id="p1", property_name="Hotel X",
                star_rating=6, actor_id="mgr", issued_at=NOW,
            )

    def test_invalid_bed_configuration(self):
        from engines.hotel_property.commands import DefineRoomTypeRequest
        with pytest.raises(ValueError, match="bed_configuration"):
            DefineRoomTypeRequest(
                business_id=BIZ, branch_id=BRANCH,
                room_type_id="rt-1", name="Standard",
                bed_configuration="BUNK", max_adults=2,
                actor_id="mgr", issued_at=NOW,
            )

    def test_invalid_rate_code(self):
        from engines.hotel_property.commands import CreateRatePlanRequest
        with pytest.raises(ValueError, match="code"):
            CreateRatePlanRequest(
                business_id=BIZ, branch_id=BRANCH,
                rate_plan_id="rp-1", name="My Rate",
                code="INVALID", actor_id="mgr", issued_at=NOW,
            )

    def test_derived_plan_requires_parent(self):
        from engines.hotel_property.commands import CreateRatePlanRequest
        with pytest.raises(ValueError, match="derived_from_plan_id"):
            CreateRatePlanRequest(
                business_id=BIZ, branch_id=BRANCH,
                rate_plan_id="rp-d1", name="Non-ref derived",
                code="NON_REF", actor_id="mgr", issued_at=NOW,
                is_derived=True,
            )

    def test_seasonal_rate_currency_must_be_3_letters(self):
        from engines.hotel_property.commands import SetSeasonalRateRequest
        with pytest.raises(ValueError, match="currency"):
            SetSeasonalRateRequest(
                business_id=BIZ, branch_id=BRANCH,
                seasonal_rate_id="sr-1", rate_plan_id="rp-1",
                room_type_id="rt-1", from_date=TODAY, to_date=NEXT_WEEK,
                nightly_rate=5000, currency="KESH",
                actor_id="mgr", issued_at=NOW,
            )

    def test_valid_configure_to_command(self):
        from engines.hotel_property.commands import ConfigurePropertyRequest
        from engines.hotel_property.events import PROPERTY_CONFIGURED_V1
        req = ConfigurePropertyRequest(
            business_id=BIZ, branch_id=BRANCH,
            property_id="p-valid", property_name="Grand Hotel",
            star_rating=5, actor_id="mgr", issued_at=NOW,
        )
        cmd = req.to_command()
        assert cmd.command_type == "hotel.property.configure.request"
        assert cmd.payload["property_name"] == "Grand Hotel"


class TestHotelPropertyService:
    def _svc(self):
        from engines.hotel_property.services import (
            HotelPropertyService, HotelPropertyProjectionStore
        )
        return HotelPropertyService(
            event_factory=StubEventFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg(),
            projection_store=HotelPropertyProjectionStore(),
        )

    def test_configure_and_add_rooms(self):
        from engines.hotel_property.commands import (
            ConfigurePropertyRequest, DefineRoomTypeRequest,
            CreateRoomRequest, CreateRatePlanRequest,
        )
        from engines.hotel_property.events import (
            PROPERTY_CONFIGURED_V1, ROOM_CREATED_V1, RATE_PLAN_CREATED_V1
        )
        svc = self._svc()
        r = svc._execute_command(cmd_ns(ConfigurePropertyRequest(
            business_id=BIZ, branch_id=BRANCH,
            property_id="p1", property_name="Lakeview Hotel",
            star_rating=3, actor_id="mgr", issued_at=NOW,
        ).to_command()))
        assert r["event_type"] == PROPERTY_CONFIGURED_V1

        svc._execute_command(cmd_ns(DefineRoomTypeRequest(
            business_id=BIZ, branch_id=BRANCH,
            room_type_id="rt-1", name="Standard Twin",
            bed_configuration="TWIN", max_adults=2,
            actor_id="mgr", issued_at=NOW,
        ).to_command()))

        r2 = svc._execute_command(cmd_ns(CreateRoomRequest(
            business_id=BIZ, branch_id=BRANCH,
            room_id="room-101", room_number="101",
            room_type_id="rt-1", actor_id="mgr", issued_at=NOW,
        ).to_command()))
        assert r2["event_type"] == ROOM_CREATED_V1
        assert svc._store.get_room("room-101")["status"] == "AVAILABLE"

        r3 = svc._execute_command(cmd_ns(CreateRatePlanRequest(
            business_id=BIZ, branch_id=BRANCH,
            rate_plan_id="rp-1", name="BAR", code="BAR",
            actor_id="mgr", issued_at=NOW,
        ).to_command()))
        assert r3["event_type"] == RATE_PLAN_CREATED_V1
        assert svc._store.get_rate_plan("rp-1")["is_active"] is True


# ══════════════════════════════════════════════════════════════
# HOTEL RESERVATION ENGINE
# ══════════════════════════════════════════════════════════════

class TestHotelReservationProjectionStore:
    def _store(self):
        from engines.hotel_reservation.services import HotelReservationProjectionStore
        return HotelReservationProjectionStore()

    def _create_res(self, s, rid="res-1", source="DIRECT"):
        from engines.hotel_reservation.events import RESERVATION_CREATED_V1
        s.apply(RESERVATION_CREATED_V1, {
            "reservation_id": rid, "external_id": None,
            "source": source, "channel": "FRONT_DESK",
            "property_id": "prop-1", "room_type_id": "rt-1",
            "rate_plan_id": "rp-1", "guest_id": "guest-1",
            "guest_name": "John Doe", "adults": 2, "children": 0,
            "arrival_date": TODAY, "departure_date": TOMORROW,
            "nights": 1, "nightly_rate": 8000, "total_amount": 8000,
            "currency": "KES", "deposit_due": 0,
            "special_requests": "", "status": "PENDING",
        })

    def test_create_reservation(self):
        s = self._store()
        self._create_res(s)
        res = s.get_reservation("res-1")
        assert res is not None
        assert res["status"] == "PENDING"
        assert res["guest_name"] == "John Doe"

    def test_confirm_reservation(self):
        from engines.hotel_reservation.events import RESERVATION_CONFIRMED_V1
        s = self._store()
        self._create_res(s)
        s.apply(RESERVATION_CONFIRMED_V1, {
            "reservation_id": "res-1", "deposit_paid": 2000,
            "payment_ref": "TXN-001",
        })
        res = s.get_reservation("res-1")
        assert res["status"] == "CONFIRMED"
        assert res["deposit_paid"] == 2000

    def test_check_in(self):
        from engines.hotel_reservation.events import GUEST_CHECKED_IN_V1
        s = self._store()
        self._create_res(s)
        s.apply(GUEST_CHECKED_IN_V1, {
            "reservation_id": "res-1", "room_id": "room-101",
            "room_number": "101", "folio_id": "folio-1",
            "key_issued": True,
        })
        res = s.get_reservation("res-1")
        assert res["status"] == "CHECKED_IN"
        assert res["room_id"] == "room-101"
        assert res["folio_id"] == "folio-1"

    def test_check_out(self):
        from engines.hotel_reservation.events import (
            GUEST_CHECKED_IN_V1, GUEST_CHECKED_OUT_V1
        )
        s = self._store()
        self._create_res(s)
        s.apply(GUEST_CHECKED_IN_V1, {
            "reservation_id": "res-1", "room_id": "room-101",
            "room_number": "101", "folio_id": "folio-1", "key_issued": True,
        })
        s.apply(GUEST_CHECKED_OUT_V1, {
            "reservation_id": "res-1", "room_id": "room-101",
            "folio_id": "folio-1", "folio_total": 8000,
            "payment_method": "CARD",
        })
        assert s.get_reservation("res-1")["status"] == "CHECKED_OUT"

    def test_cancel_reservation(self):
        from engines.hotel_reservation.events import RESERVATION_CANCELLED_V1
        s = self._store()
        self._create_res(s)
        s.apply(RESERVATION_CANCELLED_V1, {
            "reservation_id": "res-1", "reason": "GUEST_REQUEST",
            "cancellation_charge": 0, "refund_amount": 0,
        })
        res = s.get_reservation("res-1")
        assert res["status"] == "CANCELLED"
        assert res["cancel_reason"] == "GUEST_REQUEST"

    def test_no_show(self):
        from engines.hotel_reservation.events import RESERVATION_NO_SHOW_V1
        s = self._store()
        self._create_res(s)
        s.apply(RESERVATION_NO_SHOW_V1, {
            "reservation_id": "res-1", "no_show_charge": 4000,
        })
        res = s.get_reservation("res-1")
        assert res["status"] == "NO_SHOW"
        assert res["no_show_charge"] == 4000

    def test_stay_extended(self):
        from engines.hotel_reservation.events import STAY_EXTENDED_V1
        s = self._store()
        self._create_res(s)
        s.apply(STAY_EXTENDED_V1, {
            "reservation_id": "res-1",
            "old_departure_date": TOMORROW,
            "new_departure_date": NEXT_WEEK,
            "extra_nights": 6, "extra_amount": 48000,
        })
        res = s.get_reservation("res-1")
        assert res["departure_date"] == NEXT_WEEK
        assert res["nights"] == 7

    def test_room_moved(self):
        from engines.hotel_reservation.events import (
            GUEST_CHECKED_IN_V1, ROOM_MOVED_V1
        )
        s = self._store()
        self._create_res(s)
        s.apply(GUEST_CHECKED_IN_V1, {
            "reservation_id": "res-1", "room_id": "room-101",
            "room_number": "101", "folio_id": "folio-1", "key_issued": True,
        })
        s.apply(ROOM_MOVED_V1, {
            "reservation_id": "res-1", "old_room_id": "room-101",
            "new_room_id": "room-201", "new_room_number": "201",
        })
        assert s.get_reservation("res-1")["room_id"] == "room-201"

    def test_external_id_dedup(self):
        from engines.hotel_reservation.events import RESERVATION_CREATED_V1
        s = self._store()
        s.apply(RESERVATION_CREATED_V1, {
            "reservation_id": "res-ota-1", "external_id": "BDC-12345",
            "source": "OTA", "channel": "BOOKING_COM",
            "property_id": "p1", "room_type_id": "rt-1",
            "rate_plan_id": "rp-1", "guest_id": None, "guest_name": "Jane",
            "adults": 1, "children": 0,
            "arrival_date": TODAY, "departure_date": TOMORROW,
            "nights": 1, "nightly_rate": 9000, "total_amount": 9000,
            "currency": "KES", "deposit_due": 0,
            "special_requests": "", "status": "PENDING",
        })
        assert s.external_id_exists("BDC-12345") is True
        assert s.external_id_exists("BDC-XXXXX") is False
        res = s.get_by_external_id("BDC-12345")
        assert res["reservation_id"] == "res-ota-1"

    def test_list_arrivals_and_in_house(self):
        from engines.hotel_reservation.events import GUEST_CHECKED_IN_V1
        s = self._store()
        self._create_res(s, "res-A")
        self._create_res(s, "res-B")
        arrivals = s.list_arrivals(TODAY)
        assert len(arrivals) == 2
        s.apply(GUEST_CHECKED_IN_V1, {
            "reservation_id": "res-A", "room_id": "r1",
            "room_number": "101", "folio_id": "f1", "key_issued": True,
        })
        assert len(s.list_in_house()) == 1

    def test_truncate(self):
        s = self._store()
        self._create_res(s)
        s.truncate()
        assert s.get_reservation("res-1") is None
        assert s.event_count == 0


class TestHotelReservationCommandValidation:
    def test_invalid_source(self):
        from engines.hotel_reservation.commands import CreateReservationRequest
        with pytest.raises(ValueError, match="source"):
            CreateReservationRequest(
                business_id=BIZ, branch_id=BRANCH,
                reservation_id="r1", property_id="p1",
                room_type_id="rt-1", rate_plan_id="rp-1",
                source="UNKNOWN", adults=1,
                arrival_date=TODAY, departure_date=TOMORROW,
                nights=1, nightly_rate=5000, total_amount=5000,
                currency="KES", actor_id="mgr", issued_at=NOW,
            )

    def test_adults_must_be_positive(self):
        from engines.hotel_reservation.commands import CreateReservationRequest
        with pytest.raises(ValueError, match="adults"):
            CreateReservationRequest(
                business_id=BIZ, branch_id=BRANCH,
                reservation_id="r1", property_id="p1",
                room_type_id="rt-1", rate_plan_id="rp-1",
                source="DIRECT", adults=0,
                arrival_date=TODAY, departure_date=TOMORROW,
                nights=1, nightly_rate=5000, total_amount=5000,
                currency="KES", actor_id="mgr", issued_at=NOW,
            )

    def test_invalid_cancel_reason(self):
        from engines.hotel_reservation.commands import CancelReservationRequest
        with pytest.raises(ValueError, match="reason"):
            CancelReservationRequest(
                business_id=BIZ, branch_id=BRANCH,
                reservation_id="r1", reason="CHANGED_MIND",
                actor_id="mgr", issued_at=NOW,
            )

    def test_move_room_same_room_rejected(self):
        from engines.hotel_reservation.commands import MoveRoomRequest
        with pytest.raises(ValueError, match="new_room_id"):
            MoveRoomRequest(
                business_id=BIZ, branch_id=BRANCH,
                reservation_id="r1",
                old_room_id="room-101", new_room_id="room-101",
                actor_id="mgr", issued_at=NOW,
            )

    def test_valid_create_to_command(self):
        from engines.hotel_reservation.commands import CreateReservationRequest
        from engines.hotel_reservation.events import RESERVATION_CREATED_V1
        req = CreateReservationRequest(
            business_id=BIZ, branch_id=BRANCH,
            reservation_id="res-v1", property_id="p1",
            room_type_id="rt-1", rate_plan_id="rp-1",
            source="WALK_IN", channel="FRONT_DESK", adults=2,
            arrival_date=TODAY, departure_date=TOMORROW,
            nights=1, nightly_rate=6000, total_amount=6000,
            currency="KES", actor_id="reception", issued_at=NOW,
        )
        cmd = req.to_command()
        assert cmd.command_type == "hotel.reservation.create.request"
        assert cmd.payload["source"] == "WALK_IN"


class TestHotelReservationService:
    def _svc(self):
        from engines.hotel_reservation.services import (
            HotelReservationService, HotelReservationProjectionStore
        )
        return HotelReservationService(
            event_factory=StubEventFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg(),
            projection_store=HotelReservationProjectionStore(),
        )

    def test_full_checkin_checkout_flow(self):
        from engines.hotel_reservation.commands import (
            CreateReservationRequest, ConfirmReservationRequest,
            CheckInRequest, CheckOutRequest,
        )
        from engines.hotel_reservation.events import (
            RESERVATION_CREATED_V1, GUEST_CHECKED_IN_V1, GUEST_CHECKED_OUT_V1
        )
        svc = self._svc()
        r = svc._execute_command(cmd_ns(CreateReservationRequest(
            business_id=BIZ, branch_id=BRANCH,
            reservation_id="res-flow", property_id="p1",
            room_type_id="rt-1", rate_plan_id="rp-1",
            source="DIRECT", adults=2,
            arrival_date=TODAY, departure_date=TOMORROW,
            nights=1, nightly_rate=8000, total_amount=8000,
            currency="KES", actor_id="reception", issued_at=NOW,
        ).to_command()))
        assert r["event_type"] == RESERVATION_CREATED_V1

        svc._execute_command(cmd_ns(ConfirmReservationRequest(
            business_id=BIZ, branch_id=BRANCH,
            reservation_id="res-flow", deposit_paid=2000,
            actor_id="reception", issued_at=NOW,
        ).to_command()))
        assert svc._store.get_reservation("res-flow")["status"] == "CONFIRMED"

        r2 = svc._execute_command(cmd_ns(CheckInRequest(
            business_id=BIZ, branch_id=BRANCH,
            reservation_id="res-flow", room_id="room-101",
            folio_id="folio-flow", actor_id="reception", issued_at=NOW,
        ).to_command()))
        assert r2["event_type"] == GUEST_CHECKED_IN_V1

        r3 = svc._execute_command(cmd_ns(CheckOutRequest(
            business_id=BIZ, branch_id=BRANCH,
            reservation_id="res-flow", room_id="room-101",
            folio_id="folio-flow", folio_total=8000,
            actor_id="reception", issued_at=NOW,
        ).to_command()))
        assert r3["event_type"] == GUEST_CHECKED_OUT_V1
        assert svc._store.get_reservation("res-flow")["status"] == "CHECKED_OUT"


# ══════════════════════════════════════════════════════════════
# HOTEL FOLIO ENGINE
# ══════════════════════════════════════════════════════════════

class TestHotelFolioProjectionStore:
    def _store(self):
        from engines.hotel_folio.services import HotelFolioProjectionStore
        return HotelFolioProjectionStore()

    def _open_folio(self, s, fid="folio-1"):
        from engines.hotel_folio.events import FOLIO_OPENED_V1
        s.apply(FOLIO_OPENED_V1, {
            "folio_id": fid, "reservation_id": "res-1",
            "guest_id": "guest-1", "guest_name": "Jane Doe",
            "room_id": "room-101", "currency": "KES",
        })

    def test_open_folio(self):
        s = self._store()
        self._open_folio(s)
        folio = s.get_folio("folio-1")
        assert folio is not None
        assert folio["status"] == "OPEN"
        assert s.get_balance("folio-1") == 0

    def test_post_charge(self):
        from engines.hotel_folio.events import FOLIO_CHARGE_POSTED_V1
        s = self._store()
        self._open_folio(s)
        s.apply(FOLIO_CHARGE_POSTED_V1, {
            "folio_id": "folio-1", "charge_id": "chg-1",
            "charge_type": "RESTAURANT", "description": "Dinner",
            "amount": 2500, "currency": "KES", "source_ref": "bill-99",
        })
        assert s.get_balance("folio-1") == 2500

    def test_room_night_charge(self):
        from engines.hotel_folio.events import ROOM_NIGHT_CHARGE_POSTED_V1
        s = self._store()
        self._open_folio(s)
        s.apply(ROOM_NIGHT_CHARGE_POSTED_V1, {
            "folio_id": "folio-1", "charge_id": "chg-rn-1",
            "reservation_id": "res-1", "room_id": "room-101",
            "business_date": TODAY, "rate_plan_id": "rp-1",
            "nightly_rate": 8000, "currency": "KES",
        })
        assert s.get_balance("folio-1") == 8000

    def test_payment_reduces_balance(self):
        from engines.hotel_folio.events import (
            FOLIO_CHARGE_POSTED_V1, FOLIO_PAYMENT_RECEIVED_V1
        )
        s = self._store()
        self._open_folio(s)
        s.apply(FOLIO_CHARGE_POSTED_V1, {
            "folio_id": "folio-1", "charge_id": "c1",
            "charge_type": "ROOM_NIGHT", "amount": 8000,
            "currency": "KES", "description": "Room charge",
        })
        s.apply(FOLIO_PAYMENT_RECEIVED_V1, {
            "folio_id": "folio-1", "payment_id": "pay-1",
            "amount": 8000, "currency": "KES", "payment_method": "CARD",
        })
        assert s.get_balance("folio-1") == 0

    def test_folio_settlement(self):
        from engines.hotel_folio.events import FOLIO_SETTLED_V1
        s = self._store()
        self._open_folio(s)
        s.apply(FOLIO_SETTLED_V1, {
            "folio_id": "folio-1", "total_charges": 8000,
            "total_payments": 8000, "balance_due": 0,
            "payment_method": "CARD", "currency": "KES",
        })
        folio = s.get_folio("folio-1")
        assert folio["status"] == "SETTLED"
        assert folio["balance_due"] == 0

    def test_multiple_charges_and_credit(self):
        from engines.hotel_folio.events import (
            FOLIO_CHARGE_POSTED_V1, FOLIO_CREDIT_APPLIED_V1
        )
        s = self._store()
        self._open_folio(s)
        s.apply(FOLIO_CHARGE_POSTED_V1, {
            "folio_id": "folio-1", "charge_id": "c1",
            "charge_type": "MINIBAR", "amount": 1200,
            "currency": "KES", "description": "Minibar",
        })
        s.apply(FOLIO_CHARGE_POSTED_V1, {
            "folio_id": "folio-1", "charge_id": "c2",
            "charge_type": "LAUNDRY", "amount": 500,
            "currency": "KES", "description": "Laundry",
        })
        s.apply(FOLIO_CREDIT_APPLIED_V1, {
            "folio_id": "folio-1", "credit_id": "cred-1",
            "amount": 300, "currency": "KES", "source": "WALLET",
        })
        assert s.get_balance("folio-1") == 1200 + 500 - 300

    def test_list_open_folios(self):
        from engines.hotel_folio.events import FOLIO_SETTLED_V1
        s = self._store()
        self._open_folio(s, "f1")
        self._open_folio(s, "f2")
        assert len(s.list_open_folios()) == 2
        s.apply(FOLIO_SETTLED_V1, {
            "folio_id": "f1", "total_charges": 0,
            "total_payments": 0, "balance_due": 0,
            "payment_method": "CASH", "currency": "KES",
        })
        assert len(s.list_open_folios()) == 1

    def test_folio_transfer(self):
        from engines.hotel_folio.events import (
            FOLIO_CHARGE_POSTED_V1, FOLIO_TRANSFERRED_V1
        )
        s = self._store()
        self._open_folio(s, "f1")
        self._open_folio(s, "f2")
        s.apply(FOLIO_CHARGE_POSTED_V1, {
            "folio_id": "f1", "charge_id": "c1",
            "charge_type": "RESTAURANT", "amount": 3000,
            "currency": "KES", "description": "Restaurant",
        })
        s.apply(FOLIO_TRANSFERRED_V1, {
            "from_folio_id": "f1", "to_folio_id": "f2",
            "charge_ids": ["c1"], "amount": 3000,
        })
        assert s.get_balance("f1") == 0
        assert s.get_balance("f2") == 3000


class TestHotelFolioCommandValidation:
    def test_folio_id_required(self):
        from engines.hotel_folio.commands import OpenFolioRequest
        with pytest.raises(ValueError, match="folio_id"):
            OpenFolioRequest(
                business_id=BIZ, branch_id=BRANCH,
                folio_id="", reservation_id="r1",
                room_id="room-101", currency="KES",
                actor_id="mgr", issued_at=NOW,
            )

    def test_invalid_charge_type(self):
        from engines.hotel_folio.commands import PostChargeRequest
        with pytest.raises(ValueError, match="charge_type"):
            PostChargeRequest(
                business_id=BIZ, branch_id=BRANCH,
                folio_id="f1", charge_id="c1",
                charge_type="COFFEE_SHOP",
                amount=500, currency="KES",
                actor_id="mgr", issued_at=NOW,
            )

    def test_invalid_payment_method(self):
        from engines.hotel_folio.commands import ReceivePaymentRequest
        with pytest.raises(ValueError, match="payment_method"):
            ReceivePaymentRequest(
                business_id=BIZ, branch_id=BRANCH,
                folio_id="f1", payment_id="pay-1",
                amount=1000, currency="KES",
                payment_method="CRYPTO",
                actor_id="mgr", issued_at=NOW,
            )


class TestHotelFolioService:
    def _svc(self):
        from engines.hotel_folio.services import (
            HotelFolioService, HotelFolioProjectionStore
        )
        return HotelFolioService(
            event_factory=StubEventFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg(),
            projection_store=HotelFolioProjectionStore(),
        )

    def test_open_post_settle(self):
        from engines.hotel_folio.commands import (
            OpenFolioRequest, PostChargeRequest, SettleFolioRequest,
        )
        from engines.hotel_folio.events import (
            FOLIO_OPENED_V1, FOLIO_CHARGE_POSTED_V1, FOLIO_SETTLED_V1
        )
        svc = self._svc()
        r = svc._execute_command(cmd_ns(OpenFolioRequest(
            business_id=BIZ, branch_id=BRANCH,
            folio_id="f-svc", reservation_id="res-1",
            room_id="room-101", currency="KES",
            actor_id="reception", issued_at=NOW,
        ).to_command()))
        assert r["event_type"] == FOLIO_OPENED_V1

        svc._execute_command(cmd_ns(PostChargeRequest(
            business_id=BIZ, branch_id=BRANCH,
            folio_id="f-svc", charge_id="c1",
            charge_type="ROOM_SERVICE", amount=1800,
            currency="KES", actor_id="reception", issued_at=NOW,
        ).to_command()))
        assert svc._store.get_balance("f-svc") == 1800

        r2 = svc._execute_command(cmd_ns(SettleFolioRequest(
            business_id=BIZ, branch_id=BRANCH,
            folio_id="f-svc", total_charges=1800, total_payments=1800,
            balance_due=0, currency="KES", payment_method="MOBILE",
            actor_id="reception", issued_at=NOW,
        ).to_command()))
        assert r2["event_type"] == FOLIO_SETTLED_V1
        assert svc._store.get_folio("f-svc")["status"] == "SETTLED"


# ══════════════════════════════════════════════════════════════
# HOTEL HOUSEKEEPING ENGINE
# ══════════════════════════════════════════════════════════════

class TestHotelHousekeepingProjectionStore:
    def _store(self):
        from engines.hotel_housekeeping.services import HotelHousekeepingProjectionStore
        return HotelHousekeepingProjectionStore()

    def _assign_task(self, s, tid="task-1", room_id="room-101",
                     task_type="DEPARTURE_CLEAN"):
        from engines.hotel_housekeeping.events import HOUSEKEEPING_TASK_ASSIGNED_V1
        s.apply(HOUSEKEEPING_TASK_ASSIGNED_V1, {
            "task_id": tid, "room_id": room_id, "room_number": "101",
            "task_type": task_type, "housekeeper_id": "hk-1",
            "priority": "NORMAL", "notes": "", "status": "ASSIGNED",
        })

    def test_assign_task(self):
        s = self._store()
        self._assign_task(s)
        task = s.get_task("task-1")
        assert task is not None
        assert task["status"] == "ASSIGNED"
        assert task["task_type"] == "DEPARTURE_CLEAN"

    def test_task_flow_assigned_started_completed(self):
        from engines.hotel_housekeeping.events import (
            HOUSEKEEPING_TASK_STARTED_V1, HOUSEKEEPING_TASK_COMPLETED_V1
        )
        s = self._store()
        self._assign_task(s)
        s.apply(HOUSEKEEPING_TASK_STARTED_V1, {"task_id": "task-1", "room_id": "room-101"})
        assert s.get_task("task-1")["status"] == "IN_PROGRESS"
        s.apply(HOUSEKEEPING_TASK_COMPLETED_V1, {
            "task_id": "task-1", "room_id": "room-101",
            "completed_at": NOW.isoformat(), "notes": "All clean",
        })
        assert s.get_task("task-1")["status"] == "COMPLETED"

    def test_inspection_pass(self):
        from engines.hotel_housekeeping.events import (
            HOUSEKEEPING_TASK_COMPLETED_V1, ROOM_INSPECTED_V1
        )
        s = self._store()
        self._assign_task(s)
        s.apply(HOUSEKEEPING_TASK_COMPLETED_V1, {
            "task_id": "task-1", "room_id": "room-101",
            "completed_at": NOW.isoformat(),
        })
        s.apply(ROOM_INSPECTED_V1, {
            "inspection_id": "insp-1", "room_id": "room-101",
            "task_id": "task-1", "result": "PASS", "notes": "",
        })
        assert s.get_task("task-1")["status"] == "INSPECTED_PASS"

    def test_inspection_fail_reassigns(self):
        from engines.hotel_housekeeping.events import (
            HOUSEKEEPING_TASK_COMPLETED_V1, INSPECTION_FAILED_V1
        )
        s = self._store()
        self._assign_task(s)
        s.apply(HOUSEKEEPING_TASK_COMPLETED_V1, {
            "task_id": "task-1", "room_id": "room-101",
            "completed_at": NOW.isoformat(),
        })
        s.apply(INSPECTION_FAILED_V1, {
            "inspection_id": "insp-2", "room_id": "room-101",
            "task_id": "task-1", "result": "FAIL",
            "failure_reasons": ["Bathroom not cleaned", "Bed not made"],
        })
        assert s.get_task("task-1")["status"] == "INSPECTED_FAIL"

    def test_maintenance_open_and_resolve(self):
        from engines.hotel_housekeeping.events import (
            MAINTENANCE_REQUESTED_V1, MAINTENANCE_RESOLVED_V1
        )
        s = self._store()
        s.apply(MAINTENANCE_REQUESTED_V1, {
            "maintenance_id": "maint-1", "room_id": "room-101",
            "category": "PLUMBING", "description": "Tap leaking",
            "priority": "URGENT", "status": "OPEN",
        })
        assert s.get_maintenance("maint-1")["status"] == "OPEN"
        assert len(s.list_open_maintenance()) == 1
        s.apply(MAINTENANCE_RESOLVED_V1, {
            "maintenance_id": "maint-1",
            "resolution": "Tap replaced", "resolved_at": NOW.isoformat(),
        })
        assert s.get_maintenance("maint-1")["status"] == "RESOLVED"
        assert len(s.list_open_maintenance()) == 0

    def test_lost_found_log_and_claim(self):
        from engines.hotel_housekeeping.events import (
            LOST_FOUND_LOGGED_V1, LOST_FOUND_CLAIMED_V1
        )
        s = self._store()
        s.apply(LOST_FOUND_LOGGED_V1, {
            "item_id": "lf-1", "room_id": "room-101",
            "description": "Black wallet", "storage_loc": "FRONT_DESK",
            "status": "UNCLAIMED",
        })
        assert len(s.list_unclaimed_items()) == 1
        s.apply(LOST_FOUND_CLAIMED_V1, {
            "item_id": "lf-1", "claimed_by": "John Doe",
            "id_verified": True, "released_at": NOW.isoformat(),
        })
        assert s.get_lost_found("lf-1")["status"] == "CLAIMED"
        assert len(s.list_unclaimed_items()) == 0

    def test_list_pending_tasks(self):
        s = self._store()
        self._assign_task(s, "t1", "r1")
        self._assign_task(s, "t2", "r2")
        assert len(s.list_pending_tasks()) == 2


class TestHotelHousekeepingCommandValidation:
    def test_invalid_task_type(self):
        from engines.hotel_housekeeping.commands import AssignHousekeepingTaskRequest
        with pytest.raises(ValueError, match="task_type"):
            AssignHousekeepingTaskRequest(
                business_id=BIZ, branch_id=BRANCH,
                task_id="t1", room_id="r1",
                task_type="VACUUM_ONLY",
                actor_id="mgr", issued_at=NOW,
            )

    def test_invalid_maintenance_category(self):
        from engines.hotel_housekeeping.commands import RequestMaintenanceRequest
        with pytest.raises(ValueError, match="category"):
            RequestMaintenanceRequest(
                business_id=BIZ, branch_id=BRANCH,
                maintenance_id="m1", room_id="r1",
                category="ROOF", description="Roof leak",
                actor_id="mgr", issued_at=NOW,
            )

    def test_fail_inspection_requires_reasons(self):
        from engines.hotel_housekeeping.commands import FailInspectionRequest
        with pytest.raises(ValueError, match="failure_reasons"):
            FailInspectionRequest(
                business_id=BIZ, branch_id=BRANCH,
                inspection_id="i1", room_id="r1",
                failure_reasons=(),
                actor_id="mgr", issued_at=NOW,
            )


class TestHotelHousekeepingService:
    def _svc(self):
        from engines.hotel_housekeeping.services import (
            HotelHousekeepingService, HotelHousekeepingProjectionStore
        )
        return HotelHousekeepingService(
            event_factory=StubEventFactory(), persist_event=StubPersist(),
            event_type_registry=StubReg(),
            projection_store=HotelHousekeepingProjectionStore(),
        )

    def test_assign_and_complete_task(self):
        from engines.hotel_housekeeping.commands import (
            AssignHousekeepingTaskRequest, CompleteHousekeepingTaskRequest,
            InspectRoomRequest,
        )
        from engines.hotel_housekeeping.events import (
            HOUSEKEEPING_TASK_ASSIGNED_V1, ROOM_INSPECTED_V1
        )
        svc = self._svc()
        r = svc._execute_command(cmd_ns(AssignHousekeepingTaskRequest(
            business_id=BIZ, branch_id=BRANCH,
            task_id="t-svc", room_id="room-101",
            task_type="DEPARTURE_CLEAN",
            actor_id="supervisor", issued_at=NOW,
        ).to_command()))
        assert r["event_type"] == HOUSEKEEPING_TASK_ASSIGNED_V1

        svc._execute_command(cmd_ns(CompleteHousekeepingTaskRequest(
            business_id=BIZ, branch_id=BRANCH,
            task_id="t-svc", room_id="room-101",
            actor_id="hk-1", issued_at=NOW,
        ).to_command()))

        r2 = svc._execute_command(cmd_ns(InspectRoomRequest(
            business_id=BIZ, branch_id=BRANCH,
            inspection_id="insp-svc", room_id="room-101",
            task_id="t-svc", actor_id="supervisor", issued_at=NOW,
        ).to_command()))
        assert r2["event_type"] == ROOM_INSPECTED_V1
        assert svc._store.get_task("t-svc")["status"] == "INSPECTED_PASS"


# ══════════════════════════════════════════════════════════════
# HOTEL CHANNEL ENGINE
# ══════════════════════════════════════════════════════════════

class TestChannelManagerAdapters:
    def test_channex_adapter_health_check_not_connected(self):
        from engines.hotel_channel.adapters import ChannexAdapter
        adapter = ChannexAdapter()
        status = adapter.health_check()
        assert status.ok is False

    def test_channex_adapter_connect(self):
        from engines.hotel_channel.adapters import ChannexAdapter
        adapter = ChannexAdapter()
        result = adapter.connect({"api_key": "test-key", "property_id": "prop-123"})
        assert result.connected is True
        assert result.provider == "Channex"
        assert adapter.health_check().ok is True

    def test_channex_adapter_connect_missing_api_key(self):
        from engines.hotel_channel.adapters import ChannexAdapter
        adapter = ChannexAdapter()
        result = adapter.connect({"property_id": "prop-123"})
        assert result.connected is False

    def test_channex_webhook_new_booking(self):
        from engines.hotel_channel.adapters import ChannexAdapter
        adapter = ChannexAdapter("key", "prop-1")
        result = adapter.handle_webhook({
            "event": "booking_new",
            "booking": {"id": "BDC-9999"},
        })
        assert result.processed is True
        assert result.event_type == "reservation_created"
        assert result.external_id == "BDC-9999"

    def test_channex_webhook_cancellation(self):
        from engines.hotel_channel.adapters import ChannexAdapter
        adapter = ChannexAdapter("key", "prop-1")
        result = adapter.handle_webhook({
            "event": "booking_cancelled",
            "booking": {"id": "BDC-8888"},
        })
        assert result.event_type == "reservation_cancelled"
        assert result.external_id == "BDC-8888"

    def test_channex_push_availability(self):
        from engines.hotel_channel.adapters import ChannexAdapter
        adapter = ChannexAdapter("key", "prop-1")
        result = adapter.push_availability(
            "prop-1",
            {"rt-1": "cm-room-1"},
            {"rt-1": {TODAY: 3, TOMORROW: 3}},
        )
        assert result.accepted is True
        assert result.rooms_updated == 1
        assert result.dates_updated == 2

    def test_beds24_adapter_connect(self):
        from engines.hotel_channel.adapters import Beds24Adapter
        adapter = Beds24Adapter()
        result = adapter.connect({"api_key": "key-b24", "prop_key": "pk-999"})
        assert result.connected is True
        assert result.provider == "Beds24"
        assert adapter.health_check().ok is True

    def test_beds24_webhook(self):
        from engines.hotel_channel.adapters import Beds24Adapter
        adapter = Beds24Adapter("key", "pk")
        result = adapter.handle_webhook({
            "type": "newBooking", "bookId": "B24-555",
        })
        assert result.processed is True
        assert result.event_type == "reservation_created"
        assert result.external_id == "B24-555"

    def test_beds24_webhook_missing_book_id(self):
        from engines.hotel_channel.adapters import Beds24Adapter
        adapter = Beds24Adapter("key", "pk")
        result = adapter.handle_webhook({"type": "newBooking"})
        assert result.processed is False

    def test_get_adapter_unknown_provider(self):
        from engines.hotel_channel.adapters import get_adapter
        with pytest.raises(ValueError, match="Unknown channel manager provider"):
            get_adapter("unknown_cm", {})

    def test_get_adapter_channex(self):
        from engines.hotel_channel.adapters import get_adapter, ChannexAdapter
        adapter = get_adapter("channex", {"api_key": "k", "property_id": "p1"})
        assert isinstance(adapter, ChannexAdapter)
        assert adapter.provider_name == "Channex"


class TestHotelChannelProjectionStore:
    def _store(self):
        from engines.hotel_channel.services import HotelChannelProjectionStore
        return HotelChannelProjectionStore()

    def test_connect_event(self):
        from engines.hotel_channel.events import CHANNEL_CONNECTED_V1
        s = self._store()
        s.apply(CHANNEL_CONNECTED_V1, {
            "property_id": "p1", "provider": "channex",
            "property_ref": "cx-prop-1", "sync_mode": "PULL_ONLY",
            "connected_at": NOW.isoformat(),
        })
        assert s.is_connected("p1") is True
        conn = s.get_connection("p1")
        assert conn["sync_mode"] == "PULL_ONLY"

    def test_room_and_rate_maps(self):
        from engines.hotel_channel.events import (
            CHANNEL_CONNECTED_V1, ROOM_MAPPED_V1, RATE_MAPPED_V1
        )
        s = self._store()
        s.apply(CHANNEL_CONNECTED_V1, {
            "property_id": "p1", "provider": "channex",
            "property_ref": "cx-1", "sync_mode": "PULL_ONLY",
            "connected_at": NOW.isoformat(),
        })
        s.apply(ROOM_MAPPED_V1, {
            "property_id": "p1", "bos_room_type_id": "rt-1",
            "provider_room_id": "cm-rt-101", "mapped_by": "mgr",
            "mapped_at": NOW.isoformat(),
        })
        s.apply(RATE_MAPPED_V1, {
            "property_id": "p1", "bos_rate_plan_id": "rp-1",
            "provider_rate_id": "cm-bar", "mapped_by": "mgr",
            "mapped_at": NOW.isoformat(),
        })
        room_map = s.get_room_map("p1")
        rate_map = s.get_rate_map("p1")
        assert room_map.get("rt-1") == "cm-rt-101"
        assert rate_map.get("rp-1") == "cm-bar"

    def test_sync_job_lifecycle(self):
        from engines.hotel_channel.events import (
            SYNC_JOB_STARTED_V1, SYNC_JOB_COMPLETED_V1
        )
        s = self._store()
        s.apply(SYNC_JOB_STARTED_V1, {
            "job_id": "job-1", "property_id": "p1",
            "job_type": "pull_reservations",
            "started_at": NOW.isoformat(),
        })
        job = s.list_sync_jobs("p1")
        assert len(job) == 1
        assert job[0]["status"] == "RUNNING"
        s.apply(SYNC_JOB_COMPLETED_V1, {
            "job_id": "job-1", "property_id": "p1",
            "records": 5, "completed_at": NOW.isoformat(),
        })
        assert s.list_sync_jobs("p1")[0]["status"] == "COMPLETED"


class TestHotelChannelService:
    def _svc(self):
        from engines.hotel_channel.services import (
            HotelChannelService, HotelChannelProjectionStore
        )
        return HotelChannelService(
            projection_store=HotelChannelProjectionStore(),
        )

    def test_connect_channex(self):
        from engines.hotel_channel.events import CHANNEL_CONNECTED_V1
        svc = self._svc()
        result = svc.connect(
            "prop-1", "channex",
            {"api_key": "test-key", "property_id": "cx-prop-1"},
        )
        assert result["connected"] is True
        assert result["event_type"] == CHANNEL_CONNECTED_V1
        assert svc._store.is_connected("prop-1") is True

    def test_connect_beds24(self):
        svc = self._svc()
        result = svc.connect(
            "prop-2", "beds24",
            {"api_key": "b24-key", "prop_key": "b24-prop-1"},
        )
        assert result["connected"] is True
        assert svc._store.is_connected("prop-2") is True

    def test_room_and_rate_mapping(self):
        from engines.hotel_channel.events import ROOM_MAPPED_V1, RATE_MAPPED_V1
        svc = self._svc()
        svc.connect("p1", "channex", {"api_key": "k", "property_id": "cx-1"})
        r1 = svc.map_room("p1", "rt-1", "cm-101", "Deluxe", "Standard Double")
        r2 = svc.map_rate("p1", "rp-1", "cm-bar", "BAR", "Best Available")
        assert r1["event_type"] == ROOM_MAPPED_V1
        assert r2["event_type"] == RATE_MAPPED_V1
        assert svc._store.get_room_map("p1")["rt-1"] == "cm-101"
        assert svc._store.get_rate_map("p1")["rp-1"] == "cm-bar"

    def test_push_availability(self):
        from engines.hotel_channel.events import SYNC_JOB_COMPLETED_V1
        svc = self._svc()
        svc.connect("p1", "channex", {"api_key": "k", "property_id": "cx-1"})
        svc.map_room("p1", "rt-1", "cm-101")
        result = svc.push_availability(
            "p1", "job-avail-1",
            {"rt-1": {TODAY: 5, TOMORROW: 5}},
        )
        assert result["event_type"] == SYNC_JOB_COMPLETED_V1

    def test_webhook_channex(self):
        svc = self._svc()
        svc.connect("p1", "channex", {"api_key": "k", "property_id": "cx-1"})
        result = svc.handle_webhook("p1", "channex", {
            "event": "booking_new",
            "booking": {"id": "BDC-1234"},
        })
        assert result["processed"] is True
        assert result["external_id"] == "BDC-1234"

    def test_health_check(self):
        svc = self._svc()
        svc.connect("p1", "channex", {"api_key": "k", "property_id": "cx-1"})
        status = svc.health_check("p1")
        assert status["ok"] is True


# ══════════════════════════════════════════════════════════════
# HOTEL BOOKING ENGINE
# ══════════════════════════════════════════════════════════════

class TestHotelBookingEngineService:
    def _svc(self):
        from engines.hotel_booking_engine.services import (
            HotelBookingEngineService, HotelBookingEngineProjectionStore
        )
        return HotelBookingEngineService(
            projection_store=HotelBookingEngineProjectionStore(),
        )

    def test_issue_api_key(self):
        from engines.hotel_booking_engine.events import BOOKING_ENGINE_KEY_ISSUED_V1
        svc = self._svc()
        result = svc.issue_api_key("prop-1", label="Website Widget")
        assert result["event_type"] == BOOKING_ENGINE_KEY_ISSUED_V1
        assert "api_key" in result
        assert result["scope"] == "BOOKING_ENGINE"
        raw_key = result["api_key"]
        assert len(raw_key) > 10

    def test_api_key_lookup_by_raw(self):
        svc = self._svc()
        result = svc.issue_api_key("prop-1")
        raw_key = result["api_key"]
        record  = svc._store.get_api_key_by_hash(raw_key)
        assert record is not None
        assert record["property_id"] == "prop-1"
        assert record["revoked"] is False

    def test_revoke_api_key(self):
        from engines.hotel_booking_engine.events import BOOKING_ENGINE_KEY_REVOKED_V1
        svc = self._svc()
        issued = svc.issue_api_key("prop-1")
        raw_key = issued["api_key"]
        r = svc.revoke_api_key(issued["key_id"])
        assert r["event_type"] == BOOKING_ENGINE_KEY_REVOKED_V1
        # After revoke, lookup returns None
        assert svc._store.get_api_key_by_hash(raw_key) is None

    def test_search_availability_no_property_store(self):
        # Without property store, returns empty available_types
        svc = self._svc()
        result = svc.search_availability("prop-1", TODAY, TOMORROW, adults=2)
        assert result["property_id"] == "prop-1"
        assert result["available_types"] == []

    def test_search_availability_with_property_store(self):
        from engines.hotel_property.services import HotelPropertyProjectionStore
        from engines.hotel_property.events import ROOM_TYPE_DEFINED_V1, ROOM_CREATED_V1
        prop_store = HotelPropertyProjectionStore()
        prop_store.apply(ROOM_TYPE_DEFINED_V1, {
            "room_type_id": "rt-1", "name": "Standard",
            "bed_configuration": "DOUBLE", "max_adults": 2,
            "max_children": 1, "amenities": ["wifi"], "total_rooms": 3,
        })
        prop_store.apply(ROOM_CREATED_V1, {
            "room_id": "r1", "room_number": "101", "room_type_id": "rt-1",
            "floor": 1, "building": "MAIN", "notes": "",
            "status": "AVAILABLE",
        })
        from engines.hotel_booking_engine.services import (
            HotelBookingEngineService, HotelBookingEngineProjectionStore
        )
        svc = HotelBookingEngineService(
            projection_store=HotelBookingEngineProjectionStore(),
            property_store=prop_store,
        )
        result = svc.search_availability("prop-1", TODAY, TOMORROW, adults=2)
        assert len(result["available_types"]) == 1
        assert result["available_types"][0]["room_type_id"] == "rt-1"

    def test_rate_quote_no_seasonal_rate(self):
        svc = self._svc()
        quote = svc.quote_rate("p1", "rt-1", "rp-1", TODAY, TOMORROW, nights=1)
        assert quote["nightly_rate"] == 0
        assert quote["nights"] == 1

    def test_rate_quote_with_seasonal_rate(self):
        from engines.hotel_property.services import HotelPropertyProjectionStore
        from engines.hotel_property.events import RATE_PLAN_CREATED_V1, SEASONAL_RATE_SET_V1
        prop_store = HotelPropertyProjectionStore()
        prop_store.apply(RATE_PLAN_CREATED_V1, {
            "rate_plan_id": "rp-1", "name": "BAR", "code": "BAR",
            "meal_plan": "BB", "cancel_policy": "FREE_CANCEL",
            "deposit_required": False, "deposit_percent": 0,
            "min_los": 1, "is_derived": False,
            "derived_from_plan_id": None, "derived_discount_bps": 0,
            "is_active": True,
        })
        prop_store.apply(SEASONAL_RATE_SET_V1, {
            "seasonal_rate_id": "sr-1", "rate_plan_id": "rp-1",
            "room_type_id": "rt-1",
            "from_date": "2026-02-01", "to_date": "2026-03-31",
            "nightly_rate": 7500, "currency": "KES",
        })
        from engines.hotel_booking_engine.services import (
            HotelBookingEngineService, HotelBookingEngineProjectionStore
        )
        svc = HotelBookingEngineService(
            projection_store=HotelBookingEngineProjectionStore(),
            property_store=prop_store,
        )
        quote = svc.quote_rate("p1", "rt-1", "rp-1", TODAY, TOMORROW, nights=2)
        assert quote["nightly_rate"] == 7500
        assert quote["total_amount"] == 15000

    def test_create_direct_booking(self):
        from engines.hotel_booking_engine.events import DIRECT_BOOKING_CREATED_V1
        svc = self._svc()
        result = svc.create_booking(
            property_id="p1", booking_id="bk-1",
            room_type_id="rt-1", rate_plan_id="rp-1",
            guest_name="Ali Hassan", guest_email="ali@example.com",
            arrival_date=TODAY, departure_date=TOMORROW,
            nights=1, adults=2, total_amount=7500, currency="KES",
        )
        assert result["event_type"] == DIRECT_BOOKING_CREATED_V1
        assert result["payload"]["source"] == "DIRECT"
        assert result["payload"]["channel"] == "WEBSITE"
        booking = svc._store.get_booking("bk-1")
        assert booking is not None
        assert booking["status"] == "PENDING"

    def test_widget_embed_snippet(self):
        svc = self._svc()
        issued = svc.issue_api_key("prop-1")
        widget = svc.get_widget_embed_snippet(
            "prop-1", issued["api_key"], language="sw"
        )
        assert "bos-booking-widget" in widget["embed_snippet"]
        assert 'data-lang="sw"' in widget["embed_snippet"]
        assert "prop-1" in widget["embed_snippet"]
        assert "/api/v1/book/prop-1" in widget["api_endpoint"]

    def test_event_count(self):
        svc = self._svc()
        svc.issue_api_key("p1")
        svc.issue_api_key("p1")
        svc.search_availability("p1", TODAY, TOMORROW)
        assert svc._store.event_count == 3
