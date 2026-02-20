"""
BOS Promotion Engine — Policies
"""

from __future__ import annotations

from typing import Optional

from core.commands.base import Command
from core.commands.rejection import RejectionReason


def campaign_must_be_active_for_coupon_policy(
    command: Command, campaign_lookup=None,
) -> Optional[RejectionReason]:
    if campaign_lookup is None:
        return None
    if command.command_type != "promotion.coupon.issue.request":
        return None
    cid = command.payload.get("campaign_id")
    campaign = campaign_lookup(cid)
    if campaign is None:
        return RejectionReason(
            code="CAMPAIGN_NOT_FOUND", message=f"Campaign '{cid}' not found.",
            policy_name="campaign_must_be_active_for_coupon_policy")
    if campaign.get("status") != "ACTIVE":
        return RejectionReason(
            code="CAMPAIGN_NOT_ACTIVE",
            message=f"Campaign '{cid}' is {campaign.get('status')}.",
            policy_name="campaign_must_be_active_for_coupon_policy")
    return None


def coupon_must_be_issued_for_redeem_policy(
    command: Command, coupon_lookup=None,
) -> Optional[RejectionReason]:
    if coupon_lookup is None:
        return None
    if command.command_type != "promotion.coupon.redeem.request":
        return None
    cid = command.payload.get("coupon_id")
    coupon = coupon_lookup(cid)
    if coupon is None:
        return RejectionReason(
            code="COUPON_NOT_FOUND", message=f"Coupon '{cid}' not found.",
            policy_name="coupon_must_be_issued_for_redeem_policy")
    if coupon.get("status") != "ISSUED":
        return RejectionReason(
            code="COUPON_NOT_ISSUED",
            message=f"Coupon '{cid}' is {coupon.get('status')}.",
            policy_name="coupon_must_be_issued_for_redeem_policy")
    return None
