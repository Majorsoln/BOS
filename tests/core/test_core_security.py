"""
Tests for core.security — Access control and rate limiting (Phase 8 stubs).
"""

import uuid

from core.security.access import Permission, AccessDecision, check_access
from core.security.ratelimit import RateLimiter, RateLimitResult


BIZ_ID = uuid.uuid4()
BRANCH_ID = uuid.uuid4()


# ── Permission Tests ─────────────────────────────────────────

class TestPermission:
    def test_permission_constants_exist(self):
        assert Permission.CASH_CASHIN_CREATE == "cash.cashin.create"
        assert Permission.INVENTORY_ADJUST == "inventory.stock.adjust"
        assert Permission.RETAIL_SALE_CREATE == "retail.sale.create"
        assert Permission.HR_PAYROLL_RUN == "hr.payroll.run"
        assert Permission.ACCOUNTING_JOURNAL_POST == "accounting.journal.post"


# ── Access Decision Tests ────────────────────────────────────

class TestAccessDecision:
    def test_granted_decision(self):
        decision = AccessDecision(
            actor_id="user-1",
            permission=Permission.CASH_CASHIN_CREATE,
            business_id=BIZ_ID,
            branch_id=BRANCH_ID,
            granted=True,
        )
        assert decision.granted

    def test_denied_decision(self):
        decision = AccessDecision(
            actor_id="user-1",
            permission=Permission.ACCOUNTING_PERIOD_CLOSE,
            business_id=BIZ_ID,
            branch_id=None,
            granted=False,
            reason="Insufficient role",
        )
        assert not decision.granted
        assert decision.reason == "Insufficient role"


class TestCheckAccess:
    def test_stub_always_grants(self):
        """Phase 8 stub: permissive default."""
        result = check_access(
            actor_id="user-1",
            permission=Permission.CASH_CASHIN_CREATE,
            business_id=BIZ_ID,
            branch_id=BRANCH_ID,
        )
        assert result.granted
        assert "stub" in result.reason.lower()

    def test_stub_without_branch(self):
        result = check_access(
            actor_id="user-1",
            permission=Permission.REPORTING_QUERY,
            business_id=BIZ_ID,
        )
        assert result.granted
        assert result.branch_id is None


# ── Rate Limiter Tests ───────────────────────────────────────

class TestRateLimiter:
    def test_stub_always_allows(self):
        """Phase 8 stub: always allows."""
        limiter = RateLimiter(max_per_minute=60)
        result = limiter.check(actor_id="user-1", business_id=BIZ_ID)
        assert result.allowed
        assert result.remaining == 60
        assert result.limit == 60

    def test_custom_limit(self):
        limiter = RateLimiter(max_per_minute=100)
        result = limiter.check(actor_id="user-1", business_id=BIZ_ID)
        assert result.limit == 100
