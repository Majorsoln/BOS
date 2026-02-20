"""
BOS Promotion Engine — Request Commands
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.commands.base import Command
from core.context.scope import SCOPE_BUSINESS_ALLOWED
from core.identity.requirements import ACTOR_REQUIRED

PROMOTION_CAMPAIGN_CREATE_REQUEST = "promotion.campaign.create.request"
PROMOTION_CAMPAIGN_ACTIVATE_REQUEST = "promotion.campaign.activate.request"
PROMOTION_CAMPAIGN_DEACTIVATE_REQUEST = "promotion.campaign.deactivate.request"
PROMOTION_COUPON_ISSUE_REQUEST = "promotion.coupon.issue.request"
PROMOTION_COUPON_REDEEM_REQUEST = "promotion.coupon.redeem.request"

PROMOTION_COMMAND_TYPES = frozenset({
    PROMOTION_CAMPAIGN_CREATE_REQUEST,
    PROMOTION_CAMPAIGN_ACTIVATE_REQUEST,
    PROMOTION_CAMPAIGN_DEACTIVATE_REQUEST,
    PROMOTION_COUPON_ISSUE_REQUEST,
    PROMOTION_COUPON_REDEEM_REQUEST,
})

VALID_CAMPAIGN_TYPES = frozenset({"SEASONAL", "LOYALTY", "CLEARANCE", "FLASH_SALE"})
VALID_DISCOUNT_TYPES = frozenset({"PERCENTAGE", "FIXED_AMOUNT", "BUY_X_GET_Y"})


def _cmd(ct, payload, *, business_id, actor_type, actor_id,
         command_id, correlation_id, issued_at, branch_id=None):
    return Command(
        command_id=command_id, command_type=ct,
        business_id=business_id, branch_id=branch_id,
        actor_type=actor_type, actor_id=actor_id,
        payload=payload, issued_at=issued_at,
        correlation_id=correlation_id, source_engine="promotion",
        scope_requirement=SCOPE_BUSINESS_ALLOWED,
        actor_requirement=ACTOR_REQUIRED,
    )


@dataclass(frozen=True)
class CampaignCreateRequest:
    campaign_id: str
    name: str
    campaign_type: str
    discount_type: str
    discount_value: int
    start_date: str
    end_date: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty.")
        if not self.name:
            raise ValueError("name must be non-empty.")
        if self.campaign_type not in VALID_CAMPAIGN_TYPES:
            raise ValueError(f"campaign_type '{self.campaign_type}' not valid.")
        if self.discount_type not in VALID_DISCOUNT_TYPES:
            raise ValueError(f"discount_type '{self.discount_type}' not valid.")
        if not isinstance(self.discount_value, int) or self.discount_value <= 0:
            raise ValueError("discount_value must be positive integer.")

    def to_command(self, **kw) -> Command:
        return _cmd(PROMOTION_CAMPAIGN_CREATE_REQUEST, {
            "campaign_id": self.campaign_id, "name": self.name,
            "campaign_type": self.campaign_type, "discount_type": self.discount_type,
            "discount_value": self.discount_value,
            "start_date": self.start_date, "end_date": self.end_date,
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class CampaignActivateRequest:
    campaign_id: str
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty.")

    def to_command(self, **kw) -> Command:
        return _cmd(PROMOTION_CAMPAIGN_ACTIVATE_REQUEST,
                     {"campaign_id": self.campaign_id},
                     branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class CampaignDeactivateRequest:
    campaign_id: str
    reason: str = ""
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty.")

    def to_command(self, **kw) -> Command:
        return _cmd(PROMOTION_CAMPAIGN_DEACTIVATE_REQUEST,
                     {"campaign_id": self.campaign_id, "reason": self.reason},
                     branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class CouponIssueRequest:
    coupon_id: str
    campaign_id: str
    customer_id: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.coupon_id:
            raise ValueError("coupon_id must be non-empty.")
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty.")

    def to_command(self, **kw) -> Command:
        return _cmd(PROMOTION_COUPON_ISSUE_REQUEST, {
            "coupon_id": self.coupon_id, "campaign_id": self.campaign_id,
            "customer_id": self.customer_id,
        }, branch_id=self.branch_id, **kw)


@dataclass(frozen=True)
class CouponRedeemRequest:
    coupon_id: str
    sale_id: str
    discount_applied: int
    branch_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        if not self.coupon_id:
            raise ValueError("coupon_id must be non-empty.")
        if not self.sale_id:
            raise ValueError("sale_id must be non-empty.")
        if not isinstance(self.discount_applied, int) or self.discount_applied <= 0:
            raise ValueError("discount_applied must be positive integer.")

    def to_command(self, **kw) -> Command:
        return _cmd(PROMOTION_COUPON_REDEEM_REQUEST, {
            "coupon_id": self.coupon_id, "sale_id": self.sale_id,
            "discount_applied": self.discount_applied,
        }, branch_id=self.branch_id, **kw)
