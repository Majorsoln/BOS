"""
BOS Customer Engine — Policies
==============================
Consent-based access control for customer data.
"""

from typing import Optional

from core.commands.rejection import RejectionReason


def customer_must_exist_policy(
    command,
    customer_lookup=None,
) -> Optional[RejectionReason]:
    """Customer must exist in platform registry before link operations."""
    if customer_lookup is None:
        return None
    gcid = command.payload.get("global_customer_id")
    if gcid and customer_lookup(gcid) is None:
        return RejectionReason(
            code="CUSTOMER_NOT_FOUND",
            message=f"Global customer '{gcid}' not found in platform registry.",
            policy_name="customer_must_exist_policy",
        )
    return None


def link_must_be_pending_policy(
    command,
    link_lookup=None,
) -> Optional[RejectionReason]:
    """Link must be PENDING before it can be approved."""
    if link_lookup is None:
        return None
    gcid = command.payload.get("global_customer_id")
    biz = command.payload.get("approved_business_id")
    if gcid and biz:
        link = link_lookup(gcid, biz)
        if link is None:
            return RejectionReason(
                code="LINK_NOT_FOUND",
                message=f"No pending link request from business '{biz}'.",
                policy_name="link_must_be_pending_policy",
            )
        if link.status != "PENDING":
            return RejectionReason(
                code="LINK_NOT_PENDING",
                message=f"Link is '{link.status}', expected PENDING.",
                policy_name="link_must_be_pending_policy",
            )
    return None


def link_must_be_approved_policy(
    command,
    link_lookup=None,
) -> Optional[RejectionReason]:
    """Link must be APPROVED for scope updates and profile operations."""
    if link_lookup is None:
        return None
    gcid = command.payload.get("global_customer_id")
    biz = command.payload.get("target_business_id") or command.payload.get("revoked_business_id")
    if gcid and biz:
        link = link_lookup(gcid, biz)
        if link is None:
            return RejectionReason(
                code="LINK_NOT_FOUND",
                message=f"No link between customer and business '{biz}'.",
                policy_name="link_must_be_approved_policy",
            )
        if link.status != "APPROVED":
            return RejectionReason(
                code="LINK_NOT_APPROVED",
                message=f"Link is '{link.status}', must be APPROVED.",
                policy_name="link_must_be_approved_policy",
            )
    return None


def phone_hash_must_be_unique_policy(
    command,
    phone_lookup=None,
) -> Optional[RejectionReason]:
    """Phone hash must not already exist in platform registry."""
    if phone_lookup is None:
        return None
    phone_hash = command.payload.get("phone_hash")
    if phone_hash and phone_lookup(phone_hash) is not None:
        return RejectionReason(
            code="PHONE_ALREADY_REGISTERED",
            message="This phone number is already registered.",
            policy_name="phone_hash_must_be_unique_policy",
        )
    return None


def consent_scope_required_policy(
    command,
    link_lookup=None,
    required_scope: str = "",
) -> Optional[RejectionReason]:
    """Business must have consent for the required scope to access customer data."""
    if link_lookup is None or not required_scope:
        return None
    gcid = command.payload.get("global_customer_id")
    biz = str(command.business_id) if hasattr(command, "business_id") else None
    if gcid and biz:
        link = link_lookup(gcid, biz)
        if link is None or link.status != "APPROVED":
            return RejectionReason(
                code="NO_CONSENT",
                message=f"No approved link with customer '{gcid}'.",
                policy_name="consent_scope_required_policy",
            )
        if required_scope not in link.approved_scopes:
            return RejectionReason(
                code="SCOPE_NOT_CONSENTED",
                message=f"Scope '{required_scope}' not consented by customer.",
                policy_name="consent_scope_required_policy",
            )
    return None
