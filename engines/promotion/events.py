"""
BOS Promotion Engine — Event Types and Payload Builders
=========================================================
Engine: Promotion (Campaigns, Discounts, Loyalty)
"""

from __future__ import annotations

from core.commands.base import Command

PROMOTION_CAMPAIGN_CREATED_V1 = "promotion.campaign.created.v1"
PROMOTION_CAMPAIGN_ACTIVATED_V1 = "promotion.campaign.activated.v1"
PROMOTION_CAMPAIGN_DEACTIVATED_V1 = "promotion.campaign.deactivated.v1"
PROMOTION_COUPON_ISSUED_V1 = "promotion.coupon.issued.v1"
PROMOTION_COUPON_REDEEMED_V1 = "promotion.coupon.redeemed.v1"

PROMOTION_EVENT_TYPES = (
    PROMOTION_CAMPAIGN_CREATED_V1,
    PROMOTION_CAMPAIGN_ACTIVATED_V1,
    PROMOTION_CAMPAIGN_DEACTIVATED_V1,
    PROMOTION_COUPON_ISSUED_V1,
    PROMOTION_COUPON_REDEEMED_V1,
)

COMMAND_TO_EVENT_TYPE = {
    "promotion.campaign.create.request": PROMOTION_CAMPAIGN_CREATED_V1,
    "promotion.campaign.activate.request": PROMOTION_CAMPAIGN_ACTIVATED_V1,
    "promotion.campaign.deactivate.request": PROMOTION_CAMPAIGN_DEACTIVATED_V1,
    "promotion.coupon.issue.request": PROMOTION_COUPON_ISSUED_V1,
    "promotion.coupon.redeem.request": PROMOTION_COUPON_REDEEMED_V1,
}


def resolve_promotion_event_type(command_type: str) -> str | None:
    return COMMAND_TO_EVENT_TYPE.get(command_type)


def register_promotion_event_types(event_type_registry) -> None:
    for et in sorted(PROMOTION_EVENT_TYPES):
        event_type_registry.register(et)


def _base_payload(command: Command) -> dict:
    return {
        "business_id": command.business_id, "branch_id": command.branch_id,
        "actor_id": command.actor_id, "actor_type": command.actor_type,
        "correlation_id": command.correlation_id, "command_id": command.command_id,
    }


def build_campaign_created_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "campaign_id": command.payload["campaign_id"],
        "name": command.payload["name"],
        "campaign_type": command.payload["campaign_type"],
        "discount_type": command.payload["discount_type"],
        "discount_value": command.payload["discount_value"],
        "start_date": command.payload["start_date"],
        "end_date": command.payload["end_date"],
        "created_at": command.issued_at,
    })
    return p


def build_campaign_activated_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({"campaign_id": command.payload["campaign_id"], "activated_at": command.issued_at})
    return p


def build_campaign_deactivated_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "campaign_id": command.payload["campaign_id"],
        "reason": command.payload.get("reason", ""),
        "deactivated_at": command.issued_at,
    })
    return p


def build_coupon_issued_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "coupon_id": command.payload["coupon_id"],
        "campaign_id": command.payload["campaign_id"],
        "customer_id": command.payload.get("customer_id"),
        "issued_at": command.issued_at,
    })
    return p


def build_coupon_redeemed_payload(command: Command) -> dict:
    p = _base_payload(command)
    p.update({
        "coupon_id": command.payload["coupon_id"],
        "sale_id": command.payload["sale_id"],
        "discount_applied": command.payload["discount_applied"],
        "redeemed_at": command.issued_at,
    })
    return p
