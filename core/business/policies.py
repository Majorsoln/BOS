"""
BOS Core Business — Lifecycle Policies
=========================================
Pure validation functions for business/branch lifecycle.
Return RejectionReason on failure, None on success.
"""

from __future__ import annotations

import uuid
from typing import Optional

from core.business.models import Branch, Business, BusinessState
from core.commands.rejection import RejectionReason, ReasonCode


# ══════════════════════════════════════════════════════════════
# BUSINESS POLICIES
# ══════════════════════════════════════════════════════════════

def validate_business_active(business: Business) -> Optional[RejectionReason]:
    """Reject commands if business is not ACTIVE."""
    if business.state == BusinessState.SUSPENDED:
        return RejectionReason(
            code=ReasonCode.BUSINESS_SUSPENDED,
            message=f"Business {business.business_id} is suspended.",
            policy_name="validate_business_active",
        )
    if business.state == BusinessState.CLOSED:
        return RejectionReason(
            code=ReasonCode.BUSINESS_CLOSED,
            message=f"Business {business.business_id} is closed.",
            policy_name="validate_business_active",
        )
    if not business.is_operational():
        return RejectionReason(
            code=ReasonCode.BUSINESS_SUSPENDED,
            message=f"Business {business.business_id} is in state {business.state.value}.",
            policy_name="validate_business_active",
        )
    return None


# ══════════════════════════════════════════════════════════════
# BRANCH POLICIES
# ══════════════════════════════════════════════════════════════

def validate_branch_open(branch: Branch) -> Optional[RejectionReason]:
    """Reject if branch is closed."""
    if not branch.is_open():
        return RejectionReason(
            code=ReasonCode.BRANCH_NOT_IN_BUSINESS,
            message=f"Branch {branch.branch_id} is closed.",
            policy_name="validate_branch_open",
        )
    return None


def validate_branch_ownership(
    branch: Branch, business_id: uuid.UUID
) -> Optional[RejectionReason]:
    """Reject if branch does not belong to the business."""
    if not branch.belongs_to(business_id):
        return RejectionReason(
            code=ReasonCode.BRANCH_NOT_IN_BUSINESS,
            message=f"Branch {branch.branch_id} does not belong to business {business_id}.",
            policy_name="validate_branch_ownership",
        )
    return None
