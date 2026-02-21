"""
Tests for core.business — Business/branch lifecycle and policies.
"""

import uuid
import pytest
from datetime import datetime, timezone

from core.business.models import Business, BusinessState, Branch
from core.business.policies import (
    validate_business_active,
    validate_branch_open,
    validate_branch_ownership,
)


BIZ_ID = uuid.uuid4()
BRANCH_ID = uuid.uuid4()
NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


# ── Business Model Tests ─────────────────────────────────────

class TestBusiness:
    def test_active_business(self):
        biz = Business(
            business_id=BIZ_ID,
            name="Test Corp",
            state=BusinessState.ACTIVE,
            country_code="KE",
            timezone="Africa/Nairobi",
            created_at=NOW,
        )
        assert biz.is_active()
        assert biz.is_operational()

    def test_created_business_is_operational(self):
        biz = Business(
            business_id=BIZ_ID,
            name="New Corp",
            state=BusinessState.CREATED,
            country_code="KE",
            timezone="Africa/Nairobi",
            created_at=NOW,
        )
        assert not biz.is_active()
        assert biz.is_operational()

    def test_suspended_business(self):
        biz = Business(
            business_id=BIZ_ID,
            name="Suspended Corp",
            state=BusinessState.SUSPENDED,
            country_code="KE",
            timezone="Africa/Nairobi",
            created_at=NOW,
        )
        assert not biz.is_active()
        assert not biz.is_operational()

    def test_closed_business(self):
        biz = Business(
            business_id=BIZ_ID,
            name="Closed Corp",
            state=BusinessState.CLOSED,
            country_code="KE",
            timezone="Africa/Nairobi",
            created_at=NOW,
            closed_at=NOW,
        )
        assert not biz.is_active()
        assert not biz.is_operational()

    def test_frozen_immutability(self):
        biz = Business(
            business_id=BIZ_ID,
            name="Test Corp",
            state=BusinessState.ACTIVE,
            country_code="KE",
            timezone="Africa/Nairobi",
            created_at=NOW,
        )
        with pytest.raises(AttributeError):
            biz.state = BusinessState.CLOSED


# ── Branch Model Tests ───────────────────────────────────────

class TestBranch:
    def test_open_branch(self):
        branch = Branch(
            branch_id=BRANCH_ID,
            business_id=BIZ_ID,
            name="Downtown",
            created_at=NOW,
            location="Nairobi CBD",
        )
        assert branch.is_open()
        assert branch.belongs_to(BIZ_ID)

    def test_closed_branch(self):
        branch = Branch(
            branch_id=BRANCH_ID,
            business_id=BIZ_ID,
            name="Old Branch",
            created_at=NOW,
            closed_at=NOW,
        )
        assert not branch.is_open()

    def test_branch_ownership(self):
        other_biz = uuid.uuid4()
        branch = Branch(
            branch_id=BRANCH_ID,
            business_id=BIZ_ID,
            name="Downtown",
            created_at=NOW,
        )
        assert branch.belongs_to(BIZ_ID)
        assert not branch.belongs_to(other_biz)


# ── Policy Tests ─────────────────────────────────────────────

class TestBusinessPolicies:
    def test_active_business_passes(self):
        biz = Business(
            business_id=BIZ_ID,
            name="OK Corp",
            state=BusinessState.ACTIVE,
            country_code="KE",
            timezone="Africa/Nairobi",
            created_at=NOW,
        )
        assert validate_business_active(biz) is None

    def test_suspended_business_rejected(self):
        biz = Business(
            business_id=BIZ_ID,
            name="Bad Corp",
            state=BusinessState.SUSPENDED,
            country_code="KE",
            timezone="Africa/Nairobi",
            created_at=NOW,
        )
        reason = validate_business_active(biz)
        assert reason is not None
        assert reason.code == "BUSINESS_SUSPENDED"

    def test_closed_business_rejected(self):
        biz = Business(
            business_id=BIZ_ID,
            name="Dead Corp",
            state=BusinessState.CLOSED,
            country_code="KE",
            timezone="Africa/Nairobi",
            created_at=NOW,
        )
        reason = validate_business_active(biz)
        assert reason is not None
        assert reason.code == "BUSINESS_CLOSED"


class TestBranchPolicies:
    def test_open_branch_passes(self):
        branch = Branch(
            branch_id=BRANCH_ID,
            business_id=BIZ_ID,
            name="Open",
            created_at=NOW,
        )
        assert validate_branch_open(branch) is None

    def test_closed_branch_rejected(self):
        branch = Branch(
            branch_id=BRANCH_ID,
            business_id=BIZ_ID,
            name="Closed",
            created_at=NOW,
            closed_at=NOW,
        )
        reason = validate_branch_open(branch)
        assert reason is not None

    def test_ownership_passes(self):
        branch = Branch(
            branch_id=BRANCH_ID,
            business_id=BIZ_ID,
            name="Mine",
            created_at=NOW,
        )
        assert validate_branch_ownership(branch, BIZ_ID) is None

    def test_ownership_fails(self):
        branch = Branch(
            branch_id=BRANCH_ID,
            business_id=BIZ_ID,
            name="Mine",
            created_at=NOW,
        )
        reason = validate_branch_ownership(branch, uuid.uuid4())
        assert reason is not None
        assert reason.code == "BRANCH_NOT_IN_BUSINESS"
