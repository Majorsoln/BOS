"""
BOS Event Store — Hash-Chain Errors
=====================================
Rejection codes for hash-chain integrity violations.
"""


class HashRejectionCode:
    """Rejection codes for hash-chain failures."""

    HASH_CHAIN_BROKEN = "HASH_CHAIN_BROKEN"
    HASH_COMPUTATION_MISMATCH = "HASH_COMPUTATION_MISMATCH"


class HashViolatedRule:
    """Rule identifiers for audit trail."""

    EVENT_HASH_CHAIN = "EVENT_HASH_CHAIN"
