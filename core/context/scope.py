"""
BOS Context â€” Scope Constants
==============================
Scope requirements are command-owned.
"""

SCOPE_BUSINESS_ALLOWED = "SCOPE_BUSINESS_ALLOWED"
SCOPE_BRANCH_REQUIRED = "SCOPE_BRANCH_REQUIRED"

VALID_SCOPE_REQUIREMENTS = frozenset(
    {SCOPE_BUSINESS_ALLOWED, SCOPE_BRANCH_REQUIRED}
)

