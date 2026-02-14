"""
BOS Context â€” Public API
=========================
Canonical tenant context and scope constants.
"""

from core.context.actor_context import ActorContext
from core.context.business_context import BusinessContext
from core.context.scope import (
    SCOPE_BRANCH_REQUIRED,
    SCOPE_BUSINESS_ALLOWED,
)

__all__ = [
    "ActorContext",
    "BusinessContext",
    "SCOPE_BUSINESS_ALLOWED",
    "SCOPE_BRANCH_REQUIRED",
]
