"""
BOS Identity - Actor Requirement Constants
==========================================
Actor requirement is command-owned.
"""

ACTOR_REQUIRED = "ACTOR_REQUIRED"
SYSTEM_ALLOWED = "SYSTEM_ALLOWED"

VALID_ACTOR_REQUIREMENTS = frozenset(
    {ACTOR_REQUIRED, SYSTEM_ALLOWED}
)

