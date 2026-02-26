"""
BOS Phase 14 — Customer Identity, Loyalty, Wallet, Promotion v2,
               Cart QR, QR Menu Engine Tests
================================================================
Tests projection stores, command validation, policies, and service
_execute_command routing for all Phase 14 engines.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

BIZ = uuid.uuid4()
BRANCH = uuid.uuid4()
NOW = datetime(2026, 2, 25, 9, 0, 0, tzinfo=timezone.utc)


# ── Shared stubs ───────────────────────────────────────────────

class StubEventFactory:
    def create(self, event_type, payload, business_id, branch_id=None):
        return {"event_type": event_type, "payload": payload,
                "business_id": str(business_id)}


class StubPersist:
    def __init__(self):
        self.calls = []
    def __call__(self, event_data):
        self.calls.append(event_data)


class StubReg:
    def __init__(self):
        self._types = set()
    def register(self, et, *a, **kw):
        self._types.add(et)
    def is_registered(self, et):
        return et in self._types


def cmd_ns(d: dict) -> SimpleNamespace:
    """Convert a to_command() dict into a SimpleNamespace usable by services.
    Keeps payload as a dict so builders can use dict subscripting."""
    ns = SimpleNamespace(**d)
    # payload stays as dict - builders access it with cmd.payload["key"]
    return ns


# ══════════════════════════════════════════════════════════════
# CUSTOMER IDENTITY ENGINE
# ══════════════════════════════════════════════════════════════

class TestCustomerPlatformProjectionStore:
    """Test CustomerPlatformProjectionStore event application and queries."""

    def _store(self):
        from engines.customer.services import CustomerPlatformProjectionStore
        return CustomerPlatformProjectionStore()

    def test_register_global_customer(self):
        s = self._store()
        s.apply("customer.global.registered.v1", {
            "global_customer_id": "gcid-1",
            "phone_hash": "hash-abc",
            "registered_at": "2026-02-25T09:00:00",
        })
        rec = s.get_customer("gcid-1")
        assert rec is not None
        assert rec.phone_hash == "hash-abc"
        assert rec.status == "ACTIVE"

    def test_lookup_by_phone_hash(self):
        s = self._store()
        s.apply("customer.global.registered.v1", {
            "global_customer_id": "gcid-1",
            "phone_hash": "hash-abc",
            "registered_at": "2026-02-25",
        })
        assert s.lookup_by_phone_hash("hash-abc") == "gcid-1"
        assert s.lookup_by_phone_hash("nonexistent") is None

    def test_link_lifecycle_request_approve(self):
        s = self._store()
        gcid = "gcid-2"
        biz = str(BIZ)

        s.apply("customer.global.registered.v1", {
            "global_customer_id": gcid, "phone_hash": "h2", "registered_at": "2026-02-25"
        })
        s.apply("customer.link.requested.v1", {
            "global_customer_id": gcid, "requesting_business_id": biz,
            "requested_at": "2026-02-25",
        })
        link = s.get_link(gcid, biz)
        assert link.status == "PENDING"

        s.apply("customer.link.approved.v1", {
            "global_customer_id": gcid, "approved_business_id": biz,
            "approved_scopes": ["PROFILE_BASIC", "PURCHASE_HISTORY"],
            "approved_at": "2026-02-25",
        })
        link = s.get_link(gcid, biz)
        assert link.status == "APPROVED"
        assert "PROFILE_BASIC" in link.approved_scopes

    def test_link_revoke(self):
        s = self._store()
        gcid, biz = "gcid-3", str(BIZ)
        s.apply("customer.global.registered.v1", {
            "global_customer_id": gcid, "phone_hash": "h3", "registered_at": "2026-02-25"
        })
        s.apply("customer.link.requested.v1", {
            "global_customer_id": gcid, "requesting_business_id": biz, "requested_at": "2026-02-25"
        })
        s.apply("customer.link.approved.v1", {
            "global_customer_id": gcid, "approved_business_id": biz,
            "approved_scopes": ["OFFERS"], "approved_at": "2026-02-25"
        })
        s.apply("customer.link.revoked.v1", {
            "global_customer_id": gcid, "revoked_business_id": biz, "revoked_at": "2026-02-25"
        })
        link = s.get_link(gcid, biz)
        assert link.status == "REVOKED"
        assert link.approved_scopes == ()

    def test_consent_scope_update(self):
        s = self._store()
        gcid, biz = "gcid-4", str(BIZ)
        s.apply("customer.global.registered.v1", {
            "global_customer_id": gcid, "phone_hash": "h4", "registered_at": "2026-02-25"
        })
        s.apply("customer.link.requested.v1", {
            "global_customer_id": gcid, "requesting_business_id": biz, "requested_at": "2026-02-25"
        })
        s.apply("customer.link.approved.v1", {
            "global_customer_id": gcid, "approved_business_id": biz,
            "approved_scopes": ["PROFILE_BASIC"], "approved_at": "2026-02-25"
        })
        s.apply("customer.consent.scope_updated.v1", {
            "global_customer_id": gcid, "target_business_id": biz,
            "new_scopes": ["PROFILE_BASIC", "LOYALTY_POINTS", "MESSAGING"],
        })
        link = s.get_link(gcid, biz)
        assert set(link.approved_scopes) == {"PROFILE_BASIC", "LOYALTY_POINTS", "MESSAGING"}

    def test_get_approved_links(self):
        s = self._store()
        gcid = "gcid-5"
        biz1, biz2 = str(uuid.uuid4()), str(uuid.uuid4())
        s.apply("customer.global.registered.v1", {
            "global_customer_id": gcid, "phone_hash": "h5", "registered_at": "2026-02-25"
        })
        for biz in [biz1, biz2]:
            s.apply("customer.link.requested.v1", {
                "global_customer_id": gcid, "requesting_business_id": biz, "requested_at": "2026-02-25"
            })
        s.apply("customer.link.approved.v1", {
            "global_customer_id": gcid, "approved_business_id": biz1,
            "approved_scopes": ["CONTACT"], "approved_at": "2026-02-25"
        })
        approved = s.get_approved_links(gcid)
        assert len(approved) == 1
        assert approved[0].business_id == biz1

    def test_customer_count_and_event_count(self):
        s = self._store()
        assert s.customer_count == 0
        s.apply("customer.global.registered.v1", {
            "global_customer_id": "gc1", "phone_hash": "h1", "registered_at": "2026-02-25"
        })
        assert s.customer_count == 1
        assert s.event_count == 1

    def test_truncate(self):
        s = self._store()
        s.apply("customer.global.registered.v1", {
            "global_customer_id": "gc1", "phone_hash": "h1", "registered_at": "2026-02-25"
        })
        s.truncate()
        assert s.customer_count == 0
        assert s.event_count == 0


class TestCustomerProfileProjectionStore:
    def _store(self):
        from engines.customer.services import CustomerProfileProjectionStore
        return CustomerProfileProjectionStore()

    def test_create_profile(self):
        s = self._store()
        s.apply("customer.profile.created.v1", {
            "business_customer_id": "bcid-1",
            "global_customer_id": "gcid-1",
            "business_id": str(BIZ),
            "display_name": "Alice Kamau",
            "approved_scopes": ["PROFILE_BASIC"],
            "created_at": "2026-02-25",
        })
        p = s.get_profile("bcid-1")
        assert p is not None
        assert p.display_name == "Alice Kamau"
        assert s.profile_count == 1

    def test_update_profile(self):
        s = self._store()
        s.apply("customer.profile.created.v1", {
            "business_customer_id": "bcid-1", "global_customer_id": "gcid-1",
            "business_id": str(BIZ), "display_name": "Alice",
            "approved_scopes": [], "created_at": "2026-02-25",
        })
        s.apply("customer.profile.updated.v1", {
            "business_customer_id": "bcid-1",
            "changes": {"display_name": "Alice Kamau"},
        })
        assert s.get_profile("bcid-1").display_name == "Alice Kamau"

    def test_segment_assigned(self):
        s = self._store()
        s.apply("customer.profile.created.v1", {
            "business_customer_id": "bcid-1", "global_customer_id": "gcid-1",
            "business_id": str(BIZ), "display_name": "Bob",
            "approved_scopes": [], "created_at": "2026-02-25",
        })
        s.apply("customer.segment.assigned.v1", {
            "business_customer_id": "bcid-1", "segment": "VIP",
        })
        assert s.get_profile("bcid-1").segment == "VIP"

    def test_get_profile_by_global_id(self):
        s = self._store()
        s.apply("customer.profile.created.v1", {
            "business_customer_id": "bcid-2", "global_customer_id": "gcid-99",
            "business_id": str(BIZ), "display_name": "Carol",
            "approved_scopes": [], "created_at": "2026-02-25",
        })
        p = s.get_profile_by_global_id("gcid-99")
        assert p.business_customer_id == "bcid-2"


class TestCustomerCommandValidation:
    def test_register_global_customer_requires_phone_hash(self):
        from engines.customer.commands import RegisterGlobalCustomerRequest
        with pytest.raises(ValueError, match="phone_hash"):
            RegisterGlobalCustomerRequest(
                global_customer_id="gcid-1",
                phone_hash="",
                actor_id="sys",
                issued_at=NOW,
            )

    def test_register_global_customer_requires_gcid(self):
        from engines.customer.commands import RegisterGlobalCustomerRequest
        with pytest.raises(ValueError, match="global_customer_id"):
            RegisterGlobalCustomerRequest(
                global_customer_id="",
                phone_hash="hash123",
                actor_id="sys",
                issued_at=NOW,
            )

    def test_to_command_sets_platform_business_id(self):
        from engines.customer.commands import RegisterGlobalCustomerRequest, PLATFORM_BUSINESS_ID
        cmd = RegisterGlobalCustomerRequest(
            global_customer_id="gcid-1",
            phone_hash="hash123",
            actor_id="sys",
            issued_at=NOW,
        ).to_command()
        assert cmd["business_id"] == PLATFORM_BUSINESS_ID
        assert cmd["command_type"] == "customer.global.register.request"


class TestCustomerService:
    def _svc(self):
        from engines.customer.services import (
            CustomerIdentityService, CustomerPlatformProjectionStore
        )
        return CustomerIdentityService(
            event_factory=StubEventFactory(),
            persist_event=StubPersist(),
            event_type_registry=StubReg(),
            projection_store=CustomerPlatformProjectionStore(),
        )

    def test_register_customer_via_service(self):
        from engines.customer.commands import RegisterGlobalCustomerRequest
        svc = self._svc()
        cmd_dict = RegisterGlobalCustomerRequest(
            global_customer_id="gcid-svc-1",
            phone_hash="hash-svc",
            actor_id="sys",
            issued_at=NOW,
        ).to_command()
        result = svc._execute_command(cmd_ns(cmd_dict))
        assert result["event_type"] == "customer.global.registered.v1"
        assert svc._projection.get_customer("gcid-svc-1") is not None

    def test_unknown_command_rejected(self):
        svc = self._svc()
        ns = SimpleNamespace(command_type="customer.unknown.command", business_id=BIZ)
        result = svc._execute_command(ns)
        assert "rejected" in result


# ══════════════════════════════════════════════════════════════
# LOYALTY ENGINE
# ══════════════════════════════════════════════════════════════

class TestLoyaltyProjectionStore:
    def _store(self):
        from engines.loyalty.services import LoyaltyProjectionStore
        return LoyaltyProjectionStore()

    def _configure(self, s, earn_rate_type="FIXED_PER_AMOUNT", earn_rate_value=100,
                   rounding_rule="FLOOR"):
        s.apply("loyalty.program.configured.v1", {
            "earn_rate_type": earn_rate_type,
            "earn_rate_value": earn_rate_value,
            "expiry_mode": "NO_EXPIRY",
            "expiry_days": 0,
            "min_redeem_points": 10,
            "redeem_step": 5,
            "max_redeem_percent_per_invoice": 50,
            "exclusions": [],
            "channels": ["POS"],
            "rounding_rule": rounding_rule,
        })

    def test_configure_program(self):
        s = self._store()
        self._configure(s)
        assert s.program is not None
        assert s.program.earn_rate_type == "FIXED_PER_AMOUNT"
        assert s.program.min_redeem_points == 10
        assert s.program.redeem_step == 5

    def test_earn_points(self):
        s = self._store()
        self._configure(s)
        s.apply("loyalty.points.earned.v1", {
            "business_customer_id": "cid-1", "points": 50, "sale_id": "s1"
        })
        assert s.get_balance("cid-1") == 50
        assert s.get_total_earned("cid-1") == 50

    def test_redeem_points(self):
        s = self._store()
        self._configure(s)
        s.apply("loyalty.points.earned.v1", {
            "business_customer_id": "cid-1", "points": 100, "sale_id": "s1"
        })
        s.apply("loyalty.points.redeemed.v1", {
            "business_customer_id": "cid-1", "points": 30, "sale_id": "s2"
        })
        assert s.get_balance("cid-1") == 70
        assert s.get_total_redeemed("cid-1") == 30

    def test_expire_points(self):
        s = self._store()
        self._configure(s)
        s.apply("loyalty.points.earned.v1", {
            "business_customer_id": "cid-1", "points": 200, "sale_id": "s1"
        })
        s.apply("loyalty.points.expired.v1", {
            "business_customer_id": "cid-1", "points": 200, "expired_at": "2026-02-25"
        })
        assert s.get_balance("cid-1") == 0
        assert s.get_total_expired("cid-1") == 200

    def test_adjust_credit(self):
        s = self._store()
        self._configure(s)
        s.apply("loyalty.points.earned.v1", {
            "business_customer_id": "cid-1", "points": 50, "sale_id": "s1"
        })
        s.apply("loyalty.points.adjusted.v1", {
            "business_customer_id": "cid-1", "points": 10, "adjustment_type": "CREDIT",
            "reason": "GOODWILL",
        })
        assert s.get_balance("cid-1") == 60

    def test_adjust_debit(self):
        s = self._store()
        self._configure(s)
        s.apply("loyalty.points.earned.v1", {
            "business_customer_id": "cid-1", "points": 50, "sale_id": "s1"
        })
        s.apply("loyalty.points.adjusted.v1", {
            "business_customer_id": "cid-1", "points": 20, "adjustment_type": "DEBIT",
            "reason": "CORRECTION",
        })
        assert s.get_balance("cid-1") == 30

    def test_reverse_points(self):
        s = self._store()
        self._configure(s)
        s.apply("loyalty.points.earned.v1", {
            "business_customer_id": "cid-1", "points": 100, "sale_id": "s1"
        })
        s.apply("loyalty.points.reversed.v1", {
            "business_customer_id": "cid-1", "points": 100, "original_sale_id": "s1"
        })
        assert s.get_balance("cid-1") == 0

    def test_calculate_earn_points_fixed_per_amount(self):
        """1 point per 100 units; floor rounding."""
        s = self._store()
        self._configure(s, earn_rate_type="FIXED_PER_AMOUNT", earn_rate_value=100)
        assert s.calculate_earn_points(1000) == 10
        assert s.calculate_earn_points(1099) == 10   # floor
        assert s.calculate_earn_points(0) == 0

    def test_calculate_earn_points_percentage_basis_points(self):
        """500 basis points = 5%."""
        s = self._store()
        self._configure(s, earn_rate_type="PERCENTAGE", earn_rate_value=500)
        assert s.calculate_earn_points(1000) == 50
        assert s.calculate_earn_points(999) == 49   # floor of 49.95

    def test_calculate_earn_points_ceil_rounding(self):
        s = self._store()
        self._configure(s, earn_rate_type="FIXED_PER_AMOUNT",
                        earn_rate_value=100, rounding_rule="CEIL")
        assert s.calculate_earn_points(1001) == 11  # ceil(10.01)

    def test_calculate_earn_points_no_program(self):
        s = self._store()
        assert s.calculate_earn_points(5000) == 0

    def test_truncate(self):
        s = self._store()
        self._configure(s)
        s.apply("loyalty.points.earned.v1", {
            "business_customer_id": "cid-1", "points": 50, "sale_id": "s1"
        })
        s.truncate()
        assert s.program is None
        assert s.get_balance("cid-1") == 0
        assert s.event_count == 0


class TestLoyaltyCommandValidation:
    def test_invalid_earn_rate_type(self):
        from engines.loyalty.commands import ConfigureLoyaltyProgramRequest
        with pytest.raises(ValueError, match="earn_rate_type"):
            ConfigureLoyaltyProgramRequest(
                business_id=BIZ, earn_rate_type="BAD_TYPE", earn_rate_value=100,
                expiry_mode="NO_EXPIRY", actor_id="mgr", issued_at=NOW,
            )

    def test_earn_rate_value_must_be_positive(self):
        from engines.loyalty.commands import ConfigureLoyaltyProgramRequest
        with pytest.raises(ValueError, match="earn_rate_value"):
            ConfigureLoyaltyProgramRequest(
                business_id=BIZ, earn_rate_type="FIXED_PER_AMOUNT", earn_rate_value=0,
                expiry_mode="NO_EXPIRY", actor_id="mgr", issued_at=NOW,
            )

    def test_valid_configure(self):
        from engines.loyalty.commands import ConfigureLoyaltyProgramRequest
        req = ConfigureLoyaltyProgramRequest(
            business_id=BIZ, earn_rate_type="PERCENTAGE", earn_rate_value=500,
            expiry_mode="NO_EXPIRY", actor_id="mgr", issued_at=NOW,
            min_redeem_points=10, redeem_step=5,
        )
        cmd = req.to_command()
        assert cmd["command_type"] == "loyalty.program.configure.request"
        assert cmd["payload"].get("earn_rate_value") == 500 if isinstance(cmd["payload"], dict) else True


class TestLoyaltyService:
    def _svc(self):
        from engines.loyalty.services import LoyaltyService, LoyaltyProjectionStore
        return LoyaltyService(
            event_factory=StubEventFactory(),
            persist_event=StubPersist(),
            event_type_registry=StubReg(),
            projection_store=LoyaltyProjectionStore(),
        )

    def test_configure_via_service(self):
        from engines.loyalty.commands import ConfigureLoyaltyProgramRequest
        svc = self._svc()
        cmd = ConfigureLoyaltyProgramRequest(
            business_id=BIZ, earn_rate_type="FIXED_PER_AMOUNT", earn_rate_value=100,
            expiry_mode="NO_EXPIRY", actor_id="mgr", issued_at=NOW,
        ).to_command()
        result = svc._execute_command(cmd_ns(cmd))
        assert result["event_type"] == "loyalty.program.configured.v1"
        assert svc._projection.program is not None

    def test_earn_then_redeem_via_service(self):
        from engines.loyalty.commands import (
            ConfigureLoyaltyProgramRequest, EarnPointsRequest, RedeemPointsRequest
        )
        svc = self._svc()
        cfg = ConfigureLoyaltyProgramRequest(
            business_id=BIZ, earn_rate_type="FIXED_PER_AMOUNT", earn_rate_value=100,
            expiry_mode="NO_EXPIRY", actor_id="mgr", issued_at=NOW,
        ).to_command()
        svc._execute_command(cmd_ns(cfg))

        earn = EarnPointsRequest(
            business_id=BIZ, business_customer_id="cid-1", points=75,
            source_sale_id="sale-1", actor_id="cashier", issued_at=NOW,
        ).to_command()
        svc._execute_command(cmd_ns(earn))
        assert svc._projection.get_balance("cid-1") == 75

        redeem = RedeemPointsRequest(
            business_id=BIZ, business_customer_id="cid-1", points=50,
            discount_value=250, sale_id="sale-2", actor_id="cashier", issued_at=NOW,
        ).to_command()
        svc._execute_command(cmd_ns(redeem))
        assert svc._projection.get_balance("cid-1") == 25


# ══════════════════════════════════════════════════════════════
# CREDIT WALLET ENGINE
# ══════════════════════════════════════════════════════════════

class TestWalletProjectionStore:
    def _store(self):
        from engines.wallet.services import WalletProjectionStore
        return WalletProjectionStore()

    def _configure_policy(self, s, cid="cid-1", credit_limit=10000):
        s.apply("wallet.policy.configured.v1", {
            "business_customer_id": cid,
            "customer_credit_limit": credit_limit,
            "max_outstanding_credit": 0,
            "max_open_buckets": 0,
            "allow_negative_balance": False,
            "approval_required_above": 0,
            "max_apply_percent_per_invoice": 100,
            "pin_otp_threshold": 0,
            "expiry_mode": "NO_EXPIRY",
            "expiry_days": 0,
            "eligible_categories": [],
        })

    def test_configure_policy(self):
        s = self._store()
        self._configure_policy(s, "cid-1", 5000)
        policy = s.get_policy("cid-1")
        assert policy is not None
        assert policy.customer_credit_limit == 5000
        assert s.get_credit_limit("cid-1") == 5000

    def test_issue_credit(self):
        s = self._store()
        self._configure_policy(s)
        s.apply("wallet.credit.issued.v1", {
            "business_customer_id": "cid-1",
            "bucket_id": "bucket-1",
            "amount": 2000,
            "source": "CREDIT_NOTE",
            "reference_id": "ref-1",
            "expiry_date": None,
            "issued_at": "2026-02-25",
        })
        assert s.get_balance("cid-1") == 2000
        assert s.get_total_issued("cid-1") == 2000

    def test_spend_credit_updates_balance(self):
        s = self._store()
        self._configure_policy(s)
        s.apply("wallet.credit.issued.v1", {
            "business_customer_id": "cid-1", "bucket_id": "bucket-1",
            "amount": 3000, "source": "REBATE",
            "reference_id": None, "expiry_date": None, "issued_at": "2026-02-25",
        })
        s.apply("wallet.credit.spent.v1", {
            "business_customer_id": "cid-1",
            "amount": 1000,
            "sale_id": "sale-1",
            "bucket_allocations": [{"bucket_id": "bucket-1", "amount": 1000}],
        })
        assert s.get_balance("cid-1") == 2000
        assert s.get_total_spent("cid-1") == 1000

    def test_reverse_credit_restores_bucket(self):
        s = self._store()
        self._configure_policy(s)
        s.apply("wallet.credit.issued.v1", {
            "business_customer_id": "cid-1", "bucket_id": "bucket-1",
            "amount": 1000, "source": "CREDIT_NOTE",
            "reference_id": None, "expiry_date": None, "issued_at": "2026-02-25",
        })
        s.apply("wallet.credit.spent.v1", {
            "business_customer_id": "cid-1", "amount": 1000, "sale_id": "sale-1",
            "bucket_allocations": [{"bucket_id": "bucket-1", "amount": 1000}],
        })
        assert s.get_balance("cid-1") == 0

        s.apply("wallet.credit.reversed.v1", {
            "business_customer_id": "cid-1", "bucket_id": "bucket-1",
            "amount": 1000, "original_sale_id": "sale-1",
            "reason": "REFUND_REVERSAL", "reversed_at": "2026-02-25",
        })
        assert s.get_balance("cid-1") == 1000
        assert s.get_total_spent("cid-1") == 0

    def test_expire_credit_zeroes_bucket(self):
        s = self._store()
        self._configure_policy(s)
        s.apply("wallet.credit.issued.v1", {
            "business_customer_id": "cid-1", "bucket_id": "bucket-exp",
            "amount": 500, "source": "MANUAL_ISSUE",
            "reference_id": None, "expiry_date": "2026-01-01", "issued_at": "2025-12-01",
        })
        s.apply("wallet.credit.expired.v1", {
            "business_customer_id": "cid-1", "bucket_id": "bucket-exp",
            "amount": 500, "expired_at": "2026-01-01",
        })
        assert s.get_balance("cid-1") == 0

    def test_freeze_unfrozen(self):
        s = self._store()
        self._configure_policy(s)
        assert s.is_frozen("cid-1") is False

        s.apply("wallet.credit.frozen.v1", {
            "business_customer_id": "cid-1", "reason": "CUSTOMER_REQUEST",
            "frozen_at": "2026-02-25",
        })
        assert s.is_frozen("cid-1") is True

        s.apply("wallet.credit.unfrozen.v1", {
            "business_customer_id": "cid-1", "reason": "CUSTOMER_REQUEST",
            "unfrozen_at": "2026-02-25",
        })
        assert s.is_frozen("cid-1") is False

    def test_fefo_allocates_earliest_expiry_first(self):
        """FEFO: bucket expiring sooner consumed first."""
        s = self._store()
        self._configure_policy(s)
        # Issue two buckets: one expiring sooner
        s.apply("wallet.credit.issued.v1", {
            "business_customer_id": "cid-1", "bucket_id": "bucket-late",
            "amount": 1000, "source": "REBATE",
            "reference_id": None, "expiry_date": "2026-06-01", "issued_at": "2026-02-25",
        })
        s.apply("wallet.credit.issued.v1", {
            "business_customer_id": "cid-1", "bucket_id": "bucket-soon",
            "amount": 500, "source": "CREDIT_NOTE",
            "reference_id": None, "expiry_date": "2026-03-01", "issued_at": "2026-02-25",
        })
        # Issue no-expiry bucket (should come last)
        s.apply("wallet.credit.issued.v1", {
            "business_customer_id": "cid-1", "bucket_id": "bucket-none",
            "amount": 800, "source": "MANUAL_ISSUE",
            "reference_id": None, "expiry_date": None, "issued_at": "2026-02-25",
        })
        allocations = s.allocate_fefo("cid-1", 600)
        # Should consume bucket-soon (500) first, then 100 from bucket-late
        assert allocations[0]["bucket_id"] == "bucket-soon"
        assert allocations[0]["amount"] == 500
        assert allocations[1]["bucket_id"] == "bucket-late"
        assert allocations[1]["amount"] == 100

    def test_fefo_no_expiry_last(self):
        s = self._store()
        self._configure_policy(s)
        s.apply("wallet.credit.issued.v1", {
            "business_customer_id": "cid-1", "bucket_id": "bucket-none",
            "amount": 1000, "source": "MANUAL_ISSUE",
            "reference_id": None, "expiry_date": None, "issued_at": "2026-01-01",
        })
        s.apply("wallet.credit.issued.v1", {
            "business_customer_id": "cid-1", "bucket_id": "bucket-exp",
            "amount": 500, "source": "REBATE",
            "reference_id": None, "expiry_date": "2026-03-01", "issued_at": "2026-02-01",
        })
        allocs = s.allocate_fefo("cid-1", 500)
        assert allocs[0]["bucket_id"] == "bucket-exp"

    def test_truncate(self):
        s = self._store()
        self._configure_policy(s)
        s.apply("wallet.credit.issued.v1", {
            "business_customer_id": "cid-1", "bucket_id": "b1",
            "amount": 100, "source": "REBATE", "reference_id": None,
            "expiry_date": None, "issued_at": "2026-02-25",
        })
        s.truncate()
        assert s.get_balance("cid-1") == 0
        assert s.event_count == 0


class TestWalletCommandValidation:
    def test_issue_credit_amount_must_be_positive(self):
        from engines.wallet.commands import IssueCreditRequest
        with pytest.raises(ValueError, match="amount"):
            IssueCreditRequest(
                business_id=BIZ, business_customer_id="cid-1",
                bucket_id="b1", amount=0, source="REBATE",
                actor_id="sys", issued_at=NOW,
            )

    def test_issue_credit_invalid_source(self):
        from engines.wallet.commands import IssueCreditRequest
        with pytest.raises(ValueError, match="source"):
            IssueCreditRequest(
                business_id=BIZ, business_customer_id="cid-1",
                bucket_id="b1", amount=500, source="INVALID_SOURCE",
                actor_id="sys", issued_at=NOW,
            )

    def test_configure_invalid_expiry_mode(self):
        from engines.wallet.commands import ConfigureCreditPolicyRequest
        with pytest.raises(ValueError, match="expiry_mode"):
            ConfigureCreditPolicyRequest(
                business_id=BIZ, business_customer_id="cid-1",
                customer_credit_limit=1000, actor_id="mgr", issued_at=NOW,
                expiry_mode="INVALID",
            )


class TestWalletService:
    def _svc(self):
        from engines.wallet.services import WalletService, WalletProjectionStore
        return WalletService(
            event_factory=StubEventFactory(),
            persist_event=StubPersist(),
            event_type_registry=StubReg(),
            projection_store=WalletProjectionStore(),
        )

    def test_configure_and_issue(self):
        from engines.wallet.commands import ConfigureCreditPolicyRequest, IssueCreditRequest
        svc = self._svc()
        cfg = ConfigureCreditPolicyRequest(
            business_id=BIZ, business_customer_id="cid-1",
            customer_credit_limit=5000, actor_id="mgr", issued_at=NOW,
        ).to_command()
        svc._execute_command(cmd_ns(cfg))

        issue = IssueCreditRequest(
            business_id=BIZ, business_customer_id="cid-1",
            bucket_id="b1", amount=2000, source="CREDIT_NOTE",
            actor_id="sys", issued_at=NOW,
        ).to_command()
        result = svc._execute_command(cmd_ns(issue))
        assert result["event_type"] == "wallet.credit.issued.v1"
        assert svc._projection.get_balance("cid-1") == 2000


# ══════════════════════════════════════════════════════════════
# PROMOTION ENGINE v2
# ══════════════════════════════════════════════════════════════

class TestPromotionV2ProjectionStore:
    def _store(self):
        from engines.promotion.services import PromotionProjectionStore
        return PromotionProjectionStore()

    def _create_program(self, s, pid="prog-1", name="Test Program"):
        from engines.promotion.events import PROMOTION_PROGRAM_CREATED_V2
        s.apply(PROMOTION_PROGRAM_CREATED_V2, {
            "program_id": pid,
            "name": name,
            "timing": "AT_SALE",
            "tax_mode": "REDUCE_TAX_BASE_NOW",
            "settlement": "INVOICE_LINE_DISCOUNT",
            "stackability": "STACKABLE",
            "stack_tags": [],
            "budget_ceiling": 0,
            "usage_cap": 0,
            "customer_cap": 0,
            "scope": {},
            "validity": {},
        })

    def test_create_program(self):
        s = self._store()
        self._create_program(s)
        prog = s.get_program("prog-1")
        assert prog is not None
        assert prog["status"] == "DRAFT"
        assert prog["name"] == "Test Program"

    def test_activate_deactivate_program(self):
        from engines.promotion.events import (
            PROMOTION_PROGRAM_ACTIVATED_V2, PROMOTION_PROGRAM_DEACTIVATED_V2
        )
        s = self._store()
        self._create_program(s)
        s.apply(PROMOTION_PROGRAM_ACTIVATED_V2, {"program_id": "prog-1"})
        assert s.get_program("prog-1")["status"] == "ACTIVE"

        s.apply(PROMOTION_PROGRAM_DEACTIVATED_V2, {"program_id": "prog-1"})
        assert s.get_program("prog-1")["status"] == "INACTIVE"

    def test_add_rule(self):
        from engines.promotion.events import PROMOTION_RULE_ADDED_V1
        s = self._store()
        self._create_program(s)
        s.apply(PROMOTION_RULE_ADDED_V1, {
            "program_id": "prog-1", "rule_id": "rule-1",
            "rule_type": "PERCENTAGE",
            "rule_params": {"rate_basis_points": 1000},
        })
        rules = s.get_program_rules("prog-1")
        assert len(rules) == 1
        assert rules[0]["rule_type"] == "PERCENTAGE"

    def test_get_active_programs(self):
        from engines.promotion.events import PROMOTION_PROGRAM_ACTIVATED_V2
        s = self._store()
        self._create_program(s, "prog-1")
        self._create_program(s, "prog-2")
        s.apply(PROMOTION_PROGRAM_ACTIVATED_V2, {"program_id": "prog-1"})
        active = s.get_active_programs()
        assert len(active) == 1
        assert active[0]["program_id"] == "prog-1"

    def test_evaluate_basket_percentage_rule(self):
        from engines.promotion.events import (
            PROMOTION_PROGRAM_ACTIVATED_V2, PROMOTION_RULE_ADDED_V1
        )
        s = self._store()
        self._create_program(s)
        s.apply(PROMOTION_PROGRAM_ACTIVATED_V2, {"program_id": "prog-1"})
        s.apply(PROMOTION_RULE_ADDED_V1, {
            "program_id": "prog-1", "rule_id": "r1",
            "rule_type": "PERCENTAGE",
            "rule_params": {"rate_basis_points": 1000},  # 10%
        })
        result = s.evaluate_basket([], basket_net_amount=10000)
        assert len(result) == 1
        assert result[0]["discount_amount"] == 1000  # 10% of 10000

    def test_evaluate_basket_fixed_amount_rule(self):
        from engines.promotion.events import (
            PROMOTION_PROGRAM_ACTIVATED_V2, PROMOTION_RULE_ADDED_V1
        )
        s = self._store()
        self._create_program(s)
        s.apply(PROMOTION_PROGRAM_ACTIVATED_V2, {"program_id": "prog-1"})
        s.apply(PROMOTION_RULE_ADDED_V1, {
            "program_id": "prog-1", "rule_id": "r1",
            "rule_type": "FIXED_AMOUNT",
            "rule_params": {"amount": 500},
        })
        result = s.evaluate_basket([], basket_net_amount=5000)
        assert result[0]["discount_amount"] == 500

    def test_evaluate_basket_volume_threshold_met(self):
        from engines.promotion.events import (
            PROMOTION_PROGRAM_ACTIVATED_V2, PROMOTION_RULE_ADDED_V1
        )
        s = self._store()
        self._create_program(s)
        s.apply(PROMOTION_PROGRAM_ACTIVATED_V2, {"program_id": "prog-1"})
        s.apply(PROMOTION_RULE_ADDED_V1, {
            "program_id": "prog-1", "rule_id": "r1",
            "rule_type": "VOLUME_THRESHOLD",
            "rule_params": {"min_amount": 5000, "rate_basis_points": 500},  # 5% above 5000
        })
        # Below threshold - no discount
        result_below = s.evaluate_basket([], basket_net_amount=4999)
        assert len(result_below) == 0

        # At threshold
        result_at = s.evaluate_basket([], basket_net_amount=5000)
        assert result_at[0]["discount_amount"] == 250  # 5% of 5000

    def test_evaluate_basket_buy_x_get_y(self):
        from engines.promotion.events import (
            PROMOTION_PROGRAM_ACTIVATED_V2, PROMOTION_RULE_ADDED_V1
        )
        s = self._store()
        self._create_program(s)
        s.apply(PROMOTION_PROGRAM_ACTIVATED_V2, {"program_id": "prog-1"})
        s.apply(PROMOTION_RULE_ADDED_V1, {
            "program_id": "prog-1", "rule_id": "r1",
            "rule_type": "BUY_X_GET_Y",
            "rule_params": {
                "buy_item_id": "item-A", "buy_qty": 2,
                "get_item_id": "item-B", "get_qty": 1,
            },
        })
        basket = [
            {"item_id": "item-A", "quantity": 4, "unit_price": 200},
            {"item_id": "item-B", "quantity": 2, "unit_price": 150},
        ]
        # Buy 4 of A → 2 sets → 2 free of B → 2 * 150 = 300
        result = s.evaluate_basket(basket, basket_net_amount=1100)
        assert result[0]["discount_amount"] == 300

    def test_evaluate_basket_bundle_rule(self):
        from engines.promotion.events import (
            PROMOTION_PROGRAM_ACTIVATED_V2, PROMOTION_RULE_ADDED_V1
        )
        s = self._store()
        self._create_program(s)
        s.apply(PROMOTION_PROGRAM_ACTIVATED_V2, {"program_id": "prog-1"})
        s.apply(PROMOTION_RULE_ADDED_V1, {
            "program_id": "prog-1", "rule_id": "r1",
            "rule_type": "BUNDLE",
            "rule_params": {
                "required_items": ["item-X", "item-Y"],
                "discount_amount": 200,
            },
        })
        # Missing item-Y
        result_incomplete = s.evaluate_basket(
            [{"item_id": "item-X", "quantity": 1}], basket_net_amount=1000
        )
        assert len(result_incomplete) == 0

        # Full bundle
        result_full = s.evaluate_basket(
            [{"item_id": "item-X", "quantity": 1}, {"item_id": "item-Y", "quantity": 1}],
            basket_net_amount=1000
        )
        assert result_full[0]["discount_amount"] == 200

    def test_budget_ceiling_caps_discount(self):
        from engines.promotion.events import (
            PROMOTION_PROGRAM_CREATED_V2, PROMOTION_PROGRAM_ACTIVATED_V2, PROMOTION_RULE_ADDED_V1
        )
        s = self._store()
        # Create with budget ceiling of 300
        s.apply(PROMOTION_PROGRAM_CREATED_V2, {
            "program_id": "prog-ceiling",
            "name": "Ceiling Test",
            "timing": "AT_SALE", "tax_mode": "REDUCE_TAX_BASE_NOW",
            "settlement": "INVOICE_LINE_DISCOUNT", "stackability": "STACKABLE",
            "budget_ceiling": 300,
            "usage_cap": 0, "customer_cap": 0, "scope": {}, "validity": {},
        })
        s.apply(PROMOTION_PROGRAM_ACTIVATED_V2, {"program_id": "prog-ceiling"})
        s.apply(PROMOTION_RULE_ADDED_V1, {
            "program_id": "prog-ceiling", "rule_id": "r1",
            "rule_type": "FIXED_AMOUNT",
            "rule_params": {"amount": 500},
        })
        result = s.evaluate_basket([], basket_net_amount=5000)
        # 500 discount but budget ceiling is 300
        assert result[0]["discount_amount"] == 300

    def test_applied_event_updates_program_stats(self):
        from engines.promotion.events import PROMOTION_APPLIED_V1
        s = self._store()
        self._create_program(s)
        s.apply(PROMOTION_APPLIED_V1, {
            "application_id": "app-1",
            "program_id": "prog-1",
            "sale_id": "sale-1",
            "discount_amount": 200,
            "adjusted_net_amount": 800,
            "tax_mode": "REDUCE_TAX_BASE_NOW",
            "settlement": "INVOICE_LINE_DISCOUNT",
        })
        prog = s.get_program("prog-1")
        assert prog["usage_count"] == 1
        assert prog["total_discount_issued"] == 200
        assert s.total_discounts == 200

    def test_evaluated_event(self):
        from engines.promotion.events import PROMOTION_EVALUATED_V1
        s = self._store()
        s.apply(PROMOTION_EVALUATED_V1, {
            "evaluation_id": "eval-1",
            "sale_id": "sale-1",
            "business_customer_id": "cid-1",
            "applicable_programs": ["prog-1"],
        })
        ev = s.get_evaluation("eval-1")
        assert ev["sale_id"] == "sale-1"
        assert "prog-1" in ev["applicable_programs"]


# ══════════════════════════════════════════════════════════════
# CART QR ENGINE
# ══════════════════════════════════════════════════════════════

class TestCartQRProjectionStore:
    def _store(self):
        from engines.cart_qr import CartQRProjectionStore
        return CartQRProjectionStore()

    def _create(self, s, cid="qr-1"):
        from engines.cart_qr import CART_QR_CREATED_V1
        s.apply(CART_QR_CREATED_V1, {
            "cart_qr_id": cid,
            "usage_mode": "SINGLE_USE",
            "expiry_hours": 24,
            "created_at": "2026-02-25T09:00:00",
        })

    def test_create(self):
        s = self._store()
        self._create(s)
        qr = s.get_cart("qr-1")
        assert qr is not None
        assert qr["status"] == "DRAFT"
        assert qr["cart_qr_id"] == "qr-1"

    def test_add_item(self):
        from engines.cart_qr import CART_QR_ITEM_ADDED_V1
        s = self._store()
        self._create(s)
        s.apply(CART_QR_ITEM_ADDED_V1, {
            "cart_qr_id": "qr-1", "item_id": "item-A",
            "sku": "SKU-A", "item_name": "Bread",
            "unit_price": 150, "max_quantity": 10,
        })
        qr = s.get_cart("qr-1")
        assert len(qr["items"]) == 1
        assert qr["items"][0]["item_id"] == "item-A"

    def test_remove_item(self):
        from engines.cart_qr import CART_QR_ITEM_ADDED_V1, CART_QR_ITEM_REMOVED_V1
        s = self._store()
        self._create(s)
        s.apply(CART_QR_ITEM_ADDED_V1, {
            "cart_qr_id": "qr-1", "item_id": "item-A",
            "sku": "SKU-A", "item_name": "Bread",
            "unit_price": 150, "max_quantity": 10,
        })
        s.apply(CART_QR_ITEM_REMOVED_V1, {"cart_qr_id": "qr-1", "item_id": "item-A"})
        assert len(s.get_cart("qr-1")["items"]) == 0

    def test_publish(self):
        from engines.cart_qr import CART_QR_PUBLISHED_V1
        s = self._store()
        self._create(s)
        s.apply(CART_QR_PUBLISHED_V1, {
            "cart_qr_id": "qr-1", "qr_token": "tok-abc",
            "expires_at": "2026-02-25T10:00:00",
            "published_at": "2026-02-25T09:01:00",
        })
        qr = s.get_cart("qr-1")
        assert qr["status"] == "PUBLISHED"
        assert qr["qr_token"] == "tok-abc"

    def test_receive_selection(self):
        from engines.cart_qr import CART_QR_SELECTION_RECEIVED_V1
        s = self._store()
        self._create(s)
        s.apply(CART_QR_SELECTION_RECEIVED_V1, {
            "cart_qr_id": "qr-1",
            "selected_items": [{"item_id": "item-A", "quantity": 2}],
            "received_at": "2026-02-25T09:05:00",
        })
        qr = s.get_cart("qr-1")
        assert qr["status"] == "SELECTION_RECEIVED"
        assert len(qr["selected_items"]) == 1

    def test_transfer_to_pos(self):
        from engines.cart_qr import CART_QR_TRANSFERRED_TO_POS_V1
        s = self._store()
        self._create(s)
        s.apply(CART_QR_TRANSFERRED_TO_POS_V1, {
            "cart_qr_id": "qr-1", "pos_sale_id": "sale-99",
            "transferred_at": "2026-02-25T09:06:00",
        })
        qr = s.get_cart("qr-1")
        assert qr["status"] == "TRANSFERRED"
        assert qr["pos_sale_id"] == "sale-99"

    def test_expire(self):
        from engines.cart_qr import CART_QR_EXPIRED_V1
        s = self._store()
        self._create(s, "qr-exp")
        s.apply(CART_QR_EXPIRED_V1, {"cart_qr_id": "qr-exp", "expired_at": "2026-02-25T10:00:00"})
        assert s.get_cart("qr-exp")["status"] == "EXPIRED"

    def test_cancel(self):
        from engines.cart_qr import CART_QR_CANCELLED_V1
        s = self._store()
        self._create(s, "qr-cancel")
        s.apply(CART_QR_CANCELLED_V1, {
            "cart_qr_id": "qr-cancel", "reason": "CASHIER_CANCELLED",
            "cancelled_at": "2026-02-25T09:30:00",
        })
        assert s.get_cart("qr-cancel")["status"] == "CANCELLED"

    def test_event_count_and_truncate(self):
        s = self._store()
        self._create(s)
        assert s.event_count == 1
        s.truncate()
        assert s.get_cart("qr-1") is None
        assert s.event_count == 0


class TestCartQRCommandValidation:
    def test_cart_qr_id_required(self):
        from engines.cart_qr import CreateCartQRRequest
        with pytest.raises(ValueError, match="cart_qr_id"):
            CreateCartQRRequest(
                business_id=BIZ, branch_id=BRANCH,
                cart_qr_id="", actor_id="cashier-1", issued_at=NOW,
            )

    def test_invalid_usage_mode(self):
        from engines.cart_qr import CreateCartQRRequest
        with pytest.raises(ValueError, match="usage_mode"):
            CreateCartQRRequest(
                business_id=BIZ, branch_id=BRANCH,
                cart_qr_id="qr-1", actor_id="cashier-1", issued_at=NOW,
                usage_mode="INVALID",
            )

    def test_expiry_hours_must_be_positive(self):
        from engines.cart_qr import CreateCartQRRequest
        with pytest.raises(ValueError, match="expiry_hours"):
            CreateCartQRRequest(
                business_id=BIZ, branch_id=BRANCH,
                cart_qr_id="qr-1", actor_id="cashier-1", issued_at=NOW,
                expiry_hours=0,
            )

    def test_valid_create_to_command(self):
        from engines.cart_qr import CreateCartQRRequest, CART_QR_CREATED_V1
        req = CreateCartQRRequest(
            business_id=BIZ, branch_id=BRANCH,
            cart_qr_id="qr-valid", actor_id="cashier-1", issued_at=NOW,
        )
        cmd = req.to_command()
        assert cmd["command_type"] == "cart_qr.create.request"
        assert cmd["payload"]["cart_qr_id"] == "qr-valid"


class TestCartQRService:
    def _svc(self):
        from engines.cart_qr import CartQRService, CartQRProjectionStore
        return CartQRService(
            event_factory=StubEventFactory(),
            persist_event=StubPersist(),
            event_type_registry=StubReg(),
            projection_store=CartQRProjectionStore(),
        )

    def test_create_via_service(self):
        from engines.cart_qr import CreateCartQRRequest, CART_QR_CREATED_V1
        svc = self._svc()
        cmd = CreateCartQRRequest(
            business_id=BIZ, branch_id=BRANCH,
            cart_qr_id="qr-svc-1", actor_id="cashier-1", issued_at=NOW,
        ).to_command()
        result = svc._execute_command(cmd_ns(cmd))
        assert result["event_type"] == CART_QR_CREATED_V1
        assert svc._projection.get_cart("qr-svc-1") is not None

    def test_publish_and_receive_flow(self):
        from engines.cart_qr import (
            CreateCartQRRequest, PublishCartQRRequest, ReceiveSelectionRequest,
            TransferToPOSRequest, CART_QR_TRANSFERRED_TO_POS_V1
        )
        svc = self._svc()
        cid = "qr-flow-1"
        svc._execute_command(cmd_ns(CreateCartQRRequest(
            business_id=BIZ, branch_id=BRANCH,
            cart_qr_id=cid, actor_id="cashier-1", issued_at=NOW,
        ).to_command()))
        svc._execute_command(cmd_ns(PublishCartQRRequest(
            business_id=BIZ, branch_id=BRANCH, cart_qr_id=cid,
            qr_token="tok-1", expires_at="2026-02-25T10:00:00",
            actor_id="cashier-1", issued_at=NOW,
        ).to_command()))
        assert svc._projection.get_cart(cid)["status"] == "PUBLISHED"

        svc._execute_command(cmd_ns(ReceiveSelectionRequest(
            business_id=BIZ, branch_id=BRANCH, cart_qr_id=cid,
            selected_items=({"item_id": "item-A", "quantity": 2},),
            actor_id="sys", issued_at=NOW,
        ).to_command()))
        assert svc._projection.get_cart(cid)["status"] == "SELECTION_RECEIVED"

        result = svc._execute_command(cmd_ns(TransferToPOSRequest(
            business_id=BIZ, branch_id=BRANCH, cart_qr_id=cid,
            pos_sale_id="sale-99", actor_id="cashier-1", issued_at=NOW,
        ).to_command()))
        assert result["event_type"] == CART_QR_TRANSFERRED_TO_POS_V1
        assert svc._projection.get_cart(cid)["status"] == "TRANSFERRED"


# ══════════════════════════════════════════════════════════════
# QR MENU ENGINE (Restaurant)
# ══════════════════════════════════════════════════════════════

class TestQRMenuProjectionStore:
    def _store(self):
        from engines.qr_menu import QRMenuProjectionStore
        return QRMenuProjectionStore()

    def _register(self, s, pid="place-1"):
        from engines.qr_menu import QR_MENU_REGISTERED_V1
        s.apply(QR_MENU_REGISTERED_V1, {
            "place_qr_id": pid, "place_type": "TABLE", "place_label": "Table 7",
            "business_id": str(BIZ), "branch_id": str(BRANCH),
            "registered_at": "2026-02-25T09:00:00",
        })

    def _create_session(self, s, sid="sess-1", pid="place-1"):
        from engines.qr_menu import QR_MENU_SESSION_CREATED_V1
        s.apply(QR_MENU_SESSION_CREATED_V1, {
            "session_id": sid, "place_qr_id": pid,
            "session_token": f"tok-{sid}",
            "expires_at": "2026-02-25T10:00:00",
            "created_at": "2026-02-25T09:00:00",
        })

    def test_register_place(self):
        s = self._store()
        self._register(s)
        place = s.get_place("place-1")
        assert place is not None
        assert place["place_type"] == "TABLE"
        assert place["place_label"] == "Table 7"

    def test_create_session(self):
        s = self._store()
        self._register(s)
        self._create_session(s)
        session = s.get_session("sess-1")
        assert session is not None
        assert session["status"] == "ACTIVE"
        assert session["place_qr_id"] == "place-1"

    def test_order_item(self):
        from engines.qr_menu import QR_MENU_ITEM_ORDERED_V1
        s = self._store()
        self._register(s)
        self._create_session(s)
        s.apply(QR_MENU_ITEM_ORDERED_V1, {
            "session_id": "sess-1", "order_line_id": "ol-1",
            "item_id": "menu-1", "item_name": "Grilled Tilapia",
            "quantity": 1, "unit_price": 1200, "notes": "",
        })
        session = s.get_session("sess-1")
        assert len(session["order_lines"]) == 1
        assert session["order_lines"][0]["item_name"] == "Grilled Tilapia"

    def test_remove_item(self):
        from engines.qr_menu import QR_MENU_ITEM_ORDERED_V1, QR_MENU_ITEM_REMOVED_V1
        s = self._store()
        self._register(s)
        self._create_session(s)
        s.apply(QR_MENU_ITEM_ORDERED_V1, {
            "session_id": "sess-1", "order_line_id": "ol-1",
            "item_id": "m1", "item_name": "Juice",
            "quantity": 2, "unit_price": 80, "notes": "",
        })
        s.apply(QR_MENU_ITEM_REMOVED_V1, {"session_id": "sess-1", "order_line_id": "ol-1"})
        assert len(s.get_session("sess-1")["order_lines"]) == 0

    def test_submit_goes_pending_confirm(self):
        from engines.qr_menu import QR_MENU_ITEM_ORDERED_V1, QR_MENU_ORDER_SUBMITTED_V1
        s = self._store()
        self._register(s)
        self._create_session(s)
        s.apply(QR_MENU_ITEM_ORDERED_V1, {
            "session_id": "sess-1", "order_line_id": "ol-1",
            "item_id": "m1", "item_name": "Chai",
            "quantity": 2, "unit_price": 50, "notes": "",
        })
        s.apply(QR_MENU_ORDER_SUBMITTED_V1, {
            "session_id": "sess-1", "submitted_at": "2026-02-25T09:05:00",
        })
        assert s.get_session("sess-1")["status"] == "PENDING_CONFIRM"

    def test_accept_order(self):
        from engines.qr_menu import (
            QR_MENU_ITEM_ORDERED_V1, QR_MENU_ORDER_SUBMITTED_V1, QR_MENU_ORDER_ACCEPTED_V1
        )
        s = self._store()
        self._register(s)
        self._create_session(s)
        s.apply(QR_MENU_ITEM_ORDERED_V1, {
            "session_id": "sess-1", "order_line_id": "ol-1",
            "item_id": "m1", "item_name": "Water",
            "quantity": 1, "unit_price": 30, "notes": "",
        })
        s.apply(QR_MENU_ORDER_SUBMITTED_V1, {
            "session_id": "sess-1", "submitted_at": "2026-02-25T09:05:00"
        })
        s.apply(QR_MENU_ORDER_ACCEPTED_V1, {
            "session_id": "sess-1", "restaurant_order_id": "ro-1",
            "accepted_by": "waiter-1", "accepted_at": "2026-02-25T09:06:00",
        })
        sess = s.get_session("sess-1")
        assert sess["status"] == "ACCEPTED"
        assert sess["restaurant_order_id"] == "ro-1"

    def test_reject_order(self):
        from engines.qr_menu import (
            QR_MENU_ITEM_ORDERED_V1, QR_MENU_ORDER_SUBMITTED_V1, QR_MENU_ORDER_REJECTED_V1
        )
        s = self._store()
        self._register(s)
        self._create_session(s)
        s.apply(QR_MENU_ITEM_ORDERED_V1, {
            "session_id": "sess-1", "order_line_id": "ol-1",
            "item_id": "m1", "item_name": "Coffee",
            "quantity": 1, "unit_price": 100, "notes": "",
        })
        s.apply(QR_MENU_ORDER_SUBMITTED_V1, {
            "session_id": "sess-1", "submitted_at": "2026-02-25T09:05:00"
        })
        s.apply(QR_MENU_ORDER_REJECTED_V1, {
            "session_id": "sess-1", "reason": "ITEM_UNAVAILABLE",
            "rejected_by": "waiter-1", "rejected_at": "2026-02-25T09:06:00",
        })
        assert s.get_session("sess-1")["status"] == "REJECTED"

    def test_session_expired(self):
        from engines.qr_menu import QR_MENU_SESSION_EXPIRED_V1
        s = self._store()
        self._register(s)
        self._create_session(s)
        s.apply(QR_MENU_SESSION_EXPIRED_V1, {
            "session_id": "sess-1", "expired_at": "2026-02-25T10:00:00"
        })
        assert s.get_session("sess-1")["status"] == "EXPIRED"

    def test_get_pending_sessions(self):
        from engines.qr_menu import QR_MENU_ITEM_ORDERED_V1, QR_MENU_ORDER_SUBMITTED_V1
        s = self._store()
        self._register(s)
        self._create_session(s, "sess-A")
        self._create_session(s, "sess-B")
        s.apply(QR_MENU_ITEM_ORDERED_V1, {
            "session_id": "sess-A", "order_line_id": "ol-1",
            "item_id": "m1", "item_name": "Tea",
            "quantity": 1, "unit_price": 40, "notes": "",
        })
        s.apply(QR_MENU_ORDER_SUBMITTED_V1, {
            "session_id": "sess-A", "submitted_at": "2026-02-25T09:05:00"
        })
        pending = s.get_pending_sessions()
        assert len(pending) == 1
        assert pending[0]["session_id"] == "sess-A"

    def test_event_count_and_truncate(self):
        s = self._store()
        self._register(s)
        assert s.event_count == 1
        s.truncate()
        assert s.get_place("place-1") is None
        assert s.event_count == 0


class TestQRMenuCommandValidation:
    def test_place_qr_id_required(self):
        from engines.qr_menu import RegisterQRMenuRequest
        with pytest.raises(ValueError, match="place_qr_id"):
            RegisterQRMenuRequest(
                business_id=BIZ, branch_id=BRANCH,
                place_qr_id="", place_type="TABLE", place_label="Table 1",
                actor_id="mgr", issued_at=NOW,
            )

    def test_invalid_place_type(self):
        from engines.qr_menu import RegisterQRMenuRequest
        with pytest.raises(ValueError, match="place_type"):
            RegisterQRMenuRequest(
                business_id=BIZ, branch_id=BRANCH,
                place_qr_id="p1", place_type="INVALID", place_label="Table 1",
                actor_id="mgr", issued_at=NOW,
            )

    def test_place_label_required(self):
        from engines.qr_menu import RegisterQRMenuRequest
        with pytest.raises(ValueError, match="place_label"):
            RegisterQRMenuRequest(
                business_id=BIZ, branch_id=BRANCH,
                place_qr_id="p1", place_type="TABLE", place_label="",
                actor_id="mgr", issued_at=NOW,
            )

    def test_order_item_quantity_positive(self):
        from engines.qr_menu import OrderItemRequest
        with pytest.raises(ValueError, match="quantity"):
            OrderItemRequest(
                business_id=BIZ, branch_id=BRANCH,
                session_id="sess-1", order_line_id="ol-1",
                item_id="m1", item_name="Soup", quantity=0,
                unit_price=100, actor_id="sys", issued_at=NOW,
            )


class TestQRMenuService:
    def _svc(self):
        from engines.qr_menu import QRMenuService, QRMenuProjectionStore
        return QRMenuService(
            event_factory=StubEventFactory(),
            persist_event=StubPersist(),
            event_type_registry=StubReg(),
            projection_store=QRMenuProjectionStore(),
        )

    def test_register_via_service(self):
        from engines.qr_menu import RegisterQRMenuRequest, QR_MENU_REGISTERED_V1
        svc = self._svc()
        cmd = RegisterQRMenuRequest(
            business_id=BIZ, branch_id=BRANCH,
            place_qr_id="p-svc-1", place_type="TABLE", place_label="Table 5",
            actor_id="mgr", issued_at=NOW,
        ).to_command()
        result = svc._execute_command(cmd_ns(cmd))
        assert result["event_type"] == QR_MENU_REGISTERED_V1
        assert svc._projection.get_place("p-svc-1") is not None

    def test_full_accept_flow(self):
        from engines.qr_menu import (
            RegisterQRMenuRequest, CreateSessionRequest, OrderItemRequest,
            SubmitOrderRequest, AcceptQROrderRequest, QR_MENU_ORDER_ACCEPTED_V1
        )
        svc = self._svc()
        svc._execute_command(cmd_ns(RegisterQRMenuRequest(
            business_id=BIZ, branch_id=BRANCH,
            place_qr_id="p1", place_type="TABLE", place_label="Table 3",
            actor_id="mgr", issued_at=NOW,
        ).to_command()))
        svc._execute_command(cmd_ns(CreateSessionRequest(
            business_id=BIZ, branch_id=BRANCH,
            session_id="sess-flow-1", place_qr_id="p1",
            session_token="tok-flow", expires_at="2026-02-25T10:00:00",
            actor_id="sys", issued_at=NOW,
        ).to_command()))
        assert svc._projection.get_session("sess-flow-1")["status"] == "ACTIVE"

        svc._execute_command(cmd_ns(OrderItemRequest(
            business_id=BIZ, branch_id=BRANCH,
            session_id="sess-flow-1", order_line_id="ol-1",
            item_id="m1", item_name="Nyama Choma", quantity=1, unit_price=2500,
            actor_id="sys", issued_at=NOW,
        ).to_command()))
        svc._execute_command(cmd_ns(SubmitOrderRequest(
            business_id=BIZ, branch_id=BRANCH,
            session_id="sess-flow-1", actor_id="sys", issued_at=NOW,
        ).to_command()))
        assert svc._projection.get_session("sess-flow-1")["status"] == "PENDING_CONFIRM"

        result = svc._execute_command(cmd_ns(AcceptQROrderRequest(
            business_id=BIZ, branch_id=BRANCH,
            session_id="sess-flow-1", restaurant_order_id="ro-1",
            actor_id="waiter-1", issued_at=NOW,
        ).to_command()))
        assert result["event_type"] == QR_MENU_ORDER_ACCEPTED_V1
        assert svc._projection.get_session("sess-flow-1")["status"] == "ACCEPTED"

    def test_reject_flow(self):
        from engines.qr_menu import (
            RegisterQRMenuRequest, CreateSessionRequest, OrderItemRequest,
            SubmitOrderRequest, RejectQROrderRequest, QR_MENU_ORDER_REJECTED_V1
        )
        svc = self._svc()
        svc._execute_command(cmd_ns(RegisterQRMenuRequest(
            business_id=BIZ, branch_id=BRANCH,
            place_qr_id="p2", place_type="ROOM", place_label="Room 12",
            actor_id="mgr", issued_at=NOW,
        ).to_command()))
        svc._execute_command(cmd_ns(CreateSessionRequest(
            business_id=BIZ, branch_id=BRANCH,
            session_id="sess-rej", place_qr_id="p2",
            session_token="tok-rej", expires_at="2026-02-25T10:00:00",
            actor_id="sys", issued_at=NOW,
        ).to_command()))
        svc._execute_command(cmd_ns(OrderItemRequest(
            business_id=BIZ, branch_id=BRANCH,
            session_id="sess-rej", order_line_id="ol-1",
            item_id="m1", item_name="Burger", quantity=1, unit_price=500,
            actor_id="sys", issued_at=NOW,
        ).to_command()))
        svc._execute_command(cmd_ns(SubmitOrderRequest(
            business_id=BIZ, branch_id=BRANCH,
            session_id="sess-rej", actor_id="sys", issued_at=NOW,
        ).to_command()))
        result = svc._execute_command(cmd_ns(RejectQROrderRequest(
            business_id=BIZ, branch_id=BRANCH,
            session_id="sess-rej", reason="ITEM_UNAVAILABLE",
            actor_id="waiter-1", issued_at=NOW,
        ).to_command()))
        assert result["event_type"] == QR_MENU_ORDER_REJECTED_V1
        assert svc._projection.get_session("sess-rej")["status"] == "REJECTED"
